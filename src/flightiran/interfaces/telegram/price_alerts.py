"""Telegram UI for user-selected ticket price and percentage alerts."""

from __future__ import annotations

import logging
import re
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.service import CheapTicketService, parse_toman_price

from .localization import normalize_language
from .rich_tickets import send_rich_price_table

LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 12

WORDS = {
    "fa": {
        "title": "🔔 <b>زنگوله قیمت بلیط</b>",
        "intro": (
            "برای مسیر دلخواه، سقف قیمت به تومان یا درصد کاهش نسبت به میانگین "
            "۲۱روزه را انتخاب کنید. قیمت‌ها دوره‌ای بررسی می‌شوند و در صورت "
            "رسیدن به شرط انتخابی، پیام تلگرام دریافت می‌کنید."
        ),
        "choose_mode": "روش هشدار برای مسیر <b>{origin} ← {destination}</b> را انتخاب کنید:",
        "mode_price": "💰 سقف قیمت به تومان",
        "mode_percent": "📉 درصد کاهش قیمت",
        "select_percent": (
            "برای مسیر <b>{origin} ← {destination}</b>، حداقل درصد کاهش نسبت به "
            "میانگین ۲۱روزه را انتخاب کنید (حداکثر ۵۰٪).\n"
            "در صورت ناکافی بودن داده‌های قبلی، هشدار درصدی تا جمع‌آوری "
            "حداقل دو نمونه معتبر فعال نمی‌شود."
        ),
        "created_percent": (
            "✅ هشدار درصدی ثبت شد.\n<b>{origin} ← {destination}</b>\n"
            "کاهش حداقل <b>{percent}٪</b> نسبت به میانگین قیمت ۲۱روزه.\n"
            "در صورت وجود داده کافی، قیمت‌ها دوره‌ای بررسی خواهند شد."
        ),
        "percent_label": "کاهش {percent}٪ نسبت به میانگین ۲۱روزه",
        "percent_invalid": "درصد انتخابی نامعتبر است؛ از دکمه‌های ۵ تا ۵۰٪ استفاده کنید.",
        "empty": "هنوز هشدار قیمتی ثبت نکرده‌اید.",
        "new": "➕ ثبت هشدار جدید",
        "back": "↩️ منوی اصلی",
        "manage": "🔔 هشدارهای من",
        "origin": "شهر مبدأ را انتخاب کنید:",
        "destination": "مقصد را انتخاب کنید:",
        "amount": (
            "سقف قیمت برای مسیر <b>{origin} ← {destination}</b> را به تومان ارسال کنید.\n"
            "مثال: <code>5,000,000</code>\nبرای لغو /cancel را بزنید."
        ),
        "amount_heading": "💰 تعیین سقف هشدار قیمت",
        "current_fare": "قیمت فعلی مسیر",
        "route_average": "میانگین ثبت‌شده ۲۱روزه",
        "no_current": "فعلاً موجود نیست",
        "no_average": "هنوز داده تاریخی موجود نیست",
        "sample_note": "میانگین بر اساس {count} ثبت قیمت محاسبه شده است.",
        "suggest_title": "یکی از سقف‌های پیشنهادی را انتخاب کنید:",
        "manual_entry": "یا سقف دلخواه را به تومان در همین گفت‌وگو ارسال کنید.",
        "no_suggestions": "قیمت معتبری برای پیشنهاد خودکار نداریم؛ مبلغ را دستی وارد کنید.",
        "suggest_from_average": "مبالغ پیشنهادی بر مبنای میانگین تاریخی محاسبه شده‌اند.",
        "amount_ready": "👇 گزینه‌های سقف قیمت در پیام جدید نمایش داده شدند.",
        "unit": "تومان",
        "invalid": "مبلغ معتبر وارد کنید؛ فقط عدد مثبت به تومان (مثلاً 5,000,000).",
        "created": (
            "✅ هشدار ثبت شد.\n<b>{origin} ← {destination}</b>\n"
            "سقف قیمت: <b>{price:,} تومان</b>\n"
            "قیمت‌ها در بازه‌های پایش ربات بررسی خواهند شد."
        ),
        "active": "فعال",
        "paused": "متوقف",
        "pause": "⏸ توقف",
        "resume": "▶️ فعال‌سازی",
        "delete": "🗑 حذف",
        "cancel": "لغو",
        "cancelled": "ثبت هشدار لغو شد.",
        "expired": "فهرست مسیرها منقضی شده است؛ دوباره «ثبت هشدار جدید» را انتخاب کنید.",
        "not_found": "هشدار یافت نشد یا به شما تعلق ندارد.",
        "limit": "حداکثر تعداد هشدار فعال شما تکمیل شده است.",
        "unavailable": "امکان دریافت مسیرها فعلاً وجود ندارد. لطفاً بعداً تلاش کنید.",
        "private": "برای دریافت هشدارها، از گفت‌وگوی خصوصی ربات استفاده کنید.",
    },
    "en": {
        "title": "🔔 <b>Ticket price alerts</b>",
        "intro": (
            "Choose a price ceiling in tomans or a percentage drop from the "
            "21-day average. The bot checks routes periodically and sends a "
            "Telegram message when your selected condition is met."
        ),
        "choose_mode": "Choose the alert type for <b>{origin} → {destination}</b>:",
        "mode_price": "💰 Price ceiling in tomans",
        "mode_percent": "📉 Percentage price drop",
        "select_percent": (
            "Choose the minimum drop from the 21-day average for "
            "<b>{origin} → {destination}</b> (up to 50%).\n"
            "At least two valid historical samples are needed to trigger the alert."
        ),
        "created_percent": (
            "✅ Percentage alert saved.\n<b>{origin} → {destination}</b>\n"
            "Drop: <b>at least {percent}%</b> below the 21-day average.\n"
            "Scheduled checks will run when enough historical data is available."
        ),
        "percent_label": "{percent}% below the 21-day average",
        "percent_invalid": "Select a percentage between 5% and 50% using the buttons.",
        "empty": "No price alerts yet.",
        "new": "➕ New alert",
        "back": "↩️ Main menu",
        "manage": "🔔 My alerts",
        "origin": "Select the departure city:",
        "destination": "Select the destination:",
        "amount": (
            "Send the price ceiling in tomans for <b>{origin} → {destination}</b>.\n"
            "Example: <code>5,000,000</code>\nSend /cancel to stop."
        ),
        "amount_heading": "💰 Set a ticket price ceiling",
        "current_fare": "Current route fare",
        "route_average": "Recorded 21-day average",
        "no_current": "Currently unavailable",
        "no_average": "No recorded history yet",
        "sample_note": "Average based on {count} observed fares.",
        "suggest_title": "Select one of these suggested price ceilings:",
        "manual_entry": "Or send your own ceiling in tomans in this chat.",
        "no_suggestions": "No current fare to suggest amounts; type your price instead.",
        "suggest_from_average": "Suggestions are based on the recorded average.",
        "amount_ready": "👇 Suggested price options appear in the next message.",
        "unit": "tomans",
        "invalid": "Enter a positive price in tomans, e.g. 5,000,000.",
        "created": (
            "✅ Alert saved.\n<b>{origin} → {destination}</b>\n"
            "Limit: <b>{price:,} tomans</b>\n"
            "It will be checked during the bot's scheduled scans."
        ),
        "active": "Active",
        "paused": "Paused",
        "pause": "⏸ Pause",
        "resume": "▶️ Resume",
        "delete": "🗑 Delete",
        "cancel": "Cancel",
        "cancelled": "Price alert creation cancelled.",
        "expired": "The route list expired. Choose New alert again.",
        "not_found": "Alert not found or not owned by you.",
        "limit": "You have reached the maximum number of active alerts.",
        "unavailable": "Routes are temporarily unavailable. Please try later.",
        "private": "Open a private chat with the bot to receive price notifications.",
    },
    "ar": {
        "title": "🔔 <b>تنبيهات أسعار التذاكر</b>",
        "intro": (
            "اختر سقف سعر بالتومان أو نسبة انخفاض مقارنة بمتوسط آخر ٢١ يوماً. "
            "يتحقق البوت من الأسعار دورياً ويرسل رسالة عند تحقق الشرط."
        ),
        "choose_mode": "اختر نوع التنبيه للمسار <b>{origin} ← {destination}</b>:",
        "mode_price": "💰 سقف السعر بالتومان",
        "mode_percent": "📉 نسبة انخفاض السعر",
        "select_percent": (
            "اختر الحد الأدنى للانخفاض مقارنة بمتوسط ٢١ يوماً للمسار "
            "<b>{origin} ← {destination}</b> (حتى ٥٠٪).\n"
            "يلزم توفر عينتين تاريخيتين صالحتين على الأقل قبل إرسال التنبيه."
        ),
        "created_percent": (
            "✅ تم حفظ تنبيه النسبة.\n<b>{origin} ← {destination}</b>\n"
            "انخفاض لا يقل عن <b>{percent}٪</b> مقارنة بمتوسط ٢١ يوماً.\n"
            "سيتم فحص الأسعار دورياً عند توفر بيانات كافية."
        ),
        "percent_label": "انخفاض {percent}٪ عن متوسط ٢١ يوماً",
        "percent_invalid": "اختر نسبة بين ٥٪ و٥٠٪ باستخدام الأزرار.",
        "empty": "لا توجد تنبيهات مسجلة.",
        "new": "➕ تنبيه جديد",
        "back": "↩️ القائمة الرئيسية",
        "manage": "🔔 تنبيهاتي",
        "origin": "اختر مدينة المغادرة:",
        "destination": "اختر الوجهة:",
        "amount": (
            "أرسل الحد الأقصى للسعر بالتومان للمسار <b>{origin} ← {destination}</b>.\n"
            "مثال: <code>5,000,000</code>\nللإلغاء أرسل /cancel."
        ),
        "amount_heading": "💰 تحديد سقف سعر التذكرة",
        "current_fare": "السعر الحالي للمسار",
        "route_average": "المتوسط المسجل خلال ٢١ يوماً",
        "no_current": "غير متاح حالياً",
        "no_average": "لا توجد بيانات تاريخية بعد",
        "sample_note": "حُسب المتوسط من {count} أسعار مسجلة.",
        "suggest_title": "اختر أحد حدود السعر المقترحة:",
        "manual_entry": "أو أرسل السقف المطلوب بالتومان في هذه المحادثة.",
        "no_suggestions": "لا يوجد سعر مناسب للاقتراحات؛ أدخل المبلغ يدوياً.",
        "suggest_from_average": "المقترحات مستندة إلى المتوسط التاريخي.",
        "amount_ready": "👇 تظهر خيارات السعر المقترحة في الرسالة التالية.",
        "unit": "تومان",
        "invalid": "أدخل مبلغاً صحيحاً بالتومان مثل 5,000,000.",
        "created": (
            "✅ تم حفظ التنبيه.\n<b>{origin} ← {destination}</b>\n"
            "السقف: <b>{price:,} تومان</b>\nسيتم فحصه دورياً."
        ),
        "active": "نشط",
        "paused": "متوقف",
        "pause": "⏸ إيقاف",
        "resume": "▶️ استئناف",
        "delete": "🗑 حذف",
        "cancel": "إلغاء",
        "cancelled": "تم إلغاء إنشاء التنبيه.",
        "expired": "انتهت صلاحية قائمة المسارات. ابدأ تنبيهاً جديداً.",
        "not_found": "التنبيه غير موجود أو لا يخصك.",
        "limit": "وصلت إلى الحد الأقصى للتنبيهات النشطة.",
        "unavailable": "المسارات غير متاحة حالياً. حاول مجدداً.",
        "private": "استخدم المحادثة الخاصة مع البوت لاستقبال التنبيهات.",
    },
}


