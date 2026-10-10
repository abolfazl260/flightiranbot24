"""Compact ticket result cards."""

import logging
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute, TicketOffer
from flightiran.modules.tickets.service import parse_toman_price

from .keyboards import ticket_result_menu
from .localization import normalize_language
from .rich_tickets import render_ticket_footer, send_rich_price_table
from .support import support_link, support_url

LOGGER = logging.getLogger(__name__)


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
        status = "<b>هم‌سطح میانگین</b>"
        difference_text = "0 تومان"
        percentage_text = "0.0٪"
    elif difference < 0:
        status = f"<b>{abs(percentage):.1f}٪ ارزان‌تر از میانگین</b>"
        difference_text = f"-{abs(difference_toman):,} تومان"
        percentage_text = f"-{abs(percentage):.1f}٪"
    else:
        status = f"<b>{percentage:.1f}٪ گران‌تر از میانگین</b>"
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


def render_cheap_route(route: CheapTicketRoute, *, language: str = "fa") -> str:
    """Render one origin and all destinations as Telegram HTML rich text."""

    blocks = [f"✈️ <b>پروازهای ارزان از {escape(route.origin)}</b>"]
    blocks.extend(_render_destination(item) for item in route.destinations)
    return "\n\n".join(blocks) + render_ticket_footer(language, rich=False)


def render_cheap_route_chunks(
    route: CheapTicketRoute,
    *,
    language: str = "fa",
    max_length: int = 3800,
) -> list[str]:
    """Keep each destination and the booking footer inside Telegram's limit."""

    header = f"✈️ <b>پروازهای ارزان از {escape(route.origin)}</b>"
    continuation_header = f"✈️ <b>{escape(route.origin)} — ادامه</b>"
    footer = render_ticket_footer(language, rich=False)
    if len(header + footer) > max_length:
        raise ValueError("Ticket route header and footer exceed Telegram limits")

    chunks: list[str] = []
    current = header

    for item in route.destinations:
        block = _render_destination(item)
        candidate = f"{current}\n\n{block}"
        if len(candidate + footer) <= max_length:
            current = candidate
            continue

        if current == header:
            raise ValueError("A destination exceeds Telegram fallback message limits")
        chunks.append(current + footer)
        current = f"{continuation_header}\n\n{block}"
        if len(current + footer) > max_length:
            raise ValueError("A destination exceeds Telegram fallback message limits")

    if current:
        chunks.append(current + footer)

    return chunks


def render_cheap_ticket_intro() -> str:
    return "🔍 <b>در حال دریافت و مقایسه قیمت بلیط‌ها...</b>"


def render_cheap_ticket_booking_hint(
    support_username: str, language: str = "fa"
) -> str:
    """Invite questions or booking requests without overstating fare certainty."""

    contact = support_link(support_username)
    language = normalize_language(language)

    if language == "en":
        return (
            "🎫 <b>Found a route you like, or still have questions?</b>\n\n"
            "The listed fares help you compare flights. Prices and availability "
            "can change before booking, so please confirm the final details "
            "with support.\n\n"
            "💬 Not sure about your route, travel dates, baggage rules or "
            "booking steps? Send your departure city, destination, approximate "
            "travel date and any questions. Your request can then be reviewed.\n\n"
            f"📩 <b>Support for all services:</b> {contact}\n"
            "👇 <b>Use the buttons below for booking, price alerts or navigation.</b>"
        )
    if language == "ar":
        return (
            "🎫 <b>هل وجدت رحلة مناسبة أم لديك سؤال قبل الحجز؟</b>\n\n"
            "الأسعار المعروضة للمقارنة وقد تتغير عند الحجز. يرجى تأكيد "
            "السعر النهائي والتوافر مع الدعم قبل اتخاذ القرار.\n\n"
            "💬 هل لديك استفسار عن المسار أو موعد السفر أو الأمتعة أو خطوات "
            "الحجز؟ أرسل مدينة المغادرة والوجهة والتاريخ التقريبي وسؤالك "
            "لتتم مراجعة طلبك.\n\n"
            f"📩 <b>دعم جميع الخدمات:</b> {contact}\n"
            "👇 <b>استخدم الأزرار أدناه للحجز أو تنبيهات الأسعار أو الرجوع.</b>"
        )
    return (
        "🎫 <b>مسیر دلخواهتان را پیدا کرده‌اید یا هنوز سؤال دارید؟</b>\n\n"
        "قیمت‌های این فهرست برای مقایسه مسیرها هستند و ممکن است تا زمان رزرو "
        "تغییر کنند. بهتر است پیش از تصمیم نهایی، قیمت و امکان رزرو را "
        "با پشتیبانی بررسی کنید.\n\n"
        "💬 <b>برای انتخاب مسیر یا رزرو نیاز به راهنمایی دارید؟</b>\n"
        "اگر درباره تاریخ سفر، شرایط بار، قیمت یا مراحل رزرو پرسشی دارید، "
        "مبدأ، مقصد و تاریخ تقریبی سفرتان را ارسال کنید و سؤال خود را بپرسید "
        "تا درخواستتان بررسی شود.\n\n"
        f"📩 <b>پشتیبانی همه خدمات:</b> {contact}\n"
        "👇 <b>برای رزرو، ثبت زنگوله قیمت یا بازگشت از دکمه‌های زیر استفاده کنید.</b>"
    )



