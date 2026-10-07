"""Compact ticket result cards."""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.tickets.domain import TicketOffer


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
