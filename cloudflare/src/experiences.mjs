const response=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const target=/^(airport:[A-Z]{3}|airline:[a-z0-9-]{2,80}|country:[A-Z]{2}|route:[A-Z]{3}-[A-Z]{3}|flight:[A-Z0-9-]{2,16})$/;
export function publicExperience(r){
 if(!r||('state' in r&&r.state!=='approved')||('consent' in r&&r.consent!==true)||!Number.isSafeInteger(r.id)||r.id<=0||!['archive','user'].includes(r.kind)||typeof r.text!=='string'||!r.text.trim()||r.text.length>20000||
    typeof r.display_name!=='string'||r.display_name.length>80||!Array.isArray(r.targets)||r.targets.length>10||r.targets.some(t=>!target.test(t))||
    r.rating!==null&&(!Number.isInteger(r.rating)||r.rating<1||r.rating>5)||r.kind==='archive'&&r.rating!==null||
    !Number.isSafeInteger(r.helpful)||r.helpful<0||!Number.isFinite(Date.parse(r.created_at))||!Number.isFinite(Date.parse(r.modified_at)))return null;
 const criteria={};for(const [k,v]of Object.entries(r.criteria||{})){if(!['crew','seat','catering','cleanliness','delay_response','checkin','baggage','value','signage','queues','services'].includes(k)||!Number.isInteger(v)||v<1||v>5)return null;criteria[k]=v;}
 return {id:r.id,kind:r.kind,text:r.text,display_name:r.display_name,rating:r.rating,criteria,targets:[...r.targets],helpful:r.helpful,
   created_at:r.created_at,modified_at:r.modified_at,posted_label:typeof r.posted_label==='string'?r.posted_label.slice(0,100):null,
   travel_date:typeof r.travel_date==='string'&&/^\d{4}-\d\d-\d\d$/.test(r.travel_date)?r.travel_date:null};
}
export async function importExperience(payload,db,commit=false){
 const generated=Date.parse(payload?.generated_at);
 if(!Number.isFinite(generated)||generated>Date.now()+300000)return response({error:'Invalid projection clock'},422);
 const meta=await db.prepare('SELECT generated_ms,invalid_after_ms,expires_ms FROM experience_projection_meta WHERE id=1').first();
 if(meta&&(generated<meta.generated_ms||generated<=meta.invalid_after_ms))return response({error:'Stale publication generation'},409);
 if(commit){
  if(!Array.isArray(payload.ids)||payload.ids.length>1000||payload.ids.some(id=>!Number.isSafeInteger(id)||id<=0))return response({error:'Invalid public manifest'},422);
  const gate='NOT EXISTS(SELECT 1 FROM experience_projection_meta WHERE id=1 AND (generated_ms>? OR invalid_after_ms>=?))';
  const out=await db.batch([
   db.prepare('DELETE FROM public_experiences WHERE id NOT IN(SELECT value FROM json_each(?)) AND '+gate).bind(JSON.stringify(payload.ids),generated,generated),
   db.prepare('INSERT INTO experience_projection_meta(id,generated_ms,invalid_after_ms,expires_ms) VALUES(1,?,0,?) ON CONFLICT(id) DO UPDATE SET generated_ms=excluded.generated_ms,expires_ms=excluded.expires_ms WHERE excluded.generated_ms>=generated_ms AND excluded.generated_ms>invalid_after_ms').bind(generated,generated+360000)
  ]);
  if(out?.at(-1)?.meta?.changes===0)return response({error:'Stale publication generation'},409);
 }else{
  const r=publicExperience(payload.record);if(!r)return response({error:'Invalid public review'},422);
  await db.prepare('INSERT INTO public_experiences(id,modified_ms,rating,helpful,targets_json,search_key,snapshot_json) SELECT ?,?,?,?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM experience_projection_meta WHERE id=1 AND (generated_ms>? OR invalid_after_ms>=?)) ON CONFLICT(id) DO UPDATE SET modified_ms=excluded.modified_ms,rating=excluded.rating,helpful=excluded.helpful,targets_json=excluded.targets_json,search_key=excluded.search_key,snapshot_json=excluded.snapshot_json WHERE excluded.modified_ms>=modified_ms AND excluded.snapshot_json IS NOT snapshot_json')
   .bind(r.id,Date.parse(r.modified_at),r.rating,r.helpful,JSON.stringify(r.targets),r.text.toLowerCase(),JSON.stringify(r),generated,generated).run();
 }
 return response({published:true});
}
export async function experienceRead(request,env){
 const url=new URL(request.url),match=/^\/api\/v1\/experiences(?:\/(\d{1,12}))?$/.exec(url.pathname);if(!match)return null;
 if(request.method!=='GET')return response({error:'Method not allowed'},405);
 if(!env.PUBLIC_DB)return response({error:'Experiences unavailable'},503);
 const t=url.searchParams.get('target')||'',q=url.searchParams.get('q')||'',sort=url.searchParams.get('sort')||'newest',off=url.searchParams.get('offset')||'0';
 if(t&&!target.test(t)||q.length>100||!['newest','helpful','rating'].includes(sort)||!/^\d{1,5}$/.test(off)||Number(off)>10000)return response({error:'Invalid review filter'},400);
 try{
  const meta=await env.PUBLIC_DB.prepare('SELECT generated_ms,invalid_after_ms,expires_ms FROM experience_projection_meta WHERE id=1').first();
  if(!meta||meta.expires_ms<Date.now()||meta.generated_ms<=meta.invalid_after_ms)return response({error:'Public reviews awaiting fresh synchronization'},503);
  if(match[1]){
   const value=await env.PUBLIC_DB.prepare('SELECT snapshot_json FROM public_experiences WHERE id=?').bind(Number(match[1])).first();
   if(!value)return response({error:'Experience not found'},404);
   const row=publicExperience(JSON.parse(value.snapshot_json));return row?response(row):response({error:'Invalid public projection'},503);
  }
  const where="(?='' OR EXISTS(SELECT 1 FROM json_each(targets_json) WHERE value=?)) AND instr(search_key,?)>0";
  const params=[t,t,q.toLowerCase()];
  const stats=await env.PUBLIC_DB.prepare('SELECT count(*) AS total,count(rating) AS rating_count,sum(rating) AS rating_sum FROM public_experiences WHERE '+where).bind(...params).first();
  if(stats.total>1000)return response({error:'Projection exceeds bounds'},503);
  const {results:criterionRows}=await env.PUBLIC_DB.prepare("SELECT c.key AS criterion,count(*) AS count,sum(c.value) AS total FROM public_experiences,json_each(snapshot_json,'$.criteria') AS c WHERE "+where+' GROUP BY c.key').bind(...params).all();
  const criteria=Object.fromEntries(criterionRows.map(r=>[r.criterion,{count:r.count,average:Math.floor(r.total*100/r.count+0.5)/100,low_sample:r.count<5}]));
  const canCompare=stats.rating_count>=5;
  const order=sort==='helpful'?'helpful DESC,id DESC':sort==='rating'&&canCompare?'rating DESC,id DESC':'id DESC';
  const {results}=await env.PUBLIC_DB.prepare('SELECT snapshot_json FROM public_experiences WHERE '+where+' ORDER BY '+order+' LIMIT 10 OFFSET ?').bind(...params,Number(off)).all();
  const items=results.map(r=>publicExperience(JSON.parse(r.snapshot_json)));
  if(items.some(r=>!r))return response({error:'Invalid public projection'},503);
  return response({items,next_offset:Number(off)+10<stats.total?Number(off)+10:null,
   stats:{criteria,rating_count:stats.rating_count,average:stats.rating_count?Math.floor(stats.rating_sum*100/stats.rating_count+0.5)/100:null,
    low_sample:stats.rating_count>0&&!canCompare,comparison_allowed:canCompare}});

 }catch{return response({error:'Experiences unavailable'},503);}
}
