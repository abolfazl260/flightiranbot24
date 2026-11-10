"""Private, paged travel-resource widget; the existing catalog is authoritative."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import weakref
import zlib
from dataclasses import dataclass, field, replace
from datetime import date
from urllib.parse import urlsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.useful_content import UsefulContentCatalog

from .useful_content import USEFUL_CATEGORIES, USEFUL_SUBCATEGORIES, useful_menu
from .visa_widget import chunks, storage
from .widgets import _widget_api

LOGGER = logging.getLogger(__name__)
LOCKS: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
ACTION = re.compile(
    r"uf:([a-f0-9]{8}):(\d{1,9}):"
    r"(home|refresh|filters|back|legacy|page:\d{1,6}|filter:\d{1,6}"
    r"|detail:\d{1,6}|open|category:[a-z-]{1,24})\Z"
)
LABELS = dict(USEFUL_CATEGORIES) | USEFUL_SUBCATEGORIES
CHILDREN = {"flights": "flight-rules", "baggage": "flight-rules", "international": "travel-sites"}
ERROR = "ارتباط ناموفق؛ آخرین اطلاعات حفظ شد. دوباره تلاش کنید."
TEMPLATE = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<style>
body{margin:0;
padding:12px;
font:13px Arial;
color:var(--tg-theme-text-color,#222)}
h3{margin:0 0 4px}p{margin:6px 0;
line-height:1.7}.muted{font-size:11px;
color:var(--tg-theme-hint-color,#778)}
button{min-height:44px;
padding:8px;
border-radius:9px;
border:1px solid var(--tg-theme-section-separator-color,#bbc);
background:var(--tg-theme-secondary-bg-color,#eee);
color:var(--tg-theme-text-color,#222);
font:inherit;
text-align:start}
#items{display:flex;
flex-direction:column;
gap:6px;
margin:8px 0}#items.grid{display:grid;
grid-template-columns:1fr 1fr}
.row{display:flex;
gap:6px;
margin-top:7px}.row button{flex:1;
text-align:center}
.sel,#open{background:var(--tg-theme-button-color,#238ad6);
color:var(--tg-theme-button-text-color,#fff)}
#body{white-space:pre-wrap;
overflow-wrap:anywhere;
line-height:1.8}#status{min-height:16px}
[hidden]{display:none!important}
</style>
</head>
<body>
<h3>اطلاعات کاربردی سفر</h3>
<p class="muted">منابع سفر را بر اساس موضوع یا کشور پیدا کنید.</p>
<p id="count" class="muted">
</p>
<p id="selected">
</p>
<div id="items">
</div>
<div id="body">
</div>
<p id="checked" class="muted">
</p>
<div class="row">
<button id="open" hidden>مشاهده منبع</button>
</div>
<div class="row" id="pages">
</div>
<div class="row">
<button id="back">بازگشت به دسته‌ها</button>
<button id="filters">جست‌وجو با فیلتر</button>
</div>
<div class="row">
<button id="refresh">تازه‌سازی اطلاعات</button>
<button id="legacy">منوی ساده</button>
</div>
<p id="status" class="muted" role="status">
</p>
<script>(function(){
var W=window.TelegramWidget,S={},busy=false;

function id(x){return document.getElementById(x)}
function ask(a){if(busy||!W||!S.token)return;
busy=true;
id('status').textContent='در حال دریافت…';

W.request('uf:'+S.token+':'+S.rev+':'+a).then(function(r){
if(r.result!=='accepted'){busy=false;
id('status').textContent='درخواست نامعتبر یا منقضی؛ /useful را بفرستید.'}},function(){busy=false;
id('status').textContent='ارتباط ناموفق؛ دوباره تلاش کنید.'})}
function btn(label,a,host){var b=document.createElement('button');
b.textContent=label;
b.addEventListener('click',function(){ask(a)});
host.appendChild(b);
return b}
function render(){if(!W){id('status').textContent='برای منوی ساده /useful_legacy را بفرستید.';
return}
try{S=JSON.parse(W.chatData||'{}')}catch(e){
id('status').textContent='اطلاعات خوانده نشد؛ /useful_legacy';
return}
busy=false;
id('status').textContent=S.error||S.notice||'';
id('count').textContent=(S.total||0)+' منبع';

id('selected').textContent=S.title||'';
id('selected').className='sel';
id('body').textContent=S.text||'';

id('checked').textContent=S.checked?'آخرین بررسی لینک: '+S.checked:'';

id('open').hidden=!S.can_open;
id('items').textContent='';
id('items').className=S.view==='home'?'grid':'';

var rows=S.rows||[];
for(var i=0;
i<rows.length;
i++)btn(rows[i].n,rows[i].a,id('items'));

if(S.empty)id('body').textContent='منبعی برای این فیلتر ثبت نشده است.';

id('pages').textContent='';
if(S.page>0)btn('قبلی','page:'+(S.page-1),id('pages'));

if(S.page+1<S.pages)btn('بعدی','page:'+(S.page+1),id('pages'));

id('back').textContent=S.view==='detail'?'بازگشت به فهرست':'بازگشت به دسته‌ها';
}
id('back').addEventListener('click',function(){ask('back')});
id('filters').addEventListener('click',function(){ask('filters')});

id('refresh').addEventListener('click',function(){ask('refresh')});
id('legacy').addEventListener('click',function(){ask('legacy')});

id('open').addEventListener('click',function(){ask('open')});
if(W)W.onEvent('chatDataChanged',render);
render();
if(W)W.ready();

})();
</script>
</body>
</html>"""


