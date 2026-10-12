// Telegram Mini App hosted on the same free workers.dev Worker as the public API.
// Only the bot's Ubuntu SQLite services execute private actions. Cloudflare D1
// contains a short-lived authenticated job envelope, never the user database.
const encoder = new TextEncoder();
const CODE2 = /^[A-Z]{2}$/;
const JOB_ID = /^[a-f0-9-]{36}$/i;
const MAX_AUTH_LENGTH = 8192;
const MAX_JOB_AGE_MS = 90_000;
const MAX_RESULT_LENGTH = 131_072;
const READ_OPERATIONS = new Set(["bootstrap", "alerts", "useful"]);
const error = (status, message) => Response.json({error:message}, {
  status, headers: {"Cache-Control":"no-store", "X-Content-Type-Options":"nosniff"}
});
const json = (body,status=200) => Response.json(body,{
  status,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}
});
function safeText(value,limit=128) {
  return typeof value==="string" && value.length<=limit && value.trim()
    ? value.trim() : null;
}
function constantTimeHexEqual(actual,expected) {
  if (typeof actual !== "string" || !/^[a-fA-F0-9]{64}$/.test(actual)) return false;
  let diff=0;
  for(let i=0;i<64;i++) diff |= actual.toLowerCase().charCodeAt(i) ^ expected.charCodeAt(i);
  return diff===0;
}
// Telegram's documented WebApp HMAC: secret_key = HMAC_SHA256("WebAppData", bot_token)
// data_check_string contains all signed key=value pairs except hash, sorted by key.
export async function telegramUser(request,env) {
  const initData=request.headers.get("X-Telegram-Init-Data");
  if (!env.TELEGRAM_BOT_TOKEN || !initData || initData.length>MAX_AUTH_LENGTH) return null;
  try {
    const data = new URLSearchParams(initData);
    const pairs=[...data.entries()];
    if (pairs.length<3 || pairs.length>40 || pairs.length!==new Set(pairs.map(x=>x[0])).size)
      return null;
    const sentHash=data.get("hash");
    if (!sentHash || !/^[0-9a-fA-F]{64}$/.test(sentHash)) return null;
    const authDate=Number(data.get("auth_date"));
    if (!Number.isSafeInteger(authDate) || authDate<=0 ||
      !(-60<=Date.now()/1000-authDate && Date.now()/1000-authDate<=86400)) return null;
    data.delete("hash");
    const message=[...data.entries()].sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0)
      .map(([key,value])=>key+"="+value).join("\n");
    const root=await crypto.subtle.importKey("raw",encoder.encode("WebAppData"),
      {name:"HMAC",hash:"SHA-256"},false,["sign"]);
    const secret=await crypto.subtle.sign("HMAC",root,encoder.encode(env.TELEGRAM_BOT_TOKEN));
    const key=await crypto.subtle.importKey("raw",secret,
      {name:"HMAC",hash:"SHA-256"},false,["sign"]);
    const signature=await crypto.subtle.sign("HMAC",key,encoder.encode(message));
    const hex=[...new Uint8Array(signature)].map(x=>x.toString(16).padStart(2,"0")).join("");
    if (!constantTimeHexEqual(sentHash,hex)) return null;
    const user=JSON.parse(data.get("user")||"null");
    if (!user || typeof user!=="object" || Array.isArray(user) ||
      !Number.isSafeInteger(user.id) || user.id<=0) return null;
    return {
      id:user.id,
      first_name:safeText(user.first_name,100),
      last_name:safeText(user.last_name,100),
      username:safeText(user.username,100)
    };
  } catch { return null; }
}
async function miniJsonBody(request) {
  const type=request.headers.get("Content-Type")||"";
  if (!type.toLowerCase().startsWith("application/json") ||
      Number(request.headers.get("Content-Length")||"0")>8192)
    return null;
  // Limit streamed request bodies even when Content-Length is absent; do
  // not buffer an arbitrary untrusted payload in a Worker isolate.
  const reader=request.body?.getReader();
  if (!reader) return null;
  const chunks=[];
  let size=0;
  try {
    while (true) {
      const {done,value}=await reader.read();
      if (done) break;
      size+=value.byteLength;
      if (size>8192) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } catch { return null; }
  finally { reader.releaseLock(); }
  const bytes=new Uint8Array(size);
  let offset=0;
  for(const chunk of chunks) { bytes.set(chunk,offset);offset+=chunk.byteLength; }
  try {
    const value=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
    return value && typeof value==="object" && !Array.isArray(value) ? value : null;
  } catch { return null; }
}
function validOperation(path,method,payload) {
  if (method==="GET") {
    if (path==="/api/mini/bootstrap") return {operation:"bootstrap",payload:{}};
    if (path==="/api/mini/useful") return {operation:"useful",payload:{}};
    if (path==="/api/mini/alerts") return {operation:"alerts",payload:{}};
    return null;
  }
  if (method==="POST" && path==="/api/mini/passport") {
    if (!CODE2.test(payload?.passport)) return null;
    return {operation:"passport",payload:{passport:payload.passport}};
  }
  if (method==="POST" && path==="/api/mini/alerts/prices") {
    const origin=safeText(payload?.origin), destination=safeText(payload?.destination);
    if (!origin || !destination || !["percent","price"].includes(payload?.kind)) return null;
    if (payload.kind==="percent") {
      if (!Number.isInteger(payload.threshold_percent) || payload.threshold_percent<5 ||
        payload.threshold_percent>50 || payload.threshold_percent%5 ||
        payload.target_price_toman!=null) return null;
      return {operation:"price_create",payload:{origin,destination,kind:"percent",
        threshold_percent:payload.threshold_percent}};
    }
    if (!Number.isSafeInteger(payload.target_price_toman) || payload.target_price_toman<1 ||
      payload.target_price_toman>1_000_000_000_000 || payload.threshold_percent!=null)
      return null;
    return {operation:"price_create",payload:{origin,destination,kind:"price",
      target_price_toman:payload.target_price_toman}};
  }
  if (method==="POST" && path==="/api/mini/alerts/visa") {
    if (!CODE2.test(payload?.passport) || !CODE2.test(payload?.destination)) return null;
    return {operation:"visa_create",payload:{
      passport:payload.passport,destination:payload.destination}};
  }
  const price=/^\/api\/mini\/alerts\/prices\/([1-9][0-9]{0,12})$/.exec(path);
  const visa=/^\/api\/mini\/alerts\/visa\/([1-9][0-9]{0,12})$/.exec(path);
  const alertId=Number((price||visa)?.[1]);
  if (!price && !visa) return null;
  if (!Number.isSafeInteger(alertId)) return null;
  if (method==="DELETE") {
    return {operation:price?"price_delete":"visa_delete",payload:{id:alertId}};
  }
  if (method==="PATCH" && price && ["active","paused"].includes(payload?.status))
    return {operation:"price_status",payload:{id:alertId,status:payload.status}};
  if (method==="PATCH" && visa && typeof payload?.active==="boolean")
    return {operation:"visa_status",payload:{id:alertId,active:payload.active}};
  return null;
}
async function miniVisa(url,env,path) {
  if (path==="/api/mini/visa") {
    const passport=url.searchParams.get("passport")||"IR";
    if (!CODE2.test(passport)) return error(422,"Invalid passport");
    const {results}=await env.PUBLIC_DB.prepare(
      "SELECT passport,destination,country_name,status,stay_days,verified_on,source_level "+
      "FROM visa_rules WHERE passport=? ORDER BY country_name LIMIT 250"
    ).bind(passport).all();
    if (!results?.length) return error(503,"Visa catalog unavailable");
    return json({passport,rules:results});
  }
  if (path==="/api/mini/visa/rule") {
    const passport=url.searchParams.get("passport")||"IR";
    const destination=url.searchParams.get("destination");
    if (!CODE2.test(passport)||!CODE2.test(destination)) return error(422,"Invalid country code");
    const row=await env.PUBLIC_DB.prepare(
      "SELECT passport,destination,country_name,status,stay_days,notes,source_url,"+
      "verified_on,source_level FROM visa_rules WHERE passport=? AND destination=?"
    ).bind(passport,destination).first();
    return row?json(row):error(404,"Visa rule unavailable");
  }
  return null;
}
async function resultForUser(url,user,env) {
  const id=url.pathname.slice("/api/mini/results/".length);
  if (!JOB_ID.test(id)) return error(404,"Unknown request");
  const job=await env.PUBLIC_DB.prepare(
    "SELECT status,result_status,result_json,created_at_ms,lease_until_ms,operation "+
    "FROM telegram_mini_jobs WHERE id=? AND telegram_id=?"
  ).bind(id,user.id).first();
  if (!job) return error(404,"Unknown request");
  if (Date.now()-job.created_at_ms>MAX_JOB_AGE_MS) return error(410,"Request expired");
  if (job.status==="complete") {
    try { return json({state:"complete",http_status:job.result_status,
      body:JSON.parse(job.result_json)}); }
    catch { return error(503,"Invalid response"); }
  }
  if (job.status==="leased" && job.lease_until_ms<Date.now() &&
      !READ_OPERATIONS.has(job.operation)) {
    // A mutating operation might already have committed in SQLite. Never
    // automatically replay it and accidentally create duplicate subscriptions.
    return error(503,"Request not confirmed; review your alerts before retrying");
  }
  return json({state:"pending"},202);
}
async function enqueue(request,user,env,path) {
  let payload=null;
  if (!["GET","DELETE"].includes(request.method)) {
    payload=await miniJsonBody(request);
    if (!payload) return error(400,"Invalid JSON payload");
  }
  const spec=validOperation(path,request.method,payload);
  if (!spec) return error(422,"Invalid action or parameters");
  const now=Date.now();
  const recent=await env.PUBLIC_DB.prepare(
    "SELECT count(*) AS total FROM telegram_mini_jobs WHERE telegram_id=? AND created_at_ms>?"
  ).bind(user.id,now-60_000).first();
  if (Number(recent?.total||0)>=20) return error(429,"Too many Mini App requests");
  const id=crypto.randomUUID();
  await env.PUBLIC_DB.prepare(
    "INSERT INTO telegram_mini_jobs(id,telegram_id,user_json,operation,payload_json,status,"+
    "created_at_ms,lease_until_ms,attempts) VALUES(?,?,?,?,?,'pending',?,0,0)"
  ).bind(id,user.id,JSON.stringify({
    first_name:user.first_name,last_name:user.last_name,username:user.username
  }),spec.operation,JSON.stringify(spec.payload),now).run();
  return json({state:"pending",job_id:id},202);
}
async function internalMini(request,env,path,authorized) {
  if (!await authorized(request,env)) return error(401,"Unauthorized");
  if (!env.PUBLIC_DB) return error(503,"D1 unavailable");
  if (request.method==="GET" && path==="/internal/v1/mini/jobs") {
    const now=Date.now();
    // TTL cleanup: private job envelopes never become a permanent user archive.
    await env.PUBLIC_DB.prepare(
      "DELETE FROM telegram_mini_jobs WHERE created_at_ms<?"
    ).bind(now-10*60_000).run();
    const {results}=await env.PUBLIC_DB.prepare(
      "SELECT id,telegram_id,user_json,operation,payload_json,created_at_ms "+
      "FROM telegram_mini_jobs WHERE created_at_ms>? AND "+
      "(status='pending' OR (status='leased' AND lease_until_ms<? AND attempts<2 "+
      "AND operation IN ('bootstrap','alerts','useful'))) "+
      "ORDER BY created_at_ms LIMIT 8"
    ).bind(now-MAX_JOB_AGE_MS,now).all();
    const jobs=[];
    for(const row of results||[]) {
      const leased=await env.PUBLIC_DB.prepare(
        "UPDATE telegram_mini_jobs SET status='leased',lease_until_ms=?,attempts=attempts+1 "+
        "WHERE id=? AND (status='pending' OR (status='leased' AND lease_until_ms<? "+
        "AND attempts<2 AND operation IN ('bootstrap','alerts','useful')))"
      ).bind(now+25_000,row.id,now).run();
      if (leased?.meta?.changes===1) jobs.push({
        id:row.id,telegram_id:row.telegram_id,
        user:JSON.parse(row.user_json),operation:row.operation,
        payload:JSON.parse(row.payload_json)
      });
    }
    return json({jobs});
  }
  const match=/^\/internal\/v1\/mini\/jobs\/([a-f0-9-]{36})\/result$/i.exec(path);
  if (match && request.method==="POST") {
    const payload=await miniJsonBody(request);
    const status=payload?.http_status;
    if (!Number.isInteger(status) || ![200,201,400,401,404,409,422,429,503].includes(status) ||
        !payload?.body || typeof payload.body!=="object" || Array.isArray(payload.body))
      return error(422,"Invalid Mini App result");
    const serialized=JSON.stringify(payload.body);
    if (encoder.encode(serialized).length>MAX_RESULT_LENGTH)
      return error(413,"Result too large");
    const updated=await env.PUBLIC_DB.prepare(
      "UPDATE telegram_mini_jobs SET status='complete',result_status=?,result_json=? "+
      "WHERE id=? AND status='leased' AND created_at_ms>?"
    ).bind(status,serialized,match[1],Date.now()-MAX_JOB_AGE_MS).run();
    if (updated?.meta?.changes===1) return json({accepted:true});
    // Allow an identical completion to be acknowledged after a network retry.
    const existing=await env.PUBLIC_DB.prepare(
      "SELECT result_status,result_json,status FROM telegram_mini_jobs WHERE id=?"
    ).bind(match[1]).first();
    if (existing?.status==="complete" && existing.result_status===status &&
        existing.result_json===serialized) return json({accepted:true});
    return error(409,"Job is no longer claimable");
  }
  return error(404,"Unknown private endpoint");
}
async function serveAsset(request,env,path) {
  if (!env.ASSETS || !["GET","HEAD"].includes(request.method)) return error(404,"Not found");
  const target={
    "/":"/index.html","/mini":"/index.html","/mini/":"/index.html",
    "/assets/mini.js":"/mini.js","/assets/mini.css":"/mini.css"
  }[path];
  if (!target) return error(404,"Not found");
  const assetUrl=new URL(request.url);
  assetUrl.pathname=target;
  assetUrl.search="";
  const asset=await env.ASSETS.fetch(new Request(assetUrl.toString(),{method:"GET"}));
  if (!asset.ok) return error(503,"Mini App assets unavailable");
  const headers=new Headers(asset.headers);
  headers.set("X-Content-Type-Options","nosniff");
  headers.set("Referrer-Policy","no-referrer");
  headers.set("X-Frame-Options","DENY");
  if (target==="/index.html") {
    headers.set("Cache-Control","no-store");
    headers.set("Content-Security-Policy",
      "default-src 'none'; script-src 'self' https://telegram.org; "+
      "style-src 'self'; img-src 'self' data:; connect-src 'self'; "+
      "base-uri 'none'; object-src 'none'; form-action 'none'");
  } else headers.set("Cache-Control","public, max-age=300");
  return new Response(request.method==="HEAD"?null:asset.body,{status:asset.status,headers});
}
// Called by the existing Android/public Worker dispatcher.
// If null is returned, continue with the unchanged public Android API routes.
export async function miniRoute(request,env,authorized) {
  const url=new URL(request.url),path=url.pathname;
  if (path.startsWith("/internal/v1/mini/") || path==="/internal/v1/mini/jobs")
    return internalMini(request,env,path,authorized);
  if (path.startsWith("/api/mini/")) {
    if (!env.PUBLIC_DB) return error(503,"D1 unavailable");
    const user=await telegramUser(request,env);
    if (!user) return error(401,"Invalid Telegram session");
    if (request.method==="GET" && path.startsWith("/api/mini/results/"))
      return resultForUser(url,user,env);
    if (request.method==="GET") {
      const direct=await miniVisa(url,env,path);
      if (direct) return direct;
    }
    return enqueue(request,user,env,path);
  }
  if (["/","/mini","/mini/","/assets/mini.js","/assets/mini.css"].includes(path))
    return serveAsset(request,env,path);
  return null;
}
