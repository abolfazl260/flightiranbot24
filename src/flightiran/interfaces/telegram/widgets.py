"""Telegram Bot API 10.4 fare widget (private chats only).

python-telegram-bot < 23 has no native widget methods or WidgetQuery class yet.
Its forward-compatibility layer preserves new update fields in Update.api_kwargs.
"""

from __future__ import annotations

import json
import logging
import zlib
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from flightiran.modules.tickets.service import CheapTicketService, parse_toman_price

LOGGER = logging.getLogger(__name__)

# Self-contained QuickJS widget. No network, external images, or unsupported form controls.
FARE_WIDGET_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><style>
body{margin:0;padding:12px;color:var(--tg-theme-text-color);font-family:Arial,sans-serif}
h3{font-size:17px;margin:0 0 5px}
p{margin:0}
.sub{font-size:12px;color:var(--tg-theme-hint-color)}
#fares{margin:10px 0}
.fare{display:flex;justify-content:space-between;align-items:center;gap:8px;
padding:10px 0;border-bottom:1px solid var(--tg-theme-section-separator-color)}
.route{font-size:13px;max-width:60%}
.price{font-size:13px;font-weight:bold;direction:ltr;text-align:left}
button{width:100%;margin-top:10px;padding:10px}
#status{margin-top:7px;font-size:12px;color:var(--tg-theme-hint-color)}
</style></head>
<body>
<h3>قیمت‌های منتخب بلیت</h3>
<p class="sub">از داده‌های فعلی سرویس بلیت • قیمت به تومان</p>
<div id="fares"></div>
<p class="sub" id="updated"></p>
<button id="refresh">تازه‌سازی قیمت‌ها</button>
<p id="status" aria-live="polite">قیمت‌ها پیش از رزرو باید تأیید شوند.</p>
<script>
(function(){
  var W=window.TelegramWidget;
  var fares=document.getElementById('fares');
  var status=document.getElementById('status');
  var updated=document.getElementById('updated');
  var button=document.getElementById('refresh');
  function parse(value){try{return JSON.parse(value||'{}');}catch(e){return {};}}
  function format(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,',');}
  function render(){
    var data=parse(W.publicData), state=parse(W.chatData);
    fares.textContent='';
    var items=Array.isArray(data.items)?data.items:[];
    if(!items.length){fares.textContent='در حال حاضر قیمت قابل نمایشی موجود نیست.';}
    for(var i=0;i<items.length;i++){
      var fare=items[i];
      var row=document.createElement('div');row.className='fare';
      var route=document.createElement('span');route.className='route';
      route.textContent=fare.o+' ← '+fare.d;
      var price=document.createElement('span');price.className='price';
      price.textContent=format(fare.p);
      row.appendChild(route);row.appendChild(price);fares.appendChild(row);
    }
    updated.textContent=data.updated?'آخرین بررسی: '+data.updated:'';
    if(state.status==='error'){
      status.textContent='به‌روزرسانی ناموفق بود؛ آخرین قیمت‌ها حفظ شدند.';
    } else if(state.status==='ready'){
      status.textContent='به‌روزرسانی انجام شد؛ قیمت‌ها پیش از رزرو باید تأیید شوند.';
    }
    button.disabled=false;
  }
  button.addEventListener('click',function(){
    button.disabled=true;
    status.textContent='در حال دریافت قیمت‌های جدید...';
    W.request('fare:refresh').then(function(answer){
      if(answer.result!=='accepted'){
        status.textContent='درخواست قابل انجام نیست.';
        button.disabled=false;
      }
    },function(){
      status.textContent='ارتباط با ربات برقرار نشد. دوباره تلاش کنید.';
      button.disabled=false;
    });
  });
  W.onEvent('publicDataChanged',render);
  W.onEvent('chatDataChanged',render);
  render();
  W.ready();
})();
</script></body></html>"""

assert len(FARE_WIDGET_HTML.encode("utf-8")) <= 32768
assert len(zlib.compress(FARE_WIDGET_HTML.encode("utf-8"), level=9)) <= 4096


def fare_widget_data(routes: list, *, now: datetime | None = None) -> str:
    """Build a compact state from real provider results, without guessed fares."""
    values: list[tuple[int, str, str]] = []
    for route in routes:
        for destination in route.destinations:
            try:
                price = (
                    destination.price_value_toman
                    if destination.price_value_toman is not None
                    else parse_toman_price(destination.price_toman)
                )
                if price <= 0:
                    continue
                values.append((price, route.origin[:30], destination.name[:30]))
            except (ValueError, TypeError, AttributeError):
                continue

    values.sort(key=lambda row: row[0])
    data = {
        "items": [{"o": origin, "d": destination, "p": price}
                  for price, origin, destination in values[:5]],
        "updated": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
    }
    # Telegram permits only 1024 UTF-8 bytes for each widget state field.
    while True:
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) <= 1024:
            return serialized
        data["items"].pop()


async def _widget_api(bot: object, method: str, data: dict) -> object:
    """Use PTB's existing authenticated HTTP transport for new Bot API methods."""
    return await bot._post(method, data)


