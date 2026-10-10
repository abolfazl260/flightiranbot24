"""Source-neutral, localized ticket alert messages for Telegram users."""

from __future__ import annotations

from html import escape

from flightiran.db.models import PriceAlert, PriceSnapshot


def render_ticket_alert(
    origin: str,
    destination: str,
    alert: PriceAlert,
    snapshot: PriceSnapshot,
    language: str,
) -> str:
    """Display a rate comparison without exposing any upstream provider identity."""
    price = int(snapshot.price)
    route = f"{escape(origin)} → {escape(destination)}"
    kind = getattr(alert, "threshold_type", "price")
    if kind == "percent":
        reference = snapshot.reference_average_toman
        if reference is None or reference <= 0:
            raise ValueError("Percentage alert requires a recorded reference average")
        discount = (reference - price) / reference * 100
        threshold = int(alert.target_percent)
        if language == "fa":
            return (
                "🔔 <b>هشدار کاهش قیمت بلیط</b>\n"
                f"مسیر: {route}\n"
                f"قیمت فعلی: <b>{price:,} تومان</b>\n"
                f"میانگین قیمت: {reference:,.0f} تومان\n"
                f"کاهش فعلی: <b>{discount:.1f}٪</b>\n"
                f"حداقل کاهش انتخابی: {threshold}٪\n"
                "قیمت‌ها ممکن است تا زمان رزرو تغییر کنند."
            )
        if language == "ar":
            return (
                "🔔 <b>تنبيه انخفاض سعر التذكرة</b>\n"
                f"المسار: {route}\n"
                f"السعر الحالي: <b>{price:,} تومان</b>\n"
                f"متوسط الأسعار: {reference:,.0f} تومان\n"
                f"الانخفاض الحالي: <b>{discount:.1f}٪</b>\n"
                f"الحد الأدنى المطلوب: {threshold}٪\n"
                "قد تتغير الأسعار قبل الحجز."
            )
        return (
            "🔔 <b>Ticket price drop alert</b>\n"
            f"Route: {route}\n"
            f"Current fare: <b>{price:,} tomans</b>\n"
            f"Average fare: {reference:,.0f} tomans\n"
            f"Current drop: <b>{discount:.1f}%</b>\n"
            f"Your minimum drop: {threshold}%\n"
            "The fare may change before booking."
        )

    if language == "fa":
        return (
            "🔔 <b>هشدار قیمت بلیط</b>\n"
            f"مسیر: {route}\n"
            f"قیمت فعلی: <b>{price:,} تومان</b>\n"
            f"سقف تعیین‌شده: {int(alert.target_price):,} تومان\n"
            "قیمت‌ها ممکن است تا زمان رزرو تغییر کنند."
        )
    if language == "ar":
        return (
            "🔔 <b>تنبيه سعر التذكرة</b>\n"
            f"المسار: {route}\n"
            f"السعر الحالي: <b>{price:,} تومان</b>\n"
            f"الحد الأقصى: {int(alert.target_price):,} تومان\n"
            "قد تتغير الأسعار قبل الحجز."
        )
    return (
        "🔔 <b>Ticket price alert</b>\n"
        f"Route: {route}\n"
        f"Current price: <b>{price:,} tomans</b>\n"
        f"Your price ceiling: {int(alert.target_price):,} tomans\n"
        "The fare may change before booking."
    )
