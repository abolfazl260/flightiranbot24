"""Rich-text currency quote and converter renderers."""

from html import escape

from flightiran.modules.currency.domain import CurrencyQuote, QuoteStatus


def render_quotes(quotes: list[CurrencyQuote]) -> str:
    lines = ["<b>Currency rates</b>"]
    for quote in quotes:
        if quote.status == QuoteStatus.UNAVAILABLE or quote.price is None:
            value = "unavailable"
        else:
            value = f"{quote.price:,.2f} ({quote.direction})"
        lines.append(f"{escape(quote.label)}: {escape(value)}")
    return "\n".join(lines)