def _private_telegram(bot: object, chat: object) -> bool:
    return (
        getattr(bot, "platform", "telegram") != "bale"
        and getattr(chat, "type", None) == "private"
    )


async def send_fare_widget(message: object, bot: object,
                           service: CheapTicketService | None) -> bool:
    """Send a real fare widget; fall back to a readable message on API failures."""
    if not _private_telegram(bot, getattr(message, "chat", None)):
        await message.reply_text("ویجت‌های تلگرام فعلاً فقط در گفت‌وگوی خصوصی فعال هستند.")
        return False
    if service is None:
        await message.reply_text("سرویس قیمت بلیت در حال حاضر فعال نیست.")
        return False
    try:
        routes = await service.routes()
        state = fare_widget_data(routes)
    except Exception as exc:
        LOGGER.warning("widget_fares_fetch_failed type=%s", type(exc).__name__)
        await message.reply_text("دریافت قیمت‌ها فعلاً ممکن نیست؛ بعداً دوباره تلاش کنید.")
        return False

    try:
        await _widget_api(bot, "sendWidget", {
            "chat_id": message.chat_id,
            "html": FARE_WIDGET_HTML,
            "public_data": state,
            "chat_data": '{"status":"ready"}',
            "caption": "قیمت‌های منتخب بلیت؛ مبالغ قطعی نیستند.",
            "allow_queries": True,
        })
        return True
    except Exception as exc:
        # Do not log Telegram exceptions verbatim: URLs may contain the bot token.
        LOGGER.warning("widget_send_failed type=%s", type(exc).__name__)
        data = json.loads(state)
        lines = ["قیمت‌های منتخب بلیت:"]
        for fare in data["items"]:
            lines.append(f"{fare['o']} ← {fare['d']}: {fare['p']:,} تومان")
        lines.append("قیمت‌ها پیش از رزرو باید تأیید شوند.")
        await message.reply_text("\n".join(lines))
        return False


async def widget_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    service: CheapTicketService | None,
) -> None:
    """Handle raw widget_query updates on PTB versions lacking Bot API 10.4."""
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict):
        return
    query_id = raw.get("id")
    if not isinstance(query_id, str) or not query_id:
        return

    async def answer(value: str) -> None:
        await _widget_api(context.bot, "answerWidgetQuery", {
            "widget_query_id": query_id, "data": value,
        })

    chat = raw.get("chat") or {}
    sender = raw.get("from") or {}
    message_id = raw.get("message_id")
    # Production widgets are private and non-shared. Do not allow foreign chat
    # IDs, unexpected query types, or unsupported actions to trigger a fetch.
    if not (
        isinstance(chat, dict)
        and chat.get("type") == "private"
        and isinstance(sender, dict)
        and type(sender.get("id")) is int
        and sender["id"] == chat.get("id")
        and type(message_id) is int and message_id > 0
        and raw.get("data") == "fare:refresh"
        and (raw.get("type") is None
             or (isinstance(raw["type"], dict)
                 and raw["type"].get("type") == "data"))
    ):
        await answer("invalid")
        return
    if service is None:
        await answer("unavailable")
        return

    # Answer immediately. Slow provider requests must not block the 15s deadline.
    await answer("accepted")
    try:
        routes = await service.routes()
        data = fare_widget_data(routes)
    except Exception as exc:
        LOGGER.warning("widget_refresh_fetch_failed type=%s", type(exc).__name__)
        try:
            await _widget_api(context.bot, "editMessageWidgetData", {
                "chat_id": chat["id"], "message_id": message_id,
                "chat_data": '{"status":"error"}',
            })
        except Exception as edit_exc:
            LOGGER.warning("widget_refresh_error_state_failed type=%s",
                           type(edit_exc).__name__)
        return
    try:
        await _widget_api(context.bot, "editMessageWidgetData", {
            "chat_id": chat["id"], "message_id": message_id,
            "public_data": data, "chat_data": '{"status":"ready"}',
        })
    except Exception as exc:
        LOGGER.warning("widget_refresh_edit_failed type=%s", type(exc).__name__)
