import test from "node:test";
import assert from "node:assert/strict";
import {createHmac} from "node:crypto";
import {readFileSync} from "node:fs";
import {miniRoute,telegramUser} from "../src/mini.mjs";
import {handleRequest} from "../src/worker.mjs";

const BOT_TOKEN="123456:TEST_WORKER_SECRET_LONG_ENOUGH";
const PUBLISH_TOKEN="p".repeat(48);
function signedUser(id=42,{future=0,token=BOT_TOKEN}={}) {
  const data=new URLSearchParams();
  data.set("auth_date",String(Math.floor(Date.now()/1000)+future));
  data.set("user",JSON.stringify({id,first_name:"محمد",username:"test_user"}));
  const check=[...data.entries()].sort((a,b)=>a[0].localeCompare(b[0]))
    .map(([key,value])=>key+"="+value).join("\n");
  const secret=createHmac("sha256","WebAppData").update(token).digest();
  data.set("hash",createHmac("sha256",secret).update(check).digest("hex"));
  return data.toString();
}
function req(path,{method="GET",user,auth=false,json}={}) {
  return new Request("https://example.workers.dev"+path,{
    method,headers:{
      ...(user!==undefined ? {"X-Telegram-Init-Data":user}:{}),
      ...(auth?{"Authorization":"Bearer "+PUBLISH_TOKEN}:{}),
      ...(json!==undefined?{"Content-Type":"application/json"}:{})
    },
    ...(json!==undefined?{body:JSON.stringify(json)}:{})
  });
}
function fixture() {
  const jobs=new Map();
  const visa={
    "IR:TR":{
      passport:"IR",destination:"TR",country_name:"Turkey",status:"visa-free",
      stay_days:90,verified_on:"2026-10-11",source_level:"official",
      notes:"Official rules",source_url:"https://example.org/source"
    }
  };
  function statement(sql,params=[]) {
    return {
      bind(...x) { return statement(sql,x); },
      async first() {
        if(sql.includes("count(*) AS total")) {
          return {total:[...jobs.values()].filter(x=>
            x.telegram_id===params[0]&&x.created_at_ms>params[1]).length};
        }
        if(sql.includes("SELECT status,result_status")) {
          const found=jobs.get(params[0]);
          return found?.telegram_id===params[1]?found:null;
        }
        if(sql.includes("SELECT result_status,result_json,status"))
          return jobs.get(params[0])||null;
        if(sql.includes("FROM visa_rules")) return visa[params.join(":")]||null;
        throw Error("Unknown D1 first: "+sql);
      },
      async all() {
        if(sql.includes("FROM telegram_mini_jobs")) {
          return {results:[...jobs.values()].filter(x=>
            x.created_at_ms>params[0] &&
            (x.status==="pending" || (x.status==="leased" &&
              x.lease_until_ms<params[1] && x.attempts<2 &&
              ["bootstrap","alerts","useful"].includes(x.operation))))
            .sort((a,b)=>a.created_at_ms-b.created_at_ms).slice(0,8)};
        }
        if(sql.includes("FROM visa_rules")) return {results:
          Object.values(visa).filter(x=>x.passport===params[0])};
        throw Error("Unknown D1 all: "+sql);
      },
      async run() {
        if(sql.startsWith("INSERT INTO telegram_mini_jobs")) {
          const [id,telegram_id,user_json,operation,payload_json,created_at_ms]=params;
          jobs.set(id,{id,telegram_id,user_json,operation,payload_json,
            status:"pending",result_status:null,result_json:null,created_at_ms,
            lease_until_ms:0,attempts:0});
          return {meta:{changes:1}};
        }
        if(sql.startsWith("DELETE FROM telegram_mini_jobs")) {
          for(const [id,item] of jobs.entries()) if(item.created_at_ms<params[0]) jobs.delete(id);
          return {meta:{changes:0}};
        }
        if(sql.includes("SET status='leased'")) {
          const [lease,id,now]=params, job=jobs.get(id);
          if(job&&(job.status==="pending" || (job.status==="leased"&&
            job.lease_until_ms<now&&job.attempts<2&&
            ["bootstrap","alerts","useful"].includes(job.operation)))) {
            job.status="leased";job.lease_until_ms=lease;job.attempts++;
            return {meta:{changes:1}};
          }
          return {meta:{changes:0}};
        }
        if(sql.includes("SET status='complete'")) {
          const [status,payload,id,after]=params,job=jobs.get(id);
          if(job?.status==="leased"&&job.created_at_ms>after) {
            Object.assign(job,{status:"complete",result_status:status,result_json:payload});
            return {meta:{changes:1}};
          }
          return {meta:{changes:0}};
        }
        throw Error("Unknown D1 run: "+sql);
      }
    };
  }
  const env={
    TELEGRAM_BOT_TOKEN:BOT_TOKEN,PUBLISH_TOKEN,
    PUBLIC_DB:{prepare:sql=>statement(sql)},
    ASSETS:{async fetch(request) {
      const path=new URL(request.url).pathname;
      if(path==="/index.html") return new Response("<!doctype html><html lang='fa'>Mini</html>",{
        headers:{"Content-Type":"text/html"}});
      if(path==="/mini.js") return new Response("console.log('mini')",{
        headers:{"Content-Type":"text/javascript"}});
      if(path==="/mini.css") return new Response("body{}",{
        headers:{"Content-Type":"text/css"}});
      return new Response("Not found",{status:404});
    }}
  };
  return {env,jobs};
}

