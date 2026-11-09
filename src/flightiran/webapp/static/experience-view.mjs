export function createExperienceView({root,el,request}){
 let target='',query='',sort='newest',offset=0,sequence=0,ownOffset=0;
 const button=(label,click)=>el('button',{type:'button',className:'tiny-button',onClick:click},label);
 const p=text=>el('p',{text}),message=text=>root.replaceChildren(p(text),button('تلاش دوباره',()=>load()),button('تجربه‌های من',()=>mine(0)),button('ثبت تجربه',()=>form()));
 const statsText=s=>s.rating_count===0?'هنوز رأی عددی تأییدشده‌ای ثبت نشده است.':
  `میانگین رضایت: ${new Intl.NumberFormat('fa-IR',{maximumFractionDigits:2}).format(s.average)} از ۵ · ${new Intl.NumberFormat('fa-IR').format(s.rating_count)} رأی`+(s.low_sample?' · نمونه کم؛ قابل رتبه‌بندی نیست':'');
 async function perform(path,body,method='POST'){
  try{return await request(path,{method,body});}
  catch(e){throw Error('درخواست تأیید نشد؛ پیش از تکرار، «تجربه‌های من» را بررسی کنید. '+e.message);}
 }
 async function load(nextTarget=target,nextOffset=offset){
  target=nextTarget;offset=nextOffset;const seq=++sequence;
  root.replaceChildren(p('در حال دریافت تجربه‌های منتشرشده…'));
  try{
   const data=await request('/api/v1/experiences?'+new URLSearchParams({target,q:query,sort,offset}));
   if(seq!==sequence)return;
   if(!data.stats.comparison_allowed&&sort==='rating')sort='newest';
   const search=el('input',{type:'search',value:query,placeholder:'جست‌وجوی متن تجربه'});
   const kind=el('select',{},...['airport','airline','country','route','flight'].map((v,i)=>el('option',{value:v,text:['فرودگاه','ایرلاین','کشور','مسیر پرواز','پرواز'][i]})));
   kind.value=target.split(':')[0]||'airport';
   const context=el('input',{value:target.split(':').slice(1).join(':'),placeholder:'کد یا شناسهٔ راهنمای انتخاب‌شده',dir:'ltr'});
   const order=el('select',{},...['newest','helpful','rating'].map((v,i)=>el('option',{value:v,text:['جدیدترین','مفیدترین','بالاترین رضایت'][i]})));
   order.value=sort;order.querySelector('[value="rating"]').disabled=!data.stats.comparison_allowed;
   order.addEventListener('change',()=>{sort=order.value;load(target,0)});
   const nodes=[p('تجربهٔ شخصی مسافر؛ نه مقررات رسمی یا ارزیابی ایمنی.'),p(statsText(data.stats)),
    el('div',{className:'field'},kind,context,search,order,button('اعمال فیلتر',()=>{target=context.value.trim()?kind.value+':'+context.value.trim():'';query=search.value.trim();load(target,0)})),
    el('div',{className:'row'},button('ثبت تجربه و رضایت',()=>form()),button('تجربه‌های من',()=>mine(0)))];
   if(!data.items.length)nodes.push(p('تجربهٔ دارای مجوز و تأیید انتشار برای این فیلتر موجود نیست.'));
   for(const row of data.items){
    const text=p(row.text);text.hidden=true;
    const card=el('article',{className:'panel'},el('h3',{text:row.display_name}),
     p(row.kind==='archive'?'گزارش آرشیوی با مجوز انتشار؛ تجربهٔ شخصی':'تجربهٔ منتشرشدهٔ مسافر'),
     p('تاریخ پیام: '+(row.posted_label||row.created_at)+' · تاریخ سفر: '+(row.travel_date||'مشخص نشده')),
     p(row.rating===null?'بدون رأی عددی':`رضایت کلی: ${new Intl.NumberFormat('fa-IR').format(row.rating)} از ۵`),
     ...Object.entries(row.criteria||{}).map(([k,v])=>p(({crew:'خدمه',seat:'صندلی',catering:'پذیرایی',cleanliness:'نظافت',delay_response:'رسیدگی به تأخیر',signage:'راهنمایی',queues:'صف',services:'خدمات'}[k]||k)+': '+v+' از ۵')),
     p(row.text.slice(0,160)+(row.text.length>160?'…':'')),button('متن کامل',()=>{text.hidden=!text.hidden}),text,
     p('مفید برای '+new Intl.NumberFormat('fa-IR').format(row.helpful)+' مسافر'),
     button('مفید بود',async()=>{try{await perform(`/api/mini/experiences/${row.id}/vote`,{helpful:true});load()}catch(e){alertText(e.message)}}),
     button('گزارش تخلف',()=>report(row.id)));
    nodes.push(card);
   }
   if(offset>0)nodes.push(button('قبلی',()=>load(target,Math.max(0,offset-10))));
   if(data.next_offset!==null)nodes.push(button('بعدی',()=>load(target,data.next_offset)));
   root.replaceChildren(...nodes);
  }catch(e){if(seq===sequence)message('دریافت تجربه‌ها ناموفق است. '+e.message);}
 }
 function alertText(text){root.prepend(el('p',{className:'status-strip warning',text}));}
 function form(row=null){
  ++sequence;
  const context=el('input',{type:'hidden',value:row?.targets?.join(',')||target});
  const contextList=el('div'),kind=el('select',{},...['airport','airline','country','route','flight'].map((v,i)=>el('option',{value:v,text:['فرودگاه','ایرلاین','کشور','مسیر پرواز','پرواز'][i]})));
  const code=el('input',{placeholder:'کد یا شناسهٔ راهنمای انتخاب‌شده',dir:'ltr'});
  const labels={airport:'فرودگاه',airline:'ایرلاین',country:'کشور',route:'مسیر',flight:'پرواز'};
  function showContexts(){contextList.replaceChildren();for(const t of context.value.split(',').filter(Boolean))contextList.append(el('p',{},(labels[t.split(':')[0]]||'زمینه')+' '+t.split(':').slice(1).join(':'),button('حذف',()=>{context.value=context.value.split(',').filter(v=>v!==t).join(',');showContexts();criteriaFields()})));}
  const contextPicker=el('div',{},p('از راهنمای فرودگاه یا ایرلاین می‌توانید با زمینهٔ آماده وارد شوید؛ زمینه‌های دیگر اختیاری‌اند.'),contextList,kind,code,button('افزودن زمینه',()=>{const t=kind.value+':'+code.value.trim();if(code.value.trim()){context.value=[...new Set([...context.value.split(',').filter(Boolean),t])].join(',');showContexts();criteriaFields();code.value=''}}),context);
  const name=el('input',{value:row?.display_name||'مسافر',maxlength:80,placeholder:'نام نمایشی دلخواه'});
  const body=el('textarea',{maxlength:1500,rows:8,placeholder:'تجربه واقعی خود را با ۲۰ تا ۱۵۰۰ نویسه بنویسید.'});body.value=row?.body||'';
  const rating=el('select',{},el('option',{value:'',text:'بدون امتیاز عددی'}),...[1,2,3,4,5].map(n=>el('option',{value:String(n),text:`رضایت کلی: ${n} از ۵`})));
  rating.value=row?.rating==null?'':String(row.rating);
  const date=el('input',{type:'date',value:row?.travel_date||''});
  const consent=el('input',{type:'checkbox'});consent.checked=row?.consent===true;
  const criteria=el('div'),criteriaInputs={};
  function criteriaFields(){criteria.replaceChildren();for(const k of Object.keys(criteriaInputs))delete criteriaInputs[k];
   const isAirline=context.value.includes('airline:'),isAirport=context.value.includes('airport:');
   const names={...(isAirline?{crew:'خدمه',seat:'صندلی',catering:'پذیرایی',cleanliness:'نظافت',delay_response:'رسیدگی به تأخیر'}:{}),...(isAirport?{cleanliness:'نظافت',signage:'راهنمایی',queues:'صف',services:'خدمات'}:{})};
   for(const [k,label]of Object.entries(names)){
    const select=el('select',{},el('option',{value:'',text:label+' (اختیاری)'}),...[1,2,3,4,5].map(n=>el('option',{value:String(n),text:String(n)})));
    select.value=row?.criteria?.[k]?String(row.criteria[k]):'';criteriaInputs[k]=select;criteria.append(select);
   }
  }
  context.addEventListener('input',criteriaFields);criteriaFields();showContexts();
  const submit=button('ارسال برای بررسی',async()=>{
   submit.disabled=true;
   try{const values={targets:context.value.split(',').map(s=>s.trim()).filter(Boolean),body:body.value,
    rating:rating.value?Number(rating.value):null,criteria:Object.fromEntries(Object.entries(criteriaInputs).filter(([,s])=>s.value).map(([k,s])=>[k,Number(s.value)])),
    consent:consent.checked,display_name:name.value||'مسافر',travel_date:date.value||null};
    await perform('/api/mini/experiences'+(row?'/'+row.id:''),values,row?'PATCH':'POST');
    await mine(0);alertText('تجربه ذخیره شد و تا بررسی و تأیید مجوز عمومی نمی‌شود.');
   }catch(e){alertText(e.message);submit.disabled=false;}
  });
  root.replaceChildren(el('h2',{text:row?'ویرایش تجربه':'ثبت تجربه'}),p('از درج شماره تماس، مدرک هویتی و اطلاعات خصوصی دیگران خودداری کنید. نام نمایشی و متن فقط با رضایت و پس از بررسی منتشر می‌شوند.'),
   contextPicker,el('label',{},'نام نمایشی',name),el('label',{},'متن',body),rating,criteria,
   el('label',{},'تاریخ سفر (اختیاری)',date),el('label',{},consent,'با انتشار همین متن و نام نمایشی، پس از بررسی، موافقم.'),submit,button('بازگشت',()=>load()));
 }
 async function mine(page=ownOffset){
  ownOffset=page;const seq=++sequence;root.replaceChildren(p('در حال دریافت تجربه‌های شما…'));
  try{const data=await request('/api/mini/experiences/mine?offset='+page);if(seq!==sequence)return;
   const nodes=[el('h2',{text:'تجربه‌های من'}),button('بازگشت به تجربه‌های منتشرشده',()=>load())];
   if(!data.items.length)nodes.push(p('هنوز تجربه‌ای ثبت نکرده‌اید.'));
   for(const row of data.items){
    let armed=false;const remove=button('حذف و پس‌گرفتن رضایت',async()=>{
     if(!armed){armed=true;remove.textContent='تأیید حذف و پس‌گرفتن رضایت';return;}
     try{await perform('/api/mini/experiences/'+row.id,undefined,'DELETE');await mine(page)}catch(e){alertText(e.message)}
    });
    nodes.push(el('article',{className:'panel'},p('وضعیت: '+({pending:'در انتظار بررسی',approved:'تأییدشده',rejected:'ردشده',deleted:'حذف‌شده'}[row.state]||row.state)),
     p(row.reason||''),p(row.body),button('ویرایش و ارسال مجدد برای بررسی',()=>form(row)),remove));
   }
   if(page>0)nodes.push(button('قبلی',()=>mine(Math.max(0,page-10))));if(data.next_offset!==null)nodes.push(button('بعدی',()=>mine(data.next_offset)));
   root.replaceChildren(...nodes);
  }catch(e){if(seq===sequence)message(e.message);}
 }
 function report(id){
  ++sequence;const reasons=el('select',{},...['spam','privacy','abuse','inaccurate','other'].map((v,i)=>el('option',{value:v,text:['هرزنامه','حریم خصوصی','توهین','اطلاعات نادرست','سایر'][i]})));
  root.replaceChildren(p('گزارش برای بررسی فرستاده می‌شود و عمومی نیست.'),reasons,button('ارسال گزارش',async()=>{
   try{await perform(`/api/mini/experiences/${id}/report`,{reason:reasons.value});await load();alertText('گزارش برای بررسی ثبت شد.')}catch(e){alertText(e.message)}
  }),button('انصراف',()=>load()));
 }
 async function openReview(id){
  const seq=++sequence;root.replaceChildren(p('در حال دریافت تجربه…'));
  try{const row=await request('/api/v1/experiences/'+id);if(seq!==sequence)return;
   root.replaceChildren(el('h2',{text:row.display_name}),p('تجربهٔ شخصی مسافر، نه مقررات رسمی.'),p(row.text),
    button('مفید بود',async()=>{try{await perform(`/api/mini/experiences/${id}/vote`,{helpful:true});alertText('رأی شما ثبت شد.')}catch(e){alertText(e.message)}}),
    button('گزارش تخلف',()=>report(id)),button('همه تجربه‌ها',()=>load('',0)));
  }catch(e){if(seq===sequence)message(e.message);}
 }
 return {load,open:t=>load(t,0),openReview};
}
