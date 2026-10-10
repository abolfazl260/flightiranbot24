"""Telegram controls for visa-change subscriptions and localized notices."""

from __future__ import annotations

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from flightiran.modules.visa.provenance import link_html, source_date
from flightiran.modules.visa.watch import PendingNotification, VisaWatchService

from .visa_presentation import country_label, status_label

WORDS = {
    "fa": {
        "title": "🔔 <b>زنگوله تغییرات ویزا</b>",
        "description": (
            "مسیرهای انتخاب‌شده پایش می‌شوند. اگر وضعیت ویزا، مدت اقامت یا شرایط "
            "منتشرشده تغییر کند، در تلگرام پیام می‌گیرید. بررسی دوباره منبع یا تغییر "
            "تاریخ انتشار، به‌تنهایی باعث اعلان نمی‌شود."
        ),
        "empty": "هنوز مسیری را برای پیگیری ذخیره نکرده‌اید.",
        "added": "✅ مسیر برای پیگیری تغییرات ویزا ذخیره شد.",
        "active": "فعال", "paused": "متوقف",
        "pause": "⏸ توقف", "resume": "▶️ فعال‌سازی",
        "delete": "🗑 حذف", "back": "↩️ برگشت به ویزا",
        "private": "مدیریت زنگوله ویزا فقط در گفت‌وگوی خصوصی ربات ممکن است.",
        "route": "ابتدا پاسپورت و مقصد را در بخش ویزا انتخاب کنید.",
        "not_found": "اشتراک موردنظر پیدا نشد یا به شما تعلق ندارد.",
        "limit": "حداکثر تعداد مسیرهای فعال برای پیگیری تکمیل شده است.",
        "unavailable": "قابلیت پیگیری تغییرات ویزا فعلاً فعال نیست.",
        "alert_title": "🔔 <b>تغییر شرایط ویزا در داده‌های منتشرشده</b>",
        "status": "وضعیت ویزا", "stay": "حداکثر اقامت", "conditions": (
            "شرایط درخواست یا مدارک مربوط به این مسیر در دیتاست تغییر کرده است."
        ),
        "unknown": "نامشخص", "days": "روز",
        "publication": "تاریخ اعلام‌شده انتشار داده", "source": "مشاهده فایل مرجع مقصد",
        "notice": (
            "این اعلان درباره تغییر اطلاعات منتشرشده است، نه تأیید تغییر قانون. "
            "پیش از رزرو یا سفر، مرجع رسمی کشور مقصد و ایرلاین را بررسی کنید."
        ),
    },
    "en": {
        "title": "🔔 <b>Visa change alerts</b>",
        "description": (
            "Watch selected passport/destination routes. Get a private alert if the "
            "published visa status, stay allowance or entry conditions change. "
            "A source recheck or publication-date edit alone does not trigger alerts."
        ),
        "empty": "You are not watching any visa routes.",
        "added": "✅ This route is now monitored for visa changes.",
        "active": "Active", "paused": "Paused",
        "pause": "⏸ Pause", "resume": "▶️ Resume",
        "delete": "🗑 Delete", "back": "↩️ Back to visas",
        "private": "Manage visa notifications in a private chat with the bot.",
        "route": "Select a passport and destination in the visa section first.",
        "not_found": "Subscription not found or not owned by you.",
        "limit": "You have reached the active visa-route watch limit.",
        "unavailable": "Visa change notifications are currently unavailable.",
        "alert_title": "🔔 <b>Published visa requirement update</b>",
        "status": "Visa status", "stay": "Maximum stay", "conditions": (
            "Application or entry-condition details for this route changed in the dataset."
        ),
        "unknown": "Not specified", "days": "days",
        "publication": "Published data date", "source": "View source destination record",
        "notice": (
            "This reports a published data change, not a confirmed change in law. "
            "Verify with the destination immigration authority and your airline before travel."
        ),
    },
    "ar": {
        "title": "🔔 <b>تنبيهات تغيير التأشيرات</b>",
        "description": (
            "تابع تغييرات المسارات المحفوظة. ستتلقى تنبيهاً خاصاً إذا تغيّرت حالة "
            "التأشيرة أو الإقامة أو الشروط المنشورة. إعادة فحص المصدر وحدها لا تكفي."
        ),
        "empty": "لم تحفظ أي مسارات لمتابعة تغيرات التأشيرات.",
        "added": "✅ تم حفظ المسار لمتابعة تغييرات التأشيرة.",
        "active": "نشط", "paused": "متوقف",
        "pause": "⏸ إيقاف", "resume": "▶️ استئناف",
        "delete": "🗑 حذف", "back": "↩️ العودة إلى التأشيرات",
        "private": "إدارة تنبيهات التأشيرات متاحة في المحادثة الخاصة فقط.",
        "route": "اختر جواز السفر والوجهة أولاً.",
        "not_found": "الاشتراك غير موجود أو لا يخصك.",
        "limit": "بلغت الحد الأقصى لمسارات المراقبة النشطة.",
        "unavailable": "تنبيهات تغييرات التأشيرات غير متاحة الآن.",
        "alert_title": "🔔 <b>تحديث في بيانات متطلبات التأشيرة</b>",
        "status": "حالة التأشيرة", "stay": "مدة الإقامة القصوى", "conditions": (
            "تغيرت شروط التقديم أو وثائق الدخول المنشورة لهذا المسار."
        ),
        "unknown": "غير محدد", "days": "يوم",
        "publication": "تاريخ نشر البيانات", "source": "فتح السجل الأصلي للوجهة",
        "notice": (
            "يشير هذا التنبيه إلى تغير البيانات المنشورة وليس تأكيداً لتغير القانون. "
            "تحقق من الجهة الرسمية وشركة الطيران قبل السفر."
        ),
    },
}


