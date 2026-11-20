"""Minimal button-only route-chart panel for Telegram HTML fare widgets.

Uses existing recorded SQLite daily minima (21 days); no network access from
the widget sandbox and no client-side fabricated dates or prices.
"""

_SELECTOR_CSS = """
#route-panel{padding:9px 0;border-bottom:1px solid var(--tg-theme-section-separator-color)}
#route-panel h4{margin:0 0 7px;font-size:14px}
#route-buttons{display:flex;gap:6px}
#route-buttons button{flex:1;padding:10px 3px;border-radius:8px;
border:1px solid var(--tg-theme-section-separator-color,#b6bdc5);
background:var(--tg-theme-secondary-bg-color,#f1f3f5);
color:var(--tg-theme-text-color,#222);font-size:12px}
#route-options{max-height:180px;overflow:auto}
#route-options button{display:block;width:100%;margin:5px 0;padding:8px;
border-radius:7px;border:1px solid var(--tg-theme-section-separator-color)}
#route-plot{width:100%;height:120px;display:block}
#route-metrics{font-size:12px;line-height:1.8}
#route-hint{font-size:11px;color:var(--tg-theme-hint-color)}
"""

_SELECTOR_HTML = """
<section id="route-panel">
<h4>نمودار ۲۱ روزه مسیر</h4>
<div id="route-buttons">
<button type="button" id="route-origin">انتخاب مبدأ</button>
<button type="button" id="route-destination" disabled>انتخاب مقصد</button>
</div>
<div id="route-options" aria-live="polite"></div>
<div id="route-chart" style="display:none">
<p class="sort-label">کمینهٔ واقعی ثبت‌شده در روزهای دارای داده</p>
<svg id="route-plot" viewBox="0 0 300 120" role="img"
aria-label="نمودار قیمت‌های روزانه ثبت‌شده"></svg>
<div id="route-metrics"></div>
</div>
<p id="route-hint">مسیر را انتخاب کنید؛ روزهای بدون داده رسم نمی‌شوند.</p>
</section>
"""

_SELECTOR_JS = """
  var ro=document.getElementById('route-origin'),
    rd=document.getElementById('route-destination'),
    opts=document.getElementById('route-options'),
    area=document.getElementById('route-chart'),
    plot=document.getElementById('route-plot'),
    info=document.getElementById('route-metrics'),
    hint=document.getElementById('route-hint'),selection={};
  function askRoute(action){
    W.request(action).then(function(v){
      if(v.result!=='accepted')hint.textContent='درخواست انجام نشد؛ دوباره تلاش کنید.';
    },function(){hint.textContent='خطا در ارتباط؛ دوباره تلاش کنید.';});
  }
  function routeOption(label,action){
    var b=document.createElement('button');
    b.type='button';b.textContent=label;
    b.addEventListener('click',function(){askRoute(action);});
    opts.appendChild(b);
  }
  function routeSvg(name,attrs){
    var n=document.createElementNS('http://www.w3.org/2000/svg',name);
    for(var a in attrs)n.setAttribute(a,attrs[a]);
    plot.appendChild(n);
  }
  function renderRoute(){
    var d=parse(W.chatData);selection=d;var view=d.view||'';
    ro.textContent='مبدأ: '+(d.o||'انتخاب کنید');
    rd.textContent='مقصد: '+(d.d||'انتخاب کنید');
    rd.disabled=!d.ok;
    opts.textContent='';
    area.style.display=view==='chart'?'block':'none';
    hint.textContent=view==='error'?(d.message||'خطای ناشناخته'):
      view==='origins'?'مبدأ را انتخاب کنید':
      view==='destinations'?'مقصد را انتخاب کنید':
      'داده‌های تاریخی، تضمین قیمت بلیت امروز نیستند.';
    if(view==='origins'||view==='destinations'){
      var list=d.options||[],prefix=view==='origins'?'fare:origins:':
        'fare:destinations:'+d.ok+':';
      for(var i=0;i<list.length;i++)
        routeOption(list[i].n,view==='origins'?'fare:origin:'+list[i].k:
          'fare:route:'+d.ok+':'+list[i].k);
      if(d.page>0)routeOption('قبلی',prefix+(d.page-1));
      if(d.page+1<d.pages)routeOption('بعدی',prefix+(d.page+1));
    }
    if(view!=='chart')return;
    plot.textContent='';info.textContent='';
    var rows=d.series||[],valid=[];
    for(var j=0;j<rows.length;j++)
      if(typeof rows[j][0]==='number'&&typeof rows[j][1]==='number'&&
         rows[j][1]>0)valid.push(rows[j]);
    var lines=['آخرین کمینهٔ روزانه: '+format(d.p)+' تومان'];
    lines.push('مشاهدات ثبت‌شده: '+fa(d.n||0));
    lines.push('آخرین ثبت: '+fa(d.updated||''));
    if(valid.length){
      var lo=valid[0][1],hi=lo;
      for(var k=1;k<valid.length;k++){
        lo=Math.min(lo,valid[k][1]);hi=Math.max(hi,valid[k][1]);
      }
      var first=(d.end||valid[valid.length-1][0])-20;
      var range=hi-lo||1,last=null;
      routeSvg('path',{d:'M8 24H292 M8 65H292 M8 108H292',
        stroke:'currentColor',opacity:'.12',fill:'none'});
      for(var k=0;k<valid.length;k++){
        var x=8+284*(valid[k][0]-first)/20,
          y=103-80*(valid[k][1]-lo)/range;
        if(last&&valid[k][0]===last[0]+1)
          routeSvg('line',{x1:last[1],y1:last[2],x2:x,y2:y,
            stroke:'var(--tg-theme-link-color,#3390ec)','stroke-width':'2'});
        routeSvg('circle',{cx:x,cy:y,r:'3',fill:'var(--tg-theme-link-color,#3390ec)'});
        last=[valid[k][0],x,y];
      }
      lines.push('حداقل: '+format(lo)+' • حداکثر: '+format(hi)+' تومان');
    }else lines.push('تاریخچهٔ معتبر موجود نیست.');
    for(var a=0;a<lines.length;a++){
      var p=document.createElement('p');p.textContent=lines[a];
      info.appendChild(p);
    }
  }
  ro.addEventListener('click',function(){askRoute('fare:origins:0');});
  rd.addEventListener('click',function(){
    if(selection.ok)askRoute('fare:destinations:'+selection.ok+':0');
  });
  W.onEvent('chatDataChanged',renderRoute);renderRoute();
"""


def enhance_fare_html(base: str) -> str:
    """Inject one self-contained chart panel without changing fare ranking tabs."""
    heading = "<h3>قیمت‌های منتخب بلیت</h3>"
    if (
        base.count(heading) != 1
        or base.count("</style>") != 1
        or base.count("  W.ready();") != 1
    ):
        raise ValueError("Unsupported fare widget HTML")
    return (
        base.replace("</style>", _SELECTOR_CSS + "</style>")
        .replace(heading, _SELECTOR_HTML + heading)
        .replace("  W.ready();", _SELECTOR_JS + "  W.ready();")
    )
