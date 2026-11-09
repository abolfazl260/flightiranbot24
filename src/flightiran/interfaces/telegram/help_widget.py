"""Telegram 10.4 private-chat interactive help centre.

All help content is local and self-contained; no network access or text inputs
are required in QuickJS. Services are launched by allowlisted widget queries.
"""

from __future__ import annotations

import json
import logging
import re
import zlib
from types import SimpleNamespace
from typing import Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from .keyboards import main_menu
from .localization import normalize_language
from .renderers import render_help
from .widgets import _widget_api

LOGGER = logging.getLogger(__name__)
OPEN_ACTION = re.compile(
    r"^hp:open:(?:fares|airports|checklist|visa|chart|alerts|"
    r"visa_watch|visa_list|language|start|support)$"
)
SERVICE_IDS = ("fares", "airports", "checklist", "visa", "chart", "alerts")
COMMANDS = (
    ("start", "start"), ("help", ""), ("language", "language"),
    ("alerts", "alerts"), ("fares", "fares"), ("chart", "chart"),
    ("checklist", "checklist"), ("airports", "airports"), ("visa", "visa"),
    ("visa_watch", "visa_watch"), ("visa_list", "visa_list"), ("cancel", ""),
)

# Strings correspond only to already implemented bot commands and services.
WORDS = {
    "fa": {
        "title": "چطور می‌تونیم کمکت کنیم؟",
        "intro": "راهنمای سریع خدمات سفر و پرواز",
        "tabs": ["خدمات", "دستورها", "سؤالات رایج"],
        "choose": "چه کاری می‌خواهی انجام بدهی؟",
        "open": "باز کردن این خدمت",
        "support": "ارتباط با پشتیبانی",
        "question": "هنوز سؤالی داری؟",
        "status": "در حال باز کردن خدمت…",
        "sent": "خدمت در پیام جدید باز شد.",
        "error": "باز کردن خدمت ممکن نشد؛ دوباره تلاش کنید.",
        "services": [
            ["fares", "قیمت بلیت", "ارزان‌ترین و کاهش قیمت",
             "قیمت‌های منتخب و بیشترین کاهش درصدی نسبت به میانگین ثبت‌شده را ببین."],
            ["airports", "فرودگاه‌ها", "راهنمای ۲۹ فرودگاه",
             "فرودگاه را انتخاب کن و بار، نقشه، خدمات و منابع منتشرشده را ببین."],
            ["checklist", "چک‌لیست سفر", "آمادگی برای سفر",
             "وسایل و کارهای ضروری سفر داخلی و خارجی را علامت بزن و ذخیره کن."],
            ["visa", "راهنمای ویزا", "شرایط ورود کشورها",
             "شرایط ورود بر اساس گذرنامه و کشور مقصد را همراه منابع بررسی کن."],
            ["chart", "نمودار قیمت", "تاریخچه مسیر پرواز",
             "مبدأ و مقصد را انتخاب کن و نمودار قیمت‌های واقعی ثبت‌شده را ببین."],
            ["alerts", "هشدار قیمت", "زنگوله کاهش قیمت",
             "هشدارهای قیمت مسیر خود را تنظیم یا مدیریت کن."],
        ],
        "commands": {
            "start": "منوی اصلی", "help": "مرکز راهنما",
            "language": "تغییر زبان", "alerts": "هشدار قیمت",
            "fares": "قیمت بلیت", "chart": "نمودار قیمت",
            "checklist": "چک‌لیست سفر", "airports": "راهنمای فرودگاه",
            "visa": "راهنمای ویزا", "visa_watch": "هشدار تغییرات ویزا",
            "visa_list": "فهرست کشورها بر اساس گذرنامه", "cancel": "لغو عملیات فعلی",
        },
        "faqs": [
            ["آیا قیمت بلیت قطعی است؟",
             "خیر. قیمت و امکان رزرو باید پیش از خرید از منبع فروش تأیید شوند."],
            ["چطور فرودگاه را پیدا کنم؟",
             "از بخش فرودگاه‌ها یا دستور /airports استفاده کن و فرودگاه را انتخاب کن."],
            ["چطور هشدار کاهش قیمت ثبت کنم؟",
             "از بخش هشدار قیمت یا دستور /alerts وارد مدیریت زنگوله‌ها شو."],
            ["آیا برای همه ابزارها Mini App لازم است؟",
             "خیر. راهنمای فرودگاه‌ها، چک‌لیست و کارت قیمت در گفت‌وگوی خصوصی تلگرام اجرا می‌شوند."],
        ],
    },
    "en": {
        "title": "How can we help?", "intro": "Quick travel and flight help",
        "tabs": ["Services", "Commands", "FAQs"],
        "choose": "What would you like to do?", "open": "Open this service",
        "support": "Contact support", "question": "Need more help?",
        "status": "Opening service…", "sent": "Service opened in a new message.",
        "error": "Could not open the service. Try again.",
        "services": [
            ["fares", "Flight fares", "Cheapest & price drops",
             "View affordable routes and verified percentage drops from recorded averages."],
            ["airports", "Airports", "29 airport guides",
             "Select an airport to read published luggage, map and travel guidance."],
            ["checklist", "Trip checklist", "Prepare for travel",
             "Track preparation for domestic or international travel."],
            ["visa", "Visa guide", "Entry requirements",
             "Check passport-based visa and entry rules with sources."],
            ["chart", "Fare history", "Price chart",
             "Choose a route and explore recorded historical airfare observations."],
            ["alerts", "Price alerts", "Fare-drop reminders",
             "Set and manage airfare notifications for your routes."],
        ],
        "commands": {
            "start": "Main menu", "help": "Help centre", "language": "Change language",
            "alerts": "Price alerts", "fares": "Fares", "chart": "Fare chart",
            "checklist": "Travel checklist", "airports": "Airport guide",
            "visa": "Visa guide", "visa_watch": "Visa change alerts",
            "visa_list": "Countries by passport", "cancel": "Cancel current action",
        },
        "faqs": [
            ["Are fares guaranteed?", "No. Final pricing and availability must be confirmed before booking."],
            ["How can I find an airport?", "Open Airports or use /airports and choose the airport."],
            ["How do I track a fare decrease?", "Open Price alerts or send /alerts."],
            ["Is the Mini App required?", "No. Several guides and interactive tools work within a private Telegram chat."],
        ],
    },
    "ar": {
        "title": "كيف يمكننا مساعدتك؟", "intro": "دليل سريع لخدمات السفر والطيران",
        "tabs": ["الخدمات", "الأوامر", "الأسئلة الشائعة"],
        "choose": "ما الخدمة التي تريدها؟", "open": "فتح هذه الخدمة",
        "support": "التواصل مع الدعم", "question": "هل تحتاج إلى المساعدة؟",
        "status": "جارٍ فتح الخدمة…", "sent": "تم فتح الخدمة في رسالة جديدة.",
        "error": "تعذر فتح الخدمة؛ حاول مرة أخرى.",
        "services": [
            ["fares", "أسعار التذاكر", "الأرخص وانخفاض الأسعار",
             "شاهد الأسعار الحالية وأكبر الانخفاضات المسجلة مقارنة بالمتوسط."],
            ["airports", "المطارات", "دليل ٢٩ مطارًا",
             "اختر مطارًا واطلع على قواعد الأمتعة والخرائط والمصادر."],
            ["checklist", "قائمة السفر", "الاستعداد للرحلة",
             "تتبّع مستلزمات الرحلات الداخلية والدولية."],
            ["visa", "دليل التأشيرات", "متطلبات الدخول",
             "تحقق من متطلبات الدخول بحسب جواز السفر والوجهة."],
            ["chart", "مخطط الأسعار", "سجل الأسعار",
             "اختر مسارًا وشاهد ملاحظات الأسعار التاريخية."],
            ["alerts", "تنبيهات الأسعار", "متابعة انخفاض الأسعار",
             "أنشئ تنبيهات أسعار تذاكر الطيران وقم بإدارتها."],
        ],
        "commands": {
            "start": "القائمة الرئيسية", "help": "مركز المساعدة",
            "language": "تغيير اللغة", "alerts": "تنبيهات الأسعار",
            "fares": "أسعار التذاكر", "chart": "مخطط الأسعار",
            "checklist": "قائمة السفر", "airports": "دليل المطارات",
            "visa": "دليل التأشيرات", "visa_watch": "تنبيهات التأشيرات",
            "visa_list": "الدول بحسب جواز السفر", "cancel": "إلغاء العملية الحالية",
        },
        "faqs": [
            ["هل أسعار التذاكر نهائية؟", "يجب تأكيد السعر والتوافر قبل الحجز."],
            ["كيف أجد مطارًا؟", "افتح دليل المطارات أو استخدم /airports."],
            ["كيف أتابع انخفاض السعر؟", "استخدم خدمة التنبيهات أو /alerts."],
            ["هل يجب فتح التطبيق المصغر؟", "لا، تتوفر عدة أدوات داخل المحادثة الخاصة."],
        ],
    },
}


