import test from "node:test";
import assert from "node:assert/strict";
import { handleRequest } from "../src/worker.mjs";

// Minimal D1 SQL adapter: validates prepared statements and their bound values.
// It intentionally exposes NO R2 interface.
function make() {
  const visa = new Map(), airports = new Map();
  let ticket = null;
  const statement = (sql, params = []) => ({
    kind: sql,
    params,
    bind(...values) { return statement(sql, values); },
    async first() {
      if (sql.includes("FROM ticket_price_snapshots")) return ticket ? { ...ticket } : null;
      if (sql.includes("FROM visa_rules")) return visa.get(params.join(":")) || null;
      throw Error("Unknown SELECT first: " + sql);
    },
    async all() {
      if (sql.includes("FROM airports")) return { results: [...airports.values()] };
      if (sql.includes("FROM visa_rules")) {
        return { results: [...visa.values()].filter(row => row.passport === params[0]) };
      }
      throw Error("Unknown SELECT all: " + sql);
    },
    async run() {
      if (!sql.includes("INSERT INTO ticket_price_snapshots")) throw Error("Unknown D1 run");
      const [observed_epoch_ms, snapshot_json, published_at] = params;
      assert.equal(typeof snapshot_json, "string");
      assert.ok(snapshot_json.length < 1_500_000);
      if (ticket && ticket.observed_epoch_ms > observed_epoch_ms) return { meta: { changes: 0 } };
      ticket = { observed_epoch_ms, snapshot_json, published_at };
      return { meta: { changes: 1 } };
    }
  });
  const db = {
    prepare(sql) { return statement(sql); },
    async batch(statements) {
      assert.ok(statements.length <= 50, "D1 Free query count");
      for (const stmt of statements)
        assert.ok(stmt.params.length <= 100, "D1 parameter count");
      const visaImport = statements[0].kind.includes("visa_rules");
      if (visaImport) {
        const destination = statements[0].params[0];
        for (const key of visa.keys()) if (key.endsWith(":" + destination)) visa.delete(key);
        for (const stmt of statements.slice(1)) {
          const p = stmt.params;
          for (let i=0;i<p.length;i+=10) visa.set(p[i] + ":" + p[i+1], {
            passport:p[i], destination:p[i+1], country_name:p[i+2], status:p[i+3],
            stay_days:p[i+4], notes:p[i+5], source_url:p[i+6],
            verified_on:p[i+7], source_level:p[i+8], published_at:p[i+9]
          });
        }
      } else {
        airports.clear();
        for (const stmt of statements.slice(1)) {
          const p = stmt.params;
          for (let i=0;i<p.length;i+=4) airports.set(p[i], {
            code:p[i], name:p[i+1], country:p[i+2], timezone:p[i+3]
          });
        }
      }
    }
  };
  return { PUBLIC_DB: db, PUBLISH_TOKEN: "x".repeat(48) };
}

const req = (path, { method = "GET", auth = false, data } = {}) =>
  new Request("https://example.workers.dev" + path, {
    method,
    headers: auth ? {
      Authorization: "Bearer " + "x".repeat(48),
      "Content-Type": "application/json"
    } : {},
    body: data === undefined ? undefined : JSON.stringify(data)
  });
const price = (observed_at = new Date().toISOString()) => ({
  currency:"TOMAN", observed_at, stale:false,
  routes:[{origin:"تهران",destinations:[{
    name:"کیش",price_toman:4200000,average_price_toman:5000000.5,
    average_sample_count:5
  }]}]
});
const GET_PRICE = "/api/v1/tickets/prices";
const POST_PRICE = "/internal/v1/tickets/prices";
const uploadPrice = (env, data) => handleRequest(req(POST_PRICE, {
  method:"POST", auth:true, data
}), env);

test("tickets live entirely in D1 and never expose private payload fields", async () => {
  const env = make();
  assert.ok(!("PUBLIC_SNAPSHOTS" in env));
  assert.equal((await handleRequest(req(GET_PRICE),env)).status,503);
  assert.equal((await handleRequest(req(POST_PRICE,{ method:"POST",data:price() }),env)).status,401);
  assert.equal((await uploadPrice(env,{...price(), user_id:54, telegram_token:"secret"})).status,200);
  const response = await handleRequest(req(GET_PRICE),env);
  assert.equal(response.status,200);
  assert.equal(response.headers.get("cache-control"),"public, max-age=60");
  const data = await response.json();
  assert.equal(data.routes[0].destinations[0].average_price_toman,5000000.5);
  assert.equal(data.routes[0].destinations[0].price_toman,4200000);
  assert.equal(data.routes[0].destinations[0].change_percent,-16);
  assert.equal("user_id" in data,false);
  assert.ok(!JSON.stringify(data).includes("telegram_token"));
});

