"""Native Telegram Bot API rich-table rendering and transport."""

from __future__ import annotations

import re
from html import escape, unescape

import httpx

from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute
from flightiran.modules.tickets.service import parse_toman_price

# Bot API 10.1+: 32,768 text characters, 500 blocks (table rows count
# as blocks) and up to 20 table columns. Leave a margin for other blocks.
MAX_RICH_TEXT_CHARS = 32_000
MAX_RICH_TABLE_ROWS = 490

_TABLE_HEADER = (
    "<tr><th>مقصد</th><th>فعلی (تومان)</th>"
    "<th>میانگین ۲۱ روزه</th><th>اختلاف (تومان)</th><th>اختلاف ٪</th></tr>"
)


def _row(destination: CheapTicketDestination) -> str:
    """Render one priced destination with a colored percentage indicator."""

    current = destination.price_value_toman
    if current is None:
        try:
            current = parse_toman_price(destination.price_toman)
        except ValueError:
            current = None

    average = destination.average_price_toman
    price = f"{current:,}" if current is not None else destination.price_toman

    if average is None or average <= 0 or current is None:
        mean, delta, percent = "—", "—", "⚪ —"
    else:
        mean = f"{average:,.0f}"
        difference = current - average
        delta_toman = round(difference)
        delta = f"{delta_toman:+,}"
        percentage = difference / average * 100

        if delta_toman == 0:
            percent = "⚪ 0.0٪"
        elif difference < 0:
            percent = f"🟢 {percentage:.1f}٪"
        else:
            percent = f"🔴 +{percentage:.1f}٪"

    cells = (destination.name, price, mean, delta, percent)
    return "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in cells) + "</tr>"


def _plain_text_length(html: str) -> int:
    """Count rendered rich-message characters rather than HTML markup."""

    return len(unescape(re.sub(r"<[^>]*>", "", html)))


def _table_html(origin: str, rows: list[str], *, continued: bool = False) -> str:
    title = f"پروازها از {escape(origin)}"
    if continued:
        title += " (ادامه)"
    return (
        f"<h3>{title}</h3>"
        "<table bordered striped compact>"
        + _TABLE_HEADER
        + "".join(rows)
        + "</table>"
    )


def render_rich_price_tables(
    route: CheapTicketRoute,
    *,
    max_text_chars: int = MAX_RICH_TEXT_CHARS,
    max_rows: int = MAX_RICH_TABLE_ROWS,
) -> list[dict]:
    """Send one rich table per origin unless an actual Bot API limit requires splitting."""

    if max_text_chars < 1 or max_rows < 1 or max_rows > MAX_RICH_TABLE_ROWS:
        raise ValueError("Invalid Telegram rich message limits")
    if not route.destinations:
        return []

    messages: list[dict] = []
    rows: list[str] = []
    for item in route.destinations:
        row = _row(item)
        candidate = rows + [row]
        html = _table_html(route.origin, candidate, continued=bool(messages))

        if len(candidate) > max_rows or _plain_text_length(html) > max_text_chars:
            if not rows:
                raise ValueError(
                    f"One mz724 destination exceeds Telegram rich message limits: {item.name}"
                )
            messages.append(
                {"html": _table_html(route.origin, rows, continued=bool(messages)),
                 "is_rtl": True}
            )
            rows = [row]
            if _plain_text_length(
                _table_html(route.origin, rows, continued=True)
            ) > max_text_chars:
                raise ValueError(
                    f"One mz724 destination exceeds Telegram rich message limits: {item.name}"
                )
        else:
            rows.append(row)

    if rows:
        messages.append(
            {"html": _table_html(route.origin, rows, continued=bool(messages)),
             "is_rtl": True}
        )
    return messages


async def send_rich_price_table(bot, chat_id: int, rich_message: dict) -> None:
    """Call sendRichMessage directly until python-telegram-bot exposes the method."""

    url = f"https://api.telegram.org/bot{bot.token}/sendRichMessage"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            url,
            json={"chat_id": chat_id, "rich_message": rich_message},
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            description = payload.get("description", "Unknown Telegram API failure")
            raise RuntimeError(f"sendRichMessage failed: {description}")