def word(language: str, key: str) -> str:
    return WORDS[normalize_language(language)][key]


def menu_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(word(language, "manage"), callback_data="alerts:menu")],
        [InlineKeyboardButton(word(language, "new"), callback_data="alerts:new")],
        [InlineKeyboardButton(word(language, "back"), callback_data="back")],
    ])


def mode_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(word(language, "mode_price"), callback_data="alerts:mode:price")],
        [InlineKeyboardButton(
            word(language, "mode_percent"), callback_data="alerts:mode:percent"
        )],
        [InlineKeyboardButton(word(language, "cancel"), callback_data="alerts:cancel")],
    ])


def percent_keyboard(language: str) -> InlineKeyboardMarkup:
    options = list(range(5, 51, 5))
    rows = [
        [
            InlineKeyboardButton(f"{pct}٪", callback_data=f"alerts:percent:{pct}")
            for pct in options[i:i + 2]
        ]
        for i in range(0, len(options), 2)
    ]
    rows.append([
        InlineKeyboardButton(word(language, "cancel"), callback_data="alerts:cancel")
    ])
    return InlineKeyboardMarkup(rows)


def suggested_price_ceiling_amounts(
    current_price: int | None, average: float | None
) -> tuple[int, ...]:
    """Conservative, useful fare ceilings; no invented provider prices.

    The current fare takes precedence over the recorded 21-day average.
    Suggestions are rounded down to practical amounts and stay distinct.
    """
    basis = current_price if current_price is not None else average
    if basis is None or not 1_000 <= basis <= 10**13:
        return ()
    step = 10_000 if basis >= 1_000_000 else 1_000
    amounts = [
        int(basis * multiplier // step) * step
        for multiplier in (1.0, 0.95, 0.9, 0.8)
    ]
    return tuple(dict.fromkeys(amount for amount in amounts if amount >= 1_000))


def amount_keyboard(language: str, amounts: tuple[int, ...]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{amount:,} {word(language, 'unit')}",
                callback_data=f"alerts:suggest:{index}",
            )
            for index, amount in enumerate(amounts[position:position + 2], position)
        ]
        for position in range(0, len(amounts), 2)
    ]
    rows.append([
        InlineKeyboardButton(word(language, "cancel"), callback_data="alerts:cancel")
    ])
    return InlineKeyboardMarkup(rows)


