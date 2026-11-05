import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseGuideIndex,parseGuideDetail,filterGuides,fetchGuideJson} from '../../src/flightiran/webapp/static/guide-catalog.mjs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../../'+p,import.meta.url),'utf8'));
const now=Date.parse('2026-11-05T00:00:00Z');
const detail=()=>read('data/airlines/details/emirates.v1.json');
test('shared Android airline data preserves identity, draft gates, fleet unknowns and no synthetic scores',()=>{
 const rows=parseGuideIndex(read('data/airlines/airline-index.v1.json'),'airlines',[],now);
 assert.equal(rows.length,2);assert.equal(filterGuides(rows,'ايران اير','iran')[0].id,'iran-air');
 assert.equal(filterGuides(rows,'uae','foreign')[0].id,'emirates');
 const p=parseGuideDetail(detail(),'airlines','emirates',now);
 assert.equal(p.sections.length,7);assert.equal(p.reviewCount,0);assert.equal(p.average,null);
 assert(p.sections.find(s=>s.id==='fleet').blocks.filter(b=>b.type==='fleet').every(b=>b.count===null));
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
 const draft=detail();const fleet=draft.sections.find(s=>s.id==='fleet');fleet.metadata.status='draft';fleet.blocks[1].count=19;fleet.blocks[1].metadata.status='draft';
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