test("Worker static-asset binding serves the existing Mini App at / and /mini/",async()=>{
  const {env}=fixture();
  for(const path of ["/","/mini","/mini/"]) {
    const response=await handleRequest(req(path),env);
    assert.equal(response.status,200);
    assert.match(await response.text(),/lang='fa'/);
    assert.match(response.headers.get("content-security-policy"),/telegram.org/);
    assert.equal(response.headers.get("cache-control"),"no-store");
  }
  const script=await handleRequest(req("/assets/mini.js"),env);
  assert.equal(script.status,200);
  assert.match(await script.text(),/mini/);
  assert.equal((await handleRequest(req("/assets/.env"),env)).status,404);
  assert.equal((await handleRequest(req("/api/random"),env)).status,404);
  assert.match(readFileSync(new URL("../wrangler.toml",import.meta.url),"utf8"),
    /run_worker_first\s*=\s*true/);
});

test("Worker validates Telegram initData signatures, freshness and identity",async()=>{
  const {env}=fixture();
  assert.equal(await telegramUser(req("/api/mini/bootstrap"),env),null);
  assert.equal(await telegramUser(req("/api/mini/bootstrap",{user:signedUser(42,{token:"wrong"})}),env),null);
  assert.equal(await telegramUser(req("/api/mini/bootstrap",{user:signedUser(42,{future:3600})}),env),null);
  assert.equal(await telegramUser(req("/api/mini/bootstrap",{user:signedUser(42,{future:-90000})}),env),null);
  const signed=signedUser();
  assert.equal(await telegramUser(req("/api/mini/bootstrap",{user:signed+"&auth_date=1"}),env),null);
  assert.equal(await telegramUser(req("/api/mini/bootstrap",{user:signed}),env).then(x=>x.id),42);
  assert.equal((await handleRequest(req("/api/mini/bootstrap"),env)).status,401);
  assert.equal((await handleRequest(req("/api/mini/bootstrap",{user:signedUser(42,{token:"fake"})}),env)).status,401);
});