def render_amount_prompt(
    language: str, pending: dict, *, rich: bool = False
) -> str:
    """Show genuine fare history and clickable, user-specific ceiling presets."""
    current = pending.get("current_price")
    average = pending.get("average_price")
    count = pending.get("average_samples", 0)
    unit = word(language, "unit")
    body = word(language, "amount").format(
        origin=escape(pending["origin"]), destination=escape(pending["destination"])
    )
    lines = [
        f"<b>{escape(word(language, 'amount_heading'))}</b>",
        body,
        "",
        f"• <b>{escape(word(language, 'current_fare'))}:</b> "
        + (f"{current:,} {unit}" if current is not None else
           escape(word(language, "no_current"))),
        f"• <b>{escape(word(language, 'route_average'))}:</b> "
        + (f"{average:,.0f} {unit}" if average is not None else
           escape(word(language, "no_average"))),
    ]
    if average is not None and count:
        lines.append(
            escape(word(language, "sample_note").format(count=count))
        )
    amounts = pending.get("suggested_prices", ())
    if amounts:
        lines.append("")
        lines.append(escape(word(language, "suggest_title")))
        if current is None:
            lines.append(escape(word(language, "suggest_from_average")))
    else:
        lines.append(escape(word(language, "no_suggestions")))
    lines.append(escape(word(language, "manual_entry")))
    if not rich:
        return "\n".join(lines)

    blocks = ["<h3>" + escape(word(language, "amount_heading")) + "</h3>"]
    blocks.extend(
        f"<p>{line}</p>" for line in lines[1:] if line
    )
    buttons = amount_keyboard(language, amounts)
    for row in buttons.inline_keyboard:
        markup = "".join(
            '<tg-button type="callback_data" data="'
            + escape(button.callback_data, quote=True) + '">'
            + escape(button.text) + "</tg-button>"
            for button in row
        )
        blocks.append('<tg-button-row align="center">' + markup + "</tg-button-row>")
    return "\n".join(blocks)