def widget_html() -> str:
    raw = TEMPLATE.encode()
    if len(raw) > 32768 or len(zlib.compress(raw, 9)) > 4096:
        raise ValueError("Useful widget HTML too large")
    return TEMPLATE


def pack(state: dict, limit: int = 1024) -> str:
    text = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    if len(text.encode()) > limit:
        raise ValueError("Useful widget state too large")
    return text


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.replace("ي", "ی").replace("ك", "ک")).split())


def filters(catalog: UsefulContentCatalog) -> list[str]:
    # Tappable suggestions: widgets do not support keyboard inputs. Country names
    # are read from the existing country-resource titles, never a second catalog.
    terms = ["پاسپورت", "خروج", "پرواز", "بار", "بیمه", "هزینه", "نکات"]
    for link in catalog.all():
        if link.category in USEFUL_SUBCATEGORIES:
            name = normalize(link.title)
            if name and name not in terms:
                terms.append(name)
    return terms


def selected_links(catalog, category: str, term: str):
    links = catalog.all()
    if category:
        groups = {category, CHILDREN.get(category)}
        links = tuple(x for x in links if x.category in groups)
    if term:
        links = tuple(
            x
            for x in links
            if normalize(term)
            in normalize(x.title + " " + x.description + " " + LABELS.get(x.category, x.category))
        )
    return links


def preview(text: str, limit: int = 120) -> str:
    parts = chunks(text, limit)
    return parts[0] + ("…" if len(parts) > 1 else "")


def detail_chunks(text: str) -> list[str]:
    """Bound visual height too: widgets have no scrolling, even for blank lines."""
    pages, page, size, lines = [], "", 0, 0
    for char in text:
        width = len(char.encode())
        if page and (size + width > 470 or len(page) >= 160 or char == "\n" and lines >= 5):
            pages.append(page)
            page, size, lines = "", 0, 0
        page += char
        size += width
        lines += char == "\n"
    if page or not pages:
        pages.append(page)
    return pages


@dataclass
class Session:
    token: str = field(default_factory=lambda: secrets.token_hex(4))
    rev: int = 0
    view: str = "home"
    category: str = ""
    term: str = ""
    page: int = 0
    link_id: str = ""
    parent: str = ""
    terms: tuple[str, ...] = ()
    ids: tuple[str, ...] = ()
    last: dict = field(default_factory=dict)


