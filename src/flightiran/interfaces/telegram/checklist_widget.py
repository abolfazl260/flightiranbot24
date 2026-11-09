"""Telegram 10.4 personal travel checklist widget, with private SQLite persistence."""

from __future__ import annotations

import json
import logging
import re
import zlib

from telegram import Update
from telegram.ext import ContextTypes

from flightiran.modules.travel_checklist import (
    TASKS,
    SQLiteTravelChecklistService,
)

from .widgets import _widget_api

LOGGER = logging.getLogger(__name__)

# Everything is inline; no network calls, external assets, passwords or user-entered text.
# The tuple positions match the durable bit positions in travel_checklist.py.
TASKS_JSON = json.dumps(
    [[name, group, note, international] for name, group, note, international in TASKS],
    ensure_ascii=False, separators=(",", ":"),
)
CHECKLIST_WIDGET_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><style>
*{box-sizing:border-box}
body{margin:0;padding:12px 12px 8px;color:var(--tg-theme-text-color);
font-family:Arial,sans-serif;font-size:13px}
header{display:flex;justify-content:space-between;align-items:start;gap:9px}
h3{font-size:18px;line-height:1.5;margin:0;font-weight:800}
.eyebrow{color:var(--tg-theme-hint-color);font-size:11px;margin:0 0 2px}
.logo{background:var(--tg-theme-secondary-bg-color);border-radius:12px;padding:10px;font-size:23px}
.mode{display:flex;gap:6px;margin:12px 0}
.mode button{width:50%;padding:9px 4px;border-radius:10px;font-size:12px;margin:0;
background:var(--tg-theme-secondary-bg-color);color:var(--tg-theme-text-color);
border:1px solid transparent}
.mode button.sel{background:var(--tg-theme-button-color);
color:var(--tg-theme-button-text-color);font-weight:bold}
.hero{padding:12px;background:var(--tg-theme-secondary-bg-color);border-radius:15px}
.headline{display:flex;justify-content:space-between;align-items:center}
.count{font-size:20px;font-weight:800;direction:ltr}
.muted{color:var(--tg-theme-hint-color);font-size:11px}
.track{background:var(--tg-theme-bg-color);height:9px;border-radius:20px;
overflow:hidden;margin:10px 0 6px}
.fill{height:100%;background:var(--tg-theme-button-color);border-radius:20px;width:0}
#motivate{font-size:11px;color:var(--tg-theme-hint-color);margin:0}
.section-title{font-weight:700;margin:13px 0 9px}
.tabs{display:flex;gap:5px}
.tabs button{flex:1;padding:9px 2px;border:0;background:var(--tg-theme-secondary-bg-color);
color:var(--tg-theme-hint-color);font-size:11px;border-radius:9px}
.tabs button.sel{color:var(--tg-theme-button-text-color);
background:var(--tg-theme-button-color);font-weight:bold}
#tasks{margin-top:5px}
.task{width:100%;display:flex;align-items:center;gap:10px;text-align:right;direction:rtl;
padding:9px 3px;color:var(--tg-theme-text-color);background:transparent;
border:0;border-bottom:1px solid var(--tg-theme-section-separator-color);border-radius:0}
.task:last-child{border-bottom:0}
.tick{flex:0 0 23px;height:23px;width:23px;display:flex;align-items:center;justify-content:center;
border-radius:8px;border:1.5px solid var(--tg-theme-hint-color);font-size:15px}
.done .tick{background:var(--tg-theme-button-color);border-color:var(--tg-theme-button-color);
color:var(--tg-theme-button-text-color)}
.copy{display:block;flex:1;min-width:0}
.name{display:block;font-weight:600;font-size:12px}
.done .name{text-decoration:line-through;opacity:.7}
.hint{display:block;color:var(--tg-theme-hint-color);font-size:10px;margin-top:3px}
.actions{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-top:9px}
.action{font-size:11px;color:var(--tg-theme-link-color);background:transparent;
border:0;padding:7px 3px}
#reset.armed{color:var(--tg-theme-destructive-text-color);font-weight:bold}
#msg{color:var(--tg-theme-hint-color);font-size:10px;text-align:center}
button:disabled{opacity:.55}
</style></head><body>
<header><div><p class="eyebrow">همراه هوشمند سفر</p>
<h3>چک‌لیست سفر من</h3><p class="eyebrow">آماده حرکت شو، مورد به مورد</p></div>
<div class="logo">🧳</div></header>
<div class="mode">
<button id="domestic" class="sel" aria-pressed="true">پرواز داخلی</button>
<button id="international" aria-pressed="false">سفر خارجی</button></div>
<section class="hero"><div class="headline"><strong>میزان آمادگی سفر</strong>
<div class="count" id="count">۰ / ۱۱</div></div>
<div class="track" role="progressbar" aria-label="پیشرفت سفر"
 id="track" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
