"""Interactive Telegram Bot API 10.4 directory for published airport guides.

The airport catalog and its 29 per-IATA JSON documents are the same files
used by Android and the Mini App. The widget never fabricates airport facts.
"""

from __future__ import annotations

import json
import logging
import re
import zlib
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from flightiran.modules.airport.catalog import AirportCatalog

from .widgets import _widget_api

LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 4
CONTENT_LIMIT = 490
STATE_LIMIT = 1024
ACTION = re.compile(
    r"^ap:(?:home|o:[A-Z]{3}|l:[A-Z]{3}:[0-9]{1,2}|"
    r"s:[A-Z]{3}:[0-9]{2}|d:[A-Z]{3}:[0-9]{2}:[0-9]{3}|"
    r"r:[A-Z]{3}:[0-9]{2})$"
)


def _json(data: dict) -> str:
    value = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(value.encode("utf-8")) > STATE_LIMIT:
        raise ValueError("Airport widget state exceeds Telegram size limit")
    return value


def _safe_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    if any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or not url.hostname
                or url.username or url.password or url.port == 0):
            return None
        return value
    except ValueError:
        return None


def _chunks(value: str, limit: int = CONTENT_LIMIT) -> list[str]:
    """Split on Unicode codepoints; no published guidance is truncated."""
    result = []
    current = []
    length = 0
    for char in value:
        size = len(char.encode("utf-8"))
        if length + size > limit and current:
            result.append("".join(current))
            current = []
            length = 0
        current.append(char)
        length += size
    if current:
        result.append("".join(current))
    return result


def _pieces(section: dict) -> list[str]:
    pieces = []
    for block in section.get("blocks", []):
        if not isinstance(block, dict):
            continue
        typ = block.get("type")
        if typ == "text" and isinstance(block.get("text_fa"), str):
            pieces.append(block["text_fa"].strip())
        elif typ == "bullets" and isinstance(block.get("items_fa"), list):
            pieces.extend(
                "• " + x.strip() for x in block["items_fa"]
                if isinstance(x, str) and x.strip()
            )
        elif typ in {"link", "map", "video"}:
            label = block.get("title_fa")
            if isinstance(label, str) and label.strip():
                pieces.append("منبع مرتبط: " + label.strip() + " (در بخش منابع)")
        elif typ == "image":
            label = block.get("alt_fa")
            if isinstance(label, str) and label.strip():
                pieces.append("تصویر مرتبط: " + label.strip() + " (در بخش منابع)")
        elif typ == "flight_board":
            # The GitHub documents are static; do not claim live flight status.
            pieces.append("برای وضعیت لحظه‌ای پرواز از سامانه رسمی اطلاعات پرواز استفاده کنید.")
        # 'experience' is intentionally omitted pending consent/privacy checks.
    return [p for p in pieces if p]


def _pages(section: dict) -> list[str]:
    pages: list[str] = []
    current = ""
    for piece in _pieces(section):
        for fragment in _chunks(piece):
            merged = current + ("\n\n" if current else "") + fragment
            if len(merged.encode("utf-8")) > CONTENT_LIMIT:
                if current:
                    pages.append(current)
                current = fragment
            else:
                current = merged
    if current:
        pages.append(current)
    return pages


