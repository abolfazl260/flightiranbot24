import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseGuideIndex,parseGuideDetail,filterGuides,fetchGuideJson} from '../../src/flightiran/webapp/static/guide-catalog.mjs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../../'+p,import.meta.url),'utf8'));
const now=Date.parse('2026-11-11T00:00:00Z');
const detail=()=>read('data/airlines/details/emirates.v1.json');
test('shared Android airline data preserves identity, draft gates, fleet unknowns and no synthetic scores',()=>{
 const rows=parseGuideIndex(read('data/airlines/airline-index.v1.json'),'airlines',[],now);
 assert.equal(rows.length,5);assert.equal(filterGuides(rows,'ايران اير','iran')[0].id,'iran-air');
 assert.equal(filterGuides(rows,'ماهان','iran')[0].id,'mahan-air');
 assert.equal(filterGuides(rows,'آسمان','iran')[0].id,'iran-aseman');
 assert.equal(filterGuides(rows,'ایران ایرتور','iran')[0].id,'iran-airtour');
 assert.equal(filterGuides(rows,'uae','foreign')[0].id,'emirates');
 for (const [id,available,drafted,fleetCount] of [['mahan-air',19,1,6],['iran-aseman',14,4,5],['iran-airtour',13,6,6]]) {
  const d=read('data/airlines/details/'+id+'.v1.json');
  assert.equal(d.sections.filter(s=>s.metadata.status==='draft').length,drafted);
  const parsed=parseGuideDetail(d,'airlines',id,now);
  assert.equal(parsed.sections.length,available);
  assert.equal(parsed.reviewCount,0);
  assert.equal(parsed.average,null);
  const models=parsed.sections.find(s=>s.id==='fleet').blocks.filter(b=>b.type==='fleet');
  assert.equal(models.length,fleetCount);
  assert(models.every(b=>b.count===null && b.status==='unknown' && b.relationship==='unknown'));
  assert(!parsed.sections.some(s=>s.id==='onboard-connectivity'));
  if(id==='iran-airtour')assert(!parsed.sections.some(s=>s.id==='checkin'));

 }
 const p=parseGuideDetail(detail(),'airlines','emirates',now);
 assert.equal(p.sections.length,18);assert.equal(p.reviewCount,0);assert.equal(p.average,null);
 const fleet=p.sections.find(s=>s.id==='fleet').blocks.filter(b=>b.type==='fleet');
 assert.equal(fleet.reduce((n,b)=>n+b.count,0),277);assert(fleet.every(b=>b.status==='unknown'));
});
test('all enabled airport guides parse independently without importing legacy personal reviews',()=>{
 const rows=parseGuideIndex(read('data/airports/airport-index.v1.json'),'airports',read('src/flightiran/modules/airport/data/airports.json'),now);
 assert(rows.length>=28);
 for(const r of rows){const p=parseGuideDetail(read('data/airports/'+r.path),'airports',r.id,now);assert(p.sections.length>0);assert(!JSON.stringify(p).includes('"type":"experience"'));}
});
test('archived, expired, stale and unknown sections fail closed without hiding valid sections',()=>{
 const d=detail();d.metadata.status='archived';assert.equal(parseGuideDetail(d,'airlines','emirates',now),null);
 const s=detail();s.sections[0].metadata.stale=true;s.sections[1].metadata.effective_to='2020-01-01T00:00:00Z';
 s.sections[2].blocks=[{type:'future'}];const p=parseGuideDetail(s,'airlines','emirates',now);
 assert(!p.sections.some(s=>['baggage','ticket-rules','checkin'].includes(s.id)));
 const draft=detail();const fleet=draft.sections.find(s=>s.id==='fleet');fleet.metadata.status='draft';const snapshot=fleet.blocks.find(b=>b.type==='fleet_snapshot');snapshot.count=19;snapshot.metadata.status='draft';
 assert(!parseGuideDetail(draft,'airlines','emirates',now).sections.some(s=>s.id==='fleet'));
});
test('identity mismatch, duplicate sections, missing sources and unsafe links are rejected',()=>{
 assert.throws(()=>parseGuideDetail(detail(),'airlines','other',now));
 for(const mutate of [d=>d.sections.push(d.sections[0]),d=>d.sections[0].metadata.source_urls=[],d=>d.sections[0].blocks=[{type:'link',title_fa:'bad',url:'javascript:alert(1)'}]]){
 const d=detail();mutate(d);assert.throws(()=>parseGuideDetail(d,'airlines','emirates',now));}
});
test('only explicit consented ratings contribute counts, with separate criterion denominators',()=>{
 const d=detail();const r={review_id:'fixture-vote',airline_id:'emirates',consent_status:'granted',moderation_status:'approved',verified_origin:true,privacy_reviewed:true,conflict_of_interest:false,publication_timestamp:'2026-11-04T00:00:00Z',ratings:{crew:4}};
 d.published_reviews=[r];const p=parseGuideDetail(d,'airlines','emirates',now);assert.equal(p.reviewCount,1);assert.equal(p.counts.crew,1);assert.equal(p.counts.overall,0);assert.equal(p.average,null);
 r.consent_status='unknown';assert.equal(parseGuideDetail(d,'airlines','emirates',now).reviewCount,0);
 r.consent_status='granted';r.ratings.crew=4.5;assert.throws(()=>parseGuideDetail(d,'airlines','emirates',now));
});
test('bounded remote reads use exact public paths without Telegram credentials',async()=>{
 let request;const result=await fetchGuideJson('data/airlines/airline-index.v1.json',async(...args)=>{request=args;return new Response(JSON.stringify({schema_version:1}));});
 assert.equal(result.schema_version,1);assert.equal(request[1].credentials,'omit');assert.deepEqual(request[1].headers,{Accept:'application/json'});
 for(const path of ['../secrets','data/airlines/details/../../x.v1.json'])await assert.rejects(fetchGuideJson(path));
 await assert.rejects(fetchGuideJson('data/airlines/airline-index.v1.json',async()=>new Response('x'.repeat(65000))));
});

