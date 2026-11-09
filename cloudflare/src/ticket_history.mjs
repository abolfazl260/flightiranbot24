const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':status===200?'public, max-age=60':'no-store','X-Content-Type-Options':'nosniff'}});
const dayMs=86400000, today=()=>new Date().toISOString().slice(0,10);
const dayNumber=s=>typeof s==='string'&&/^\d{4}-\d\d-\d\d$/.test(s)&&new Date(s).toISOString().slice(0,10)===s?Date.parse(s)/dayMs:NaN;
const name=s=>typeof s==='string'&&s.trim().length>0&&s.length<=128?s.trim():null;
export function validatedHistory(raw) {
 try {
  const origin=name(raw?.origin),destination=name(raw?.destination),end=dayNumber(raw?.as_of);
  if(!origin||!destination||raw.currency!=='TOMAN'||raw.metric!=='daily_minimum'||raw.days!==21||
     !Number.isFinite(end)||end>dayNumber(today())||!Array.isArray(raw.points)||raw.points.length>21)return null;
  let previous=-Infinity;const points=[];
  for(const p of raw.points){
   const day=dayNumber(p?.day),when=Date.parse(p?.last_observed_at);
   if(!Number.isFinite(day)||day<end-20||day>end||day<=previous||
      !Number.isSafeInteger(p.price_toman)||p.price_toman<=0||p.price_toman>1e12||
      !Number.isSafeInteger(p.sample_count)||p.sample_count<=0||p.sample_count>100000||
      typeof p.last_observed_at!=='string'||!/(Z|\+00:00)$/.test(p.last_observed_at)||
      !Number.isFinite(when)||when>Date.now()+300000||new Date(when).toISOString().slice(0,10)!==p.day)return null;
   previous=day;points.push({day:p.day,price_toman:p.price_toman,sample_count:p.sample_count,last_observed_at:p.last_observed_at});
  }
  const observed=points.length?points.reduce((a,b)=>Date.parse(a)>Date.parse(b.last_observed_at)?a:b.last_observed_at,points[0].last_observed_at):null;
  if(raw.observed_at!==observed)return null;
  return {origin,destination,currency:'TOMAN',metric:'daily_minimum',days:21,as_of:raw.as_of,observed_at:observed,points};
 }catch{return null;}
}
export async function publishHistory(raw,db) {
 const d=validatedHistory(raw);if(!d||!d.points.length)return json({error:'Invalid route history'},422);
 const result=await db.prepare('INSERT INTO ticket_route_history(origin,destination,last_day,observed_epoch_ms,snapshot_json) VALUES(?,?,?,?,?) ON CONFLICT(origin,destination) DO UPDATE SET last_day=excluded.last_day,observed_epoch_ms=excluded.observed_epoch_ms,snapshot_json=excluded.snapshot_json WHERE excluded.observed_epoch_ms>=ticket_route_history.observed_epoch_ms AND excluded.snapshot_json IS NOT ticket_route_history.snapshot_json')
 .bind(d.origin,d.destination,d.points.at(-1).day,Date.parse(d.observed_at),JSON.stringify(d)).run();
 // At most one small indexed expiry sweep per changed route, never at user read time.
 if(result?.meta?.changes)await db.prepare('DELETE FROM ticket_route_history WHERE last_day < ?').bind(new Date(Date.now()-20*dayMs).toISOString().slice(0,10)).run();
 return json({published:true},200);
}
export async function publicHistory(request,env) {
 const url=new URL(request.url),path=url.pathname;
 if(!['/api/v1/tickets/history','/api/v1/tickets/history/routes'].includes(path))return null;
 if(request.method!=='GET')return json({error:'Method not allowed'},405);
 const routes=path.endsWith('/routes'),origin=name(url.searchParams.get('origin')),destination=name(url.searchParams.get('destination'));
 const offsetRaw=url.searchParams.get('offset')||'0',offset=Number(offsetRaw);
 if(routes?(!/^\d{1,5}$/.test(offsetRaw)||offset>10000):(!origin||!destination))return json({error:'Invalid history route'},400);
 if(!env.PUBLIC_DB)return json({error:'History unavailable'},503);
 const cache=globalThis.caches?.default;
 if(cache){const hit=await cache.match(request);if(hit)return hit;}
 try {
  const start=new Date(Date.now()-20*dayMs).toISOString().slice(0,10);let response;
  if(routes){
   const {results}=await env.PUBLIC_DB.prepare('SELECT origin,destination FROM ticket_route_history WHERE last_day >= ? ORDER BY origin,destination LIMIT 101 OFFSET ?').bind(start,offset).all();
   response=json({routes:(results||[]).slice(0,100).map(r=>({origin:r.origin,destination:r.destination})),next_offset:results?.length>100?offset+100:null});
  }else{
   const row=await env.PUBLIC_DB.prepare('SELECT snapshot_json FROM ticket_route_history WHERE origin=? AND destination=?').bind(origin,destination).first();
   const original=row?validatedHistory(JSON.parse(row.snapshot_json)):null;
   if(row&&(!original||original.origin!==origin||original.destination!==destination))return json({error:'Invalid history data'},503);
   const points=(original?.points||[]).filter(p=>p.day>=start&&p.day<=today());
   const observed=points.length?points.reduce((a,b)=>Date.parse(a)>Date.parse(b.last_observed_at)?a:b.last_observed_at,points[0].last_observed_at):null;
   response=json({origin,destination,currency:'TOMAN',metric:'daily_minimum',days:21,as_of:today(),observed_at:observed,points,stale:!observed||Date.now()-Date.parse(observed)>10800000});
  }
  if(cache)await cache.put(request,response.clone());return response;
 }catch{return json({error:'History unavailable'},503);}
}
