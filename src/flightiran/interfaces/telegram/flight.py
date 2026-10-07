"""Localized rich-text flight result renderer."""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.flight_tracking.domain import FlightSearchResult, FlightSearchStatus


def render_flight_result(
    result: FlightSearchResult, language: str = "fa"
) -> tuple[str, InlineKeyboardMarkup | None]:
    if result.status == FlightSearchStatus.DISABLED:
        return "جستجوی پرواز موقتاً غیرفعال است.", None
    if result.status == FlightSearchStatus.INVALID:
        return "شماره پرواز معتبر نیست. نمونه: KLM561", None
    if result.status == FlightSearchStatus.NOT_FOUND:
        return "پروازی با این شماره پیدا نشد.", None
    if result.status == FlightSearchStatus.ERROR:
        return "خطا در دریافت اطلاعات پرواز. لطفاً بعداً تلاش کنید.", None
    flight = result.flight
    assert flight is not None
    lines = [f"<b>{escape(flight.flight_number)}</b>"]
    for label, value in (
        ("Airline", flight.airline),
        ("Callsign", flight.callsign),
        ("Aircraft", flight.aircraft),
        ("Route", f"{flight.origin or 'N/A'} → {flight.destination or 'N/A'}"),
    ):
        if value:
            lines.append(f"{label}: {escape(str(value))}")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Map", url=f"https://www.flightradar24.com/data/flights/{flight.flight_number}"
                ),
                InlineKeyboardButton("Back", callback_data="back"),
            ]
        ]
    )
    return "\n".join(lines), keyboard