test('dated route snapshots preserve unknown operator and hide stale or expired observations',()=>{
 const d=detail(), network=d.sections.find(s=>s.id==='network');
 let page=parseGuideDetail(d,'airlines','emirates',now);
 const routes=page.sections.find(s=>s.id==='network').blocks.filter(b=>b.type==='route');
 assert.equal(routes.length,2);
 const tehran=routes.find(b=>b.destination==='IKA');
 assert.equal(tehran.status,'listed');assert.equal(tehran.operatingCarrier,null);assert.equal(tehran.serviceType,'unknown');
 const raw=network.blocks.find(b=>b.type==='route_snapshot');raw.metadata.stale=true;
 page=parseGuideDetail(d,'airlines','emirates',now);
 assert.equal(page.sections.find(s=>s.id==='network').blocks.filter(b=>b.type==='route').length,1);
 raw.metadata.stale=false;raw.metadata.effective_to='2026-11-09T00:00:00Z';
 assert.equal(parseGuideDetail(d,'airlines','emirates',now).sections.find(s=>s.id==='network').blocks.filter(b=>b.type==='route').length,1);
 raw.metadata.effective_to=null;raw.destination=raw.origin;
 assert.throws(()=>parseGuideDetail(d,'airlines','emirates',now));
 raw.destination='LHR';raw.observed_at='2099-01-01T00:00:00Z';
 assert.throws(()=>parseGuideDetail(d,'airlines','emirates',now));
});

test('review age warns after thirty days without inventing legal expiry',()=>{
 const d=detail(), later=Date.parse('2026-12-11T00:00:01Z');
 assert.equal(parseGuideDetail(d,'airlines','emirates',now).sections.find(s=>s.id==='network').reviewOverdue,false);
 assert.equal(parseGuideDetail(d,'airlines','emirates',later).sections.find(s=>s.id==='network').reviewOverdue,true);
});
