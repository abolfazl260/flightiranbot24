"""Reusable Telegram keyboard definitions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from .localization import safe_text
from .support import support_url

CARGO_MARKETPLACE_URL = "https://t.me/advertio_cargo"


def main_menu(
    language: str,
    web_app_url: str | None = None,
    *,
    is_admin: bool = False,
) -> InlineKeyboardMarkup:
    rows = [
        [("airports", "menu:airports"), ("tickets", "menu:tickets")],
        [("currency", "menu:currency"), ("visa", "menu:visa")],
        [("price_alerts", "menu:price_alerts")],
        [("rules", "menu:rules"), ("cargo", "menu:cargo")],
        [("useful", "menu:useful"), ("support", "menu:support")],
        [("settings", "menu:settings")],
    ]
    if is_admin:
        rows.append([("admin_reports", "menu:admin_reports")])
    if web_app_url:
        rows.append([InlineKeyboardButton("Web App", web_app=WebAppInfo(web_app_url))])
    def button_for(item: tuple[str, str] | InlineKeyboardButton) -> InlineKeyboardButton:
        if isinstance(item, InlineKeyboardButton):
            return item
        label, data = item
        if label == "cargo":
            return InlineKeyboardButton(
                safe_text(language, label), url=CARGO_MARKETPLACE_URL
            )
        return InlineKeyboardButton(safe_text(language, label), callback_data=data)

    return InlineKeyboardMarkup(
        [[button_for(item) for item in row] for row in rows]
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


TICKET_ORIGINS_PAGE_SIZE = 16


def ticket_origins_menu(language: str, origins: list[str], page: int = 0) -> InlineKeyboardMarkup:
    """Compact paginated origin chooser (indices avoid oversized callback data)."""

    max_page = max(0, (len(origins) - 1) // TICKET_ORIGINS_PAGE_SIZE)
    page = max(0, min(page, max_page))
    start = page * TICKET_ORIGINS_PAGE_SIZE
    rows = []
    for idx in range(start, min(start + TICKET_ORIGINS_PAGE_SIZE, len(origins)), 2):
        rows.append([
            InlineKeyboardButton(origins[pos], callback_data=f"tickets:origin:{pos}")
            for pos in range(idx, min(idx + 2, len(origins)))
        ])
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton("◀", callback_data=f"tickets:page:{page - 1}")
        )
    if page < max_page:
        navigation.append(
            InlineKeyboardButton("▶", callback_data=f"tickets:page:{page + 1}")
        )
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(
        safe_text(language, "price_alerts"), callback_data="menu:price_alerts"
    )])
    rows.append([InlineKeyboardButton(safe_text(language, "back"), callback_data="back")])
    return InlineKeyboardMarkup(rows)


def ticket_result_menu(language: str, support_username: str) -> InlineKeyboardMarkup:
    """Show another city without sending every origin's results."""

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                safe_text(language, "support_open_chat"),
                url=support_url(support_username),
            )],
            [InlineKeyboardButton(
                {
                    "fa": "✈️ انتخاب مبدأ دیگر",
                    "en": "✈️ Choose another origin",
                    "ar": "✈️ اختيار مدينة مغادرة أخرى",
                }.get(language, "✈️ Choose another origin"),
                callback_data="tickets:menu",
            )],
            [InlineKeyboardButton(
                safe_text(language, "price_alerts"), callback_data="menu:price_alerts"
            )],
            [InlineKeyboardButton(safe_text(language, "back"), callback_data="back")],
        ]
    )
