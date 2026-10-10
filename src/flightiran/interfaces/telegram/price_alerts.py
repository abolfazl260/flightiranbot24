"""Telegram UI for per-user mz724 price threshold alerts."""

from __future__ import annotations

import logging
import re
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.service import CheapTicketService

from .localization import normalize_language

LOGGER = logging.getLogger(__name__)
PAGE_SIZE = 12

WORDS = {
    "fa": {
        "title": "🔔 <b>زنگوله قیمت بلیط</b>",
        "intro": (
            "برای مسیر دلخواه سقف قیمت تعیین کنید؛ قیمت‌ها به‌صورت دوره‌ای بررسی می‌شوند "
            "و پس از رسیدن قیمت به سقف تعیین‌شده، پیام تلگرام دریافت می‌کنید. "
            "قیمت‌ها به تومان و براساس اطلاعات mz724 هستند."
        ),
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
            "Set a price ceiling for a route. The bot checks mz724 prices periodically "
            "and messages you when the price reaches your limit. Amounts are in tomans."
        ),
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
            "حدد سقف السعر لمسار معين. يفحص البوت أسعار mz724 دورياً ويرسل لك إشعاراً "
            "عند بلوغ السعر المحدد. المبالغ بالتومان."
        ),
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
        lines.append(
            f"<b>#{item.id}</b> {escape(item.origin)} → {escape(item.destination)}\n"
            f"{item.target_price:,} TOMAN — {status}"
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
            destination = route.destinations[dest_index].name
            context.user_data["price_alert_pending"] = {
                "origin": route.origin, "destination": destination,
            }
            await query.edit_message_text(
                word(language, "amount").format(
                    origin=escape(route.origin), destination=escape(destination)
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(word(language, "cancel"), callback_data="alerts:cancel")
                ]]),
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
    try:
        amount = parse_alert_price(update.message.text or "")
    except ValueError:
        await update.message.reply_text(word(language, "invalid"))
        return True
    try:
        route = await service.save_route(user_id, pending["origin"], pending["destination"])
        await service.create(user_id, route.id, amount, "TOMAN")
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