def render_rich_ticket_booking_hint(
    support_username: str, language: str = "fa", *, origin_index: int | None = None
) -> dict:
    """Place support and navigation buttons *inside* one Rich Message.

    Keep this derived from the regular HTML copy and the existing fallback
    keyboard, so the two delivery formats have exactly the same content,
    localized labels and callback actions.
    """
    language = normalize_language(language)
    paragraphs = render_cheap_ticket_booking_hint(
        support_username, language
    ).split("\n\n")

    blocks = [f"<h3>{paragraphs[0]}</h3>"]
    for paragraph in paragraphs[1:]:
        blocks.extend(
            f"<p>{line}</p>" for line in paragraph.split("\n") if line
        )

    for row in ticket_result_menu(
        language, support_username, origin_index=origin_index
    ).inline_keyboard:
        buttons: list[str] = []
        for button in row:
            label = escape(button.text)
            if button.url is not None:
                action = f'type="url" style="primary" url="{escape(button.url, quote=True)}"'
            elif button.callback_data is not None:
                action = (
                    'type="callback_data" '
                    f'data="{escape(button.callback_data, quote=True)}"'
                )
            else:
                raise ValueError("Unsupported ticket action")
            buttons.append(f"<tg-button {action}>{label}</tg-button>")
        blocks.append(
            '<tg-button-row align="center">'
            + "".join(buttons)
            + "</tg-button-row>"
        )

    return {"html": "\n".join(blocks), "is_rtl": language in {"fa", "ar"}}


async def send_ticket_booking_hint(
    bot, message, support_username: str, language: str = "fa"
) -> None:
    """Prefer an in-message rich CTA; retain a working HTML+keyboard fallback."""
    try:
        await send_rich_price_table(
            bot,
            message.chat_id,
            render_rich_ticket_booking_hint(support_username, language),
        )
    except Exception as exc:
        # HTTP client errors may contain bot-token URLs: never log their text.
        LOGGER.warning(
            "rich_ticket_booking_hint_send_failed error_type=%s",
            type(exc).__name__,
        )
        await message.reply_text(
            render_cheap_ticket_booking_hint(support_username, language),
            parse_mode="HTML",
            reply_markup=ticket_result_menu(language, support_username),
        )



