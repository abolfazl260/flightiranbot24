"""Reusable Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from .localization import safe_text
from .support import support_url

CARGO_MARKETPLACE_URL = "https://t.me/advertio_cargo"


def main_menu(language: str, web_app_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [("flights", "menu:flights"), ("airports", "menu:airports")],
        [("tickets", "menu:tickets"), ("currency", "menu:currency")],
        [("visa", "menu:visa"), ("rules", "menu:rules")],
        [("cargo", "menu:cargo"), ("useful", "menu:useful")],
        [("support", "menu:support"), ("settings", "menu:settings")],
    ]
    if web_app_url:
        rows.append([InlineKeyboardButton("Web App", web_app=WebAppInfo(web_app_url))])
    return InlineKeyboardMarkup(
        [
            [
                (
                    InlineKeyboardButton(
                        safe_text(language, label),
                        url=CARGO_MARKETPLACE_URL,
                    )
                    if label == "cargo"
                    else InlineKeyboardButton(
                        safe_text(language, label),
                        callback_data=data,
                    )
                )
                for label, data in row
            ]
            for row in rows
        ]
    )


def language_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("فارسی", callback_data="language:fa"),
                InlineKeyboardButton("English", callback_data="language:en"),
                InlineKeyboardButton("العربية", callback_data="language:ar"),
            ]
        ]
    )


def back_menu(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(safe_text(language, "back"), callback_data="back")]]
    )



def support_menu(language: str, support_username: str) -> InlineKeyboardMarkup:
    """Provide a direct, user-friendly link to the unified support bot."""

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    safe_text(language, "support_open_chat"),
                    url=support_url(support_username),
                )
            ],
            [
                InlineKeyboardButton(
                    safe_text(language, "back"),
                    callback_data="back",
                )
            ],
        ]
    )
