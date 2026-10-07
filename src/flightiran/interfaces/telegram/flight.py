"""Localized, provider-independent flight result renderer."""

from datetime import datetime
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.flight_tracking.domain import FlightSearchResult, FlightSearchStatus


def _value(value: object | None) -> str:
    return "—" if value in (None, "") else escape(str(value))


def _time(value: datetime | None) -> str:
    return _value(value.strftime("%Y-%m-%d %H:%M") if value else None)


def _location(
    country: str | None, city: str | None, airport: str | None, fallback: str | None
) -> str:
    parts = [part for part in (country, city, airport or fallback) if part]
    return escape("، ".join(parts)) if parts else "—"


def render_flight_result(
    result: FlightSearchResult, language: str = "fa"
) -> tuple[str, InlineKeyboardMarkup | None]:
    if result.status == FlightSearchStatus.DISABLED:
        return "جستجوی پرواز موقتاً غیرفعال است.", None
    if result.status == FlightSearchStatus.INVALID:
        return "شماره پرواز ارسال نشده یا معتبر نیست. نمونه: <code>/flight KLM561</code>", None
    if result.status == FlightSearchStatus.NOT_FOUND:
        return "پروازی با این شماره پیدا نشد. شماره پرواز را بررسی کنید و دوباره تلاش کنید.", None
    if result.status == FlightSearchStatus.ERROR:
        return "خطا در دریافت اطلاعات پرواز از FlightRadar24. لطفاً بعداً دوباره تلاش کنید.", None
    flight = result.flight
    assert flight is not None

    origin = _location(
        flight.origin_country, flight.origin_city, flight.origin_airport, flight.origin
    )
    destination = _location(
        flight.destination_country,
        flight.destination_city,
        flight.destination_airport,
        flight.destination,
    )
    lines = [
        f"✈️ <b>اطلاعات پرواز {_value(flight.flight_number)}</b>",
        f"🏷 شرکت هواپیمایی: {_value(flight.airline)}",
        f"🎫 شماره / Callsign: <code>{_value(flight.callsign)}</code>",
        f"🛩 مدل هواپیما: {_value(flight.aircraft)}",
        f"⌛ عمر هواپیما: {_value(flight.aircraft_age)}",
        "",
        f"🛫 <b>مبدأ</b>: {origin}",
        f"⛩ ترمینال مبدأ: {_value(flight.origin_terminal)}",
        f"🕒 زمان برنامه‌ریزی‌شده پرواز: {_time(flight.scheduled_departure)}",
        f"🟢 زمان واقعی پرواز: {_time(flight.actual_departure)}",
        "",
        f"🛬 <b>مقصد</b>: {destination}",
        f"⛩ ترمینال مقصد: {_value(flight.destination_terminal)}",
        f"🕒 زمان برنامه‌ریزی‌شده فرود: {_time(flight.scheduled_arrival)}",
        f"🔵 زمان تخمینی فرود: {_time(flight.estimated_arrival)}",
        f"✅ زمان واقعی فرود: {_time(flight.actual_arrival)}",
    ]
    if flight.position:
        lines.extend(
            [
                "",
                f"🌐 موقعیت فعلی: عرض {_value(flight.position.latitude)}، "
                f"طول {_value(flight.position.longitude)}",
            ]
        )
    rows: list[list[InlineKeyboardButton]] = []
    if flight.map_url:
        rows.append([InlineKeyboardButton("🗺 مشاهده پرواز روی نقشه", url=flight.map_url)])
    if flight.history_url:
        rows.append([InlineKeyboardButton("📅 تاریخچه پرواز / هواپیما", url=flight.history_url)])
    if flight.aircraft_image:
        rows.append([InlineKeyboardButton("🖼 تصویر هواپیما", url=flight.aircraft_image)])
    if not rows:
        rows.append(
            [
                InlineKeyboardButton(
                    "🗺 مشاهده در FlightRadar24",
                    url=f"https://www.flightradar24.com/data/flights/{flight.flight_number}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back")])
    return "\n".join(lines), InlineKeyboardMarkup(rows)