_RESERVATION_WORDS = {
    "fa": {
        "title": "🎫 درخواست بررسی رزرو بلیط",
        "origin": "مبدأ",
        "destination": "مقصد",
        "price": "قیمت فعلی اعلام‌شده",
        "average": "میانگین قیمت ثبت‌شده",
        "unavailable": "نامشخص",
        "unit": "تومان",
        "notice": (
            "این قیمت صرفاً برای مقایسه است و رزرو یا موجودی صندلی را "
            "تضمین نمی‌کند. برای بررسی تاریخ سفر، قیمت نهایی و امکان "
            "رزرو، مسیر و تاریخ تقریبی خود را به پشتیبانی ارسال کنید."
        ),
        "support": "💬 ارتباط با پشتیبانی برای درخواست رزرو",
    },
    "en": {
        "title": "🎫 Ticket booking inquiry",
        "origin": "Origin",
        "destination": "Destination",
        "price": "Last listed fare",
        "average": "Recorded average fare",
        "unavailable": "Unavailable",
        "unit": "tomans",
        "notice": (
            "This fare is for comparison only; no seat availability or booking "
            "is guaranteed. Contact support with your route and approximate "
            "travel date to check the final price and booking options."
        ),
        "support": "💬 Contact support about booking",
    },
    "ar": {
        "title": "🎫 طلب الاستفسار عن حجز تذكرة",
        "origin": "مدينة المغادرة",
        "destination": "الوجهة",
        "price": "السعر الحالي المعلن",
        "average": "متوسط الأسعار المسجل",
        "unavailable": "غير متاح",
        "unit": "تومان",
        "notice": (
            "هذا السعر للمقارنة فقط ولا يضمن توفر المقاعد أو الحجز. "
            "أرسل المسار والتاريخ التقريبي إلى الدعم للتحقق من السعر النهائي والحجز."
        ),
        "support": "💬 التواصل مع الدعم لطلب الحجز",
    },
}


def render_ticket_reservation_request(
    origin: str,
    destination: CheapTicketDestination,
    support_username: str,
    language: str = "fa",
    *,
    rich: bool = True,
) -> str:
    """Route-specific request text; directing to support is not a confirmed booking."""
    language = normalize_language(language)
    words = _RESERVATION_WORDS[language]
    price = destination.price_value_toman
    if price is None:
        try:
            price = parse_toman_price(destination.price_toman)
        except ValueError:
            price = None
    average = destination.average_price_toman
    unit = escape(words["unit"])
    amount = (
        f"{price:,} {unit}" if price is not None else escape(words["unavailable"])
    )
    mean = (
        f"{average:,.0f} {unit}"
        if average is not None and average > 0
        else escape(words["unavailable"])
    )
    title = escape(words["title"])
    items = [
        (words["origin"], origin),
        (words["destination"], destination.name),
    ]
    text_lines = [
        title,
        *[
            f"<b>{escape(label)}:</b> {escape(value)}"
            for label, value in items
        ],
        f"<b>{escape(words['price'])}:</b> {amount}",
        f"<b>{escape(words['average'])}:</b> {mean}",
        "",
        escape(words["notice"]),
    ]
    if not rich:
        return "\n".join(text_lines) + "\n" + support_link(support_username)

    button = (
        '<tg-button-row align="center">'
        '<tg-button type="url" style="primary" url="'
        + escape(support_url(support_username), quote=True) + '">'
        + escape(words["support"]) + "</tg-button></tg-button-row>"
    )
    return (
        f"<h3>{title}</h3>"
        + "".join(f"<p>{line}</p>" for line in text_lines[1:] if line)
        + button
    )


async def send_ticket_reservation_request(
    bot,
    message,
    origin: str,
    destination: CheapTicketDestination,
    support_username: str,
    language: str = "fa",
) -> None:
    """Send an actionable route-specific Rich Message, or an HTML fallback."""
    language = normalize_language(language)
    try:
        await send_rich_price_table(
            bot,
            message.chat_id,
            {
                "html": render_ticket_reservation_request(
                    origin, destination, support_username, language
                ),
                "is_rtl": language in {"fa", "ar"},
            },
        )
    except Exception as exc:
        LOGGER.warning(
            "rich_ticket_reservation_request_failed error_type=%s",
            type(exc).__name__,
        )
        await message.reply_text(
            render_ticket_reservation_request(
                origin, destination, support_username, language, rich=False
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    _RESERVATION_WORDS[language]["support"],
                    url=support_url(support_username),
                ),
            ]]),
            disable_web_page_preview=True,
        )
