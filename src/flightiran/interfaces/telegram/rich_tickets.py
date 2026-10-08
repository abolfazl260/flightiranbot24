"""Native Telegram Bot API rich-table rendering and transport."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable
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


@dataclass(frozen=True)
class PriceDrop:
    """A current route price more than a specified amount below its rolling mean."""

    origin: str
    destination: str
    current_toman: int
    average_toman: float
    decrease_toman: float
    decrease_percent: float


def find_price_drops(
    routes: Iterable[CheapTicketRoute], *, threshold_percent: float = 20.0
) -> list[PriceDrop]:
    """Select strictly greater-than-threshold reductions from the existing feed."""

    if threshold_percent < 0:
        raise ValueError("threshold_percent must be non-negative")

    drops: list[PriceDrop] = []
    for route in routes:
        for destination in route.destinations:
            average = destination.average_price_toman
            if average is None or average <= 0:
                continue

            current = destination.price_value_toman
            if current is None:
                try:
                    current = parse_toman_price(destination.price_toman)
                except ValueError:
                    continue

            decrease = average - current
            percent = decrease / average * 100
            if percent > threshold_percent:
                drops.append(
                    PriceDrop(
                        origin=route.origin,
                        destination=destination.name,
                        current_toman=current,
                        average_toman=average,
                        decrease_toman=decrease,
                        decrease_percent=percent,
                    )
                )

    return sorted(
        drops,
        key=lambda drop: (
            -drop.decrease_percent,
            -drop.decrease_toman,
            drop.origin,
            drop.destination,
        ),
    )


_DROP_TABLE_HEADER = (
    "<tr><th>مبدأ</th><th>مقصد</th><th>فعلی (تومان)</th>"
    "<th>میانگین ۲۱ روزه</th><th>کاهش (تومان)</th><th>کاهش ٪</th></tr>"
)


def _drop_table_row(drop: PriceDrop) -> str:
    cells = (
        drop.origin,
        drop.destination,
        f"{drop.current_toman:,}",
        f"{drop.average_toman:,.0f}",
        f"{drop.decrease_toman:,.0f}",
        f"🟢 {drop.decrease_percent:.2f}٪",
    )
    return "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>"


def _drop_report_html(rows: list[str], total: int, *, continued: bool = False) -> str:
    continuation = " (ادامه)" if continued else ""
    return (
        f"<h3>🟢 گزارش کاهش قیمت بیش از ۲۰٪{continuation}</h3>"
        f"<p>{total} مسیر، مرتب‌شده از بیشترین کاهش نسبت به میانگین ۲۱روزه</p>"
        "<table bordered striped compact>"
        + _DROP_TABLE_HEADER
        + "".join(rows)
        + "</table>"
    )


def _paginate_rich_rows(
    rows: list[str],
    render: Callable[[list[str], bool], str],
    *,
    max_text_chars: int,
    max_rows: int,
) -> list[dict]:
    """Keep whole table rows together and respect Telegram's rich-message limits."""

    if max_text_chars < 1 or not 1 <= max_rows <= MAX_RICH_TABLE_ROWS:
        raise ValueError("Invalid Telegram rich message limits")

    pages: list[dict] = []
    current_rows: list[str] = []
    for row in rows:
        candidate = current_rows + [row]
        candidate_html = render(candidate, bool(pages))
        if len(candidate) <= max_rows and _plain_text_length(candidate_html) <= max_text_chars:
            current_rows.append(row)
            continue

        if not current_rows:
            raise ValueError("A price table row exceeds Telegram rich message limits")

        pages.append({"html": render(current_rows, bool(pages)), "is_rtl": True})
        current_rows = [row]
        if _plain_text_length(render(current_rows, True)) > max_text_chars:
            raise ValueError("A price table row exceeds Telegram rich message limits")

    if current_rows:
        pages.append({"html": render(current_rows, bool(pages)), "is_rtl": True})
    return pages


def render_rich_price_drop_report(
    routes: Iterable[CheapTicketRoute],
    *,
    max_text_chars: int = MAX_RICH_TEXT_CHARS,
    max_rows: int = MAX_RICH_TABLE_ROWS,
) -> list[dict]:
    """Create one cross-origin 20%+ discount report from the already-fetched routes."""

    drops = find_price_drops(routes)
    if not drops:
        return [{
            "html": (
                "<h3>🟢 گزارش کاهش قیمت بیش از ۲۰٪</h3>"
                "<p>در بررسی فعلی، مسیری با کاهش بیش از ۲۰٪ نسبت به "
                "میانگین ۲۱روزه پیدا نشد.</p>"
            ),
            "is_rtl": True,
        }]

    rows = [_drop_table_row(drop) for drop in drops]
    return _paginate_rich_rows(
        rows,
        lambda batch, continued: _drop_report_html(
            batch, len(drops), continued=continued
        ),
        max_text_chars=max_text_chars,
        max_rows=max_rows,
    )


def render_price_drop_fallback_chunks(
    routes: Iterable[CheapTicketRoute], *, max_length: int = 3800
) -> list[str]:
    """Safe plain Telegram HTML fallback when sendRichMessage is unavailable."""

    if max_length < 1:
        raise ValueError("max_length must be positive")

    drops = find_price_drops(routes)
    title = "🟢 <b>گزارش کاهش قیمت بیش از ۲۰٪</b>"
    if not drops:
        return [title + "\nدر بررسی فعلی موردی پیدا نشد."]

    chunks: list[str] = []
    current = title
    for drop in drops:
        line = (
            f"✈️ {escape(drop.origin)} ← {escape(drop.destination)} | "
            f"{drop.current_toman:,} تومان | "
            f"کاهش {drop.decrease_toman:,.0f} تومان | "
            f"🟢 {drop.decrease_percent:.2f}٪"
        )
        candidate = current + "\n" + line
        if len(candidate) > max_length:
            if current == title:
                raise ValueError("A price drop exceeds fallback message limits")
            chunks.append(current)
            current = title + " (ادامه)\n" + line
            if len(current) > max_length:
                raise ValueError("A price drop exceeds fallback message limits")
        else:
            current = candidate
    chunks.append(current)
    return chunks


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
