import {BLOCK_TYPES,FIELD_DEFS,blockFromValues,emptyAirport,newSection,
  prettyJson,publishable,validateDetail,validateIndex} from "./model.mjs";

const $=id=>document.getElementById(id);
const state={identities:[],index:null,page:null,selected:null,changedIndex:false};
const codes=()=>state.identities.map(a=>a.code);
function ui(tag,attributes={},content=null){
 const e=document.createElement(tag);
 for(const [key,value] of Object.entries(attributes)){
  if(key==="className")e.className=value;
  else if(key==="value")e.value=value;
  else if(key==="type")e.type=value;
  else if(key==="checked")e.checked=!!value;
  else if(key==="disabled")e.disabled=!!value;
  else if(key==="onClick")e.addEventListener("click",value);
  else if(key==="onChange")e.addEventListener("change",value);
  else if(key==="onInput")e.addEventListener("input",value);
  else e.setAttribute(key,value);
 }
 if(typeof content==="string")e.textContent=content;
 else if(Array.isArray(content))content.forEach(node=>e.append(node));
 return e;
}
function clear(element){element.replaceChildren()}
function notify(message,error=false){
 const e=$("notice");e.textContent=message;e.className="notice "+(error?"bad":"good");
}
const option=(v,name)=>ui("option",{value:String(v)},name);
function field(parent,title,value,change,kind="text",choices=[]){
 const wrap=ui("div",{className:"field"}),label=ui("label",{},title);
 let input;
 if(kind==="textarea")input=ui("textarea",{rows:"3",value:value??""});
 else if(kind==="select"||kind==="source"||kind==="direction"){
  input=ui("select");
  const items=kind==="source"?[["iran_fids","سامانه FIDS (اتصال داخلی)"]]:
   kind==="direction"?[["both","ورودی و خروجی"],["arrivals","ورودی"],["departures","خروجی"]]:choices;
  items.forEach(([id,name])=>input.append(option(id,name)));
  input.value=value;
 }else if(kind==="checkbox") input=ui("input",{type:"checkbox",checked:value});
 else input=ui("input",{type:kind==="number"?"number":kind==="date"?"date":kind==="url"?"url":"text",value:value??""});
 input.addEventListener(kind==="checkbox"||kind==="select"?"change":"input",()=>{
  change(kind==="checkbox"?input.checked:input.value);
 });
 wrap.append(label,input);parent.append(wrap);
 return input;
}
function download(file,payload){
 const content=prettyJson(payload),blob=new Blob([content],{type:"application/json;charset=utf-8"});
 const address=URL.createObjectURL(blob),a=ui("a",{href:address,download:file});
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(address),1500);
}
function check(){
 validateIndex(state.index,codes());validateDetail(state.page,codes());
 const entry=state.index.airports.find(a=>a.iata===state.page.iata);
 if(entry?.enabled)publishable(state.page,codes());
}
function exportDetail(){
 try{check();download(state.page.iata+".v1.json",state.page);
 notify("فایل دریافت شد. مسیر ثبت در گیت: data/airports/details/"+state.page.iata+".v1.json");}
 catch(e){notify(e.message,true)}
}
function exportIndex(){
 try{check();download("airport-index.v1.json",state.index);
 notify("کاتالوگ دریافت شد. مسیر ثبت در گیت: data/airports/airport-index.v1.json");}
 catch(e){notify(e.message,true)}
}
function selectedSection(){return state.page?.sections.find(s=>s.id===state.selected)}
function renderSections(){
 const list=$("section-list");clear(list);
 const sections=[...state.page.sections].sort((a,b)=>a.order-b.order||a.id.localeCompare(b.id));
 for(const section of sections){
  const button=ui("button",{className:"section-link "+(section.id===state.selected?"selected":""),
    onClick:()=>{state.selected=section.id;render();}});
  const badge=ui("small",{},section.status==="published"?"منتشرشده":section.status==="archived"?"بایگانی":"پیش‌نویس");
  button.append(ui("strong",{},section.title_fa),badge);
  list.append(button);
 }
 if(!sections.length)list.append(ui("p",{className:"hint"},"هنوز بخشی برای این فرودگاه ثبت نشده است."));
}
function renderBlockForm(root,type,original,save,cancel){
 clear(root);
 const wrapper=ui("div",{className:"block-form"}),values={...original};
 wrapper.append(ui("h3",{},"اطلاعات "+BLOCK_TYPES[type]));
 for(const [name,label,kind] of FIELD_DEFS[type]){
  const initial=values[name]??(kind==="source"?"iran_fids":kind==="direction"?"both":kind==="checkbox"?false:"");
  field(wrapper,label,Array.isArray(initial)?initial.join("\n"):initial,v=>{values[name]=v;},kind);
  if(values[name]===undefined)values[name]=initial;
 }
 const row=ui("div",{className:"btnline"});
 row.append(
  ui("button",{className:"primary",onClick:()=>{
   try{const block=blockFromValues(type,values);save(block);notify("محتوا ثبت شد. برای ثبت در GitHub خروجی JSON بگیرید.");}
   catch(e){notify(e.message,true)}
  }},"ثبت محتوا"),
  ui("button",{onClick:cancel},"انصراف")
 );
 wrapper.append(row);root.append(wrapper);
}
function renderEditor(){
 const box=$("section-editor"),empty=$("editor-empty"),section=selectedSection();
 clear(box);box.hidden=!section;empty.hidden=!!section;
 if(!section)return;
 const top=ui("div",{className:"row"});
 top.append(ui("h2",{},"ویرایش: "+section.title_fa),
 ui("button",{className:"danger minor",onClick:()=>{
  if(!confirm("این بخش به همراه همه بلوک‌ها حذف شود؟"))return;
  state.page.sections=state.page.sections.filter(s=>s!==section);
  state.selected=state.page.sections[0]?.id??null;render();
 }},"حذف بخش"));
 box.append(top);
 const grid=ui("div",{className:"edit-grid"});
 field(grid,"عنوان بخش",section.title_fa,v=>{section.title_fa=v;renderSections();renderPreview()});
 field(grid,"شناسه تغییرناپذیر",section.id,()=>{});
 field(grid,"آیکون (Lucide)",section.icon,v=>{section.icon=v;});
 field(grid,"ترتیب نمایش",section.order,v=>{section.order=Number(v);renderSections()},"number");
 box.append(grid);
 field(box,"توضیح کوتاه",section.subtitle_fa??"",v=>{
  if(v.trim())section.subtitle_fa=v;
  else delete section.subtitle_fa;
  renderPreview();
 });
 field(box,"وضعیت انتشار",section.status,v=>{section.status=v;renderSections();renderPreview();},
  "select",[["draft","پیش‌نویس"],["published","منتشرشده"],["archived","بایگانی‌شده"]]);
 field(box,"آدرس منابع HTTPS (هر منبع در یک خط)",section.source_urls.join("\n"),v=>{
  section.source_urls=v.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
 },"textarea");
 const reviewed=ui("div",{className:"btnline"});
 reviewed.append(ui("span",{className:"statusline"},section.reviewed_at?"بازبینی: "+section.reviewed_at:"هنوز بازبینی نشده"),
 ui("button",{className:"minor",onClick:()=>{
  section.reviewed_at=new Date().toISOString();renderEditor();
 }},"ثبت تاریخ بررسی امروز"));
 box.append(reviewed,ui("div",{className:"divider"}));
 box.append(ui("h2",{},"بلوک‌های محتوا"));
 const cards=ui("div");
 section.blocks.forEach((block,index)=>{
  const card=ui("div",{className:"block-card"});
  const heading=ui("div",{className:"row"});
  heading.append(ui("strong",{},String(index+1)+". "+(BLOCK_TYPES[block.type]||block.type)));
  const controls=ui("div",{className:"btnline"});
  controls.append(ui("button",{className:"minor",onClick:()=>{
   renderBlockForm(card,block.type,block,changed=>{
    section.blocks[index]=changed;renderEditor();renderPreview();
   },renderEditor);
  }},"ویرایش"),ui("button",{className:"minor danger",onClick:()=>{
   section.blocks.splice(index,1);renderEditor();renderPreview();
  }},"حذف"));
  heading.append(controls);
  card.append(heading,ui("p",{className:"hint"},block.text_fa||
   block.title_fa||block.items_fa?.join("، ")||block.url||"اطلاعات ساختاریافته"));
  cards.append(card);
 });
 box.append(cards);
 const addRow=ui("div",{className:"btnline"}),types=ui("select");
 Object.entries(BLOCK_TYPES).forEach(([id,label])=>types.append(option(id,label)));
 const add=ui("button",{onClick:()=>{
  renderBlockForm(formBox,types.value,{},b=>{
   section.blocks.push(b);renderEditor();renderPreview();
  },()=>clear(formBox));
 }},"افزودن بلوک +");
 addRow.append(types,add);box.append(addRow);
 const formBox=ui("div");box.append(formBox);
}
function renderPreview(){
 const root=$("preview-body");clear(root);
 if(!state.page)return;
 root.append(ui("h3",{},"فرودگاه "+state.page.iata));
 for(const section of [...state.page.sections].sort((a,b)=>a.order-b.order)){
  const card=ui("div",{className:"preview-item"});
  const head=ui("div",{className:"row"});
  head.append(ui("strong",{},section.title_fa),
  ui("span",{className:"pill "+section.status},section.status==="published"?"انتشار":section.status==="draft"?"پیش‌نویس":"بایگانی"));
  card.append(head,ui("p",{},section.subtitle_fa??""));
  section.blocks.slice(0,6).forEach(b=>card.append(ui("p",{},
   "• "+(BLOCK_TYPES[b.type]||b.type)+": "+String(b.title_fa||b.text_fa||b.url||"داده ثبت‌شده").slice(0,90))));
  root.append(card);
 }
 if(!state.page.sections.length)root.append(ui("p",{className:"hint"},"بخشی تعریف نشده است."));
}
function render(){
 if(!state.page)return;
 $("airport-state").textContent="کد: "+state.page.iata+" · "+state.page.sections.length+" بخش";
 const entry=state.index.airports.find(a=>a.iata===state.page.iata);
 $("airport-enabled").disabled=false;
 $("airport-enabled").checked=!!entry?.enabled;
 $("download-detail").disabled=false;$("download-index").disabled=false;
 $("add-section").disabled=false;
 renderSections();renderEditor();renderPreview();
}
function createSection(){
 const root=$("section-create");clear(root);
 const form=ui("div",{className:"block-form"}),values={};
 field(form,"شناسه انگلیسی، مانند parking","",v=>values.id=v);
 field(form,"عنوان فارسی","",v=>values.title=v);
 field(form,"آیکون (پیش‌فرض info)","info",v=>values.icon=v);
 field(form,"ترتیب نمایش","100",v=>values.order=v,"number");
 const row=ui("div",{className:"btnline"});
 row.append(ui("button",{className:"primary",onClick:()=>{
  try{const id=values.id?.trim();
   if(state.page.sections.some(s=>s.id===id))throw Error("شناسه بخش تکراری است");
   const section=newSection(id,values.title,values.icon||"info",values.order??100);
   state.page.sections.push(section);state.selected=section.id;clear(root);render();
   notify("بخش جدید به‌صورت پیش‌نویس اضافه شد");
  }catch(e){notify(e.message,true)}
 }},"ایجاد پیش‌نویس"),ui("button",{onClick:()=>clear(root)},"انصراف"));
 form.append(row);root.append(form);
}
async function getJson(path){
 const response=await fetch(path,{cache:"no-store",credentials:"omit"});
 if(!response.ok)throw Error("HTTP "+response.status+" for "+path);
 return response.json();
}
async function choose(code){
 try{
  const entry=state.index.airports.find(a=>a.iata===code);
  state.page=entry?await getJson("/data/airports/"+entry.detail_path):emptyAirport(code);
  validateDetail(state.page,codes());
  if(!entry){
   state.index.airports.push({iata:code,detail_path:"details/"+code+".v1.json",enabled:false});
   state.index.airports.sort((a,b)=>a.iata.localeCompare(b.iata));
   state.changedIndex=true;
   notify("برای این فرودگاه پرونده جدید ایجاد شد؛ هر دو فایل «فرودگاه» و «کاتالوگ» را خروجی بگیرید.");
  }else notify("اطلاعات محلی "+code+" بارگذاری شد. تغییرات تا دریافت فایل JSON ذخیره نخواهند شد.");
  state.selected=state.page.sections[0]?.id??null;render();
 }catch(e){notify("بارگذاری این فرودگاه ناموفق بود: "+e.message,true)}
}
async function start(){
 try{
  const [identities,index]=await Promise.all([
   getJson("/src/flightiran/modules/airport/data/airports.json"),
   getJson("/data/airports/airport-index.v1.json")
  ]);
  if(!Array.isArray(identities)||!identities.every(a=>/^[A-Z]{3}$/.test(a.code)))throw Error("فهرست کدها معتبر نیست");
  state.identities=identities;state.index=index;validateIndex(index,codes());
  const select=$("airport-choice");clear(select);
  identities.forEach(a=>select.append(option(a.code,(a.names?.fa||a.names?.en||a.code)+" ("+a.code+")")));
  select.disabled=false;select.addEventListener("change",()=>choose(select.value));
  $("add-section").addEventListener("click",createSection);
  $("airport-enabled").addEventListener("change",event=>{
   const entry=state.index.airports.find(a=>a.iata===state.page.iata);
   if(event.target.checked)try{publishable(state.page,codes());entry.enabled=true}
   catch(e){event.target.checked=false;notify(e.message,true);return}
   else entry.enabled=false;
   state.changedIndex=true;notify("وضعیت انتشار کاتالوگ تغییر کرد؛ فایل آن را نیز خروجی بگیرید");
  });
  $("download-detail").addEventListener("click",exportDetail);
  $("download-index").addEventListener("click",exportIndex);
  await choose(index.airports[0]?.iata||identities[0].code);
  select.value=state.page.iata;
 }catch(e){notify("امکان بارگذاری وجود ندارد. از ریشه پروژه با دستور python -m http.server 8787 --bind 127.0.0.1 اجرا کنید. "+e.message,true)}
}
start();