def state_for(session: Session, catalog: UsefulContentCatalog) -> dict:
    base = {
        "token": session.token,
        "rev": session.rev,
        "view": session.view,
        "total": len(catalog.all()),
        "page": 0,
        "pages": 1,
    }
    if session.view == "detail":
        link = catalog.get(session.link_id)
        if link is None:
            raise ValueError("Resource no longer available")
        pages = detail_chunks(link.title + ("\n" + link.description if link.description else ""))
        page = min(session.page, len(pages) - 1)
        checked = link.checked_on.isoformat() if type(link.checked_on) is date else ""
        state = {
            **base,
            "text": pages[page],
            "page": page,
            "pages": len(pages),
            "can_open": True,
            "checked": checked,
        }
        pack(state, 900)
        return state
    if session.view == "home":
        rows = [
            {
                "n": label + " · " + str(len(selected_links(catalog, key, ""))),
                "a": "category:" + key,
            }
            for key, label in USEFUL_CATEGORIES
        ]
        rows.append({"n": "همه منابع", "a": "category:all"})
        title = "دسته‌های سفر"
    elif session.view == "filters":
        session.terms = tuple(filters(catalog))
        rows = [
            {"n": preview(term), "a": "filter:" + str(i)} for i, term in enumerate(session.terms)
        ]
        title = "موضوع یا کشور را انتخاب کنید"
    else:
        links = selected_links(catalog, session.category, session.term)
        session.ids = tuple(x.id for x in links)
        rows = [{"n": preview(x.title), "a": "detail:" + str(i)} for i, x in enumerate(links)]
        child = CHILDREN.get(session.category)
        if child:
            rows.insert(0, {"n": USEFUL_SUBCATEGORIES[child], "a": "category:" + child})
        title = preview(session.term or LABELS.get(session.category, "همه منابع"))
    base["title"] = title
    pages, page = [], []
    for row in rows:
        try:
            # Leave room for an error status without losing prior valid data.
            pack({**base, "page": 999999, "pages": 999999, "rows": page + [row]}, 760)
            if len(page) >= (8 if session.view == "home" else 4):
                raise ValueError("Height page limit")
        except ValueError:
            if not page:
                raise
            pages.append(page)
            page = [row]
        else:
            page.append(row)
    pages.append(page)
    index = min(session.page, len(pages) - 1)
    state = {**base, "rows": pages[index], "page": index, "pages": len(pages), "empty": not rows}
    pack(state, 900)
    return state


async def send_useful_widget(message, context, catalog) -> bool:
    if (
        getattr(context.bot, "platform", "telegram") == "bale"
        or getattr(getattr(message, "chat", None), "type", None) != "private"
    ):
        return False
    try:
        session = Session()
        state = state_for(session, catalog())
        result = await _widget_api(
            context.bot,
            "sendWidget",
            {
                "chat_id": message.chat_id,
                "html": widget_html(),
                "chat_data": pack(state),
                "public_data": "{}",
                "allow_queries": True,
                "caption": "اطلاعات کاربردی سفر · اگر ویجت نمایش داده نمی‌شود: /useful_legacy",
            },
        )
        mid = (
            result.get("message_id")
            if isinstance(result, dict)
            else getattr(result, "message_id", None)
        )
        if type(mid) is not int or mid <= 0:
            raise ValueError("No widget message ID")
        sessions = storage(context, message.chat_id).setdefault("useful_widget_sessions", {})
        sessions[mid] = session
        while len(sessions) > 20:
            sessions.pop(next(iter(sessions)))
        session.last = state
        return True
    except Exception as exc:
        LOGGER.warning("useful_widget_send_failed type=%s", type(exc).__name__)
        return False


def safe_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return bool(
            parts.scheme in {"http", "https"}
            and parts.hostname
            and not parts.username
            and not parts.password
            and parts.port != 0
            and not any(c.isspace() or ord(c) < 32 for c in url)
        )
    except ValueError:
        return False


