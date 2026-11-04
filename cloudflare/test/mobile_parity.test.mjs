import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseVisaSnapshot,createVisaSnapshotReader,filterCountries,FIDS_HOME,VISA_CACHE} from '../../src/flightiran/webapp/static/mobile-parity.mjs';
const dir=new URL('../../android/app/src/main/assets/visa/',import.meta.url);
const manifest=JSON.parse(fs.readFileSync(new URL('manifest.v1.json',dir)));
const shards=manifest.shards.map(s=>JSON.parse(fs.readFileSync(new URL(s,dir))));
const bundle={manifest,shards};
test('Android visa snapshot preserves every destination, attribution, timestamps and unknowns',()=>{
 const p=parseVisaSnapshot(bundle,'IR');assert.equal(p.rules.length,manifest.destinations);assert.equal(p.passportCodes.length,199);
 assert.equal(p.sourceDataModifiedOn,manifest.source_data_modified_on);assert.equal(p.attribution,manifest.attribution);
 assert(p.rules.some(r=>r.destination==='TR'));assert.equal(new Set(p.rules.map(r=>r.destination)).size,p.rules.length);
 const d=shards.flatMap(s=>s.destinations)[0],row=d.rules.find(r=>r[0]==='IR');
 const first=p.rules.find(r=>r.destination===d.destination);assert.equal(first.notes,row[3]);assert.equal(first.verified_on,row[5]);assert.equal(first.destination_updated_on,d.updated_on);
});
test('invalid or incomplete snapshot and unknown passport fail closed',()=>{
 assert.throws(()=>parseVisaSnapshot(bundle,'ZZ'));
 assert.throws(()=>parseVisaSnapshot({...bundle,shards:shards.slice(1)},'IR'));
 assert.throws(()=>parseVisaSnapshot({...bundle,manifest:{...manifest,license:'unknown'}},'IR'));
 const invalid=structuredClone(bundle);invalid.shards[0].destinations[0].rules[0][2]=-1;
 assert.throws(()=>parseVisaSnapshot(invalid,'IR'));
});
test('public snapshot cache supports later offline reads, clear affects only its own cache',async()=>{
 const entries=new Map();let available=true,count=0;const deleted=[];
 const caches={async open(name){assert.equal(name,VISA_CACHE);return {async put(k,r){entries.set(k,await r.text());},async match(k){return entries.has(k)?new Response(entries.get(k)):undefined;}};},async delete(name){deleted.push(name);entries.clear();}};
 const fetcher=async(url,opts)=>{count++;assert.equal(opts.credentials,'omit');assert.deepEqual(opts.headers,{Accept:'application/json'});if(!available)throw new TypeError('offline');return new Response(fs.readFileSync(new URL(url.split('/visa/')[1],dir)));};
 const reader=createVisaSnapshotReader(fetcher,caches);assert.equal((await reader.get('IR')).cached,false);const initial=count;
 await reader.get('DE');assert.equal(count,initial);
 available=false;const restored=createVisaSnapshotReader(fetcher,caches);assert.equal((await restored.get('IR')).cached,true);
 await restored.clear();assert.deepEqual(deleted,[VISA_CACHE]);await assert.rejects(restored.get('IR'));
});
test('passport country search normalizes Persian letters and matches ISO codes',()=>{
 const countries=[{code:'IR',name:'ایران'},{code:'DE',name:'آلمان'}];assert.equal(filterCountries(countries,'ايران')[0].code,'IR');assert.equal(filterCountries(countries,'de')[0].code,'DE');assert.equal(FIDS_HOME,'https://fids.airport.ir/');
});
test('clearing during an in-flight snapshot cannot repopulate public storage',async()=>{
 let release,writes=0,deletes=0;
 const fetcher=async(url)=>url.endsWith('manifest.v1.json')?await new Promise(r=>{release=r;}):new Response(fs.readFileSync(new URL(url.split('/visa/')[1],dir)));
 const cache={async open(){return {async put(){writes++;},async match(){return undefined;}};},async delete(){deletes++;}};
 const reader=createVisaSnapshotReader(fetcher,cache);const pending=reader.get('IR');const clear=reader.clear();
 release(new Response(JSON.stringify(manifest)));await assert.rejects(pending);await clear;
 assert.equal(writes,0);assert.equal(deletes,1);
});