class AirportGuideStore:
    """Read published content from the existing GitHub-managed data directory."""

    def __init__(self, catalog: AirportCatalog, root: Path | str = "data/airports") -> None:
        self.catalog = catalog
        self.root = Path(root)

    def airports(self) -> list[list]:
        index = json.loads((self.root / "airport-index.v1.json").read_text(encoding="utf-8"))
        if index.get("schema_version") != 1:
            raise ValueError("Unsupported airport catalog")
        result = []
        seen = set()
        for row in index["airports"]:
            code = row["iata"]
            airport = self.catalog.get(code)
            if (row.get("enabled") is not True or code in seen or airport is None
                    or not re.fullmatch(r"[A-Z]{3}", code)
                    or row.get("detail_path") != f"details/{code}.v1.json"):
                continue
            seen.add(code)
            result.append([code, airport.display_name("fa"), airport.country == "IR"])
        return sorted(result, key=lambda a: (not a[2], a[1]))

    def _airport(self, code: str) -> tuple[str, dict]:
        allowed = {row[0]: row[1] for row in self.airports()}
        if code not in allowed:
            raise ValueError("Airport is disabled or unavailable")
        # The allowlisted 3-letter code is the only variable part of this path.
        document = json.loads(
            (self.root / "details" / f"{code}.v1.json").read_text(encoding="utf-8")
        )
        if document.get("schema_version") != 1 or document.get("iata") != code:
            raise ValueError("Invalid airport detail document")
        return allowed[code], document

    def sections(self, code: str) -> tuple[str, list[dict]]:
        name, document = self._airport(code)
        sections = []
        for row in document["sections"]:
            if row.get("status") != "published":
                continue
            review = row.get("reviewed_at")
            if not isinstance(review, str) or not review:
                continue
            try:
                if date.fromisoformat(review[:10]) > date.today():
                    continue
            except ValueError:
                continue
            if _pages(row):
                sections.append(row)
        return name, sorted(sections, key=lambda s: (s.get("order", 0), s["id"]))

    def list_state(self, code: str, page: int = 0) -> str:
        name, sections = self.sections(code)
        pages = max(1, (len(sections) + PAGE_SIZE - 1) // PAGE_SIZE)
        if not 0 <= page < pages:
            raise ValueError("Invalid airport section page")
        start = page * PAGE_SIZE
        return _json({
            "v": "list", "a": code, "n": name, "p": page, "pages": pages,
            "total": len(sections),
            "items": [[i, s["title_fa"]] for i, s in enumerate(sections)
                      if start <= i < start + PAGE_SIZE],
        })

    def detail_state(self, code: str, index: int, page: int = 0) -> str:
        name, sections = self.sections(code)
        if not 0 <= index < len(sections):
            raise ValueError("Unknown airport section")
        section = sections[index]
        pages = _pages(section)
        if not 0 <= page < len(pages):
            raise ValueError("Invalid airport content page")
        return _json({
            "v": "detail", "a": code, "n": name, "i": index,
            "s": section["title_fa"], "r": section["reviewed_at"][:10],
            "p": page, "pages": len(pages), "t": pages[page],
        })

    def sources(self, code: str, index: int) -> tuple[str, str, list[tuple[str, str]]]:
        name, sections = self.sections(code)
        if not 0 <= index < len(sections):
            raise ValueError("Unknown airport section")
        section = sections[index]
        found: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add(title: str, candidate: object) -> None:
            url = _safe_url(candidate)
            if url and url not in seen:
                seen.add(url)
                found.append((title, url))

        for url in section.get("source_urls", []):
            add("مرجع منتشرشده", url)
        for block in section.get("blocks", []):
            if not isinstance(block, dict):
                continue
            typ = block.get("type")
            if typ in {"link", "video", "image", "map"}:
                key = "external_url" if typ == "map" else "url"
                add(block.get("title_fa") or block.get("alt_fa") or "منبع", block.get(key))
        return name, section["title_fa"], found


# Names/codes are injected at send time from the canonical identity + enabled
# index. There is no network access from a Telegram widget's QuickJS runtime.
HTML_TEMPLATE = r"""<!DOCTYPE html><html lang="fa" dir="rtl">
<head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;padding:12px;font:13px Arial,sans-serif;
color:var(--tg-theme-text-color,#222)}h3{font-size:17px;margin:0 0 4px}
h4{font-size:14px;margin:6px 0}.muted{color:var(--tg-theme-hint-color,#73808e);
font-size:11px;line-height:1.7;margin:3px 0}
.tabs{display:flex;gap:6px;margin:10px 0}.tabs[hidden]{display:none}
.tabs button{flex:1;padding:9px 3px;
font-size:12px;border:1px solid var(--tg-theme-section-separator-color,#aaa);
border-radius:9px;color:var(--tg-theme-text-color,#222);
background:var(--tg-theme-secondary-bg-color,#f2f3f5)}
.tabs button.sel{background:var(--tg-theme-button-color,#2484d5);
color:var(--tg-theme-button-text-color,#fff);font-weight:bold}
#items{max-height:270px;overflow:auto}.item{display:flex;align-items:center;
justify-content:space-between;gap:8px;width:100%;text-align:right;margin:5px 0;
padding:11px 9px;border-radius:10px;border:1px solid
var(--tg-theme-section-separator-color,#ddd);background:var(--tg-theme-bg-color,#fff);
color:var(--tg-theme-text-color,#222);font-size:12px}
.code{direction:ltr;color:var(--tg-theme-hint-color,#73808e);font-size:11px}
.bar{display:flex;gap:7px;justify-content:space-between;align-items:center;
margin-top:10px}.bar button{flex:1;padding:9px 3px;border-radius:9px;
background:var(--tg-theme-secondary-bg-color,#eee);
color:var(--tg-theme-text-color,#222);border:1px solid
var(--tg-theme-section-separator-color,#ddd);font-size:11px}
#content{white-space:pre-wrap;line-height:1.9;font-size:12px;max-height:255px;
overflow:auto;padding:11px;background:var(--tg-theme-secondary-bg-color,#eee);
border-radius:10px;overflow-wrap:anywhere}#status{margin:7px 0 0;
color:var(--tg-theme-hint-color,#73808e);font-size:11px}
button:disabled{opacity:.5}
</style></head><body>
<h3>راهنمای فرودگاه‌ها</h3><p class="muted" id="subtitle">۲۹ فرودگاه، اطلاعات تأییدشده</p>
<div class="tabs" id="filters" role="tablist" aria-label="محدوده فرودگاه‌ها">
<button id="all" class="sel" aria-pressed="true">همه</button>
<button id="iran" aria-pressed="false">ایران</button>
<button id="foreign" aria-pressed="false">خارجی</button></div>
<h4 id="heading">انتخاب فرودگاه</h4>
<div id="items"></div><div id="content" hidden></div>
<div class="bar" id="controls"></div><p id="status" role="status"></p>
<script>(function(){
var W=window.TelegramWidget, AIRPORTS=__AIRPORTS__;
var state={v:'home'},filter='all',busy=false;
function el(x){return document.getElementById(x);}
function parse(s){try{return JSON.parse(s||'{}');}catch(e){return {};}}
function fa(n){return String(n).replace(/[0-9]/g,function(c){
return '۰۱۲۳۴۵۶۷۸۹'.charAt(c.charCodeAt(0)-48);});}
function button(label,click,where){
var b=document.createElement('button');b.type='button';b.textContent=label;
b.disabled=busy;b.addEventListener('click',click);where.appendChild(b);return b;}
function send(action,source){
if(busy||!W)return;busy=true;el('status').textContent='در حال دریافت اطلاعات...';
W.request(action).then(function(response){
busy=false;var value=parse(response.result);
if(value.v){state=value;render();el('status').textContent='';}
else{el('status').textContent=source&&response.result==='accepted'
?'لینک‌های منابع در پیام بعدی ربات ارسال شدند.':'دریافت اطلاعات ممکن نشد.';render();}
},function(){busy=false;render();el('status').textContent='ارتباط برقرار نشد.';});
}
function render(){
var home=state.v==='home',list=state.v==='list',detail=state.v==='detail';
el('filters').hidden=!home;el('items').hidden=detail;el('content').hidden=!detail;
el('items').textContent='';el('controls').textContent='';
el('heading').textContent=home?'انتخاب فرودگاه':
list?state.n+' ('+state.a+')':state.s;
el('subtitle').textContent=home?fa(AIRPORTS.length)+' فرودگاه فعال':
state.n+' • '+state.a;
if(home){
var count=0;for(var i=0;i<AIRPORTS.length;i++){
var a=AIRPORTS[i];if(filter==='iran'&&!a[2]||filter==='foreign'&&a[2])continue;
count++;(function(row){var b=button(row[1]+' · '+row[0],function(){
send('ap:o:'+row[0]);},el('items'));b.className='item';})(a);
}
if(!count)el('items').textContent='فرودگاهی برای نمایش موجود نیست.';
}else if(list){
for(var j=0;j<(state.items||[]).length;j++){
(function(info){var b=button(info[1]+'  ←',function(){
send('ap:s:'+state.a+':'+('0'+info[0]).slice(-2));},el('items'));b.className='item';
})(state.items[j]);}
if(!state.total)el('items').textContent='موضوع منتشرشده‌ای وجود ندارد.';
if(state.p>0)button('صفحه قبل',function(){send('ap:l:'+state.a+':'+(state.p-1));},
el('controls'));
button('فهرست فرودگاه‌ها',function(){send('ap:home');},el('controls'));
if(state.p+1<state.pages)button('صفحه بعد',function(){
send('ap:l:'+state.a+':'+(state.p+1));},el('controls'));
el('subtitle').textContent=state.n+' • '+fa(state.total)+' موضوع • صفحه '+
fa(state.p+1)+' از '+fa(state.pages);
}else if(detail){
el('content').textContent=state.t||'';
el('subtitle').textContent=state.n+' • آخرین بررسی: '+state.r+' • صفحه '+
fa(state.p+1)+' از '+fa(state.pages);
if(state.p>0)button('قبلی',function(){
send('ap:d:'+state.a+':'+('0'+state.i).slice(-2)+':'+('00'+(state.p-1)).slice(-3));
},el('controls'));
button('موضوعات',function(){send('ap:l:'+state.a+':0');},el('controls'));
if(state.p+1<state.pages)button('بعدی',function(){
send('ap:d:'+state.a+':'+('0'+state.i).slice(-2)+':'+('00'+(state.p+1)).slice(-3));
},el('controls'));
button('منابع و لینک‌ها',function(){
send('ap:r:'+state.a+':'+('0'+state.i).slice(-2),true);},el('controls'));
}
for(var f=0;f<3;f++){
var key=['all','iran','foreign'][f],node=el(key);
node.className=filter===key?'sel':'';
node.setAttribute('aria-pressed',filter===key?'true':'false');}
}
for(var i=0;i<3;i++){
(function(key){el(key).addEventListener('click',function(){filter=key;render();});
})(['all','iran','foreign'][i]);}
if(W){var saved=parse(W.chatData);if(saved.v)state=saved;
W.onEvent('chatDataChanged',function(){var next=parse(W.chatData);
if(next.v){state=next;render();}});}
render();if(W)W.ready();
})();</script></body></html>"""


def airport_widget_html(store: AirportGuideStore) -> str:
    rows = store.airports()
    if not rows:
        raise ValueError("No enabled airport guides")
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__AIRPORTS__", data)
    if len(html.encode("utf-8")) > 32768 or len(zlib.compress(html.encode("utf-8"), 9)) > 4096:
        raise ValueError("Airport widget HTML exceeds Telegram size limit")
    return html


async def send_airport_widget(
    message: object, bot: object, store: AirportGuideStore | None,
    mini_app_url: str | None = None,
) -> bool:
    if getattr(bot, "platform", "telegram") == "bale":
        return False
    if getattr(getattr(message, "chat", None), "type", None) != "private":
        await message.reply_text("راهنمای تعاملی فقط در گفت‌وگوی خصوصی تلگرام فعال است.")
        return False
    if store is None:
        await message.reply_text("راهنمای فرودگاه‌ها فعلاً در دسترس نیست.")
        return False
    try:
        html = airport_widget_html(store)
    except Exception as exc:
        LOGGER.warning("airport_widget_data_failed type=%s", type(exc).__name__)
        await message.reply_text("دریافت فهرست فرودگاه‌ها ممکن نشد؛ دوباره تلاش کنید.")
        return False
    try:
        await _widget_api(bot, "sendWidget", {
            "chat_id": message.chat_id,
            "html": html,
            "chat_data": '{"v":"home"}',
            "allow_queries": True,
        })
        return True
    except Exception as exc:
        LOGGER.warning("airport_widget_send_failed type=%s", type(exc).__name__)
        keyboard = None
        if mini_app_url and mini_app_url.startswith("https://"):
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("راهنمای فرودگاه‌ها در مینی‌اپ",
                                     web_app=WebAppInfo(mini_app_url))
            ]])
        await message.reply_text(
            "راهنمای ۲۹ فرودگاه در نسخه‌های جدید تلگرام به شکل تعاملی نمایش "
            "داده می‌شود. تلگرام را به‌روز کنید یا از مینی‌اپ استفاده کنید.",
            reply_markup=keyboard,
        )
        return False


