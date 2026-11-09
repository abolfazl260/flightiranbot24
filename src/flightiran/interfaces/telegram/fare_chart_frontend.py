"""Enhance the existing fare widget with button-only route selection and an SVG chart.

Telegram's HTML widget sandbox does not support text fields or native selects.
All user input here uses clickable buttons and TelegramWidget.request.
"""

from __future__ import annotations


_SELECTOR_CSS = """
#route-panel{padding:10px 0 12px;border-bottom:1px solid var(--tg-theme-section-separator-color)}
#route-panel h3{margin-bottom:7px}
.route-buttons{display:flex;gap:6px}
.route-buttons button{flex:1;min-width:0;padding:10px 4px;border-radius:8px;
border:1px solid var(--tg-theme-section-separator-color,#b6bdc5);
background:var(--tg-theme-secondary-bg-color,#f1f3f5);
color:var(--tg-theme-text-color,#222);font-size:12px}
#route-options{max-height:180px;overflow:auto}
#route-options button{display:block;width:100%;margin-top:5px;padding:8px;
text-align:right;border-radius:7px;border:1px solid var(--tg-theme-section-separator-color)}
.route-pagination{display:flex;gap:8px;margin-top:5px}
.route-pagination button{flex:1;text-align:center}
#route-plot{width:100%;height:138px;display:block}
#route-metrics{font-size:12px;line-height:1.9}
#route-metrics strong{font-weight:bold}
#route-book{width:100%;padding:11px;margin-top:8px;border:0;border-radius:8px;
background:var(--tg-theme-button-color,#3390ec);
color:var(--tg-theme-button-text-color,#fff);font-weight:bold}
#route-hint{font-size:11px;color:var(--tg-theme-hint-color)}
"""

_SELECTOR_HTML = """
<section id="route-panel">
<h3>نمودار قیمت مسیر پرواز</h3>
<div class="route-buttons">
<button id="route-origin" type="button">مبدأ: انتخاب کنید</button>
<button id="route-destination" type="button">مقصد: انتخاب کنید</button>
</div>
<div id="route-options"></div>
<div id="route-chart" style="display:none">
<p class="sort-label">کمترین قیمت مشاهده‌شده در هر روز (۲۱ روز اخیر)</p>
<svg id="route-plot" viewBox="0 0 300 138"></svg>
<div id="route-metrics"></div>
<button id="route-book" type="button">درخواست رزرو این مسیر</button>
</div>
<p id="route-hint" class="sub">برای مشاهده روند قیمت، ابتدا مبدأ و مقصد را انتخاب کنید.</p>
</section>
"""