async def save_amount_alert(
    service: PriceAlertService, user_id: int, pending: dict, amount: int
):
    route = await service.save_route(
        user_id, pending["origin"], pending["destination"]
    )
    await service.create(user_id, route.id, amount, "TOMAN")
    return route


def parse_alert_price(value: str) -> int:
    normalized = value.strip().translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
    if not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:[,٬،\s][0-9]{3})+)", normalized):
        raise ValueError("Invalid price format")
    amount = int(re.sub(r"[,٬،\s]", "", normalized))
    if amount < 1000 or amount > 10**13:
        raise ValueError("Price is outside acceptable bounds")
    return amount


def _chooser_keyboard(items: list[str], callback_prefix: str, language: str, page: int):
    max_page = max(0, (len(items) - 1) // PAGE_SIZE)
    page = max(0, min(page, max_page))
    offset = page * PAGE_SIZE
    rows = [
        [
            InlineKeyboardButton(items[index], callback_data=f"{callback_prefix}:{index}")
            for index in range(i, min(i + 2, len(items)))
        ]
        for i in range(offset, min(offset + PAGE_SIZE, len(items)), 2)
    ]
    nav = []
    if page:
        nav.append(InlineKeyboardButton("◀", callback_data=f"{callback_prefix}:page:{page - 1}"))
    if page < max_page:
        nav.append(InlineKeyboardButton("▶", callback_data=f"{callback_prefix}:page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(word(language, "manage"), callback_data="alerts:menu")])
    return InlineKeyboardMarkup(rows)


def _destination_keyboard(route_index: int, items: list[str], language: str, page: int):
    max_page = max(0, (len(items) - 1) // PAGE_SIZE)
    page = max(0, min(page, max_page))
    offset = page * PAGE_SIZE
    rows = [
        [
            InlineKeyboardButton(items[index], callback_data=f"alerts:select:{route_index}:{index}")
            for index in range(i, min(i + 2, len(items)))
        ]
        for i in range(offset, min(offset + PAGE_SIZE, len(items)), 2)
    ]
    nav = []
    if page:
        nav.append(InlineKeyboardButton(
            "◀", callback_data=f"alerts:destpage:{route_index}:{page - 1}"
        ))
    if page < max_page:
        nav.append(InlineKeyboardButton(
            "▶", callback_data=f"alerts:destpage:{route_index}:{page + 1}"
        ))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(word(language, "new"), callback_data="alerts:new")])
    return InlineKeyboardMarkup(rows)


async def show_alerts(query, service: PriceAlertService, user_id: int, language: str) -> None:
    alerts = await service.list_user_alerts(user_id)
    lines = [word(language, "title"), "", word(language, "intro"), ""]
    rows = [[InlineKeyboardButton(word(language, "new"), callback_data="alerts:new")]]
    if not alerts:
        lines.append(word(language, "empty"))
    for item in alerts:
        status = word(language, item.status)
        if item.threshold_type == "percent" and item.target_percent is not None:
            criterion = word(language, "percent_label").format(
                percent=item.target_percent
            )
        else:
            unit = "tomans" if normalize_language(language) == "en" else "تومان"
            criterion = f"{item.target_price:,} {unit}"
        lines.append(
            f"<b>#{item.id}</b> {escape(item.origin)} → {escape(item.destination)}\n"
            f"{escape(criterion)} — {escape(status)}"
        )
        rows.append([
            InlineKeyboardButton(
                word(language, "pause" if item.status == "active" else "resume"),
                callback_data=f"alerts:toggle:{item.id}",
            ),
            InlineKeyboardButton(
                word(language, "delete"), callback_data=f"alerts:delete:{item.id}"
            ),
        ])
    rows.append([InlineKeyboardButton(word(language, "back"), callback_data="back")])
    await query.edit_message_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows),
    )


