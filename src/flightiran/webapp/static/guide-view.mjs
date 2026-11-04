import {fetchGuideJson,parseGuideIndex,parseGuideDetail,filterGuides} from './guide-catalog.mjs';
export function createGuideView({kind,root,el,openUrl,onAirport,onFids,fetcher=fetch}) {
  let rows=null,selected=null,sectionId=null,page=null,offline=false,sequence=0;
  const pages=new Map(),positions=new Map();let directoryDate=null;
  const button=(title,fn)=>el('button',{type:'button',className:'secondary-cta',onClick:fn},title);
  const key=()=>`${selected||'list'}/${sectionId||'overview'}`;
  const save=()=>positions.set(key(),window.scrollY);
  const restore=()=>requestAnimationFrame(()=>window.scrollTo(0,positions.get(key())||0));
  const date=s=>s?new Intl.DateTimeFormat('fa-IR',{dateStyle:'medium'}).format(new Date(s)):'ثبت نشده';
  const p=s=>el('p',{text:s});
  const link=(title,target)=>button(title,()=>openUrl(target));
  function status(message,retry=false) {
    root.replaceChildren(p(message),...(selected?[button('بازگشت',back)]:[]),...(retry?[button('تلاش دوباره',()=>load(true))]:[]));
  }
  async function directory(force=false) {
    if(rows&&!force)return;
    const raw=await fetchGuideJson(`data/${kind}/${kind==='airlines'?'airline':'airport'}-index.v1.json`,fetcher);
    const identities=kind==='airports'?await fetchGuideJson('src/flightiran/modules/airport/data/airports.json',fetcher):[];
    rows=parseGuideIndex(raw,kind,identities);directoryDate=new Date().toISOString();
  }
  async function load(force=false) {
    const seq=++sequence;status('در حال دریافت راهنما…');offline=false;
    try {
      await directory(force);if(seq!==sequence)return;
      if(selected) {
        const ref=rows.find(r=>r.id===selected);
        if(!ref){page=null;render();return;}
        if(pages.has(selected)&&!force)page=parseGuideDetail(pages.get(selected),kind,selected);
        else {
          const raw=await fetchGuideJson(`data/${kind}/${ref.path}`,fetcher);
          const parsed=parseGuideDetail(raw,kind,ref.id);
          pages.set(ref.id,raw);if(seq!==sequence)return;page=parsed;
        }
      }
      render();
    }catch {
      if(seq!==sequence)return;
      if(rows&&(!selected||pages.has(selected))) {
        page=selected?parseGuideDetail(pages.get(selected),kind,selected):null;offline=true;render();
      } else status('راهنما در دسترس نیست؛ اتصال اینترنت را بررسی کنید.',true);
    }
  }
  function open(id){save();selected=id;sectionId=null;page=null;load();}
  function back(){save();++sequence;if(sectionId)sectionId=null;else if(selected){selected=null;page=null;}else return false;render();return true;}
  function block(b) {
    if(b.type==='text')return p(b.text);
    if(b.type==='bullets')return el('ul',{},b.items.map(s=>el('li',{text:s})));
    if(b.type==='link')return el('div',{},link(b.title,b.url),b.credit?p(b.credit):null);
    if(b.type==='airport')return button(b.title+' · '+b.id,()=>onAirport(b.id));
    if(b.type==='fids')return button('مشاهده وضعیت پروازها',onFids);
    if(b.type==='fleet') {
      const relation={owned:'ملکی',operated:'بهره‌برداری',leased:'اجاره‌ای',unknown:'نامعلوم'};
      const status={active:'فعال',stored:'پارک‌شده','leased-in':'اجاره ورودی','leased-out':'اجاره خروجی',retired:'بازنشسته',unknown:'تأیید نشده'};
      return el('article',{className:'panel guide-fleet'},el('h3',{text:b.manufacturer+' '+b.model}),
        p('تعداد: '+(b.count===null?'تأیید نشده':new Intl.NumberFormat('fa-IR').format(b.count))),
        p('تاریخ مشاهده: '+date(b.observedAt)),p('نوع رابطه: '+relation[b.relationship]+' · وضعیت: '+status[b.status]),
        b.configuration?p(b.configuration):null,p('نوع هواپیما و چیدمان روز سفر باید جداگانه تأیید شود.'),
        b.sources.map(s=>link('مرجع ناوگان',s)));
    }
  }
  function render() {
    const nodes=[];
    if(offline)nodes.push(el('div',{className:'website-warning',role:'status'},
      'داده تازه دریافت نشد؛ نسخهٔ همین نشست نمایش داده می‌شود. آخرین دریافت فهرست: '+date(directoryDate)+
      '؛ تاریخ بررسی هر بخش درج شده است. پیش از سفر مرجع رسمی را بررسی کنید.'));
    if(!selected) {
      const search=el('input',{type:'search',value:root.dataset.query||'','aria-label':'جست‌وجوی نام یا کد',placeholder:'جست‌وجوی نام یا کد'});
      const select=el('select',{'aria-label':'فیلتر کشور'},...['all','iran','foreign'].map((v,i)=>el('option',{value:v,text:['همه','ایرانی','خارجی'][i]})));
      select.value=root.dataset.region||'all';const results=el('div',{className:'guide-results'});
      const update=()=>{
        root.dataset.query=search.value;root.dataset.region=select.value;
        const visible=filterGuides(rows||[],search.value,select.value);
        results.replaceChildren(...visible.map(r=>el('button',{type:'button',className:'panel guide-card',onClick:()=>open(r.id)},
          el('strong',{text:r.name}),p(r.codes.join(' / ')),kind==='airlines'?p('راهنما در حال تکمیل'):null,
          r.reviewedAt?p('آخرین بررسی هویت: '+date(r.reviewedAt)):null)));
        if(!visible.length)results.append(p('موردی پیدا نشد.'));
      };
      search.addEventListener('input',update);select.addEventListener('change',update);update();nodes.push(search,select,results);
    } else {
      nodes.push(button('بازگشت',back));const ref=rows?.find(r=>r.id===selected);
      if(!ref||!page)nodes.push(p('این راهنما هنوز منتشر نشده یا فعلاً در دسترس نیست.'));
      else if(sectionId) {
        const s=page.sections.find(s=>s.id===sectionId);
        if(!s)nodes.push(p('این بخش منتشر نشده یا نیازمند بررسی دوباره است.'));
        else {
          nodes.push(el('h2',{text:s.title}),p('آخرین بررسی: '+date(s.reviewedAt)));
          if(s.scope){nodes.push(p(s.scope.note_fa));for(const [field,label] of [['route','مسیر'],['fare_brand','نرخ'],['cabin_class','کلاس']])if(s.scope[field])nodes.push(p(label+': '+s.scope[field]));
            if(s.scope.seller&&s.scope.seller!=='unknown')nodes.push(p('فروشنده: '+({airline:'خرید مستقیم',agency:'آژانس',third_party:'واسطه'}[s.scope.seller]||'نیازمند تأیید')));
            if(s.scope.journey_type&&s.scope.journey_type!=='unknown')nodes.push(p(s.scope.journey_type==='domestic'?'مخصوص پرواز داخلی':'مخصوص پرواز خارجی'));
            if(s.scope.operating_carrier)nodes.push(p('شرکت اجراکننده: '+(rows.find(r=>r.id===s.scope.operating_carrier)?.name||'نیازمند تأیید')));
          }
          nodes.push(...s.blocks.map(block),el('h3',{text:'منابع و آخرین قوانین'}),...s.sources.map(s=>link(new URL(s).host,s)));
        }
      }else {
        nodes.push(el('h2',{text:ref.name}),p(ref.codes.join(' / ')));
        if(ref.website)nodes.push(link('وب‌سایت رسمی ایرلاین',ref.website),button('اشتراک‌گذاری لینک رسمی',()=>openUrl('https://t.me/share/url?url='+encodeURIComponent(ref.website))));
        if(!page.sections.length)nodes.push(p('بخش منتشرشده‌ای در دسترس نیست.'));
        nodes.push(...page.sections.map(s=>el('button',{type:'button',className:'panel guide-card',onClick:()=>{save();sectionId=s.id;render();}},
          el('strong',{text:s.title}),p('آخرین بررسی: '+date(s.reviewedAt)))));
        if(kind==='airlines')nodes.push(el('h3',{text:'تجربه‌های مسافران و امتیازها'}),
          p('تجربهٔ شخصی کاربر، نه مقررات رسمی شرکت هواپیمایی یا ارزیابی ایمنی.'),
          p('تجربهٔ دارای مجوز انتشار هنوز متصل نشده است.'),p('تعداد رأی معتبر: '+page.reviewCount),
          p('میانگین و مقایسه تا تعیین حداقل نمونهٔ معتبر نمایش داده نمی‌شود.'),
          ...(page.reviewCount>0?Object.entries(page.counts).map(([key,n])=>p(({overall:'رضایت کلی',crew:'رفتار خدمه',seat:'راحتی صندلی',cleanliness:'نظافت',catering:'پذیرایی',checkin:'پذیرش و سوارشدن',baggage:'مدیریت بار',value:'ارزش در برابر هزینه'}[key])+': '+n+' رأی')):[]));
      }
    }
    nodes.push(button('بررسی دوباره اطلاعات',()=>load(true)));
    root.replaceChildren(...nodes);restore();
  }
  return {load,open,back};
}