HELP_WIDGET_TEMPLATE = r"""<!DOCTYPE html><html lang="__LANG__" dir="__DIR__">
<head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;padding:12px 12px 9px;
color:var(--tg-theme-text-color,#202124);font:13px Arial,sans-serif}
h3{font-size:17px;margin:2px 0 5px;line-height:1.5}
.muted{color:var(--tg-theme-hint-color,#78838e);font-size:11px;line-height:1.65}
.header{display:flex;justify-content:space-between;align-items:center;gap:8px}
.mark{padding:10px;background:var(--tg-theme-secondary-bg-color,#eef1f3);
border-radius:11px;font-size:20px}
.tabs{display:flex;gap:5px;padding:4px;margin:12px 0 9px;
background:var(--tg-theme-secondary-bg-color,#eef1f3);border-radius:11px}
.tabs button{flex:1;min-width:0;padding:10px 2px;font-size:12px;font-weight:bold;
border:1px solid var(--tg-theme-section-separator-color,#c4cbd0);
border-radius:8px;background:var(--tg-theme-bg-color,#fff);
color:var(--tg-theme-text-color,#202124)}
.tabs button.sel{background:var(--tg-theme-button-color,#3390ec);
color:var(--tg-theme-button-text-color,#fff);
border:2px solid var(--tg-theme-button-color,#3390ec)}
#services{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.card{display:flex;flex-direction:column;align-items:flex-start;min-height:80px;
text-align:start;gap:5px;border-radius:11px;padding:10px 8px;
background:var(--tg-theme-secondary-bg-color,#f1f3f5);
color:var(--tg-theme-text-color,#202124);border:1px solid
var(--tg-theme-section-separator-color,#c4cbd0)}
.card.sel{border:2px solid var(--tg-theme-button-color,#3390ec)}
.card strong{font-size:12px}.card span{font-size:11px;
color:var(--tg-theme-hint-color,#778)}
#detail{border:1px solid var(--tg-theme-section-separator-color,#ccc);
border-radius:11px;padding:10px;margin:9px 0}
#detail h4{font-size:13px;margin:0 0 5px}
#detail p{font-size:12px;line-height:1.7;margin:0 0 9px}
.primary{width:100%;padding:10px;border:0;border-radius:9px;
background:var(--tg-theme-button-color,#3390ec);
color:var(--tg-theme-button-text-color,#fff);font-weight:bold;font-size:12px}
.primary:disabled{opacity:.5}
.list{max-height:255px;overflow:auto}
.row{width:100%;display:flex;justify-content:space-between;align-items:center;
padding:10px 7px;margin:3px 0;border:1px solid
var(--tg-theme-section-separator-color,#c4cbd0);border-radius:9px;
background:var(--tg-theme-bg-color,#fff);color:var(--tg-theme-text-color,#202124);
font-size:12px;text-align:start}
.row small{color:var(--tg-theme-hint-color,#78838e);font-size:10px}
.answer{font-size:12px;line-height:1.8;white-space:pre-wrap;
padding:8px 9px;background:var(--tg-theme-secondary-bg-color,#eef1f3);
border-radius:8px}
.footer{display:flex;align-items:center;justify-content:space-between;
gap:7px;border-top:1px solid var(--tg-theme-section-separator-color,#ccc);
margin-top:10px;padding-top:9px}
.footer button{padding:9px 10px;border-radius:9px;border:1px solid
var(--tg-theme-button-color,#3390ec);background:transparent;
color:var(--tg-theme-link-color,#3390ec);font-size:12px;font-weight:bold}
#note{min-height:12px;margin:6px 0 0;font-size:11px;
color:var(--tg-theme-hint-color,#78838e)}
[hidden]{display:none!important}
</style></head><body>
<div class="header"><div><div class="muted">FLIGHTIRANBOT24 · HELP CENTER</div>
<h3 id="title"></h3><div id="intro" class="muted"></div></div>
<div class="mark" aria-hidden="true">◈</div></div>
<nav class="tabs" role="tablist" aria-label="Help categories">
<button id="tservices" class="sel" role="tab" aria-selected="true"></button>
<button id="tcommands" role="tab" aria-selected="false"></button>
<button id="tfaq" role="tab" aria-selected="false"></button></nav>
<div id="ps" role="tabpanel"><div class="muted" id="choose"></div>
<div id="services"></div><div id="detail"></div></div>
<div id="pc" class="list" role="tabpanel" hidden></div>
<div id="pf" class="list" role="tabpanel" hidden></div>
<div class="footer"><div class="muted" id="question"></div>
<button id="support"></button></div>
<p id="note" role="status"></p>
<script>(function(){
var D=__DATA__,W=window.TelegramWidget,tab='services',chosen='fares',opened=-1,busy=false;
function el(x){return document.getElementById(x);}
function node(tag,text,parent){var x=document.createElement(tag);x.textContent=text;
if(parent)parent.appendChild(x);return x;}
function btn(label,fn,parent,cls){var b=node('button',label,parent);b.type='button';
if(cls)b.className=cls;b.addEventListener('click',fn);return b;}
function open(id){
if(!W||busy)return;busy=true;el('note').textContent=D.status;
W.request('hp:open:'+id).then(function(response){
busy=false;el('note').textContent=response.result==='accepted'?D.sent:D.error;
},function(){busy=false;el('note').textContent=D.error;});
}
function renderServices(){
el('services').textContent='';
for(var i=0;i<D.services.length;i++){
(function(item){var selected=item[0]===chosen;
var card=btn((selected?'✓  ':'')+item[1],function(){
chosen=item[0];renderServices();},el('services'),'card'+(selected?' sel':''));
node('span',item[2],card);card.setAttribute('aria-pressed',selected?'true':'false');
})(D.services[i]);}
var detail=el('detail');detail.textContent='';
for(var j=0;j<D.services.length;j++)if(D.services[j][0]===chosen){
node('h4',D.services[j][1],detail);
node('p',D.services[j][3],detail);
btn(D.open,function(){open(chosen);},detail,'primary');break;
}
}
function renderCommands(){
var host=el('pc');host.textContent='';
for(var i=0;i<D.commands.length;i++){
(function(c){var line=btn('/'+c[0]+' — '+D.commandNames[c[0]],function(){
if(c[1])open(c[1]);else el('note').textContent='/'+c[0];
},host,'row');line.setAttribute('aria-label','/'+c[0]+' '+D.commandNames[c[0]]);
})(D.commands[i]);}
}
function renderFaq(){
var host=el('pf');host.textContent='';
for(var i=0;i<D.faqs.length;i++){
(function(index){var question=D.faqs[index],isOpen=opened===index;
var row=btn((isOpen?'⌃ ':'⌄ ')+question[0],function(){
opened=isOpen?-1:index;renderFaq();},host,'row');
row.setAttribute('aria-expanded',isOpen?'true':'false');
if(isOpen)node('div',question[1],host).className='answer';
})(i);}
}
function chooseTab(id){
tab=id;var ids=['services','commands','faq'],panels=['ps','pc','pf'];
for(var i=0;i<3;i++){
var yes=ids[i]===tab,b=el('t'+ids[i]);b.className=yes?'sel':'';
b.setAttribute('aria-selected',yes?'true':'false');
el(panels[i]).hidden=!yes;}
if(id==='services')renderServices();
if(id==='commands')renderCommands();
if(id==='faq')renderFaq();
}
el('title').textContent=D.title;el('intro').textContent=D.intro;
el('choose').textContent=D.choose;el('question').textContent=D.question;
el('support').textContent=D.support;
el('tservices').textContent=D.tabs[0];
el('tcommands').textContent=D.tabs[1];
el('tfaq').textContent=D.tabs[2];
['services','commands','faq'].forEach(function(x){
el('t'+x).addEventListener('click',function(){chooseTab(x);});});
el('support').addEventListener('click',function(){open('support');});
chooseTab('services');if(W)W.ready();
})();</script></body></html>"""


