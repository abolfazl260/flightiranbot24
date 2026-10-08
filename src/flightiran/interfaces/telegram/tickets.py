"""Compact ticket result cards."""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute, TicketOffer


def render_offer(offer: TicketOffer) -> tuple[str, InlineKeyboardMarkup]:
    lines = [
        f"<b>{escape(offer.airline)}</b> · {offer.total_price:,.2f} {escape(offer.currency)}",
        f"{offer.departure_at:%Y-%m-%d %H:%M} → {offer.arrival_at:%H:%M}",
        f"Stops: {offer.stops}",
    ]
    if offer.baggage:
        lines.append(f"Baggage: {escape(offer.baggage)}")
    if offer.refund_policy:
        lines.append(f"Refund: {escape(offer.refund_policy)}")
    if offer.fees:
        lines.append(f"Fees included: {offer.fees:,.2f} {escape(offer.currency)}")
    return "\n".join(lines), InlineKeyboardMarkup(
        [[InlineKeyboardButton("Book / source", url=offer.source_url)]]
    )


def _render_destination(item: CheapTicketDestination) -> str:
    current = item.price_value_toman
    if current is None:
        return f"🛬 <b>{escape(item.name)}</b>\n💰 قیمت: <b>{escape(item.price_toman)} تومان</b>"

    lines = [
        f"🛬 <b>{escape(item.name)}</b>",
        f"💰 قیمت فعلی: <b>{current:,} تومان</b>",
    ]
    average = item.average_price_toman
    if average is None or average <= 0:
        lines.append("📊 میانگین ۲۱ روزه: <i>هنوز داده کافی ثبت نشده</i>")
        return "\n".join(lines)

    rounded_average = round(average)
    difference = current - average
    percentage = (difference / average) * 100
    lines.append(
        f"📊 میانگین ۲۱ روزه: <b>{rounded_average:,} تومان</b> "
        f"<i>({item.average_sample_count} نمونه)</i>"
    )
    if abs(difference) < 0.5:
        lines.append("⚪️ اختلاف با میانگین: <b>بدون تغییر (۰٪)</b>")
    elif difference < 0:
        lines.append(
            f"🟢 اختلاف با میانگین: <b>{round(abs(difference)):,} تومان ارزان‌تر</b> "
            f"(<b>{abs(percentage):.1f}٪ کمتر</b>)"
        )
    else:
        lines.append(
            f"🔴 اختلاف با میانگین: <b>{round(difference):,} تومان گران‌تر</b> "
            f"(<b>{percentage:.1f}٪ بیشتر</b>)"
        )
    return "\n".join(lines)


def render_cheap_route(route: CheapTicketRoute) -> str:
    """Render one origin and all destinations as Telegram HTML rich text."""

    blocks = [f"✈️ <b>پروازهای ارزان از {escape(route.origin)}</b>"]
    blocks.extend(_render_destination(item) for item in route.destinations)
    return "\n\n".join(blocks)


def render_cheap_route_chunks(
    route: CheapTicketRoute,
    *,
    max_length: int = 3800,
) -> list[str]:
    """Split one origin's rich-text output into Telegram-safe messages.

    Destination blocks are kept intact so HTML tags are never split across
    message boundaries.
    """

    header = f"✈️ <b>پروازهای ارزان از {escape(route.origin)}</b>"
    continuation_header = f"✈️ <b>{escape(route.origin)} — ادامه</b>"
    chunks: list[str] = []
    current = header

    for item in route.destinations:
        block = _render_destination(item)
        candidate = f"{current}\n\n{block}"
        if len(candidate) <= max_length:
            current = candidate
            continue

        chunks.append(current)
        current = f"{continuation_header}\n\n{block}"

    if current:
        chunks.append(current)

    return chunks


def render_cheap_ticket_intro() -> str:
    return "🔍 <b>در حال دریافت و مقایسه قیمت بلیط‌ها با میانگین ۲۱ روزه...</b>"


def render_cheap_ticket_booking_hint(support_username: str) -> str:
    return (
        "📥 برای رزرو بلیط، مسیر موردنظر را انتخاب کنید و از طریق پشتیبانی پیام دهید: "
        f"<b>{escape(support_username)}</b>"
    )