async def handle_alert_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: PriceAlertService,
    ticket_service: CheapTicketService | None,
    user_id: int,
    language: str,
) -> None:
    query = update.callback_query
    if query is None:
        return
    data = query.data or ""
    if data in ("menu:price_alerts", "alerts:menu"):
        context.user_data.pop("price_alert_pending", None)
        await show_alerts(query, service, user_id, language)
        return

    if data == "alerts:cancel":
        context.user_data.pop("price_alert_pending", None)
        await show_alerts(query, service, user_id, language)
        return

    if data.startswith(("alerts:toggle:", "alerts:delete:")):
        try:
            alert_id = int(data.rsplit(":", 1)[1])
        except ValueError:
            alert_id = -1
        alerts = await service.list_user_alerts(user_id)
        selected = next((item for item in alerts if item.id == alert_id), None)
        if selected is None:
            await query.edit_message_text(
                word(language, "not_found"), reply_markup=menu_keyboard(language)
            )
            return
        if data.startswith("alerts:delete:"):
            await service.delete_user_alert(user_id, alert_id)
        else:
            status = "paused" if selected.status == "active" else "active"
            if status == "active":
                active = sum(item.status == "active" for item in alerts)
                if active >= service.max_alerts_per_user:
                    await query.edit_message_text(
                        word(language, "limit"), reply_markup=menu_keyboard(language)
                    )
                    return
            await service.set_user_status(user_id, alert_id, status)
        await show_alerts(query, service, user_id, language)
        return

    if data == "alerts:new":
        context.user_data.pop("price_alert_pending", None)
        if ticket_service is None:
            await query.edit_message_text(
                word(language, "unavailable"), reply_markup=menu_keyboard(language)
            )
            return
        try:
            routes = await ticket_service.routes()
        except Exception:
            LOGGER.exception("price_alert_route_fetch_failed")
            await query.edit_message_text(
                word(language, "unavailable"), reply_markup=menu_keyboard(language)
            )
            return
        context.user_data["alert_routes"] = routes
        await query.edit_message_text(
            word(language, "origin"),
            reply_markup=_chooser_keyboard(
                [route.origin for route in routes], "alerts:origin", language, 0
            ),
        )
        return

    if data.startswith(("alerts:mode:", "alerts:percent:", "alerts:suggest:")):
        pending = context.user_data.get("price_alert_pending")
        chat = getattr(update, "effective_chat", None)
        if not pending or chat is None or chat.type != "private":
            await query.edit_message_text(
                word(language, "expired"), reply_markup=menu_keyboard(language)
            )
            return
        origin = escape(pending["origin"])
        destination = escape(pending["destination"])
        if data == "alerts:mode:price" and pending.get("step") == "choose_mode":
            pending["step"] = "price"
            amount_text = render_amount_prompt(language, pending)
            amounts = tuple(pending.get("suggested_prices", ()))
            bot = getattr(context, "bot", None)
            chat_id = getattr(getattr(query, "message", None), "chat_id", None)
            if bot is not None and chat_id is not None:
                try:
                    await send_rich_price_table(
                        bot, chat_id,
                        {
                            "html": render_amount_prompt(language, pending, rich=True),
                            "is_rtl": normalize_language(language) != "en",
                        },
                    )
                except Exception as exc:
                    # Do not expose Telegram bot tokens embedded in HTTP errors.
                    LOGGER.warning(
                        "price_alert_rich_ceiling_failed error_type=%s",
                        type(exc).__name__,
                    )
                else:
                    await query.edit_message_text(
                        word(language, "amount_ready")
                    )
                    return
            await query.edit_message_text(
                amount_text,
                parse_mode="HTML",
                reply_markup=amount_keyboard(language, amounts),
            )
            return
        if data.startswith("alerts:suggest:") and pending.get("step") == "price":
            try:
                index = int(data.rsplit(":", 1)[1])
            except ValueError:
                index = -1
            amounts = pending.get("suggested_prices", ())
            if index < 0 or index >= len(amounts):
                await query.message.reply_text(
                    word(language, "invalid"),
                    reply_markup=amount_keyboard(language, tuple(amounts)),
                )
                return
            try:
                amount = parse_alert_price(str(amounts[index]))
                route = await save_amount_alert(service, user_id, pending, amount)
            except ValueError:
                await query.message.reply_text(
                    word(language, "limit"), reply_markup=menu_keyboard(language)
                )
                return
            context.user_data.pop("price_alert_pending", None)
            await query.message.reply_text(
                word(language, "created").format(
                    origin=escape(route.origin),
                    destination=escape(route.destination),
                    price=amount,
                ),
                parse_mode="HTML",
                reply_markup=menu_keyboard(language),
            )
            return
        if data == "alerts:mode:percent" and pending.get("step") == "choose_mode":
            pending["step"] = "percent"
            await query.edit_message_text(
                word(language, "select_percent").format(
                    origin=origin, destination=destination
                ),
                parse_mode="HTML",
                reply_markup=percent_keyboard(language),
            )
            return
        if data.startswith("alerts:percent:") and pending.get("step") == "percent":
            try:
                percent = int(data.rsplit(":", 1)[1])
            except ValueError:
                percent = 0
            if percent not in range(5, 51, 5):
                await query.edit_message_text(
                    word(language, "percent_invalid"),
                    reply_markup=percent_keyboard(language),
                )
                return
            try:
                route = await service.save_route(
                    user_id, pending["origin"], pending["destination"]
                )
                await service.create_percent(user_id, route.id, percent)
            except ValueError as exc:
                label = "limit" if "limit" in str(exc) else "expired"
                await query.edit_message_text(
                    word(language, label), reply_markup=menu_keyboard(language)
                )
                return
            context.user_data.pop("price_alert_pending", None)
            await query.edit_message_text(
                word(language, "created_percent").format(
                    origin=escape(route.origin),
                    destination=escape(route.destination),
                    percent=percent,
                ),
                parse_mode="HTML",
                reply_markup=menu_keyboard(language),
            )
            return
        await query.edit_message_text(
            word(language, "expired"), reply_markup=menu_keyboard(language)
        )
        return

    routes = context.user_data.get("alert_routes", [])
    if not routes:
        await query.edit_message_text(
            word(language, "expired"), reply_markup=menu_keyboard(language)
        )
        return

    try:
        if data.startswith("alerts:origin:page:"):
            page = int(data.rsplit(":", 1)[1])
            await query.edit_message_text(
                word(language, "origin"),
                reply_markup=_chooser_keyboard(
                    [route.origin for route in routes], "alerts:origin", language, page
                ),
            )
            return
        if data.startswith("alerts:origin:"):
            route_index = int(data.rsplit(":", 1)[1])
            page = 0
        elif data.startswith("alerts:destpage:"):
            _, _, route_idx, page_idx = data.split(":")
            route_index, page = int(route_idx), int(page_idx)
        elif data.startswith("alerts:select:"):
            _, _, route_idx, dest_idx = data.split(":")
            route_index, dest_index = int(route_idx), int(dest_idx)
            page = None
        else:
            raise ValueError("Unknown alert callback")
        if route_index < 0 or route_index >= len(routes):
            raise ValueError("Invalid route index")
        route = routes[route_index]
        if page is None:
            if dest_index < 0 or dest_index >= len(route.destinations):
                raise ValueError("Invalid destination index")
            chat = getattr(update, "effective_chat", None)
            if chat is None or chat.type != "private":
                await query.edit_message_text(
                    word(language, "private"), reply_markup=menu_keyboard(language)
                )
                return
            item = route.destinations[dest_index]
            destination = item.name
            current = item.price_value_toman
            if current is None:
                try:
                    current = parse_toman_price(item.price_toman)
                except ValueError:
                    current = None
            average = (
                float(item.average_price_toman)
                if item.average_price_toman is not None
                and item.average_price_toman > 0 else None
            )
            count = item.average_sample_count
            context.user_data["price_alert_pending"] = {
                "origin": route.origin, "destination": destination,
                "step": "choose_mode",
                "current_price": current,
                "average_price": average,
                "average_samples": count,
                "suggested_prices": suggested_price_ceiling_amounts(current, average),
            }
            await query.edit_message_text(
                word(language, "choose_mode").format(
                    origin=escape(route.origin), destination=escape(destination)
                ),
                parse_mode="HTML",
                reply_markup=mode_keyboard(language),
            )
        else:
            await query.edit_message_text(
                word(language, "destination"),
                reply_markup=_destination_keyboard(
                    route_index, [item.name for item in route.destinations], language, page
                ),
            )
    except (ValueError, IndexError):
        await query.edit_message_text(
            word(language, "expired"), reply_markup=menu_keyboard(language)
        )