test("User-scoped Mini App jobs flow securely through the outbound polling bridge",async()=>{
  const {env,jobs}=fixture();
  const pending=await handleRequest(req("/api/mini/bootstrap",{user:signedUser()}),env);
  assert.equal(pending.status,202);
  assert.equal(pending.headers.get("cache-control"),"no-store");
  const {job_id:id}=await pending.json();
  assert.match(id,/^[a-f0-9-]{36}$/);
  assert.equal((await handleRequest(req("/api/mini/results/"+id,{user:signedUser(84)}),env)).status,404);
  assert.equal((await handleRequest(req("/internal/v1/mini/jobs"),env)).status,401);
  const poll=await handleRequest(req("/internal/v1/mini/jobs",{auth:true}),env);
  assert.equal(poll.status,200);
  const batch=(await poll.json()).jobs;
  assert.equal(batch.length,1);
  assert.equal(batch[0].telegram_id,42);
  assert.equal(batch[0].user.first_name,"محمد");
  assert.equal(batch[0].operation,"bootstrap");
  assert.equal("initData" in batch[0],false);
  assert.equal((await handleRequest(req("/internal/v1/mini/jobs",{auth:true}),env)
    .then(x=>x.json())).jobs.length,0);
  const body={http_status:200,body:{user:{first_name:"محمد"},passport:"IR",countries:[],links:{}}};
  const url="/internal/v1/mini/jobs/"+id+"/result";
  assert.equal((await handleRequest(req(url,{method:"POST",auth:true,json:body}),env)).status,200);
  assert.equal((await handleRequest(req(url,{method:"POST",auth:true,json:body}),env)).status,200);
  const finished=await handleRequest(req("/api/mini/results/"+id,{user:signedUser()}),env);
  assert.equal(finished.status,200);
  assert.deepEqual((await finished.json()).body,body.body);
  assert.equal(jobs.size,1);
});

test("A leased mutating action is NOT executed twice after lost acknowledgement",async()=>{
  const {env,jobs}=fixture();
  const signed=signedUser();
  const action=await handleRequest(req("/api/mini/alerts/prices",{
    method:"POST",user:signed,json:{origin:"تهران",destination:"کیش",
      kind:"percent",threshold_percent:10}
  }),env);
  assert.equal(action.status,202);
  const id=(await action.json()).job_id;
  const batch=await (await handleRequest(req("/internal/v1/mini/jobs",{auth:true}),env)).json();
  assert.equal(batch.jobs[0].operation,"price_create");
  jobs.get(id).lease_until_ms=Date.now()-5000;
  assert.equal((await handleRequest(req("/api/mini/results/"+id,{user:signed}),env)).status,503);
  const repeat=await (await handleRequest(req("/internal/v1/mini/jobs",{auth:true}),env)).json();
  assert.equal(repeat.jobs.length,0);
  // The first execution may have committed; its late completion is accepted.
  const ack=await handleRequest(req("/internal/v1/mini/jobs/"+id+"/result",{
    method:"POST",auth:true,json:{http_status:201,body:{created:true,id:12}}
  }),env);
  assert.equal(ack.status,200);
});

test("D1 serves signed visa lookups immediately without exposing SQLite rows",async()=>{
  const {env}=fixture(),user=signedUser();
  assert.equal((await handleRequest(req("/api/mini/visa",{user}),env)).status,200);
  const v=await handleRequest(req("/api/mini/visa/rule?passport=IR&destination=TR",{user}),env);
  assert.equal(v.status,200);
  assert.equal((await v.json()).stay_days,90);
  assert.equal((await handleRequest(req("/api/mini/visa/rule?passport=IR&destination=NO",{user}),env)).status,404);
  assert.equal((await handleRequest(req("/api/mini/visa?passport=invalid",{user}),env)).status,422);
  assert.equal((await handleRequest(req("/api/mini/visa",{user:signedUser(99,{token:"invalid"})}),env)).status,401);
});

test("Invalid mutations never create jobs and no unauthenticated owner APIs exist",async()=>{
  const {env,jobs}=fixture(),user=signedUser();
  for(const action of [
    req("/api/mini/alerts/prices",{user,method:"POST",json:{origin:"ا",destination:"ب",
      kind:"percent",threshold_percent:11}}),
    req("/api/mini/passport",{user,method:"POST",json:{passport:"!!"}}),
    req("/api/mini/alerts/visa",{user,method:"POST",json:{passport:"IR",destination:"bad"}}),
    req("/api/mini/alerts/prices/0",{user,method:"DELETE"}),
    req("/api/mini/alerts/visa/123",{user,method:"PATCH",json:{active:"true"}})
  ]) assert.equal((await handleRequest(action,env)).status,422);
  assert.equal(jobs.size,0);
  assert.equal((await handleRequest(req("/api/mini/alerts"),env)).status,401);
  assert.equal((await handleRequest(req("/api/mini/alerts/prices/9",{method:"DELETE"}),env)).status,401);
});