test("D1 price updates replace exactly one batch without growing a history table", async () => {
  const env=make();
  const first=new Date(Date.now()-60_000).toISOString();
  const later=new Date().toISOString();
  assert.equal((await uploadPrice(env,price(first))).status,200);
  assert.equal((await uploadPrice(env,{...price(later),routes:[
    {origin:"تهران",destinations:[{name:"مشهد",price_toman:700000,
      average_price_toman:null,average_sample_count:0}]}
  ]})).status,200);
  const data=await (await handleRequest(req(GET_PRICE),env)).json();
  assert.equal(data.observed_at,later);
  assert.equal(data.routes[0].destinations.length,1);
  assert.equal(data.routes[0].destinations[0].name,"مشهد");
});

test("D1 conditional upsert prevents older writes after newer batch", async()=>{
  const env=make();
  const recent=new Date().toISOString();
  const older=new Date(Date.now()-5*3600_000).toISOString();
  assert.equal((await uploadPrice(env,price(recent))).status,200);
  assert.equal((await uploadPrice(env,price(older))).status,409);
  assert.equal((await (await handleRequest(req(GET_PRICE),env)).json()).observed_at,recent);
});

test("price age is evaluated on every GET even when imports stop",async()=>{
  const env=make();
  const fourHoursAgo=new Date(Date.now()-4*3600_000).toISOString();
  assert.equal((await uploadPrice(env,price(fourHoursAgo))).status,200);
  const rsp=await handleRequest(req(GET_PRICE),env);
  assert.equal((await rsp.json()).stale,true);
  assert.equal(rsp.headers.get("cache-control"),"public, max-age=0");
});

test("invalid currency, timestamps, missing booleans, and lost D1 fail closed",async()=>{
  const env=make();
  for(const data of [
    {...price(),currency:"USD"}, {...price(),observed_at:"garbage"},
    {...price(),stale:"no"}, {...price(),stale:undefined},
    {...price(),routes:[{origin:"تهران",destinations:[]}]}
  ]) assert.equal((await uploadPrice(env,data)).status,422);
  assert.equal((await uploadPrice({ PUBLIC_DB: env.PUBLIC_DB, PUBLISH_TOKEN:"" },price())).status,401);
  assert.equal((await uploadPrice({ PUBLISH_TOKEN:env.PUBLISH_TOKEN },price())).status,503);
  assert.equal((await handleRequest(req(GET_PRICE),{ PUBLISH_TOKEN:env.PUBLISH_TOKEN })).status,503);
});

const passports = Array.from({length:190},(_,i)=>
  String.fromCharCode(65+Math.floor(i/26),65+i%26));
const visaRule = passport => ({
  passport, country_name:"ترکیه",status:"visa-free",stay_days:90,
  notes:null,source_url:"https://example.org/rules",
  verified_on:"2026-10-11",source_level:"official"
});

test("D1 visa and airports preserve API behavior and reject partial replacements",async()=>{
  const env=make();
  const visa = {destination:"TR",rules:passports.map(visaRule)};
  assert.equal((await handleRequest(req("/internal/v1/visa/destination/TR",{
    method:"POST",auth:true,data:visa
  }),env)).status,200);
  const rule=await (await handleRequest(req("/api/v1/visa/rule?passport=AA&destination=TR"),env)).json();
  assert.equal(rule.status,"visa-free");
  assert.equal((await handleRequest(req("/api/v1/visa/list?passport=AA"),env)).status,200);
  assert.equal((await handleRequest(req("/internal/v1/visa/destination/TR",{
    method:"POST",auth:true,data:{destination:"TR",rules:[visaRule("IR")]}
  }),env)).status,422);
  assert.equal((await handleRequest(req("/api/v1/visa/rule?passport=AA&destination=TR"),env)).status,200);
  assert.equal((await handleRequest(req("/internal/v1/airports",{
    method:"POST",auth:true,data:{airports:[
      {code:"IKA",name:"فرودگاه امام",country:"IR",timezone:"Asia/Tehran"}
    ]}
  }),env)).status,200);
  assert.equal((await (await handleRequest(req("/api/v1/airports"),env)).json()).airports[0].code,"IKA");
});

test("D1 import of 190 visa records stays within parameter/statement limits",async()=>{
  const env=make();
  const response=await handleRequest(req("/internal/v1/visa/destination/TR",{
    method:"POST",auth:true,data:{destination:"TR",rules:passports.map(visaRule)}
  }),env);
  assert.equal(response.status,200);
  assert.equal((await response.json()).rules,190);
  assert.equal((await handleRequest(req("/api/v1/visa/rule?passport=HH&destination=TR"),env)).status,200);
});

test("public API is GET-only and arbitrary endpoints cannot expose SQLite",async()=>{
  const env=make();
  assert.equal((await handleRequest(req("/internal/v1/airports"),env)).status,405);
  assert.equal((await handleRequest(req("/internal/v1/nope",{
    method:"POST",auth:true,data:{}
  }),env)).status,404);
  assert.equal((await handleRequest(req("/api/v1/users"),env)).status,404);
  assert.equal((await handleRequest(req("/api/v1/visa/list?passport=INVALID"),env)).status,400);
});
