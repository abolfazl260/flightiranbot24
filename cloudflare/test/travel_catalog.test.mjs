import test from "node:test";
import assert from "node:assert/strict";
import {CATALOG_URL, approvedExternalUrl, approvedImageUrl,
  normalizePersian, filterWebsites, parseCatalog, fetchCatalog
} from "../../src/flightiran/webapp/static/travel-catalog.mjs";

const image = index => "images/site-"+index+".webp";
function fixture() {
  const categories=Array.from({length:8},(_,index)=>({
    id:"category_"+index,title_fa:"دسته "+index,order:index
  }));
  const websites=Array.from({length:26},(_,index)=>({
    id:"website_"+index,name_fa:"وب‌سایت "+index,
    description_fa:"منبع سفر و پرواز "+index,
    category_id:categories[index%8].id,
    url:"https://example"+index+".org/",image:image(index),
    order:index,enabled:true
  }));
  return {schema_version:1,categories,websites};
}
test("v1 shared catalog displays 26 distinct sites in 8 remotely defined categories",()=>{
  const parsed=parseCatalog(fixture());
  assert.equal(parsed.schemaVersion,1);
  assert.equal(parsed.categories.length,8);
  assert.equal(parsed.sites.length,26);
  assert.equal(new Set(parsed.sites.map(x=>x.id)).size,26);
  assert(parsed.sites.every(x=>x.image.startsWith(
    "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/travel-websites/images/")));
  assert.equal(filterWebsites(parsed.sites,"category_1","").length,4);
  assert.equal(filterWebsites(parsed.sites,"all","وب‌سایت ۲").length,1);
  assert.equal(parsed.sites[0].id,"website_0");
  assert.equal(parsed.sites[1].id,"website_8");
  assert.equal(parsed.sites[2].id,"website_16");
  assert.equal(parsed.sites[3].id,"website_24");
});
test("Persian search normalizes Arabic letter variants, diacritics and zero width joins",()=>{
  assert.equal(normalizePersian("كيش‌ سفر"),"کیش سفر");
  assert.equal(normalizePersian("سَفر"),"سفر");
  const sites=[{categoryId:"a",name:"كيش",description:"راهـنماي سفر",
    categoryName:"پرواز"}];
  assert.equal(filterWebsites(sites,"a","کیش").length,1);
  assert.equal(filterWebsites(sites,"all","غذا").length,0);
});
test("bad versions, malformed payloads, missing images, unknown categories and duplicate IDs fail closed",()=>{
  const invalid=[
    {...fixture(),schema_version:2},
    {...fixture(),websites:[]},
    {...fixture(),websites:[...fixture().websites,{...fixture().websites[0],url:"https://other.example/"}]},
    {...fixture(),websites:fixture().websites.map((w,i)=>i? w : {...w,enabled:"true"})},
    {...fixture(),websites:fixture().websites.map((w,i)=>i? w : {...w,category_id:"missing"})},
    {...fixture(),websites:fixture().websites.map((w,i)=>i? w : {...w,image:"https://example.com/evil.webp"})},
    {...fixture(),categories:[fixture().categories[0],fixture().categories[0]]},
  ];
  for(const raw of invalid) assert.throws(()=>parseCatalog(raw));
});
test("disabled items are filtered without altering stable IDs",()=>{
  const raw=fixture();
  raw.websites[3].enabled=false;
  const parsed=parseCatalog(raw);
  assert.equal(parsed.sites.length,25);
  assert(!parsed.sites.some(x=>x.id==="website_3"));
});
test("untrusted URL and image paths may never trigger arbitrary schemes or origins",()=>{
  for(const value of ["javascript:alert(1)","http://example.org/","https://user:pw@example.org",
    "data:image/svg+xml,foo","https://localhost/","https://127.0.0.1/"]) {
    assert.equal(approvedExternalUrl(value),null);
  }
  assert.equal(approvedExternalUrl("https://example.org/path?x=1"),
    "https://example.org/path?x=1");
  for(const value of ["../bad.webp","images/../bad.webp",
    "images/a.svg","images/a.webp?token=secret",
    "https://attacker.example/images/a.webp","//attacker.example/a.webp"]) {
    assert.equal(approvedImageUrl(value),null);
  }
  assert.equal(approvedImageUrl("images/site.webp"),
    CATALOG_URL.replace("catalog.v1.json","images/site.webp"));
});
test("network fetch goes only to approved GitHub URL with no Telegram or user credentials",async()=>{
  let args;
  const raw=fixture();
  const catalog=await fetchCatalog(async(url,opts)=>{
    args={url,opts};
    return new Response(JSON.stringify(raw),{headers:{"content-type":"application/json"}});
  },800,"reload");
  assert.equal(catalog.sites.length,26);
  assert.equal(args.url,CATALOG_URL);
  assert.equal(args.opts.credentials,"omit");
  assert.equal(args.opts.referrerPolicy,"no-referrer");
  assert.equal(args.opts.redirect,"error");
  assert.equal(args.opts.cache,"reload");
  assert.deepEqual(args.opts.headers,{"Accept":"application/json"});
  assert(!JSON.stringify(args).includes("initData"));
});
test("GitHub network failures and unsupported payloads are surfaced as retryable errors",async()=>{
  await assert.rejects(fetchCatalog(async()=>new Response("not found",{status:404})),
    /منتشر نشده/);
  await assert.rejects(fetchCatalog(async()=>new Response("not json")),/JSON/);
  await assert.rejects(fetchCatalog(async()=>new Response(JSON.stringify(
    {...fixture(),schema_version:99}))),/سازگار نیست/);
  await assert.rejects(fetchCatalog(async()=>{throw new TypeError("Failed to fetch")}),
    /ارتباط/);
});
