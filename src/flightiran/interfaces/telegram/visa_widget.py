"""Private Telegram visa widget backed by the existing catalog and watch services."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import weakref
import zlib
from dataclasses import dataclass, replace
from html import escape, unescape
from urllib.parse import urlsplit

from flightiran.modules.visa.provenance import safe_source_url, visa_provenance

from .localization import normalize_language
from .visa_presentation import (
    _ENTRY_LABELS,
    _label,
    country_label,
    render_overview,
    render_section,
    tr,
)
from .visa_quality import render_freshness
from .visa_watches import word
from .widgets import _widget_api

LOGGER = logging.getLogger(__name__)
ACTION = re.compile(
    r"vi:([a-f0-9]{8}):(\d{1,6}):"
    r"(reload|home|legacy|watches|on|off|menu:[pd]:\d{1,3}|[pd]:[A-Z]{2}"
    r"|tab:[sce]:\d{1,3}|link:\d{1,3})\Z"
)
LOCKS: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
EXTRA = {
    "fa": [
        "خلاصه",
        "شرایط و مدارک",
        "منابع",
        "بعدی",
        "قبلی",
        "جست‌وجوی متنی",
        "هشدار فعال است",
        "هشدار متوقف است",
        "ارسال این منبع",
        "ویجت منقضی شده؛ /visa را بفرستید.",
        "دریافت اطلاعات ناموفق؛ آخرین نتیجه حفظ شد.",
        "تغییرات داده منتشرشده؛ نه تضمین تغییر قانون",
    ],
    "en": [
        "Summary",
        "Conditions",
        "Sources",
        "Next",
        "Previous",
        "Text search",
        "Alert active",
        "Alert paused",
        "Send source link",
        "Widget expired; send /visa.",
        "Update failed; last result retained.",
        "Published data changes, not guaranteed legal changes",
    ],
    "ar": [
        "الملخص",
        "الشروط والوثائق",
        "المصادر",
        "التالي",
        "السابق",
        "بحث نصي",
        "التنبيه نشط",
        "التنبيه متوقف",
        "إرسال المصدر",
        "انتهت الجلسة؛ أرسل /visa.",
        "فشل التحديث؛ تم حفظ آخر نتيجة.",
        "تغييرات البيانات المنشورة، لا ضمان لتغيير القانون",
    ],
}
TEMPLATE = r"""<!DOCTYPE html><html lang="__LANG__" dir="__DIR__"><head><style>
body{padding:12px;
margin:0;
font:13px Arial;
color:var(--tg-theme-text-color,#222)}
h3{margin:0 0 8px}button{min-height:44px;
border-radius:8px;
padding:8px;

border:1px solid var(--tg-theme-section-separator-color,#bbc);

background:var(--tg-theme-secondary-bg-color,#eee);
color:var(--tg-theme-text-color,#222)}
.row{display:flex;
gap:5px;
margin:8px 0}.row button{flex:1;
min-width:0}
.sel{background:var(--tg-theme-button-color,#238ad6);
color:var(--tg-theme-button-text-color,#fff)}
#body{white-space:pre-wrap;
line-height:1.8;
overflow-wrap:anywhere;
margin:10px 0}
#options button{display:block;
width:100%;
margin:5px 0;
text-align:start}
.small{font-size:11px;
color:var(--tg-theme-hint-color,#778)}
</style></head><body><h3 id="title"></h3>
<p class="small" id="fresh"></p><div class="row"><button id="passport"></button>
<button id="destination"></button>
</div><div class="row" id="tabs"></div>
<div id="options"></div><div id="body"></div><div class="row" id="pages"></div>
<button id="source"></button>
<div class="row"><button id="watch"></button>
<button id="watches"></button>
</div>
<p class="small" id="notice"></p><div class="row"><button id="legacy"></button>
<button id="home"></button>
</div>
<p class="small" id="status"></p><script>(function(){
var W=window.TelegramWidget,L=__LABELS__,S={},busy=false;

function id(x){return document.getElementById(x)}
function ask(a){if(busy||!S.token)return;
busy=true;

W.request('vi:'+S.token+':'+S.rev+':'+a).then(function(x){
busy=false;if(x.result!=='accepted'){
id('status').textContent=L.x[10]}},function(){busy=false;
id('status').textContent=L.x[10]})}
function button(label,a,parent){var b=document.createElement('button');
b.textContent=label;

b.addEventListener('click',function(){ask(a)});
parent.appendChild(b);
return b}
function render(){try{S=JSON.parse(W.chatData||'{}')}catch(e){return}busy=false;

id('title').textContent=L.title;id('fresh').textContent=S.fresh||'';
id('passport').textContent=L.passport+': '+(S.pl||S.p||'—');

id('destination').textContent=L.destination+': '+(S.dl||S.d||'—');id('destination').disabled=!S.p;
id('body').textContent=S.text||'';

id('status').textContent=S.error||'';
id('notice').textContent=L.x[11];

id('tabs').textContent='';
var kinds=['s','c','e'];
for(var i=0;
i<3;
i++){
var b=button(L.x[i],'tab:'+kinds[i]+':0',id('tabs'));
b.className=S.tab===kinds[i]?'sel':'';
b.disabled=!S.d}
id('options').textContent='';
var opts=S.options||[];
for(var q=0;
q<opts.length;
q++)button(opts[q].n,opts[q].a,id('options'));

id('pages').textContent='';
if(S.page>0)button(L.x[4],S.nav+':'+(S.page-1),id('pages'));

if(S.page+1<S.pages)button(L.x[3],S.nav+':'+(S.page+1),id('pages'));

id('watch').textContent=S.watch?L.active:L.add;
id('watch').disabled=!S.d||!S.watchable;

id('source').textContent=L.x[8];
id('source').style.display=typeof S.link==='number'?'block':'none';

id('watches').textContent=L.watches;
id('legacy').textContent=L.x[5];
id('home').textContent=L.home;

}
id('passport').addEventListener('click',function(){ask('menu:p:0')});

id('destination').addEventListener('click',function(){ask('menu:d:0')});

id('source').addEventListener('click',function(){if(typeof S.link==='number')ask('link:'+S.link)});

id('watch').addEventListener('click',function(){ask(S.watch?'off':'on')});

id('watches').addEventListener('click',function(){ask('watches')});
id('legacy').addEventListener('click',function(){ask('legacy')});

id('home').addEventListener('click',function(){ask('home')});
W.onEvent('chatDataChanged',render);
render();
W.ready();

})();
</script></body></html>"""


def widget_html(language: str) -> str:
    lang = normalize_language(language)
    labels = {
        "title": tr(lang, "title"),
        "passport": tr(lang, "passport"),
        "destination": tr(lang, "destination"),
        "x": EXTRA[lang],
        "active": word(lang, "pause"),
        "add": word(lang, "resume"),
        "watches": word(lang, "title").replace("<b>", "").replace("</b>", ""),
        "home": tr(lang, "back"),
    }
    html = TEMPLATE.replace("__LANG__", lang).replace("__DIR__", "ltr" if lang == "en" else "rtl")
    html = html.replace(
        "__LABELS__", json.dumps(labels, ensure_ascii=False).replace("<", "\\u003c")
    )
    raw = html.encode()
    if len(raw) > 32768 or len(zlib.compress(raw, 9)) > 4096:
        raise ValueError("Visa widget exceeds HTML limits")
    return html


def pack(value: dict, limit: int = 1024) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode()) > limit:
        raise ValueError("Visa state too large")
    return raw


def chunks(text: str, limit: int = 330) -> list[str]:
    pages, current, size = [], [], 0
    for char in text:
        width = len(char.encode())
        if size + width > limit:
            pages.append("".join(current))
            current, size = [], 0
        current.append(char)
        size += width
    if current or not pages:
        pages.append("".join(current))
    return pages


def plain(html: str) -> str:
    return unescape(re.sub(r"<[^>]*>", "", html))


def published_text(value: object, language: str) -> str:
    """Retain every selected published condition with readable labels, without truncation."""
    if isinstance(value, dict):
        keys = {
            "entryRequirements": "entry",
            "passport": "row",
            "visaTypes": "types",
            "status": "status",
            "stayDays": "stay",
            "notes": "tips",
            "text": "details",
            "rule": "condition",
            "documents": "docs",
            "items": "docs",
            "source": "source",
            "url": "source",
            "lastVerified": "checked",
            "name": "title",
        }
        lines = []
        for key, item in value.items():
            label = (
                _label(_ENTRY_LABELS, key, language)
                if key in _ENTRY_LABELS
                else tr(language, keys[key])
                if key in keys
                else re.sub(r"([a-z])([A-Z])", r"\1 \2", str(key))
            )
            lines.append(label + ": " + published_text(item, language))
        return "\n".join(lines)
    if isinstance(value, (list, tuple)):
        return "\n".join("• " + published_text(v, language) for v in value)
    return json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value


def source_links(detail) -> list[str]:
    result = []

    def visit(value):
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            url = safe_source_url(value)
            if url and url not in result:
                result.append(url)

    visit(
        [
            detail.record,
            detail.visa_types,
            detail.destination_data.get("entryRequirements"),
            (detail.destination_data.get("meta") or {}).get("primarySources"),
            (detail.destination_data.get("visaPolicy") or {}).get("defaultSource"),
        ]
    )
    provenance = visa_provenance(detail)
    visit([provenance.source_url, provenance.destination_json_url])
    return result


@dataclass
class Session:
    token: str
    passport: str
    destination: str = ""
    rev: int = 0
    view: str = "menu:d"
    page: int = 0
    last: dict | None = None


def storage(context, telegram_id: int) -> dict:
    app = getattr(context, "application", None)
    if app is not None:
        return app.user_data[telegram_id]
    data = getattr(context, "user_data", None)
    if not isinstance(data, dict):
        raise ValueError("No owner context")
    return data


async def state_for(session: Session, catalog, watches, user_id: int, language: str) -> dict:
    countries = {c.code: c for c in await catalog.countries()}
    names = {code: country_label(code, c.name, language) for code, c in countries.items()}
    freshness = await catalog.freshness()
    checked = freshness.checked_at.strftime("%Y-%m-%d %H:%M UTC") if freshness.checked_at else "—"
    fresh_label = {"fa": "بررسی فهرست محلی", "en": "Local index check", "ar": "فحص الفهرس المحلي"}[
        language
    ]
    status_label = {"fa": "قدیمی / نامشخص", "en": "stale / unknown", "ar": "قديم / غير معروف"}[
        language
    ]
    brief_freshness = fresh_label + ": " + checked
    if freshness.status != "fresh":
        brief_freshness += " • " + status_label
    base = {
        "fresh": brief_freshness,
        "token": session.token,
        "rev": session.rev,
        "p": session.passport,
        "d": session.destination,
        "pl": names.get(session.passport, session.passport),
        "dl": names.get(session.destination, ""),
        "watch": False,
        "watchable": False,
    }
    if session.view.startswith("menu:"):
        kind = session.view[-1]
        options = sorted(countries, key=lambda code: (names[code], code))
        if kind == "d":
            popular = [c for c in ("TR", "AE", "GE", "AM", "AZ", "IQ") if c in options]
            options = popular + [c for c in options if c not in popular]
        pages, page = [], []
        for code in options:
            item = {"n": names[code] + " (" + code + ")", "a": kind + ":" + code}
            candidate = {
                **base,
                "options": page + [item],
                "nav": session.view,
                "page": 999,
                "pages": 999,
            }
            try:
                pack(candidate, 900)
            except ValueError:
                if not page:
                    raise
                pages.append(page)
                page = [item]
            else:
                page.append(item)
        pages.append(page)
        index = min(session.page, len(pages) - 1)
        return {
            **base,
            "options": pages[index],
            "page": index,
            "pages": len(pages),
            "nav": session.view,
        }
    detail = await catalog.detail(session.passport, session.destination)
    if detail is None:
        return {**base, "text": tr(language, "missing"), "tab": "s"}
    if watches is not None:
        owned = await watches.list_user(user_id)
        base["watch"] = any(
            w.passport == session.passport and w.destination == session.destination and w.active
            for w in owned
        )
        base["watchable"] = True
    tab = session.view[-1]
    freshness = plain(render_freshness(await catalog.freshness(), language))
    if tab == "s":
        text = plain(render_overview(detail, language)) + "\n" + freshness
        if detail.rule.notes and detail.rule.notes not in text:
            text += "\n" + detail.rule.notes
    elif tab == "c":
        text = (
            tr(language, "caution")
            + "\n"
            + published_text(
                {
                    "entryRequirements": detail.destination_data.get("entryRequirements") or {},
                    "passport": detail.record,
                    "visaTypes": detail.visa_types,
                },
                language,
            )
        )
        if not detail.destination_data.get("entryRequirements") and not detail.visa_types:
            text += "\n" + tr(language, "not_known")
    else:
        text = plain(render_section(detail, language, "sources")) + "\n" + freshness
    overhead = len(
        pack(
            {**base, "text": "", "tab": tab, "page": 999, "pages": 999, "nav": "tab:" + tab}
        ).encode()
    )
    pages = chunks(text, max(50, 780 - overhead))
    index = min(session.page, len(pages) - 1)
    result = {
        **base,
        "text": pages[index],
        "tab": tab,
        "page": index,
        "pages": len(pages),
        "nav": "tab:" + tab,
    }
    links = source_links(detail) if tab == "e" else []
    # A separate source choice page is encoded as one ordinary content page per URL.
    if links:
        result["pages"] += len(links)
        index = min(session.page, result["pages"] - 1)
        result["page"] = index
        if index >= len(pages):
            link = index - len(pages)
            result["text"] = urlsplit(links[link]).hostname or tr(language, "source")
            result["link"] = link
    result["text"] += "\n" + (
        EXTRA[language][6 if base["watch"] else 7]
        if watches is not None
        else word(language, "unavailable")
    )
    pack(result, 900)
    return result


async def send_visa_widget(
    message, context, catalog, watches, users, user_id: int, language: str
) -> bool:
    if (
        getattr(context.bot, "platform", "telegram") == "bale"
        or getattr(getattr(message, "chat", None), "type", None) != "private"
        or catalog is None
    ):
        return False
    try:
        if not await catalog.ready():
            return False
        countries = {c.code for c in await catalog.countries()}
        selected = await users.get_visa_passport(user_id)
        passport = selected if selected in countries else "IR" if "IR" in countries else ""
        session = Session(secrets.token_hex(4), passport, view="menu:d" if passport else "menu:p")
        state = await state_for(session, catalog, watches, user_id, language)
        result = await _widget_api(
            context.bot,
            "sendWidget",
            {
                "chat_id": message.chat_id,
                "html": widget_html(language),
                "chat_data": pack(state),
                "public_data": "{}",
                "allow_queries": True,
            },
        )
        mid = (
            result.get("message_id")
            if isinstance(result, dict)
            else getattr(result, "message_id", None)
        )
        if type(mid) is not int or mid <= 0:
            raise ValueError("Missing widget message ID")
        data = storage(context, message.chat_id).setdefault("visa_widget_sessions", {})
        data[mid] = session
        while len(data) > 20:
            data.pop(next(iter(data)))
        session.last = state
        return True
    except Exception as exc:
        LOGGER.warning("visa_widget_send_failed type=%s", type(exc).__name__)
        return False


async def handle_visa_widget_query(update, context, catalog, watches, users, on_open) -> None:
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
        return

    async def answer(value):
        await _widget_api(
            context.bot, "answerWidgetQuery", {"widget_query_id": raw["id"], "data": value}
        )

    sender, chat, action, typ = raw.get("from"), raw.get("chat"), raw.get("data"), raw.get("type")
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
        and type(raw.get("message_id")) is int
        and raw["message_id"] > 0
        and not raw.get("widget_id")
        and (typ is None or isinstance(typ, dict) and typ.get("type") == "data")
        and getattr(context.bot, "platform", "telegram") != "bale"
    ):
        await answer("invalid")
        return
    await answer("accepted")
    owner, mid = sender["id"], raw["message_id"]

    async def edit(state):
        await _widget_api(
            context.bot,
            "editMessageWidgetData",
            {"chat_id": owner, "message_id": mid, "chat_data": pack(state)},
        )

    lock = LOCKS.setdefault((owner, mid), asyncio.Lock())
    async with lock:
        session = storage(context, owner).get("visa_widget_sessions", {}).get(mid)
        record = await users.get_or_create(owner)
        language = normalize_language(await users.get_language(record.id))
        if session is None or match[1] != session.token:
            await edit({"error": EXTRA[language][9]})
            return
        original = replace(session)
        try:
            if int(match[2]) != session.rev:
                await edit(await state_for(session, catalog, watches, record.id, language))
                return
            command = match[3]
            countries = {c.code for c in await catalog.countries()}
            if session.passport and session.passport not in countries:
                raise ValueError("Passport unavailable")
            session.rev += 1
            if command.startswith("menu:"):
                _, kind, page = command.split(":")
                session.view, session.page = "menu:" + kind, int(page)
            elif command.startswith(("p:", "d:")):
                kind, code = command.split(":")
                if code not in countries:
                    raise ValueError("Unknown country")
                if kind == "p":
                    await users.set_visa_passport(record.id, code)
                    storage(context, owner)["visa_passport"] = code
                    session.passport, session.destination, session.view = code, "", "menu:d"
                else:
                    session.destination, session.view = code, "tab:s"
                session.page = 0
            elif command.startswith("tab:"):
                _, tab, page = command.split(":")
                session.view, session.page = "tab:" + tab, int(page)
            elif command in {"on", "off", "link"} or command.startswith("link:"):
                if not session.passport or session.destination not in countries:
                    raise ValueError("No route")
                detail = await catalog.detail(session.passport, session.destination)
                if detail is None:
                    raise ValueError("No verified data")
                if command == "on":
                    if watches is None:
                        raise ValueError("Watches unavailable")
                    await watches.subscribe(record.id, session.passport, session.destination)
                elif command == "off":
                    if watches is None:
                        raise ValueError("Watches unavailable")
                    for watch in await watches.list_user(record.id):
                        if (watch.passport, watch.destination) == (
                            session.passport,
                            session.destination,
                        ):
                            await watches.set_active(record.id, watch.id, False)
                else:
                    url = source_links(detail)[int(command.split(":")[1])]
                    await context.bot.send_message(
                        chat_id=owner,
                        text=escape(url),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
            elif command in {"legacy", "watches", "home"}:
                await on_open(command, owner)
            state = await state_for(session, catalog, watches, record.id, language)
            session.last = state
            await edit(state)
        except Exception as exc:
            LOGGER.warning("visa_widget_action_failed type=%s", type(exc).__name__)
            original.rev = session.rev
            storage(context, owner)["visa_widget_sessions"][mid] = original
            previous = dict(original.last or {"token": original.token})
            error = (
                word(language, "limit")
                if isinstance(exc, ValueError) and "limit" in str(exc)
                else EXTRA[language][10]
            )
            previous.update(rev=original.rev, error=error)
            await edit(previous)
