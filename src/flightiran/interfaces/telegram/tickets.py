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
    """Render one destination as a compact Telegram HTML table card."""

    destination = escape(item.name)
    current = item.price_value_toman
    if current is None:
        price = escape(item.price_toman)
        return (
            f"📍 <b>{destination}</b>\n"
            "<pre>"
            f"قیمت فعلی   {price} تومان\n"
            "میانگین     —\n"
            "اختلاف      —\n"
            "درصد        —"
            "</pre>"
        )

    average = item.average_price_toman
    if average is None or average <= 0:
        return (
            f"📍 <b>{destination}</b>\n"
            "<pre>"
            f"قیمت فعلی   {current:,} تومان\n"
            "میانگین     در حال جمع‌آوری داده\n"
            "اختلاف      —\n"
            "درصد        —"
            "</pre>"
        )

    rounded_average = round(average)
    difference = current - average
    percentage = (difference / average) * 100
    difference_toman = round(difference)

    if abs(difference) < 0.5:
        status = "⚪️ <b>هم‌سطح میانگین</b>"
        difference_text = "0 تومان"
        percentage_text = "0.0٪"
    elif difference < 0:
        status = f"🟢 <b>{abs(percentage):.1f}٪ ارزان‌تر از میانگین</b>"
        difference_text = f"-{abs(difference_toman):,} تومان"
        percentage_text = f"-{abs(percentage):.1f}٪"
    else:
        status = f"🔴 <b>{percentage:.1f}٪ گران‌تر از میانگین</b>"
        difference_text = f"+{difference_toman:,} تومان"
        percentage_text = f"+{percentage:.1f}٪"

    table = (
        "<pre>"
        f"قیمت فعلی   {current:,} تومان\n"
        f"میانگین     {rounded_average:,} تومان\n"
        f"اختلاف      {difference_text}\n"
        f"درصد        {percentage_text}\n"
        f"نمونه       {item.average_sample_count}"
        "</pre>"
    )
    return f"📍 <b>{destination}</b>\n{table}\n{status}"


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
