import test from "node:test";
import assert from "node:assert/strict";
import { getIranFidsBoard, normalizeFidsPayload } from "../src/iran_fids.mjs";

const endpoint = "https://app.test/api/v1/iran/fids/THR/departures";
const configured = { FIDS_SOURCE_URL_TEMPLATE:
  "https://fids.airport.ir/api/board?airport={airport}&direction={direction}" };
const record = {
  flight_number:"IR123", airline:"هواپیمایی ایران",
  city:"مشهد", scheduled_time:"13:25", status:"طبق برنامه"
};
const response = (payload, type="application/json") =>
  new Response(JSON.stringify(payload), {status:200, headers:{"content-type":type}});
const get = (path=endpoint, env=configured, fetcher=async()=>response({flights:[record]})) =>
  getIranFidsBoard(new Request(path), env, fetcher);

test("fail closed before the official JSON endpoint is inspected and configured", async()=>{
  const result=await get(endpoint,{});
  assert.equal(result.status,503);
  assert.equal(result.headers.get("cache-control"),"no-store");
});
test("only approved Iranian airport and directions are allowed", async()=>{
  assert.equal((await get("https://app.test/api/v1/iran/fids/LHR/departures")).status,404);
  assert.equal((await get("https://app.test/api/v1/iran/fids/IKA/departures")).status,404);
  assert.equal((await get("https://app.test/api/v1/iran/fids/THR/bad")).status,400);
  assert.equal((await get(endpoint+"?source=https://evil.test")).status,400);
});
test("only exact official FIDS HTTPS host is permitted",async()=>{
  for(const template of [
    "https://evil.test/api/{airport}/{direction}",
    "http://fids.airport.ir/api/{airport}/{direction}",
    "https://fids.airport.ir.evil.test/{airport}/{direction}",
    "https://fids.airport.ir/{airport}/{unknown}/{direction}",
    "https://user@fids.airport.ir/{airport}/{direction}"
  ]) assert.equal((await get(endpoint,{FIDS_SOURCE_URL_TEMPLATE:template})).status,503);
});
test("sanitizes public flights, strips unknown private data, includes fetched time",async()=>{
  let inspected;
  const result=await get(endpoint,configured,async (url,opts)=>{
    inspected={url,opts};
    return response({airport:"THR",direction:"departures",flights:[
      {...record,phone:"secret",passenger_name:"secret"},
      {...record,flight_number:"IR124", gate:"8"}
    ]});
  });
  assert.equal(result.status,200);
  assert.equal(result.headers.get("cache-control"),"no-store");
  assert.equal(inspected.url,"https://fids.airport.ir/api/board?airport=THR&direction=departures");
  assert.equal(inspected.opts.redirect,"manual");
  const parsed=await result.json();
  assert.equal(parsed.airport,"THR");
  assert.equal(parsed.flights.length,2);
  assert.equal(parsed.flights[0].status,"طبق برنامه");
  assert.equal(parsed.flights[1].gate,"8");
  assert.equal(parsed.freshness,"unverified");
  assert.equal(parsed.source_updated_at,null);
  assert.ok(parsed.fetched_at.endsWith("Z"));
  assert.equal(JSON.stringify(parsed).includes("secret"),false);
});
test("upstream errors, HTML, bad JSON, unknown row fields and mismatch must fail",async()=>{
  for(const fetched of [
    async()=>new Response("error",{status:503}),
    async()=>new Response("<html></html>",{headers:{"content-type":"text/html"}}),
    async()=>response({unexpected:[]}),
    async()=>response({flights:[{}]}),
    async()=>response({airport:"MHD",flights:[record]}),
    async()=>response({flights:[{...record,scheduled_time:"not-a-time"}]}),
    async()=>response({flights:Array.from({length:251},()=>record)}),
    async()=>{throw Error("no network");}
  ]) assert.equal((await get(endpoint,configured,fetched)).status,503);
});
test("empty real board distinguished from unknown format",async()=>{
  const r=await get(endpoint,configured,async()=>response({airport:"THR",flights:[]}));
  assert.equal(r.status,200);
  assert.deepEqual((await r.json()).flights,[]);
});
test("freshness means a provider timestamp, never the app request time",()=>{
  const parsed=normalizeFidsPayload({flights:[record],updated_at:"2026-10-31T15:00:00Z"},
    "THR","arrivals","2026-11-01T10:00:00Z");
  assert.equal(parsed.freshness,"reported");
  assert.equal(parsed.source_updated_at,"2026-10-31T15:00:00Z");
});
