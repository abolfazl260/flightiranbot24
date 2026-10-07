"""Reusable Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .localization import safe_text


def main_menu(language: str) -> InlineKeyboardMarkup:
    rows = [
        [("flights", "menu:flights"), ("airports", "menu:airports")],
        [("tickets", "menu:tickets"), ("currency", "menu:currency")],
        [("visa", "menu:visa"), ("rules", "menu:rules")],
        [("cargo", "menu:cargo"), ("useful", "menu:useful")],
        [("support", "menu:support"), ("settings", "menu:settings")],
    ]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(safe_text(language, label), callback_data=data)
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