<div class="fill" id="fill"></div></div>
<p id="motivate">هر قدم کوچک، یک سفر آسوده‌تر.</p></section>
<p class="section-title" id="section">کارهای سفر</p>
<nav class="tabs" aria-label="دسته‌های چک‌لیست">
<button id="g0" class="sel">مدارک</button>
<button id="g1">برنامه سفر</button>
<button id="g2">وسایل ضروری</button></nav>
<div id="tasks"></div>
<div class="actions">
<button class="action" id="sync">↻ همگام‌سازی</button>
<span id="msg" role="status">پیشرفت شما ذخیره می‌شود</span>
<button class="action" id="reset">بازنشانی</button>
</div>
<script>
(function(){
  var W=window.TelegramWidget, ITEMS=__TASKS__;
  var state={m:'d',d:0,i:0,v:0},cat=0,busy=false,armed=false;
  var names=['مدارک','برنامه سفر','وسایل ضروری'];
  function el(id){return document.getElementById(id);}
  function fa(n){return String(n).replace(/[0-9]/g,function(c){
    return '۰۱۲۳۴۵۶۷۸۹'.charAt(c.charCodeAt(0)-48);
  });}
  function parse(s){try{return JSON.parse(s||'{}');}catch(e){return {};}}
  function isValid(s){return s && (s.m==='d'||s.m==='i') &&
    typeof s.d==='number' && typeof s.i==='number' && typeof s.v==='number';}
  function apply(raw){
    var next=parse(raw);
    if(isValid(next) && next.v>=state.v){state=next;render();}
  }
  function bit(i){return (state.m==='d'?state.d:state.i)&(1<<i);}
  function visible(t){return state.m==='i'||!t[3];}
  function send(action){
    if(busy||!W)return;
    busy=true;el('msg').textContent='در حال ذخیره...';render();
    W.request(action).then(function(answer){
      busy=false;
      if(isValid(parse(answer.result))){
        apply(answer.result);
        el('msg').textContent='✓ ذخیره شد';
      }else{
        el('msg').textContent='ذخیره نشد، دوباره تلاش کنید';
        render();
      }
    },function(){
      busy=false;el('msg').textContent='اتصال برقرار نشد';render();
    });
  }
  function render(){
    var total=0,done=0;
    for(var i=0;i<ITEMS.length;i++){
      if(visible(ITEMS[i])){total++;if(bit(i))done++;}
    }
    var pct=total?Math.round(done*100/total):0;
    el('count').textContent=fa(done)+' / '+fa(total);
    el('fill').style.width=pct+'%';
    el('track').setAttribute('aria-valuenow',String(pct));
    el('motivate').textContent=done===total?'آماده‌ای! سفر خوبی داشته باشی ✨':
      done===0?'شروع کن؛ هر تیک یک قدم نزدیک‌تر به سفر است.':
      pct>=70?'تقریباً آماده‌ای؛ فقط چند مورد باقی مانده.':
      'عالی پیش می‌روی؛ ادامه بده.';
    for(var m=0;m<2;m++){
      var id=m?'international':'domestic',selected=state.m===(m?'i':'d');
      el(id).className=selected?'sel':'';
      el(id).setAttribute('aria-pressed',selected?'true':'false');
      el(id).disabled=busy;
    }
    for(var g=0;g<3;g++){
      var selected=cat===g;
      el('g'+g).className=selected?'sel':'';
      el('g'+g).disabled=busy;
    }
    el('section').textContent=names[cat];
    var box=el('tasks');box.textContent='';
    for(var k=0;k<ITEMS.length;k++){
      if(ITEMS[k][1]!==cat||!visible(ITEMS[k]))continue;
      (function(index){
        var item=ITEMS[index],checked=!!bit(index);
        var b=document.createElement('button');b.type='button';
        b.className='task'+(checked?' done':'');b.disabled=busy;
        b.setAttribute('aria-pressed',checked?'true':'false');
        var mark=document.createElement('span');mark.className='tick';
        mark.textContent=checked?'✓':'';
        var body=document.createElement('span');body.className='copy';
        var title=document.createElement('span');title.className='name';
        title.textContent=item[0];
        var hint=document.createElement('span');hint.className='hint';
        hint.textContent=item[2];
        body.appendChild(title);body.appendChild(hint);
        b.appendChild(mark);b.appendChild(body);
        b.addEventListener('click',function(){
          armed=false;send('cl:t:'+state.m+':'+index);
        });
        box.appendChild(b);
      })(k);
    }
    el('sync').disabled=busy;el('reset').disabled=busy;
    el('reset').className=armed?'action armed':'action';
    el('reset').textContent=armed?'تأیید پاک‌سازی':'بازنشانی';
  }
  el('domestic').addEventListener('click',function(){
    if(state.m!=='d'){cat=0;armed=false;send('cl:m:d');}
  });
  el('international').addEventListener('click',function(){
    if(state.m!=='i'){cat=0;armed=false;send('cl:m:i');}
  });
  for(var j=0;j<3;j++){
    (function(index){el('g'+index).addEventListener('click',function(){
      cat=index;armed=false;render();
    });})(j);
  }
  el('sync').addEventListener('click',function(){armed=false;send('cl:s');});
  el('reset').addEventListener('click',function(){
    if(!armed){armed=true;render();return;}
    armed=false;send('cl:x:'+state.m);
  });
  if(W){
    apply(W.chatData);
    W.onEvent('chatDataChanged',function(){apply(W.chatData);});
  }
  render();
  if(W){W.ready();if(W.chatType==='private'&&W.viewer){send('cl:s');}}
})();
</script></body></html>""".replace("__TASKS__", TASKS_JSON)

assert len(CHECKLIST_WIDGET_HTML.encode("utf-8")) <= 32768
assert len(zlib.compress(CHECKLIST_WIDGET_HTML.encode("utf-8"), 9)) <= 4096


async def send_checklist_widget(message: object, bot: object,
                                service: SQLiteTravelChecklistService | None) -> bool:
    """Open the latest saved progress, even after a bot or Telegram restart."""
    if getattr(bot, "platform", "telegram") == "bale":
        return False
    if getattr(getattr(message, "chat", None), "type", None) != "private":
        await message.reply_text("چک‌لیست تعاملی فقط در گفت‌وگوی خصوصی تلگرام فعال است.")
        return False
    if service is None:
        await message.reply_text("چک‌لیست سفر موقتاً در دسترس نیست.")
        return False

    try:
        saved = await service.get(message.chat_id)
    except Exception as exc:
        LOGGER.warning("checklist_open_failed type=%s", type(exc).__name__)
        await message.reply_text("دریافت چک‌لیست ممکن نشد. دوباره تلاش کنید.")
        return False

    try:
        await _widget_api(bot, "sendWidget", {
            "chat_id": message.chat_id,
            "html": CHECKLIST_WIDGET_HTML,
            "chat_data": saved.as_json(),
            "allow_queries": True,
        })
        return True
    except Exception as exc:
        LOGGER.warning("checklist_widget_send_failed type=%s", type(exc).__name__)
        done, total = saved.progress()
        await message.reply_text(
            f"چک‌لیست سفر من\\nپیشرفت فعلی: {done} از {total} مورد\\n"
            "برای استفاده از چک‌لیست تعاملی، تلگرام خود را به‌روز کنید "
            "و دستور /checklist را دوباره بفرستید."
        )
        return False


# The request is untrusted: only allow predefined, short data actions.
ACTION = re.compile(r"^cl:(s|m:[di]|x:[di]|t:[di]:(?:[0-9]|1[0-4]))$")


async def handle_checklist_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    service: SQLiteTravelChecklistService | None,
) -> None:
    """Validate Telegram ownership, mutate stored progress and repaint silently."""
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        return
    qid = raw["id"]

    async def answer(result: str) -> None:
        await _widget_api(context.bot, "answerWidgetQuery", {
            "widget_query_id": qid, "data": result,
        })

    sender = raw.get("from")
    chat = raw.get("chat")
    mid = raw.get("message_id")
    data = raw.get("data")
    typ = raw.get("type")
    if not (
        isinstance(sender, dict)
        and isinstance(chat, dict)
        and type(sender.get("id")) is int and sender["id"] > 0
        and chat.get("type") == "private"
        and chat.get("id") == sender["id"]
        and type(mid) is int and mid > 0
        and isinstance(data, str) and ACTION.fullmatch(data)
        and (typ is None or (isinstance(typ, dict) and typ.get("type") == "data"))
        and not raw.get("widget_id")
    ):
        await answer("invalid")
        return
    if service is None:
        await answer("unavailable")
        return

    try:
        if data == "cl:s":
            saved = await service.get(sender["id"])
        else:
            parts = data.split(":")
            action = {"t": "toggle", "m": "mode", "x": "reset"}[parts[1]]
            mode = parts[2]
            index = int(parts[3]) if action == "toggle" else None
            saved = await service.apply(sender["id"], action, mode, index)
    except ValueError:
        await answer("invalid")
        return
    except Exception as exc:
        LOGGER.warning("checklist_mutation_failed type=%s", type(exc).__name__)
        await answer("unavailable")
        return

    # Returning the new state immediately makes the card responsive even if
    # Telegram's silent message edit arrives later or is throttled.
    result = saved.as_json()
    await answer(result)
    try:
        await _widget_api(context.bot, "editMessageWidgetData", {
            "chat_id": sender["id"], "message_id": mid, "chat_data": result,
        })
    except Exception as exc:
        # The SQL state has already been committed; a subsequent sync restores it.
        LOGGER.warning("checklist_state_edit_failed type=%s", type(exc).__name__)
