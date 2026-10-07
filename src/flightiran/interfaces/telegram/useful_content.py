"""Telegram presentation for curated travel information."""

from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.useful_content import UsefulContentCatalog

from .localization import safe_text


def useful_menu(language: str, catalog: UsefulContentCatalog) -> InlineKeyboardMarkup:
    """Render the top-level menu and keep long lists behind two categories."""

    rows = []
    for link in catalog.all():
        if link.category == "general":
            rows.append([InlineKeyboardButton(link.title, url=link.url)])
    rows.extend(
        [
            [InlineKeyboardButton("قوانین پرواز و بار 🌍", callback_data="useful:flight-rules")],
            [
                InlineKeyboardButton(
                    "وب‌سایت‌های مرتبط با سفر 🌐", callback_data="useful:travel-sites"
                )
            ],
            [InlineKeyboardButton(safe_text(language, "back"), callback_data="back")],
        ]
    )
    return InlineKeyboardMarkup(rows)


def useful_category_menu(
    language: str, catalog: UsefulContentCatalog, category: str
) -> InlineKeyboardMarkup:
    links = catalog.by_category(category)
    rows = [[InlineKeyboardButton(link.title, url=link.url)] for link in links]
    rows.append([InlineKeyboardButton(safe_text(language, "back"), callback_data="menu:useful")])
    return InlineKeyboardMarkup(rows)


def render_useful_category(category: str) -> str:
    if category == "flight-rules":
        return "<b>قوانین پرواز و بار</b>\nکشور یا منطقه را انتخاب کنید:"
    if category == "travel-sites":
        return "<b>وب‌سایت‌های مرتبط با سفر و پرواز</b>\nکشور یا منطقه را انتخاب کنید:"
    return "<b>اطلاعات کاربردی سفر</b>"


def render_useful_link(link) -> str:
    """Render a link preview for clients that need a text fallback."""

    title = escape(link.title)
    return f'<b>{title}</b>\n<a href="{escape(link.url, quote=True)}">باز کردن منبع</a>'