async def handle_useful_widget_query(update, context, catalog) -> None:
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
        return

    async def answer(value):
        await _widget_api(
            context.bot, "answerWidgetQuery", {"widget_query_id": raw["id"], "data": value}
        )

    sender, chat = raw.get("from"), raw.get("chat")
    action, typ = raw.get("data"), raw.get("type")
    match = (
        ACTION.fullmatch(action) if isinstance(action, str) and len(action.encode()) <= 64 else None
    )
    if not (
        match
        and isinstance(sender, dict)
        and isinstance(chat, dict)
        and type(sender.get("id")) is int
        and sender["id"] > 0
        and type(chat.get("id")) is int
        and chat["id"] == sender["id"]
        and chat.get("type") == "private"
        and not raw.get("widget_id")
        and type(raw.get("message_id")) is int
        and raw["message_id"] > 0
        and (typ is None or isinstance(typ, dict) and typ.get("type") == "data")
        and getattr(context.bot, "platform", "telegram") != "bale"
    ):
        await answer("invalid")
        return
    owner, mid = sender["id"], raw["message_id"]
    lock = LOCKS.setdefault((owner, mid), asyncio.Lock())
    async with lock:
        session = storage(context, owner).get("useful_widget_sessions", {}).get(mid)
        if session is None or session.token != match[1] or session.rev != int(match[2]):
            await answer("invalid")
            return
        await answer("accepted")
        previous = replace(session)

        async def edit(state):
            await _widget_api(
                context.bot,
                "editMessageWidgetData",
                {"chat_id": owner, "message_id": mid, "chat_data": pack(state)},
            )

        try:
            current = catalog()  # Latest deployed server catalog, not external sites.
            command = match[3]
            session.rev += 1
            if command in {"home", "filters"}:
                session.view, session.page = command, 0
            elif command == "back":
                if session.view == "detail":
                    session.view = "list"
                elif session.view == "list" and session.category in USEFUL_SUBCATEGORIES:
                    session.category = (
                        session.parent
                        or {"flight-rules": "baggage", "travel-sites": "international"}[
                            session.category
                        ]
                    )
                else:
                    session.view = "home"
                session.page = 0
            elif command.startswith("category:"):
                category = command.partition(":")[2]
                if category not in LABELS and category != "all":
                    raise ValueError("Unknown category")
                session.parent = session.category if category in USEFUL_SUBCATEGORIES else ""
                session.category = "" if category == "all" else category
                session.term, session.view, session.page = "", "list", 0
            elif command.startswith("filter:"):
                if previous.view != "filters":
                    raise ValueError("Filter not displayed")
                session.term = session.terms[int(command.partition(":")[2])]
                session.category, session.view, session.page = "", "list", 0
            elif command.startswith("page:"):
                page = int(command.partition(":")[2])
                if page >= session.last.get("pages", 1):
                    raise ValueError("Unknown page")
                session.page = page
            elif command.startswith("detail:"):
                if previous.view != "list":
                    raise ValueError("Resource not listed")
                session.link_id = session.ids[int(command.partition(":")[2])]
                session.view, session.page = "detail", 0
            elif command == "open":
                if previous.view != "detail":
                    raise ValueError("No selected resource")
                link = current.get(session.link_id)
                if link is None or not safe_url(link.url):
                    raise ValueError("Unknown or unsafe resource")
                await context.bot.send_message(
                    chat_id=owner,
                    text=preview(link.title, 300),
                    parse_mode=None,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("مشاهده منبع", url=link.url)]]
                    ),
                    disable_web_page_preview=True,
                )
            elif command == "legacy":
                storage(context, owner)["useful_widget_legacy"] = True
                await context.bot.send_message(
                    chat_id=owner,
                    text="اطلاعات کاربردی سفر",
                    reply_markup=useful_menu("fa", current),
                )
            state = state_for(session, current)
            if command == "open":
                state["notice"] = "دکمه منبع در پیام جدید ارسال شد."
            await edit(state)
            session.last = state
        except Exception as exc:
            LOGGER.warning("useful_widget_action_failed type=%s", type(exc).__name__)
            previous.rev = session.rev
            state = {**previous.last, "rev": previous.rev, "error": ERROR}
            storage(context, owner)["useful_widget_sessions"][mid] = previous
            previous.last = state
            try:
                await edit(state)
            except Exception as failure:
                LOGGER.warning("useful_widget_edit_failed type=%s", type(failure).__name__)
                # A visible fallback also covers clients that stopped accepting widget edits.
                await context.bot.send_message(
                    chat_id=owner,
                    text="دریافت اطلاعات ناموفق بود؛ برای منوی ساده /useful_legacy را بفرستید.",
                )
