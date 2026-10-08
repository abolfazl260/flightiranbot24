"""Native Telegram Bot API rich-table rendering and transport."""

from __future__ import annotations

from html import escape

import httpx

from flightiran.modules.tickets.domain import CheapTicketRoute


def _row(destination) -> str:
    current = destination.price_value_toman
    if current is None:
        from flightiran.modules.tickets.service import parse_toman_price

        try:
            current = parse_toman_price(destination.price_toman)
        except ValueError:
            current = None

    average = destination.average_price_toman
    price = f"{current:,}" if current is not None else destination.price_toman

    if average is None or average <= 0 or current is None:
        mean, delta, percent = "—", "—", "—"
    else:
        mean = f"{average:,.0f}"
        difference = current - average
        delta = f"{difference:+,.0f}"
        percent = f"{difference / average * 100:+.1f}٪"

    cells = (destination.name, price, mean, delta, percent)
    return "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in cells) + "</tr>"


def render_rich_price_tables(
    route: CheapTicketRoute, *, rows_per_message: int = 12
) -> list[dict]:
    """Build actual HTML table rich messages, each with a bounded row count."""

    if rows_per_message < 1:
        raise ValueError("rows_per_message must be positive")

    destinations = route.destinations
    if not destinations:
        return []

    result: list[dict] = []
    for start in range(0, len(destinations), rows_per_message):
        batch = destinations[start : start + rows_per_message]
        caption = escape(route.origin)
        if start:
            caption += " (ادامه)"
        table = (
            "<table>"
            "<tr><th>مقصد</th><th>فعلی (تومان)</th>"
            "<th>میانگین ۲۱ روزه</th><th>اختلاف (تومان)</th><th>اختلاف ٪</th></tr>"
            + "".join(_row(item) for item in batch)
            + "</table>"
        )
        html = f"<h3>پروازها از {caption}</h3>" + table
        result.append({"html": html, "is_rtl": True})
    return result


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