async def handle_alert_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: PriceAlertService,
    user_id: int,
    language: str,
) -> bool:
    """Consume the next text message only while an alert amount is pending."""
    pending = context.user_data.get("price_alert_pending")
    if not pending or update.message is None:
        return False
    chat = getattr(update, "effective_chat", None)
    if chat is None or chat.type != "private":
        await update.message.reply_text(word(language, "private"))
        return True
    if pending.get("step") != "price":
        await update.message.reply_text(
            word(language, "choose_mode").format(
                origin=escape(pending["origin"]),
                destination=escape(pending["destination"]),
            ),
            parse_mode="HTML",
            reply_markup=(
                percent_keyboard(language)
                if pending.get("step") == "percent" else mode_keyboard(language)
            ),
        )
        return True
    try:
        amount = parse_alert_price(update.message.text or "")
    except ValueError:
        await update.message.reply_text(word(language, "invalid"))
        return True
    try:
        route = await save_amount_alert(service, user_id, pending, amount)
    except ValueError:
        await update.message.reply_text(
            word(language, "limit"), reply_markup=menu_keyboard(language)
        )
        return True
    context.user_data.pop("price_alert_pending", None)
    await update.message.reply_text(
        word(language, "created").format(
            origin=escape(route.origin), destination=escape(route.destination), price=amount
        ),
        parse_mode="HTML",
        reply_markup=menu_keyboard(language),
    )
    return True
