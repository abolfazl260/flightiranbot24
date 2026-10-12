import test from "node:test";
import assert from "node:assert/strict";
import { handleRequest } from "../src/worker.mjs";

function make() {
  const objects = new Map(), visa = new Map(), airports = new Map();
  const snapshots = {
    async get(k) { return objects.has(k) ? { text: async () => objects.get(k) } : null; },
    async put(k, v) { objects.set(k, v); }
  };
  const db = {
    prepare(sql) {
      return {
        bind(...params) { return { kind: sql, params, run: async () => {}, first: async () => visa.get(params.join(":")) || null }; },
        all: async () => ({ results: [...airports.values()] })
      };
    },
    async batch(stmts) {
      const cmd = stmts[0].kind || ""; const kind = cmd.includes("visa_rules") ? "visa" : "airport";
      if (kind === "visa") {
        for (const [k] of visa) if (k.endsWith(":" + stmts[0].params[0])) visa.delete(k);
        for (const s of stmts.slice(1)) {
          const p=s.params; visa.set(p[0]+":"+p[1], {
            passport:p[0],destination:p[1],country_name:p[2],status:p[3],
            stay_days:p[4],notes:p[5],source_url:p[6],verified_on:p[7],source_level:p[8],published_at:p[9]
          });
        }
      } else {
        airports.clear();
        for (const s of stmts.slice(1)) { const p=s.params; airports.set(p[0], {code:p[0],name:p[1],country:p[2],timezone:p[3]}); }
      }
    }
  };
  return { PUBLIC_SNAPSHOTS:snapshots, PUBLIC_DB:db, PUBLISH_TOKEN:"x".repeat(48) };
}
const req = (path, {method="GET", auth=false, data}={}) => new Request("https://example.workers.dev"+path, {
  method, headers: auth ? {Authorization:"Bearer "+"x".repeat(48),"Content-Type":"application/json"} : {},
  body: data === undefined ? undefined : JSON.stringify(data)
});
const price = (observed_at = new Date().toISOString()) => ({
  currency:"TOMAN",observed_at,stale:false,routes:[{origin:"تهران",destinations:[
    {name:"کیش",price_toman:4200000,average_price_toman:5000000,average_sample_count:5}
  ]}]
});
test("ticket reads fail closed, only authenticated writes and no private spill", async () => {
  const env=make();
  assert.equal((await handleRequest(req("/api/v1/tickets/prices"),env)).status,503);
  assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",data:price()}),env)).status,401);
  assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",auth:true,data:{...price(),user_id:5}}),env)).status,200);
  const rsp=await handleRequest(req("/api/v1/tickets/prices"),env);
  assert.equal(rsp.status,200);
  const data=await rsp.json();
  assert.equal(data.routes[0].destinations[0].price_toman,4200000);
  assert.equal("user_id" in data,false);
  assert.equal(data.routes[0].destinations[0].change_percent,-16);
});
test("prices expire at read time even without a new import",async()=>{
  const env=make();
  const fourHoursAgo=new Date(Date.now()-4*3600_000).toISOString();
  assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",auth:true,data:price(fourHoursAgo)}),env)).status,200);
  const rsp=await handleRequest(req("/api/v1/tickets/prices"),env);
  assert.equal((await rsp.json()).stale,true);
  assert.equal(rsp.headers.get("cache-control"),"public, max-age=0");
  assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",auth:true,data:price(new Date(Date.now()-7*3600_000).toISOString())}),env)).status,409);
});
test("reject invalid JSON source currency and fake timestamps",async()=>{
  const env=make();
  for(const data of [{...price(),currency:"USD"},{...price(),observed_at:"2026-10-14-invalid"},{...price(),stale:"no"}]){
    assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",auth:true,data}),env)).status,422);
  }
  assert.equal((await handleRequest(req("/internal/v1/tickets/prices",{method:"POST",auth:true,data:price(),}),{...env,PUBLISH_TOKEN:""})).status,401);
});
test("D1 visa rule and airports serve only validated public projections",async()=>{
  const env=make();
  const visa={destination:"TR",rules:[{passport:"IR",country_name:"ترکیه",status:"visa-free",stay_days:90,notes:null,source_url:"https://example.org/rules",verified_on:"2026-10-11",source_level:"official"}]};
  assert.equal((await handleRequest(req("/internal/v1/visa/destination/TR",{method:"POST",auth:true,data:visa}),env)).status,200);
  const response=await handleRequest(req("/api/v1/visa/rule?passport=IR&destination=TR"),env);
  assert.equal((await response.json()).status,"visa-free");
  assert.equal((await handleRequest(req("/api/v1/visa/rule?passport=bad&destination=TR"),env)).status,400);
  assert.equal((await handleRequest(req("/internal/v1/visa/destination/TR",{method:"POST",auth:true,data:{destination:"TR",rules:[{...visa.rules[0],passport:"NOT-ISO"}]}}),env)).status,422);
  const response2=await handleRequest(req("/api/v1/visa/rule?passport=IR&destination=TR"),env);
  assert.equal((await response2.json()).status,"visa-free");
  assert.equal((await handleRequest(req("/internal/v1/airports",{method:"POST",auth:true,data:{airports:[{code:"IKA",name:"فرودگاه امام",country:"IR",timezone:"Asia/Tehran"}]}}),env)).status,200);
  assert.equal((await (await handleRequest(req("/api/v1/airports"),env)).json()).airports[0].code,"IKA");
});
test("GET endpoints never accept writes and unknown import paths deny",async()=>{
  const env=make();
  assert.equal((await handleRequest(req("/internal/v1/airports"),env)).status,405);
  assert.equal((await handleRequest(req("/internal/v1/nope",{method:"POST",auth:true,data:{}}),env)).status,404);
  assert.equal((await handleRequest(req("/api/v1/users"),env)).status,404);
  assert.equal((await handleRequest(req("/api/v1/visa/list?passport=NOTVALID"),env)).status,400);
});
