"""Consistent support links and localized contact messages."""

import re
from html import escape

from .localization import normalize_language

_USERNAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{4,31}\Z")


def support_url(username: str) -> str:
    """Build a safe Telegram link from a configured public support username."""

    handle = username.strip().removeprefix("@")
    if not _USERNAME_PATTERN.fullmatch(handle):
        raise ValueError("Invalid Telegram support username")
    return f"https://t.me/{handle}"


def support_link(username: str) -> str:
    """Return a clickable HTML mention for Telegram messages."""

    handle = username.strip().removeprefix("@")
    return f'<a href="{support_url(username)}">@{escape(handle)}</a>'


def render_support_message(language: str, username: str) -> str:
    """Invite users to ask questions about any of the bot's services."""

    contact = support_link(username)
    language = normalize_language(language)
    if language == "fa":
        return (
            "💬 <b>پشتیبانی Flight Iran Bot 24</b>\n\n"
            "برای استفاده از خدمات ربات، بررسی مسیر و قیمت بلیط، "
            "راهنمایی درباره روند رزرو یا پیگیری درخواستتان سؤال دارید؟\n\n"
            "سؤال خود را همراه با اطلاعات مرتبط، مانند مبدأ، مقصد و تاریخ سفر "
            "ارسال کنید تا درخواستتان بررسی شود.\n\n"
            f"📩 <b>ارتباط با پشتیبانی همه خدمات:</b> {contact}\n"
            "👇 برای شروع گفتگو، دکمه زیر را انتخاب کنید."
        )
    if language == "ar":
        return (
            "💬 <b>دعم Flight Iran Bot 24</b>\n\n"
            "هل لديك سؤال عن خدمات البوت أو مسارات الرحلات وأسعار التذاكر "
            "أو خطوات الحجز أو متابعة طلبك؟\n\n"
            "أرسل سؤالك مع التفاصيل المناسبة، مثل مدينة المغادرة والوجهة "
            "وتاريخ السفر، لمراجعة طلبك.\n\n"
            f"📩 <b>دعم جميع الخدمات:</b> {contact}\n"
            "👇 اضغط الزر أدناه لبدء المحادثة."
        )
    return (
        "💬 <b>Flight Iran Bot 24 Support</b>\n\n"
        "Have a question about the bot, flight routes, ticket prices, "
        "booking steps, or an existing request?\n\n"
        "Send your question with relevant details, such as departure city, "
        "destination and travel date, so your request can be reviewed.\n\n"
        f"📩 <b>Support for all services:</b> {contact}\n"
        "👇 Tap the button below to start a conversation."
    )
