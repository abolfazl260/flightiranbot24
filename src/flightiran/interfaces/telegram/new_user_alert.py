"""Safe HTML for private notifications about newly registered Telegram users."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape

from telegram import User

_VALID_USERNAME = re.compile(r"[A-Za-z0-9_]{5,32}\Z")


def _text(value: str | None) -> str:
    return escape(value) if value else "ثبت نشده"


def render_new_user_alert(user: User, registered_at: datetime | None = None) -> str:
    """Only include Telegram profile information actually provided by Telegram."""
    username = (user.username or "").lstrip("@")
    if username and _VALID_USERNAME.fullmatch(username):
        username_display = (
            f'<a href="https://t.me/{username}">@{escape(username)}</a>'
        )
    elif username:
        username_display = f"@{escape(username)}"
    else:
        username_display = "ندارد"

    when = registered_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        # SQLite CURRENT_TIMESTAMP is stored in UTC without a timezone suffix.
        when = when.replace(tzinfo=timezone.utc)
    stamp = when.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    telegram_id = int(user.id)

    lines = [
        "<b>🆕 کاربر جدید ربات</b>",
        "",
        f"👤 نام: <b>{_text(user.first_name)}</b>",
        f"👥 نام خانوادگی: <b>{_text(user.last_name)}</b>",
        f"🔖 یوزرنیم: {username_display}",
        f"🆔 شناسه تلگرام: <code>{telegram_id}</code>",
        f"🌐 زبان تلگرام: {_text(getattr(user, 'language_code', None))}",
        f"🕒 زمان فعال‌سازی: <code>{stamp}</code>",
        "",
        f'🔗 <a href="tg://user?id={telegram_id}">مشاهده پروفایل کاربر</a>',
    ]
    premium = getattr(user, "is_premium", None)
    if premium is not None:
        lines.insert(-2, f"⭐ تلگرام پریمیوم: {'بله' if premium else 'خیر'}")
    return "\n".join(lines)
