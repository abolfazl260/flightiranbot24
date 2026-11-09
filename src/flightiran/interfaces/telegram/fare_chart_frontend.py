"""Enhance the existing fare widget with button-only route selection and an SVG chart.

Telegram's HTML widget sandbox does not support text fields or native selects.
All user input here uses clickable buttons and TelegramWidget.request.
"""

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
  var ro=document.getElementById('route-origin'),
    rd=document.getElementById('route-destination'),
    opts=document.getElementById('route-options'),
    area=document.getElementById('route-chart'),
    plot=document.getElementById('route-plot'),
    info=document.getElementById('route-metrics'),
    book=document.getElementById('route-book'),
    hint=document.getElementById('route-hint'),selection={};
  function ask(a){
    W.request(a).then(function(x){
      if(x.result!=='accepted')hint.textContent='درخواست انجام نشد';
    },function(){hint.textContent='خطای ارتباط';});
  }
  function opt(text,action,where){
    var b=document.createElement('button');
    b.type='button';b.textContent=text;
    b.addEventListener('click',function(){ask(action);});
    where.appendChild(b);
  }
  function svg(name,attrs){
    var n=document.createElementNS('http://www.w3.org/2000/svg',name);
    for(var a in attrs)n.setAttribute(a,attrs[a]);
    plot.appendChild(n);
  }
  function renderRoute(){
    var d=parse(W.chatData);selection=d;var v=d.view||'';
    ro.textContent='مبدأ: '+(d.o||'انتخاب');
    rd.textContent='مقصد: '+(d.d||'انتخاب');
    rd.disabled=!d.ok||v==='origins';
    opts.textContent='';area.style.display=v==='chart'?'block':'none';
    hint.textContent=v==='error'?d.message:
      v==='origins'?'مبدأ را انتخاب کنید':
      v==='destinations'?'مقصد را انتخاب کنید':
      'قیمت‌ها قطعی نیستند و پیش از رزرو باید تأیید شوند.';
    if(v==='origins'||v==='destinations'){
      var list=d.options||[],prefix=v==='origins'?'fare:origins:':
        'fare:destinations:'+d.ok+':';
      for(var i=0;i<list.length;i++)
        opt(list[i].n,v==='origins'?'fare:origin:'+list[i].k:
            'fare:route:'+d.ok+':'+list[i].k,opts);
      if(d.page>0)opt('قبلی',prefix+(d.page-1),opts);
      if(d.page+1<d.pages)opt('بعدی',prefix+(d.page+1),opts);
    }
    if(v!=='chart')return;
    plot.textContent='';info.textContent='';
    var rows=d.series||[],valid=[];
    for(var i=0;i<rows.length;i++)
      if(typeof rows[i][0]==='number'&&typeof rows[i][1]==='number')
        valid.push(rows[i]);
    var lines=['قیمت فعلی: '+format(d.p)+' تومان'];
    if(typeof d.a==='number'){
      lines.push('میانگین تاریخی: '+format(d.a)+' تومان');
      if(typeof d.pct==='number')
        lines.push(fa(Math.abs(d.pct))+'٪ '+
          (d.pct<0?'کمتر از':d.pct>0?'بیشتر از':'برابر با')+' میانگین');
    }
    lines.push('مشاهدات: '+fa(d.n||0)+' • '+fa(d.updated||''));
    if(!valid.length)lines.push('برای این مسیر هنوز تاریخچه قیمت ثبت نشده است.');
    else{
      var lo=valid[0][1],hi=lo;
      for(var j=0;j<valid.length;j++){
        lo=Math.min(lo,valid[j][1]);hi=Math.max(hi,valid[j][1]);
      }
      var first=valid[0][0],span=valid[valid.length-1][0]-first||1,
        range=hi-lo||1,last=null;
      svg('path',{d:'M8 25H292 M8 75H292 M8 125H292',
        stroke:'currentColor',opacity:'.12',fill:'none'});
      for(var k=0;k<valid.length;k++){
        var x=8+284*(valid[k][0]-first)/span,
          y=110-84*(valid[k][1]-lo)/range;
        if(last&&valid[k][0]===last[0]+1)
          svg('line',{x1:last[1],y1:last[2],x2:x,y2:y,
            stroke:'#14877d','stroke-width':'2'});
        svg('circle',{cx:x,cy:y,r:'3',fill:'#14877d'});
        last=[valid[k][0],x,y];
      }
      lines.push('کمینه ثبت‌شده: '+format(lo)+' • بیشینه: '+format(hi)+' تومان');
    }
    for(var q=0;q<lines.length;q++){
      var p=document.createElement('p');p.textContent=lines[q];info.appendChild(p);
    }
  }
  ro.addEventListener('click',function(){ask('fare:origins:0');});
  rd.addEventListener('click',function(){
    if(selection.ok)ask('fare:destinations:'+selection.ok+':0');
  });
  book.addEventListener('click',function(){
    if(selection.view==='chart'&&selection.ok&&selection.dk)
      ask('fare:book:'+selection.ok+':'+selection.dk);
  });
  W.onEvent('chatDataChanged',renderRoute);renderRoute();
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
