"""Daily private admin report of unique users active in the last 24 hours."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy import select

from flightiran.db.engine import Database
from flightiran.db.models import User

_USERNAME = re.compile(r"[A-Za-z0-9_]{5,32}\Z")


@dataclass(frozen=True)
class ActiveUser:
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    last_active_at: datetime


class ActiveUsersReportRepository:
    """Read tracked bot and authenticated Web App users, without making remote calls."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def collect(self, now: datetime | None = None) -> list[ActiveUser]:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("Report time must have a timezone")
        end = now.astimezone(timezone.utc).replace(tzinfo=None)
        start = end - timedelta(hours=24)
        async with self.database.session() as session:
            users = (await session.scalars(
                select(User)
                .where(User.last_active_at >= start, User.last_active_at <= end)
                .order_by(User.last_active_at.desc(), User.telegram_id)
            )).all()
        return [
            ActiveUser(
                telegram_id=user.telegram_id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                last_active_at=user.last_active_at,
            )
            for user in users
        ]


def _user_line(index: int, user: ActiveUser, zone: ZoneInfo) -> str:
    name = " ".join(
        field[:100] for field in (user.first_name, user.last_name) if field
    ) or "ثبت نشده"
    handle = (user.username or "").lstrip("@")
    if _USERNAME.fullmatch(handle):
        username = f'<a href="https://t.me/{handle}">@{escape(handle)}</a>'
    elif handle:
        username = escape("@" + handle[:100])
    else:
        username = "ندارد"
    observed = user.last_active_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    stamp = observed.astimezone(zone).strftime("%Y-%m-%d %H:%M")
    return (
        f'{index}. <a href="tg://user?id={int(user.telegram_id)}">'
        f'{escape(name)}</a> · {username}\n'
        f'    ID: <code>{int(user.telegram_id)}</code> · آخرین فعالیت: {stamp}'
    )


def render_active_users_report(
    users: list[ActiveUser], *, now: datetime | None = None,
    report_timezone: str = "Asia/Tehran", max_length: int = 3900,
) -> list[str]:
    """Split a complete private HTML report into Telegram-safe messages."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Report time must have a timezone")
    zone = ZoneInfo(report_timezone)
    to_local = now.astimezone(zone)
    from_local = (now - timedelta(hours=24)).astimezone(zone)
    header = (
        "<b>📊 گزارش روزانه کاربران فعال</b>\n"
        f"بازه: {from_local:%Y-%m-%d %H:%M} تا {to_local:%Y-%m-%d %H:%M}\n"
        f"منطقه زمانی: {escape(report_timezone)}\n"
        f"تعداد کاربران یکتا: <b>{len(users)}</b>\n"
    )
    if not users:
        return [header + "\nدر ۲۴ ساعت گذشته فعالیتی ثبت نشده است."]

    parts: list[str] = []
    lines: list[str] = []
    for number, user in enumerate(users, 1):
        line = _user_line(number, user, zone)
        candidate = header + "\n" + "\n\n".join([*lines, line])
        if len(candidate) > max_length and lines:
            parts.append(header + "\n" + "\n\n".join(lines))
            lines = [line]
        else:
            lines.append(line)
    if lines:
        parts.append(header + "\n" + "\n\n".join(lines))
    return [
        part + f"\n\n<b>بخش {i} از {len(parts)}</b>" if len(parts) > 1 else part
        for i, part in enumerate(parts, 1)
    ]
