import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createHmac} from 'node:crypto';
import {handleRequest} from '../src/worker.mjs';
import {publicExperience} from '../src/experiences.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('../../docs/fixtures/experiences-public-v1.json',import.meta.url)));
const TOKEN='x'.repeat(48),BOT='123456:TEST_SECRET_FOR_VALID_TELEGRAM_INIT_DATA';
function environment(){
 const db=new DatabaseSync(':memory:');
 for(const f of fs.readdirSync(new URL('../migrations/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())db.exec(fs.readFileSync(new URL('../migrations/'+f,import.meta.url),'utf8'));
 function stmt(sql,args=[]){return {bind(...values){return stmt(sql,values)},async run(){const r=db.prepare(sql).run(...args);return {meta:{changes:Number(r.changes)}}},async first(){return db.prepare(sql).get(...args)||null},async all(){return {results:db.prepare(sql).all(...args)}}};}
 return {db,PUBLISH_TOKEN:TOKEN,TELEGRAM_BOT_TOKEN:BOT,PUBLIC_DB:{prepare:stmt,async batch(statements){db.exec('BEGIN');try{const r=[];for(const s of statements)r.push(await s.run());db.exec('COMMIT');return r}catch(e){db.exec('ROLLBACK');throw e}}}};
}
const req=(path,body,auth=false,init=null,method=body?'POST':'GET')=>new Request('https://example.org'+path,{method,headers:{...(body?{'Content-Type':'application/json'}:{}),...(auth?{Authorization:'Bearer '+TOKEN}:{}),...(init?{'X-Telegram-Init-Data':init}:{})},...(body?{body:JSON.stringify(body)}:{})});
function signed(){const p=new URLSearchParams({auth_date:String(Math.floor(Date.now()/1000)),user:JSON.stringify({id:123,first_name:'Test'})});const secret=createHmac('sha256','WebAppData').update(BOT).digest();const text=[...p].sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>k+'='+v).join('\n');p.set('hash',createHmac('sha256',secret).update(text).digest('hex'));return p.toString();}
test('public experience validation rejects unapproved/invalid ratings and strips actor/archive/private fields',()=>{
 const r=fixture.items[0];assert.deepEqual(publicExperience({...r,owner_id:42,raw_source:'PRIVATE'}),r);
 for(const v of [{...r,state:'pending'},{...r,consent:false},{...r,rating:0},{...r,rating:1.5},{...r,kind:'archive'}])assert.equal(publicExperience(v),null);
 assert.equal(publicExperience({...r,kind:'archive',rating:null}).rating,null);
});
test('actual SQLite projection SQL: authenticated, no private fields, shared counts and withdrawal freshness gate',async()=>{
 const e=environment(),generated=new Date().toISOString(),body={generated_at:generated,record:{...fixture.items[0],owner_id:999}};
 assert.equal((await handleRequest(req('/internal/v1/experiences/record',body),e)).status,401);
 assert.equal((await handleRequest(req('/internal/v1/experiences/record',body,true),e)).status,200);
 assert.equal((await handleRequest(req('/internal/v1/experiences/commit',{generated_at:generated,ids:[1]},true),e)).status,200);
 const first=await handleRequest(req('/api/v1/experiences?target=airport:IKA'),e);assert.equal(first.status,200);assert.equal(first.headers.get('cache-control'),'no-store');
 const data=await first.json();assert.deepEqual(data,fixture);assert(!JSON.stringify(data).includes('owner_id'));
 const expired=new Date(Date.parse(generated)-1000).toISOString();assert.equal((await handleRequest(req('/internal/v1/experiences/record',{...body,generated_at:expired},true),e)).status,409);
 e.db.prepare('UPDATE experience_projection_meta SET expires_ms=0,invalid_after_ms=?').run(Date.parse(generated));
 assert.equal((await handleRequest(req('/api/v1/experiences'),e)).status,503);
 assert.equal((await handleRequest(req('/internal/v1/experiences/commit',{generated_at:generated,ids:[1]},true),e)).status,409);
 const newer=new Date(Date.parse(generated)+10).toISOString();assert.equal((await handleRequest(req('/internal/v1/experiences/commit',{generated_at:newer,ids:[]},true),e)).status,200);
 assert.equal((await (await handleRequest(req('/api/v1/experiences'),e)).json()).stats.average,null);
 assert.equal((await handleRequest(req('/api/v1/experiences/1'),e)).status,404);e.db.close();
});
test('Mini App review jobs are authenticated, sanitize identities, paginate own rows and invalidate after confirmed edits',async()=>{
 const e=environment(),user=signed(),payload={targets:['airport:IKA'],body:'A genuine twenty-character travel experience.',consent:true,rating:4,owner_id:999,state:'approved'};
 assert.equal((await handleRequest(req('/api/mini/experiences',payload),e)).status,401);
 const r=await handleRequest(req('/api/mini/experiences',payload,false,user),e);assert.equal(r.status,202);
 const job=e.db.prepare('SELECT * FROM telegram_mini_jobs').get();assert.equal(job.operation,'xp_create');assert.equal(job.telegram_id,123);assert(!job.payload_json.includes('owner_id'));assert(!job.payload_json.includes('approved'));
 assert.equal((await handleRequest(req('/api/mini/experiences/mine?offset=10',null,false,user),e)).status,202);
 assert.equal(JSON.parse(e.db.prepare("SELECT payload_json FROM telegram_mini_jobs WHERE operation='xp_mine'").get().payload_json).offset,10);
 e.db.prepare("UPDATE telegram_mini_jobs SET status='leased' WHERE id=?").run(job.id);
 const result={http_status:200,body:{id:1,state:'pending',experience_mutation:true,modified_at:new Date().toISOString()}};
 assert.equal((await handleRequest(req(`/internal/v1/mini/jobs/${job.id}/result`,result,true),e)).status,200);
 assert.equal(e.db.prepare('SELECT expires_ms FROM experience_projection_meta').get().expires_ms,0);e.db.close();
});