def word(language: str, key: str) -> str:
    return WORDS.get(language, WORDS["en"])[key]


def _menu_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(word(language, "back"), callback_data="visa:home")
    ]])


async def show_watches(
    target, service: VisaWatchService, user_id: int, language: str, *, edit: bool = True
) -> None:
    watches = await service.list_user(user_id)
    lines = [word(language, "title"), "", escape(word(language, "description")), ""]
    rows: list[list[InlineKeyboardButton]] = []
    if not watches:
        lines.append(escape(word(language, "empty")))
    for watch in watches:
        state = word(language, "active" if watch.active else "paused")
        lines.append(
            f"<b>#{watch.id}</b> "
            f"{escape(country_label(watch.passport, watch.passport, language))} "
            f"({watch.passport}) → "
            f"{escape(country_label(watch.destination, watch.destination, language))} "
            f"({watch.destination}) — {escape(state)}"
        )
        rows.append([
            InlineKeyboardButton(
                word(language, "pause" if watch.active else "resume"),
                callback_data=f"visa:watch:toggle:{watch.id}"
            ),
            InlineKeyboardButton(
                word(language, "delete"),
                callback_data=f"visa:watch:delete:{watch.id}"
            ),
        ])
    rows.append(_menu_keyboard(language).inline_keyboard[0])
    kwargs = {
        "parse_mode": "HTML",
        "reply_markup": InlineKeyboardMarkup(rows),
        "disable_web_page_preview": True,
    }
    if edit:
        await target.edit_message_text("\n".join(lines), **kwargs)
    else:
        await target.reply_text("\n".join(lines), **kwargs)


async def handle_watch_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: VisaWatchService | None,
    user_id: int,
    language: str,
) -> None:
    query = update.callback_query
    if query is None:
        return
    if update.effective_chat is None or update.effective_chat.type != "private":
        await query.edit_message_text(word(language, "private"))
        return
    if service is None:
        await query.edit_message_text(
            word(language, "unavailable"), reply_markup=_menu_keyboard(language)
        )
        return
    action = query.data or ""
    if action == "visa:watch:add":
        passport = context.user_data.get("visa_passport")
        destination = context.user_data.get("visa_destination")
        if not passport or not destination:
            await query.edit_message_text(
                word(language, "route"), reply_markup=_menu_keyboard(language)
            )
            return
        try:
            await service.subscribe(user_id, passport, destination)
        except ValueError as exc:
            reason = "limit" if "limit" in str(exc) else "route"
            await query.edit_message_text(
                word(language, reason), reply_markup=_menu_keyboard(language)
            )
            return
        await show_watches(query, service, user_id, language)
        return
    if action == "visa:watch:menu":
        await show_watches(query, service, user_id, language)
        return
    if action.startswith(("visa:watch:toggle:", "visa:watch:delete:")):
        try:
            watch_id = int(action.rsplit(":", 1)[1])
        except ValueError:
            watch_id = -1
        listed = await service.list_user(user_id)
        current = next((item for item in listed if item.id == watch_id), None)
        if current is None:
            await query.edit_message_text(
                word(language, "not_found"), reply_markup=_menu_keyboard(language)
            )
            return
        if action.startswith("visa:watch:delete:"):
            await service.remove(user_id, watch_id)
        else:
            try:
                await service.set_active(user_id, watch_id, not current.active)
            except ValueError:
                await query.edit_message_text(
                    word(language, "limit"), reply_markup=_menu_keyboard(language)
                )
                return
        await show_watches(query, service, user_id, language)
        return
    await query.edit_message_text(
        word(language, "not_found"), reply_markup=_menu_keyboard(language)
    )


def render_change_alert(notification: PendingNotification, language: str) -> str:
    data = notification.payload
    before, after = data.get("before") or {}, data.get("after") or {}
    categories = data.get("categories") or []
    lines = [
        word(language, "alert_title"),
        f"<b>{escape(country_label(notification.passport, notification.passport, language))}"
        f" ({escape(notification.passport)}) → "
        f"{escape(country_label(notification.destination, notification.destination, language))}"
        f" ({escape(notification.destination)})</b>",
        "",
    ]
    if "status" in categories:
        old_status = status_label(str(before.get("status")), language)
        new_status = status_label(str(after.get("status")), language)
        lines.append(
            f"• <b>{escape(word(language, 'status'))}:</b> "
            f"{escape(old_status)} → {escape(new_status)}"
        )
    if "stay" in categories:
        def stay_value(value: object) -> str:
            return (
                f"{value} {word(language, 'days')}"
                if type(value) is int else word(language, "unknown")
            )
        lines.append(
            f"• <b>{escape(word(language, 'stay'))}:</b> "
            f"{escape(stay_value(before.get('stay_days')))} → "
            f"{escape(stay_value(after.get('stay_days')))}"
        )
        if before.get("stay_days") == after.get("stay_days"):
            # The change was to a stay window or another constraint, not its max days.
            lines[-1] = (
                f"• <b>{escape(word(language, 'stay'))}:</b> "
                + escape(word(language, "conditions"))
            )
    if "conditions" in categories:
        lines.append("• " + escape(word(language, "conditions")))
    published = source_date(data.get("published"))
    if published:
        lines.append(
            f"🗓 {escape(word(language, 'publication'))}: {escape(published)}"
        )
    source = link_html(data.get("source_url"), word(language, "source"))
    if source:
        lines.append(source)
    lines.extend(["", "<i>" + escape(word(language, "notice")) + "</i>"])
    return "\n".join(lines)
