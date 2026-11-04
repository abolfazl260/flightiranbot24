import {fetchGuideJson} from './guide-catalog.mjs';
import {approvedExternalUrl,normalizePersian} from './travel-catalog.mjs';
export const VISA_CACHE='flightiran-public-visa-v1';
export const FIDS_HOME='https://fids.airport.ir/';
export const POPULAR_VISA=['TR','AE','DE','TH','GE','MY'];
export function filterCountries(rows,query) {
 const q=normalizePersian(query);return rows.filter(r=>normalizePersian(r.name+' '+r.code).includes(q));
}
function need(ok){if(!ok)throw new Error('نسخهٔ همراه ویزا معتبر یا کامل نیست.');}
function safeDate(s){if(s==null)return null;need(/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s)));return s;}
export function parseVisaSnapshot(bundle,passport) {
 const {manifest:m,shards}=bundle;need(m?.schema_version===1&&m.license==='CC-BY-4.0');
 need(Array.isArray(m.passport_codes)&&m.passport_codes.length===m.passports&&new Set(m.passport_codes).size===m.passports&&m.passport_codes.every(c=>/^[A-Z]{2}$/.test(c)));
 need(m.passports>0&&m.passports<=250&&m.destinations>0&&m.destinations<=250&&m.rows===m.passports*m.destinations);
 need(m.passport_codes.includes(passport)&&typeof m.attribution==='string'&&m.attribution.length>0);
 need(Array.isArray(m.shards)&&m.shards.length>0&&m.shards.length<=40&&new Set(m.shards).size===m.shards.length&&m.shards.every(s=>/^shard-\d{2}\.json$/.test(s)));
 need(Array.isArray(shards)&&shards.length===m.shards.length);const rules=[],seen=new Set();let count=0;
 for(const shard of shards){need(shard.version===1&&Array.isArray(shard.destinations));for(const d of shard.destinations){
  need(/^[A-Z]{2}$/.test(d.destination)&&!seen.has(d.destination)&&typeof d.country_name==='string');seen.add(d.destination);
  need(Array.isArray(d.rules)&&d.rules.length===m.passports);const passports=new Set();
  for(const row of d.rules){need(Array.isArray(row)&&row.length===7&&m.passport_codes.includes(row[0])&&!passports.has(row[0]));passports.add(row[0]);count++;
   need(typeof row[1]==='string'&&(row[2]===null||Number.isInteger(row[2])&&row[2]>=1&&row[2]<=36500));
   need(row[3]===null||typeof row[3]==='string');safeDate(row[5]);
   if(row[0]===passport)rules.push({passport,destination:d.destination,country_name:d.country_name,status:row[1],stay_days:row[2],notes:row[3],source_url:approvedExternalUrl(row[4]),verified_on:safeDate(row[5]),source_level:row[6],destination_updated_on:safeDate(d.updated_on)});
  }
 }}
 need(rules.length===m.destinations&&count===m.rows);
 return {passport,rules,passportCodes:m.passport_codes,attribution:m.attribution,sourceDataModifiedOn:safeDate(m.source_data_modified_on)};
}
export function createVisaSnapshotReader(fetcher=fetch,cacheStorage=globalThis.caches) {
 let bundle=null,pending=null,generation=0;
 const key='https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/android/app/src/main/assets/visa/manifest.v1.json';
 async function read(token){
  let cached=false;
  try{
   const manifest=await fetchGuideJson('android/app/src/main/assets/visa/manifest.v1.json',fetcher);
   need(Array.isArray(manifest.shards)&&manifest.shards.length<=40&&manifest.shards.every(s=>/^shard-\d{2}\.json$/.test(s)));
   const shards=new Array(manifest.shards.length);let next=0;
   await Promise.all(Array.from({length:4},async()=>{while(next<manifest.shards.length){const i=next++;shards[i]=await fetchGuideJson('android/app/src/main/assets/visa/'+manifest.shards[i],fetcher);}}));
   const data={manifest,shards};parseVisaSnapshot(data,manifest.passport_codes[0]);
   need(token===generation);
   try{const c=await cacheStorage?.open(VISA_CACHE);if(token===generation)await c?.put(key,new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}}));}catch{/* Storage is optional. */}
   return {data,cached};
  }catch(error){
   if(token!==generation)throw error;
   const c=await cacheStorage?.open(VISA_CACHE);const response=await c?.match(key);if(!response)throw error;
   const data=await response.json();parseVisaSnapshot(data,data.manifest.passport_codes[0]);return {data,cached:true};
  }
 }
 return {async get(passport){if(!bundle){const token=generation;pending??=read(token).finally(()=>{pending=null;});const result=await pending;need(token===generation);bundle=result;}
   return {...parseVisaSnapshot(bundle.data,passport),cached:bundle.cached};},
   async clear(){generation++;bundle=null;await pending?.catch(()=>{});pending=null;await cacheStorage?.delete(VISA_CACHE);}};
}
