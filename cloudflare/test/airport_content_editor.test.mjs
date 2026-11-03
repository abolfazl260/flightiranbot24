import test from "node:test";
import assert from "node:assert/strict";
import {BLOCK_TYPES,blockFromValues,emptyAirport,https,newSection,publishable,validateDetail,
 validateIndex} from "../../tools/airport-content-editor/model.mjs";
test("unlimited feature types can be added per airport using known render blocks",()=>{
 const page=emptyAirport("THR");
 page.sections.push(newSection("airport-videos","ویدیوها","video",50));
 page.sections.push(newSection("parking","پارکینگ","car",60));
 assert.deepEqual(page.sections.map(s=>s.id),["airport-videos","parking"]);
 assert.equal(validateDetail(page,["THR","MHD"]),true);
 assert.equal(Object.keys(BLOCK_TYPES).length,8);
});
test("public sections require verified data and source",()=>{
 const page=emptyAirport("THR"),s=newSection("baggage","بار مجاز","luggage",10);
 page.sections.push(s);
 s.blocks.push(blockFromValues("text",{text_fa:"قوانین را از ایرلاین بررسی کنید"}));
 s.status="published";
 assert.throws(()=>validateDetail(page),/تاریخ بررسی/);
 s.reviewed_at="2026-11-03T12:00:00Z";
 assert.throws(()=>validateDetail(page),/منبع/);
 s.source_urls.push("https://example.org/");
 assert.equal(validateDetail(page),true);
 assert.equal(publishable(page),true);
});
test("unsafe links and unapproved reviews rejected",()=>{
 assert.equal(https("javascript:alert(1)"),false);
 assert.equal(https("http://example.org/"),false);
 assert.throws(()=>blockFromValues("image",{url:"http://example.org/image.webp",alt_fa:"نمونه"}),/HTTPS/);
 assert.throws(()=>blockFromValues("experience",{id:"review-1",text_fa:"تجربه خوب در فرودگاه",
 rating:4,visit_date:"2026-11-01",approved:false}),/تأیید/);
});
test("map, flight board, video blocks normalize correctly",()=>{
 assert.deepEqual(blockFromValues("flight_board",{data_source:"iran_fids",direction:"both"}),
 {type:"flight_board",data_source:"iran_fids",direction:"both"});
 const map=blockFromValues("map",{title_fa:"ورودی",latitude:"35.66",longitude:"51.35",
 external_url:"https://maps.example.org/"});
 assert.equal(map.latitude,35.66);
 assert.throws(()=>blockFromValues("map",{title_fa:"خراب",latitude:"100",
 longitude:"51",external_url:"https://maps.example.org/"}),/نامعتبر/);
 const video=blockFromValues("video",{title_fa:"راهنمای سالن",
 url:"https://example.org/video",duration_seconds:"125"});
 assert.equal(video.duration_seconds,125);
});
test("index enforces canonical codes and safe detail path",()=>{
 const index={schema_version:1,airports:[{iata:"THR",detail_path:"details/THR.v1.json",enabled:false}]};
 assert.equal(validateIndex(index,["THR","IKA"]),true);
 index.airports[0].detail_path="../secrets.json";
 assert.throws(()=>validateIndex(index,["THR","IKA"]),/نامعتبر/);
});