async def _send_sources(bot: object, user_id: int, name: str, title: str,
                        sources: list[tuple[str, str]]) -> None:
    heading = f"📎 <b>{escape(name)} | {escape(title)}</b>"
    if not sources:
        await bot.send_message(chat_id=user_id,
                               text=heading + "\nمنبع لینک‌شده‌ای برای این بخش وجود ندارد.",
                               parse_mode="HTML")
        return
    message = heading
    for label, url in sources:
        entry = f'\n• <a href="{escape(url, quote=True)}">{escape(label)}</a>'
        if len(message) + len(entry) > 3700:
            await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML",
                                   disable_web_page_preview=True)
            message = heading
        message += entry
    await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML",
                           disable_web_page_preview=True)


async def handle_airport_widget_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    store: AirportGuideStore | None,
) -> None:
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        return

    async def answer(value: str) -> None:
        await _widget_api(context.bot, "answerWidgetQuery", {
            "widget_query_id": raw["id"], "data": value,
        })

    sender = raw.get("from")
    chat = raw.get("chat")
    mid = raw.get("message_id")
    action = raw.get("data")
    typ = raw.get("type")
    if not (
        isinstance(sender, dict)
        and isinstance(chat, dict)
        and type(sender.get("id")) is int and sender["id"] > 0
        and chat.get("type") == "private" and chat.get("id") == sender["id"]
        and type(mid) is int and mid > 0
        and isinstance(action, str) and ACTION.fullmatch(action)
        and (typ is None or (isinstance(typ, dict) and typ.get("type") == "data"))
        and not raw.get("widget_id")
    ):
        await answer("invalid")
        return
    if store is None:
        await answer("unavailable")
        return

    try:
        parts = action.split(":")
        if action == "ap:home":
            state = _json({"v": "home"})
        elif parts[1] == "o":
            state = store.list_state(parts[2])
        elif parts[1] == "l":
            state = store.list_state(parts[2], int(parts[3]))
        elif parts[1] == "s":
            state = store.detail_state(parts[2], int(parts[3]))
        elif parts[1] == "d":
            state = store.detail_state(parts[2], int(parts[3]), int(parts[4]))
        else:
            name, title, sources = store.sources(parts[2], int(parts[3]))
            await answer("accepted")
            try:
                await _send_sources(context.bot, sender["id"], name, title, sources)
            except Exception as exc:
                LOGGER.warning("airport_sources_send_failed type=%s", type(exc).__name__)
            return
    except (ValueError, KeyError, IndexError, OSError, TypeError) as exc:
        LOGGER.warning("airport_widget_read_failed type=%s", type(exc).__name__)
        await answer("unavailable")
        return

    await answer(state)
    try:
        await _widget_api(context.bot, "editMessageWidgetData", {
            "chat_id": sender["id"], "message_id": mid, "chat_data": state,
        })
    except Exception as exc:
        # The QuickJS request already received this state in answerWidgetQuery.
        LOGGER.warning("airport_widget_edit_failed type=%s", type(exc).__name__)