_SELECTOR_JS = """
  var origButton=document.getElementById('route-origin');
  var destButton=document.getElementById('route-destination');
  var choiceArea=document.getElementById('route-options');
  var plotArea=document.getElementById('route-chart');
  var plot=document.getElementById('route-plot');
  var metrics=document.getElementById('route-metrics');
  var booking=document.getElementById('route-book');
  var hint=document.getElementById('route-hint');
  var routeState={};
  function askRoute(action){
    W.request(action).then(function(reply){
      if(reply.result!=='accepted')hint.textContent='امکان انجام درخواست نیست؛ دوباره تلاش کنید.';
    },function(){hint.textContent='ارتباط با ربات برقرار نشد.';});
  }
  function makeButton(text,action,where){
    var btn=document.createElement('button');
    btn.type='button';btn.textContent=text;
    btn.addEventListener('click',function(){askRoute(action);});
    where.appendChild(btn);
  }
  function svgTag(tag,attrs){
    var node=document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(var k in attrs){node.setAttribute(k,String(attrs[k]));}
    plot.appendChild(node);
  }
  function renderRoute(){
    var d=parse(W.chatData);routeState=d;
    var view=d.view||'';
    origButton.textContent='مبدأ: '+(d.o||'انتخاب کنید');
    destButton.textContent='مقصد: '+(d.d||'انتخاب کنید');
    destButton.disabled=!(d.ok&&view!=='origins');
    choiceArea.textContent='';
    plotArea.style.display=view==='chart'?'block':'none';
    hint.textContent=view==='error'?(d.message||'خطا در دریافت اطلاعات'):
      view==='chart'?'نرخ‌ها صرفاً اطلاع‌رسانی هستند؛ رزرو باید تأیید شود.':
      view==='origins'?'مبدأ موردنظر را انتخاب کنید.':
      view==='destinations'?'مقصد موردنظر را انتخاب کنید.':
      'برای مشاهده نمودار، مبدأ و مقصد را انتخاب کنید.';
    if(view==='origins'||view==='destinations'){
      var opts=Array.isArray(d.options)?d.options:[];
      for(var i=0;i<opts.length;i++){
        var opt=opts[i];
        var action=view==='origins'?'fare:origin:'+opt.k:
          'fare:route:'+d.ok+':'+opt.k;
        makeButton(opt.n,action,choiceArea);
      }
      if(d.pages>1){
        var pager=document.createElement('div');pager.className='route-pagination';
        var prefix=view==='origins'?'fare:origins:':'fare:destinations:'+d.ok+':';
        if(d.page>0)makeButton('صفحه قبل',prefix+(d.page-1),pager);
        if(d.page<d.pages-1)makeButton('صفحه بعد',prefix+(d.page+1),pager);
        choiceArea.appendChild(pager);
      }
    }
    if(view!=='chart')return;
    destButton.disabled=false;
    destButton.textContent='مقصد: '+d.d;
    origButton.textContent='مبدأ: '+d.o;
    var points=Array.isArray(d.series)?d.series:[];
    plot.textContent='';metrics.textContent='';
    var clean=[];
    for(var k=0;k<points.length;k++){
      if(Array.isArray(points[k])&&typeof points[k][0]==='number'
         &&typeof points[k][1]==='number')clean.push(points[k]);
    }
    var price=document.createElement('p');
    price.textContent='قیمت فعلی: '+format(d.p)+' تومان';
    metrics.appendChild(price);
    if(typeof d.a==='number'){
      var average=document.createElement('p');
      average.textContent='میانگین تاریخی: '+format(d.a)+' تومان';
      metrics.appendChild(average);
      if(typeof d.pct==='number'){
        var diff=document.createElement('p');
        diff.textContent=fa(Math.abs(d.pct))+'٪ '+
          (d.pct<0?'کمتر از':d.pct>0?'بیشتر از':'برابر با')+' میانگین';
        if(d.pct<0)diff.style.color='var(--tg-theme-link-color)';
        metrics.appendChild(diff);
      }
    }
    var sampled=document.createElement('p');
    sampled.textContent='تعداد مشاهده تاریخی: '+fa(d.n||0)+
      ' • بررسی: '+fa(d.updated||'—');
    metrics.appendChild(sampled);
    if(!clean.length){
      svgTag('text',{x:150,y:65,'text-anchor':'middle',
        fill:'var(--tg-theme-hint-color)','font-size':13})
        .textContent='داده تاریخی کافی ثبت نشده است';
    }else{
      var minDay=clean[0][0],maxDay=clean[clean.length-1][0];
      var minPrice=clean[0][1],maxPrice=minPrice;
      for(var j=1;j<clean.length;j++){
        minPrice=Math.min(minPrice,clean[j][1]);
        maxPrice=Math.max(maxPrice,clean[j][1]);
      }
      var range=maxPrice-minPrice||1,span=maxDay-minDay||1;
      svgTag('path',{d:'M12 15H288 M12 65H288 M12 115H288',
        stroke:'var(--tg-theme-hint-color)',opacity:.22,fill:'none',
        'stroke-dasharray':'3 4'});
      var last=null;
      for(var p=0;p<clean.length;p++){
        var cx=12+(clean[p][0]-minDay)*276/span;
        var cy=105-(clean[p][1]-minPrice)*82/range;
        if(last&&clean[p][0]-last[0]===1){
          svgTag('line',{x1:last[2],y1:last[3],x2:cx,y2:cy,
            stroke:'var(--tg-theme-link-color,#168a79)','stroke-width':2});
        }
        svgTag('circle',{cx:cx,cy:cy,r:3.3,fill:'var(--tg-theme-link-color,#168a79)'});
        last=[clean[p][0],clean[p][1],cx,cy];
      }
      var rangeLine=document.createElement('p');
      rangeLine.textContent='کمینه ثبت‌شده: '+format(minPrice)+
        ' • بیشینه: '+format(maxPrice)+' تومان';
      metrics.appendChild(rangeLine);
    }
    booking.disabled=false;
  }
  origButton.addEventListener('click',function(){askRoute('fare:origins:0');});
  destButton.addEventListener('click',function(){
    if(routeState.ok)askRoute('fare:destinations:'+routeState.ok+':0');
  });
  booking.addEventListener('click',function(){
    if(routeState.view==='chart'&&routeState.ok&&routeState.dk){
      hint.textContent='در حال آماده‌سازی درخواست رزرو در گفتگو...';
      askRoute('fare:book:'+routeState.ok+':'+routeState.dk);
    }
  });
  W.onEvent('chatDataChanged',renderRoute);
  renderRoute();
"""


def enhance_fare_html(base: str) -> str:
    """Preserve the two existing price tabs under the route chart controls."""
    heading = "<h3>قیمت‌های منتخب بلیت</h3>"
    end_style = "</style>"
    ready = "  W.ready();"
    if base.count(heading) != 1 or base.count(end_style) != 1 or base.count(ready) != 1:
        raise ValueError("Unsupported fare widget base HTML")
    return (
        base.replace(end_style, _SELECTOR_CSS + end_style)
        .replace(heading, _SELECTOR_HTML + heading)
        .replace(ready, _SELECTOR_JS + ready)
    )