def help_widget_html(language: str) -> str:
    """Render localized help from a single allowlisted service-command catalogue."""
    lang = normalize_language(language)
    words = WORDS[lang]
    data = {
        **words,
        "commands": COMMANDS,
        "commandNames": words["commands"],
    }
    # A separate command-name object avoids collision with command tuples.
    data["commandNames"] = words["commands"]
    data["commands"] = COMMANDS
    html = (
        HELP_WIDGET_TEMPLATE.replace("__LANG__", lang)
        .replace("__DIR__", "ltr" if lang == "en" else "rtl")
        .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    )
    raw = html.encode("utf-8")
    if len(raw) > 32768 or len(zlib.compress(raw, level=9)) > 4096:
        raise ValueError("Telegram help widget exceeds HTML limits")
    return html


class PrivateChatMessage:
    """Expose only the standard reply_text surface required by existing flows."""

    def __init__(self, bot: object, chat_id: int) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.chat = SimpleNamespace(type="private", id=chat_id)

    async def reply_text(self, text: str, **kwargs: object) -> object:
        return await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)


async def send_help_widget(
    message: object, bot: object, language: str,
    support_username: str, *, fallback_markup: object = None,
) -> bool:
    """Send one private HTML widget, with the old multilingual help as fallback."""
    if (getattr(bot, "platform", "telegram") == "bale"
            or getattr(getattr(message, "chat", None), "type", None) != "private"):
        await message.reply_text(
            render_help(language, support_username),
            parse_mode="HTML", reply_markup=fallback_markup,
        )
        return False
    try:
        await _widget_api(bot, "sendWidget", {
            "chat_id": message.chat_id, "html": help_widget_html(language),
            "allow_queries": True,
        })
        return True
    except Exception as exc:
        LOGGER.warning("help_widget_send_failed type=%s", type(exc).__name__)
        await message.reply_text(
            render_help(language, support_username),
            parse_mode="HTML", reply_markup=fallback_markup,
        )
        return False


