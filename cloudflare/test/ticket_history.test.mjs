import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {handleRequest} from '../src/worker.mjs';
import {validatedHistory} from '../src/ticket_history.mjs';
import {parseHistory} from '../../src/flightiran/webapp/static/ticket-history.mjs';
const shared=JSON.parse(fs.readFileSync(new URL('../../docs/fixtures/ticket-history-v1.json',import.meta.url)));
const now=Date.parse('2026-01-02T13:00:00Z');
test('shared year-boundary fixture retains calendar spacing, daily counts and gaps',()=>{
 const h=parseHistory(shared,now);
 assert.equal(h.min,100);assert.equal(h.max,300);assert.equal(h.samples,10);
 assert.equal(h.segments.length,2);assert.equal(h.points.length,4);assert.equal(h.points[0].x,22);assert.equal(h.points.at(-1).x,294);
 for(const points of [[],shared.points.slice(-1),shared.points.map(p=>({...p,price_toman:100}))]){
  const d={...shared,points,observed_at:points.at(-1)?.last_observed_at||null};const v=parseHistory(d,now);
  assert.equal(v.points.length,points.length);assert(v.points.every(p=>Number.isFinite(p.y)));
 }
 for(const p of [{...shared.points[0],price_toman:0},{...shared.points[0],sample_count:0},{...shared.points[0],day:'2025-12-12'}])
  assert.throws(()=>parseHistory({...shared,points:[p]},now));
 assert.throws(()=>parseHistory({...shared,points:[shared.points[0],shared.points[0]]},now));
 assert.equal(parseHistory({...shared,stale:true},now).stale,true);
 assert(validatedHistory(shared));
 assert.equal(validatedHistory({...shared,points:[{...shared.points[0],price_toman:-1}]}),null);
});
function env(){const rows=new Map();let writes=0;return {PUBLISH_TOKEN:'x'.repeat(48),rows,get writes(){return writes},PUBLIC_DB:{prepare(sql){let args=[];return {bind(...p){args=p;return this},async run(){if(sql.startsWith('DELETE'))return {meta:{changes:0}};assert.match(sql,/snapshot_json IS NOT/);const key=args.slice(0,2).join('/'),old=rows.get(key);if(old?.snapshot_json===args[4]||old?.observed_epoch_ms>args[3])return {meta:{changes:0}};rows.set(key,{snapshot_json:args[4],observed_epoch_ms:args[3],origin:args[0],destination:args[1],last_day:args[2]});writes++;return {meta:{changes:1}}},async first(){return rows.get(args.join('/'))||null},async all(){return {results:[...rows.values()].filter(r=>r.last_day>=args[0])}}}}}};}
const req=(path,body,auth=true)=>new Request('https://example.org'+path,body?{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer '+'x'.repeat(48)}:{})},body:JSON.stringify(body)}:{});
test('history publication is authenticated, idempotent, whitelist-only and public reads are bounded',async()=>{
 const e=env(),date=new Date().toISOString().slice(0,10),when=new Date().toISOString();
 const d={...shared,as_of:date,observed_at:when,points:[{day:date,price_toman:100,sample_count:3,last_observed_at:when}],user_id:'PRIVATE'};
 assert.equal((await handleRequest(req('/internal/v1/tickets/history',d,false),e)).status,401);
 assert.equal((await handleRequest(req('/internal/v1/tickets/history',d),e)).status,200);
 assert.equal((await handleRequest(req('/internal/v1/tickets/history',d),e)).status,200);assert.equal(e.writes,1);
 const r=await handleRequest(req('/api/v1/tickets/history?origin=A&destination=B'),e),body=await r.json();
 assert.equal(r.status,200);assert.equal(body.points.length,1);assert.equal(body.stale,false);assert(!JSON.stringify(body).includes('PRIVATE'));
 assert.equal((await handleRequest(req('/api/v1/tickets/history/routes'),e)).status,200);
 for(const path of ['/api/v1/tickets/history','/api/v1/tickets/history/routes?offset=-1','/api/v1/tickets/history?origin='+('x'.repeat(129))+'&destination=B'])
  assert.equal((await handleRequest(req(path),e)).status,400);
 assert.deepEqual((await (await handleRequest(req('/api/v1/tickets/history?origin=X&destination=Y'),e)).json()).points,[]);
 const broken={PUBLIC_DB:{prepare(){throw Error('offline')}}};assert.equal((await handleRequest(req('/api/v1/tickets/history?origin=A&destination=B'),broken)).status,503);
});
