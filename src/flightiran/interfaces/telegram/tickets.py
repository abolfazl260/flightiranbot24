"""Compact ticket result cards."""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.tickets.domain import CheapTicketRoute, TicketOffer


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


def render_cheap_route(route: CheapTicketRoute) -> str:
    """Render one provider row; one row is intentionally one Telegram message."""
    lines = [f"🛫 <b>مبدأ: {escape(route.origin)}</b>", ""]
    lines.extend(
        f"🛬 مقصد: {escape(item.name)} | قیمت: <b>{escape(item.price_toman)} تومان</b>"
        for item in route.destinations
    )
    return "\n".join(lines)


def render_cheap_ticket_intro() -> str:
    return "🔍 در حال دریافت ارزان‌ترین بلیط‌ها از mz724.ir ..."


def render_cheap_ticket_booking_hint(support_username: str) -> str:
    return (
        "📥 برای رزرو بلیط، مسیر موردنظر را انتخاب کنید و از طریق پشتیبانی پیام دهید: "
        f"{escape(support_username)}"
    )