async def handle_help_widget_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    on_open: Callable[[str, int], Awaitable[None]],
) -> None:
    """Validate the owner before allowing a service-opening side effect."""
    raw = update.api_kwargs.get("widget_query")
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
        return

    async def answer(value: str) -> None:
        await _widget_api(context.bot, "answerWidgetQuery", {
            "widget_query_id": raw["id"], "data": value,
        })

    sender, chat = raw.get("from"), raw.get("chat")
    action, typ = raw.get("data"), raw.get("type")
    if not (
        isinstance(sender, dict) and isinstance(chat, dict)
        and type(sender.get("id")) is int and sender["id"] > 0
        and chat.get("type") == "private" and chat.get("id") == sender["id"]
        and type(raw.get("message_id")) is int and raw["message_id"] > 0
        and isinstance(action, str) and OPEN_ACTION.fullmatch(action)
        and (typ is None or (isinstance(typ, dict) and typ.get("type") == "data"))
        and not raw.get("widget_id")
        and getattr(context.bot, "platform", "telegram") != "bale"
    ):
        await answer("invalid")
        return

    # Acknowledge promptly, then open the selected existing service.
    await answer("accepted")
    try:
        await on_open(action.removeprefix("hp:open:"), sender["id"])
    except Exception as exc:
        LOGGER.warning("help_widget_open_failed type=%s", type(exc).__name__)
        try:
            await context.bot.send_message(
                chat_id=sender["id"],
                text="باز کردن خدمت ممکن نشد. لطفاً دستور مربوطه را مستقیماً ارسال کنید.",
            )
        except Exception as failure:
            LOGGER.warning("help_widget_error_delivery_failed type=%s",
                           type(failure).__name__)
