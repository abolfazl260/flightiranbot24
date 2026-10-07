"""Telegram presentation for curated travel information."""

from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.useful_content import UsefulContentCatalog

from .localization import safe_text

USEFUL_CATEGORIES = (
    ("documents", "🛂 پاسپورت و خروج از کشور"),
    ("flights", "✈️ پرواز و حقوق مسافر"),
    ("baggage", "🧳 بار، گمرک و کالاهای ممنوعه"),
    ("international", "🌍 سفر خارجی و منابع کشورها"),
    ("payments", "💳 هزینه‌ها و بیمه سفر"),
    ("tips", "💡 نکات و راهنمای سفر"),
)
USEFUL_SUBCATEGORIES = {
    "flight-rules": "قوانین پرواز و بار",
    "travel-sites": "سامانه‌ها و لینک‌های سفر",
}
USEFUL_CATEGORY_IDS = frozenset(
    category for category, _ in USEFUL_CATEGORIES
) | frozenset(USEFUL_SUBCATEGORIES)


def useful_menu(language: str, catalog: UsefulContentCatalog) -> InlineKeyboardMarkup:
    """Keep the landing page short; resources appear inside their categories."""
    rows = [
        [InlineKeyboardButton(label, callback_data=f"useful:{category}")]
        for category, label in USEFUL_CATEGORIES
    ]
    rows.append([InlineKeyboardButton(safe_text(language, "back"), callback_data="back")])
    return InlineKeyboardMarkup(rows)


def useful_category_menu(
    language: str, catalog: UsefulContentCatalog, category: str
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(link.title, url=link.url)]
        for link in catalog.by_category(category)
    ]
    if category in {"flights", "baggage"}:
        rows.append([InlineKeyboardButton(
            "🌍 قوانین بار و پرواز به تفکیک کشور",
            callback_data="useful:flight-rules",
        )])
    elif category == "international":
        rows.append([InlineKeyboardButton(
            "🔗 منابع سفر به تفکیک کشور",
            callback_data="useful:travel-sites",
        )])
    parent = {
        "flight-rules": "baggage",
        "travel-sites": "international",
    }.get(category)
    rows.append([InlineKeyboardButton(
        safe_text(language, "back"),
        callback_data=f"useful:{parent}" if parent else "menu:useful",
    )])
    return InlineKeyboardMarkup(rows)


def render_useful_category(category: str) -> str:
    labels = dict(USEFUL_CATEGORIES)
    labels.update(USEFUL_SUBCATEGORIES)
    label = escape(labels.get(category, "اطلاعات سفر"))
    return f"<b>{label}</b>\nموضوع موردنظر را انتخاب کنید:"


def render_useful_link(link) -> str:
    """Render a link preview for clients that need a text fallback."""
    title = escape(link.title)
    return f'<b>{title}</b>\n<a href="{escape(link.url, quote=True)}">باز کردن منبع</a>'
