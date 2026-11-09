"""Telegram Bot API 10.4 fare widget (private chats only).

python-telegram-bot < 23 has no native widget methods or WidgetQuery class yet.
Its forward-compatibility layer preserves new update fields in Update.api_kwargs.
"""

from __future__ import annotations

import json
import logging
import math
import zlib
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from flightiran.config.settings import DEFAULT_SUPPORT_USERNAME
from flightiran.modules.tickets.service import CheapTicketService, parse_toman_price

from .fare_chart_frontend import enhance_fare_html
from .fare_route_chart import handle_route_widget_query

LOGGER = logging.getLogger(__name__)

# Self-contained QuickJS widget. No network, external images, or unsupported form controls.
FARE_WIDGET_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><style>
body{margin:0;padding:12px;font-family:Arial,sans-serif;color:var(--tg-theme-text-color)}
h3{font-size:17px;margin:0 0 7px}
.sub{font-size:12px;color:var(--tg-theme-hint-color)}
.sort-label{font-size:12px;font-weight:bold;margin:10px 0 5px}
.tabs{display:flex;gap:6px;padding:4px;border-radius:10px;
background:var(--tg-theme-secondary-bg-color,#f1f3f5)}
.tabs button{flex:1;font-size:12px;font-weight:bold;padding:10px 5px;
border:1px solid var(--tg-theme-section-separator-color);
background:var(--tg-theme-bg-color,#fff);color:var(--tg-theme-text-color,#222);
border-radius:8px}
.tabs button.active{background:var(--tg-theme-button-color,#3390ec);
color:var(--tg-theme-button-text-color,#fff);border:2px solid var(--tg-theme-button-color)}
#fares{margin:6px 0}
.fare{display:flex;justify-content:space-between;gap:7px;padding:9px 0;
border-bottom:1px solid var(--tg-theme-section-separator-color)}
.route{font-size:12px}
.price{font-size:13px;font-weight:bold;direction:ltr}
.drop{font-size:11px;color:var(--tg-theme-link-color)}
#refresh{width:100%;margin-top:9px;padding:10px}
</style></head><body>
<h3>قیمت‌های منتخب بلیت</h3>
<p class="sub">قیمت‌ها به تومان</p>
<p class="sort-label">مرتب‌سازی بلیت‌ها بر اساس:</p>
<div class="tabs" role="tablist">
<button id="cheap" type="button" role="tab" class="active"
aria-selected="true">✓ ارزان‌ترین بلیت‌ها</button>
<button id="drops" type="button" role="tab"
aria-selected="false">بیشترین کاهش قیمت</button></div>
<div id="fares" role="tabpanel" aria-labelledby="cheap"></div>
<p class="sub" id="updated"></p>
<button id="refresh">تازه‌سازی قیمت‌ها</button>
<script>
(function(){
  var W=window.TelegramWidget,fares=document.getElementById('fares'),
    updated=document.getElementById('updated'),
    button=document.getElementById('refresh'),
    cheap=document.getElementById('cheap'),
    drops=document.getElementById('drops'),active='cheap';
  function parse(x){try{return JSON.parse(x||'{}');}catch(e){return {};}}
  function fa(x){return String(x).replace(/[0-9]/g,function(c){
    return '۰۱۲۳۴۵۶۷۸۹'.charAt(c.charCodeAt(0)-48);});}
  function format(n){return fa(String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g,'٬'));}
  function render(){
    var d=parse(W.publicData),s=parse(W.chatData);
    var items=active==='cheap'?d.items:d.drops;
    items=Array.isArray(items)?items:[];
    fares.textContent='';
    if(!items.length)fares.textContent=active==='cheap'
      ?'در حال حاضر قیمتی موجود نیست.':'کاهش قیمت معتبر ثبت نشده است.';
    for(var i=0;i<items.length;i++){
      var f=items[i],row=document.createElement('div');row.className='fare';
      var name=document.createElement('span');name.className='route';
      name.textContent='از '+f.o+' به '+f.d;
      var right=document.createElement('div'),price=document.createElement('div');
      price.className='price';price.textContent=format(f.p);right.appendChild(price);
      if(typeof f.x==='number'&&f.x>0){
        var drop=document.createElement('div');drop.className='drop';
        drop.textContent=fa(f.x)+'٪ کاهش نسبت به میانگین';
        right.appendChild(drop);
      }
      row.appendChild(name);row.appendChild(right);fares.appendChild(row);
    }
    updated.textContent=d.updated?'آخرین بررسی: '+d.updated:'';
    button.textContent=s.status==='error'?'تلاش مجدد':'تازه‌سازی قیمت‌ها';
    button.disabled=false;
  }
  function switchTab(which){
    active=which;
    cheap.className=which==='cheap'?'active':'';
    drops.className=which==='drops'?'active':'';
    cheap.textContent=which==='cheap'?'✓ ارزان‌ترین بلیت‌ها':'ارزان‌ترین بلیت‌ها';
    drops.textContent=which==='drops'?'✓ بیشترین کاهش قیمت':'بیشترین کاهش قیمت';
    cheap.setAttribute('aria-selected',which==='cheap'?'true':'false');
    drops.setAttribute('aria-selected',which==='drops'?'true':'false');
    fares.setAttribute('aria-labelledby',which);render();
  }
  cheap.addEventListener('click',function(){switchTab('cheap');});
  drops.addEventListener('click',function(){switchTab('drops');});
  button.addEventListener('click',function(){
    button.disabled=true;button.textContent='در حال تازه‌سازی...';
    W.request('fare:refresh').then(function(a){
      if(a.result!=='accepted'){button.disabled=false;button.textContent='تلاش مجدد';}
    },function(){button.disabled=false;button.textContent='تلاش مجدد';});
  });
  W.onEvent('publicDataChanged',render);
  W.onEvent('chatDataChanged',render);
  render();
  W.ready();
})();
</script></body></html>"""


FARE_WIDGET_HTML = enhance_fare_html(FARE_WIDGET_HTML)

assert len(FARE_WIDGET_HTML.encode("utf-8")) <= 32768
assert len(zlib.compress(FARE_WIDGET_HTML.encode("utf-8"), level=9)) <= 4096, (
    f"Compressed fare widget bytes: {len(zlib.compress(FARE_WIDGET_HTML.encode('utf-8'), level=9))}"
)


def fare_widget_data(routes: list, *, now: datetime | None = None) -> str:
    """Build cheapest and largest genuine percentage drops from the same feed.

    A reduction requires at least three history samples and a current price
    below a positive finite historical mean. Other routes remain eligible for
    the cheapest-price tab but never receive invented discount percentages.
    """
    values: list[dict[str, str | int | float]] = []
    for route in routes:
        for destination in route.destinations:
            try:
                price = (
                    destination.price_value_toman
                    if destination.price_value_toman is not None
                    else parse_toman_price(destination.price_toman)
                )
                if not isinstance(price, int) or price <= 0:
                    continue
                item: dict[str, str | int | float] = {
                    "o": route.origin[:30],
                    "d": destination.name[:30],
                    "p": price,
                }
                average = destination.average_price_toman
                count = destination.average_sample_count
                if (
                    isinstance(average, (float, int))
                    and math.isfinite(average)
                    and average > price
                    and isinstance(count, int)
                    and count >= 3
                ):
                    percentage = round((average - price) * 100 / average, 1)
                    if percentage > 0:
                        item["x"] = percentage
                values.append(item)
            except (ValueError, TypeError, AttributeError):
                continue

    cheapest = sorted(values, key=lambda item: item["p"])[:5]
    reductions = sorted(
        (item for item in values if "x" in item),
        key=lambda item: (-item["x"], item["p"]),
    )[:5]
    data = {
        "items": cheapest,
        "drops": reductions,
        "updated": (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
    }

    # Both lists are included in one state so changing tabs needs no API call.
    # Telegram limits each state field to 1024 UTF-8 bytes.
    while True:
        serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) <= 1024:
            return serialized
        if data["drops"] and len(data["drops"]) >= len(data["items"]):
            data["drops"].pop()
        elif data["items"]:
            data["items"].pop()
        elif data["drops"]:
            data["drops"].pop()
        else:
            raise ValueError("Fare widget metadata exceeds Telegram size limit")


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
    *, support_username: str = DEFAULT_SUPPORT_USERNAME,
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
    action = raw.get("data")
    # Production widgets are private and non-shared. Do not allow foreign chat
    # IDs, unexpected query types, or unsupported actions to trigger a fetch.
    if not (
        isinstance(chat, dict)
        and chat.get("type") == "private"
        and isinstance(sender, dict)
        and type(sender.get("id")) is int
        and sender["id"] == chat.get("id")
        and type(message_id) is int and message_id > 0
        and isinstance(action, str)
        and (action == "fare:refresh" or action.startswith("fare:"))
        and (raw.get("type") is None
             or (isinstance(raw["type"], dict)
                 and raw["type"].get("type") == "data"))
    ):
        await answer("invalid")
        return
    if service is None:
        await answer("unavailable")
        return

    if action != "fare:refresh":
        await handle_route_widget_query(
            raw, context.bot, service, answer, support_username=support_username,
        )
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
