/* Offline, browser/Node compatible model. No user data is transmitted. */
export const BLOCK_TYPES = {
  text:"متن", bullets:"فهرست موارد", link:"لینک", image:"تصویر",
  video:"ویدیو", map:"نقشه", flight_board:"تابلوی پرواز", experience:"تجربه تأییدشده"
};
export const FIELD_DEFS = {
  text:[["text_fa","متن فارسی","textarea",true]],
  bullets:[["items_fa","هر مورد در یک خط","textarea",true]],
  link:[["title_fa","عنوان لینک","text",true],["url","نشانی HTTPS","url",true]],
  image:[["url","نشانی تصویر HTTPS","url",true],["alt_fa","توضیح تصویر","text",true],["caption_fa","زیرنویس تصویر","text",false]],
  video:[["title_fa","عنوان ویدیو","text",true],["url","نشانی HTTPS ویدیو","url",true],
    ["thumbnail_url","نشانی کاور","url",false],["duration_seconds","مدت به ثانیه","number",false],
    ["attribution_fa","صاحب اثر","text",false]],
  map:[["title_fa","عنوان نقشه","text",true],["latitude","عرض جغرافیایی","number",true],
    ["longitude","طول جغرافیایی","number",true],["external_url","لینک نقشه HTTPS","url",true],
    ["image_url","نشانی تصویر نقشه","url",false]],
  flight_board:[["data_source","منبع","source",true],["direction","جهت پرواز","direction",true]],
  experience:[["id","شناسه ناشناس","text",true],["text_fa","متن بدون اطلاعات شخصی","textarea",true],
    ["rating","امتیاز ۱ تا ۵","number",true],["visit_date","تاریخ مراجعه","date",true],
    ["approved","تأیید مدیر و اجازه انتشار","checkbox",true]]
};
const IATA=/^[A-Z]{3}$/, SEC=/^[a-z][a-z0-9-]{1,79}$/, ICON=/^[a-z][a-z0-9-]{0,49}$/, REVIEW=/^[a-z0-9][a-z0-9_-]{1,79}$/;
function fail(m){throw new Error(m)}
const nonempty=v=>typeof v==="string"&&!!v.trim();
function txt(v,max,key){if(!nonempty(v)||v.length>max)fail("فیلد "+key+" الزامی یا طولانی است");return v.trim()}
function integer(v,min,max,key){const n=Number(v);if(v===""||!Number.isInteger(n)||n<min||n>max)fail("عدد نامعتبر: "+key);return n}
function real(v,min,max,key){const n=Number(v);if(v===""||!Number.isFinite(n)||n<min||n>max)fail("عدد نامعتبر: "+key);return n}
export function https(url){
 try{if(!nonempty(url)||/\s/.test(url))return false;const u=new URL(url);
 return u.protocol==="https:"&&!!u.hostname&&!u.username&&!u.password&&u.port!=="0"}
 catch{return false}
}
export function requireHttps(url){if(!https(url))fail("نشانی باید HTTPS معتبر باشد");return url}
export function emptyAirport(iata){if(!IATA.test(iata))fail("کد فرودگاه نامعتبر است");return {schema_version:1,iata,sections:[]}}
export function newSection(id,title,icon="info",order=100){
 if(!SEC.test(id)||!ICON.test(icon))fail("شناسه یا آیکون نامعتبر است");
 return {id,title_fa:txt(title,160,"عنوان"),icon,order:integer(order,0,10000,"ترتیب"),
 status:"draft",reviewed_at:null,source_urls:[],blocks:[]}
}
export function blockFromValues(type,values){
 if(!(type in BLOCK_TYPES))fail("نوع محتوا ناشناخته است");
 const o={type};
 for(const [key,label,kind,required] of FIELD_DEFS[type]){
  const v=values[key];
  if(kind==="checkbox"){o[key]=v===true;continue}
  if(!required&&(v===undefined||v===null||String(v).trim()===""))continue;
  if(kind==="url")o[key]=requireHttps(txt(v,2048,label));
  else if(kind==="number"){
   o[key]=key==="duration_seconds"?integer(v,1,86400,label):key==="rating"?integer(v,1,5,label):
    key==="latitude"?real(v,-90,90,label):real(v,-180,180,label)
  }else if(kind==="source"){if(v!=="iran_fids")fail("منبع نامعتبر");o[key]=v}
  else if(kind==="direction"){if(!["arrivals","departures","both"].includes(v))fail("جهت نامعتبر");o[key]=v}
  else if(kind==="date"){
   if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||Number.isNaN(Date.parse(v+"T00:00:00Z")))fail("تاریخ نامعتبر");
   o[key]=v;
  }else if(key==="items_fa"){
   const rows=(Array.isArray(v)?v:String(v??"").split(/\r?\n/)).map(x=>String(x).trim()).filter(Boolean);
   if(!rows.length||rows.length>100||rows.some(x=>x.length>1200))fail("فهرست نامعتبر");
   o[key]=rows;
  }else o[key]=txt(v,key==="text_fa"?8000:key==="alt_fa"?300:key==="caption_fa"?400:
    key==="attribution_fa"?300:key==="id"?80:180,label)
 }
 if(type==="experience"){
  if(!REVIEW.test(o.id)||o.text_fa.length<10||o.text_fa.length>2000)fail("تجربه نامعتبر است");
  if(!o.approved)fail("تجربه منتشرنشده باید ابتدا تأیید شود");
 }
 return o;
}
export function validateDetail(page,codes=null){
 if(!page||page.schema_version!==1||!IATA.test(page.iata))fail("ساختار صفحه نامعتبر است");
 if(codes&&!codes.includes(page.iata))fail("کد در کاتالوگ اصلی نیست");
 if(!Array.isArray(page.sections)||page.sections.length>100)fail("فهرست بخش‌ها نامعتبر است");
 const seen=new Set();
 for(const s of page.sections){
  if(!SEC.test(s.id)||seen.has(s.id))fail("شناسه تکراری یا نامعتبر");seen.add(s.id);
  txt(s.title_fa,160,"عنوان");
  if(!ICON.test(s.icon))fail("آیکون نامعتبر");
  integer(s.order,0,10000,"ترتیب");
  if(!["draft","published","archived"].includes(s.status))fail("وضعیت نامعتبر");
  if(!Array.isArray(s.source_urls)||s.source_urls.length>20||
    new Set(s.source_urls).size!==s.source_urls.length)fail("منابع نامعتبر");
  s.source_urls.forEach(requireHttps);
  if(s.reviewed_at!==null&&(!nonempty(s.reviewed_at)||Number.isNaN(Date.parse(s.reviewed_at))||
    !/^\d{4}-\d{2}-\d{2}T/.test(s.reviewed_at)))fail("تاریخ بررسی نامعتبر");
  if(!Array.isArray(s.blocks)||s.blocks.length>200)fail("تعداد بلوک‌ها نامعتبر");
  const reviews=new Set();
  for(const b of s.blocks){
   blockFromValues(b.type,{...b,items_fa:Array.isArray(b.items_fa)?b.items_fa.join("\n"):b.items_fa});
   if(b.type==="experience"){if(reviews.has(b.id))fail("تجربه تکراری");reviews.add(b.id)}
  }
  if(s.status==="published"){
   if(!s.blocks.length||!s.reviewed_at)fail("بخش منتشرشده نیازمند محتوا و تاریخ بررسی است");
   if(!s.source_urls.length&&s.blocks.some(x=>x.type!=="experience"))fail("بخش منتشرشده نیازمند منبع است");
  }
 }
 return true;
}
export function validateIndex(index,codes){
 if(!index||index.schema_version!==1||!Array.isArray(index.airports))fail("فهرست فرودگاه‌ها نامعتبر");
 const seen=new Set();
 for(const entry of index.airports){
  if(!IATA.test(entry.iata)||seen.has(entry.iata)||!codes.includes(entry.iata)||
   entry.detail_path!=="details/"+entry.iata+".v1.json"||typeof entry.enabled!=="boolean")fail("ورودی فرودگاه نامعتبر");
  seen.add(entry.iata);
 }
 return true;
}
export function publishable(page,codes=null){
 validateDetail(page,codes);
 if(!page.sections.some(s=>s.status==="published"))fail("برای فعال‌کردن فرودگاه ابتدا یک بخش معتبر منتشر کنید");
 return true;
}
export function prettyJson(o){return JSON.stringify(o,null,2)+"\n"}
