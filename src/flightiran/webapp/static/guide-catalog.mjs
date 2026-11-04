/* Shared Android JSON, read-only. Never send Telegram credentials to GitHub. */
import {approvedExternalUrl, normalizePersian} from './travel-catalog.mjs';
const BASE='https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/';
const idPattern=/^[a-z][a-z0-9-]{1,79}$/;
function need(ok) { if(!ok) throw new Error('ساختار راهنما معتبر نیست.'); }
function text(s) { need(typeof s==='string' && s.trim().length>0); return s; }
function url(s) { need(Boolean(approvedExternalUrl(s))); return s; }
function array(a, max=200) { need(Array.isArray(a)&&a.length<=max); return a; }
function date(s) { need(typeof s==='string' && Number.isFinite(Date.parse(s))); return Date.parse(s); }
function sources(a) { need(array(a,20).length>0); return a.map(url); }
function active(meta, now) {
  if(meta?.status!=='published'||meta.stale===true) return false;
  need(meta.stale===false && ['official','secondary'].includes(meta.confidence));
  need(date(meta.verified_at)<=now); sources(meta.source_urls);
  const start=meta.effective_from==null?-Infinity:date(meta.effective_from);
  const end=meta.effective_to==null?Infinity:date(meta.effective_to);
  need(start<=end); return now>=start&&now<=end;
}
export function parseGuideIndex(raw, kind, identities=[], now=Date.now()) {
  need(['airlines','airports'].includes(kind)&&raw?.schema_version===1);
  const seen=new Set();
  return array(raw[kind],1000).flatMap(row=>{
    const id=kind==='airlines'?row.airline_id:row.iata;
    need(typeof id==='string'&&(kind==='airlines'?idPattern.test(id):/^[A-Z]{3}$/.test(id))&&!seen.has(id));
    seen.add(id); need(row.detail_path===`details/${id}.v1.json`);
    if(kind==='airlines') {
      if(!active(row.metadata,now)) return [];
      const i=row.identity;
      const codes=array(i.codes,30).flatMap(c=>{
        need(c.system==='iata'?/^[A-Z0-9]{2}$/.test(c.value):c.system==='icao'&&/^[A-Z]{3}$/.test(c.value));
        const start=c.valid_from==null?-Infinity:date(c.valid_from), end=c.valid_to==null?Infinity:date(c.valid_to);
        need(start<=end); return now>=start&&now<=end?[c.value]:[];
      });
      return [{id,path:row.detail_path,name:text(i.name_fa),country:i.country,
        names:[text(i.name_en),text(i.legal_name),...array(i.aliases,30),...array(i.former_names,30),...codes],
        codes,website:url(i.website),reviewedAt:row.metadata.verified_at}];
    }
    need(typeof row.enabled==='boolean'); if(!row.enabled) return [];
    const i=identities.find(i=>i.code===id);
    return [{id,path:row.detail_path,name:i?.names?.fa||id,country:i?.country||'',
      names:Object.values(i?.names||{}),codes:[id]}];
  });
}
export function filterGuides(rows, query='', region='all') {
  const norm=s=>normalizePersian(s).replace(/\s/g,'');
  return rows.filter(r=>(region==='all'||(region==='iran'?r.country==='IR':r.country!==''&&r.country!=='IR'))&&
    [r.name,r.id,...r.names].some(s=>norm(s).includes(norm(query))));
}
function parseBlock(b, kind, now) {
  switch(b.type) {
    case 'text':return {type:'text',text:text(b.text_fa)};
    case 'bullets':need(array(b.items_fa,50).length>0);return {type:'bullets',items:b.items_fa.map(text)};
    case 'link':return {type:'link',title:text(b.title_fa),url:url(b.url)};
    case 'image':case 'video':
      if(kind==='airlines') {need(b.rights_verified===true);text(b.license);url(b.source_url);text(b.attribution_fa);}
      return {type:'link',title:text(b.title_fa||b.alt_fa),url:url(b.url),credit:b.attribution_fa||b.caption_fa};
    case 'map':return {type:'link',title:text(b.title_fa),url:url(b.external_url)};
    case 'airport_link':need(/^[A-Z]{3}$/.test(b.iata));return {type:'airport',id:b.iata,title:text(b.title_fa)};
    case 'fleet_snapshot': {
      if(kind!=='airlines'||!active(b.metadata,now))return null;
      need(date(b.observed_at)<=now && (b.count===null||Number.isSafeInteger(b.count)&&b.count>=0));
      need(['owned','operated','leased','unknown'].includes(b.relationship));
      need(['active','stored','leased-in','leased-out','retired','unknown'].includes(b.status));
      return {type:'fleet',model:text(b.model),manufacturer:text(b.manufacturer),count:b.count,
        observedAt:b.observed_at,status:b.status,relationship:b.relationship,
        configuration:b.configuration_fa,sources:sources(b.metadata.source_urls)};
    }
    case 'flight_board':return {type:'fids'};
    // The airport legacy experience block lacks explicit consent/privacy gates.
    // Never import its stars or personal text into the new public web reader.
    default:return null;
  }
}
export function parseGuideDetail(raw, kind, id, now=Date.now()) {
  need(raw?.schema_version===1 && (kind==='airlines'?raw.airline_id:raw.iata)===id);
  if(kind==='airlines'&&!active(raw.metadata,now))return null;
  const seen=new Set();
  const sections=array(raw.sections,100).flatMap(s=>{
    need(idPattern.test(s.id)&&!seen.has(s.id));seen.add(s.id);
    if(kind==='airlines'?!active(s.metadata,now):s.status!=='published')return [];
    const reviewedAt=kind==='airlines'?s.metadata.verified_at:s.reviewed_at;
    need(date(reviewedAt)<=now);
    const refs=sources(kind==='airlines'?s.metadata.source_urls:s.source_urls);
    if(s.kind==='policy')need(s.scope&&typeof s.scope.note_fa==='string');
    const blocks=array(s.blocks).map(b=>parseBlock(b,kind,now)).filter(Boolean);
    if(!blocks.length)return [];
    return [{id:s.id,title:text(s.title_fa),order:s.order,reviewedAt,sources:refs,scope:s.scope,blocks}];
  }).sort((a,b)=>a.order-b.order);
  const counts={overall:0,crew:0,seat:0,cleanliness:0,catering:0,checkin:0,baggage:0,value:0};
  const reviewIds=new Set();let reviewCount=0;
  if(kind==='airlines')for(const r of array(raw.published_reviews,1000)) {
    if(r.airline_id!==id||r.consent_status!=='granted'||r.moderation_status!=='approved'||
      r.verified_origin!==true||r.privacy_reviewed!==true||r.conflict_of_interest!==false)continue;
    need(idPattern.test(r.review_id)&&!reviewIds.has(r.review_id)); reviewIds.add(r.review_id);
    need(date(r.publication_timestamp)<=now&&r.ratings&&Object.keys(r.ratings).length>0);
    for(const [key,value] of Object.entries(r.ratings)) {
      need(Object.hasOwn(counts,key)&&Number.isInteger(value)&&value>=1&&value<=5);counts[key]++;
    }
    reviewCount++;
  }
  return {id,sections,reviewCount,counts,average:null};
}
export async function fetchGuideJson(path, fetcher=fetch) {
  need(/^(data\/(airlines|airports)\/(airline-index|airport-index)\.v1\.json|data\/(airlines|airports)\/details\/[A-Za-z0-9-]+\.v1\.json|src\/flightiran\/modules\/airport\/data\/airports\.json)$/.test(path));
  const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),10000);
  try {
    const r=await fetcher(BASE+path,{credentials:'omit',redirect:'error',referrerPolicy:'no-referrer',
      headers:{Accept:'application/json'},signal:abort.signal});
    need(r.ok);const max=path.includes('/details/')?512000:64000;
    const reader=r.body?.getReader();need(reader);let size=0;const chunks=[];
    try {while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;need(size<=max);chunks.push(value);}}
    finally {await reader.cancel();}
    const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
    return JSON.parse(new TextDecoder().decode(bytes));
  } finally {clearTimeout(timer);}
}
