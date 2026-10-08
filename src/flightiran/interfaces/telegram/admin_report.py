"""Telegram-safe HTML presentation of the administrator's full bot report."""

from __future__ import annotations

from datetime import timezone
from html import escape

from flightiran.modules.admin.reports import BotReport


def _entries(rows: tuple[tuple[str, int], ...], *, limit: int = 12) -> str:
    if not rows:
        return "داده‌ای ثبت نشده است."
    return "\n".join(
        f"• {escape(str(name))}: <b>{count:,}</b>"
        for name, count in rows[:limit]
    )


def _operations(rows: tuple[tuple[str, str, int], ...]) -> str:
    if not rows:
        return "داده‌ای در این جدول ثبت نشده است؛ وضعیت واقعی سرویس نامشخص است."
    return "\n".join(
        f"• {escape(name)} / {escape(status)}: <b>{count:,}</b>"
        for name, status, count in rows
    )


def _timestamp(value) -> str:
    if value is None:
        return "هنوز ثبت نشده"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def render_admin_report(report: BotReport) -> tuple[str, ...]:
    """Return a comprehensive readable report in three bounded private messages."""

    c = report.counts
    intro = (
        "📊 <b>گزارش جامع FlightIranBot24</b>\n"
        f"زمان تهیه: {_timestamp(report.generated_at)}\n"
        "مبنای آمار: اطلاعات ثبت‌شده در دیتابیس ربات\n\n"
        "<b>کاربران</b>\n"
        f"• مجموع کاربران: <b>{c['users_total']:,}</b>\n"
        f"• کاربران جدید: ۲۴ ساعت {c['new_users_24h']:,} | "
        f"۷ روز {c['new_users_7d']:,} | ۳۰ روز {c['new_users_30d']:,}\n"
        f"• کاربران فعال ثبت‌شده: ۲۴ ساعت {c['active_users_24h']:,} | "
        f"۷ روز {c['active_users_7d']:,} | ۳۰ روز {c['active_users_30d']:,}\n"
        f"• مجموع رویدادها: {c['audit_total']:,}\n"
        f"• رویدادها: ۲۴ ساعت {c['events_24h']:,} | "
        f"۷ روز {c['events_7d']:,} | ۳۰ روز {c['events_30d']:,}\n\n"
        "<b>زبان کاربران دارای تنظیم زبان</b>\n"
        f"{_entries(report.language_counts)}\n\n"
        "<b>پرمراجعه‌ترین بخش‌ها در ۷ روز اخیر</b>\n"
        f"{_entries(report.top_events)}\n\n"
        "فعال یعنی کاربری که حداقل یک رویداد قابل‌اندازه‌گیری داشته؛ "
        "این عدد لزوماً تمام کاربران فعال واقعی نیست."
    )
    fares = (
        "🎫 <b>گزارش بلیط و هشدارهای قیمت</b>\n"
        f"زمان: {_timestamp(report.generated_at)}\n\n"
        "<b>پایش قیمت پرواز</b>\n"
        f"• مسیرهای دارای میانگین: <b>{c['tracked_routes']:,}</b>\n"
        f"• تعداد شهرهای مبدأ: <b>{c['origins']:,}</b>\n"
        f"• ثبت‌های قیمت در بازه نگهداری: {c['price_snapshots']:,}\n"
        f"• ثبت‌های قیمت در ۲۴ ساعت اخیر: {c['price_samples_24h']:,}\n"
        f"• آخرین ثبت قیمت: {_timestamp(report.last_price_capture)}\n"
        f"• مسیرهای ذخیره‌شده کاربران: {c['saved_routes']:,}\n\n"
        "<b>شهرهای مبدأ پرتقاضا (انتخاب‌های ۳۰ روز)</b>\n"
        f"{_entries(report.top_origins, limit=7)}\n\n"
        f"<b>هشدارهای قیمت (مجموع {c['price_alerts']:,})</b>\n"
        f"{_entries(report.price_alert_status)}\n"
        f"• اعلان‌های موفق قیمت: {c['price_notifications']:,}"
    )
    operations = (
        "🛠 <b>گزارش فنی و سرویس‌ها</b>\n"
        f"زمان: {_timestamp(report.generated_at)}\n\n"
        "<b>درخواست‌های ثبت‌شده سرویس‌دهنده‌ها (۷ روز اخیر)</b>\n"
        f"{_operations(report.provider_status)}\n"
        f"• مجموع ثبت‌ها: {c['provider_requests']:,}\n"
        f"• موارد ناموفق ۷ روز: {c['failed_provider_7d']:,}\n\n"
        "<b>اجراهای ثبت‌شده وظایف زمان‌بندی‌شده (۷ روز اخیر)</b>\n"
        f"{_operations(report.job_status)}\n"
        f"• مجموع اجراها: {c['job_runs']:,}\n"
        f"• اجراهای ناموفق ۷ روز: {c['failed_jobs_7d']:,}\n\n"
        "<b>خطاهای ثبت‌شده</b>\n"
        f"• خطاهای سیستمی در دفتر رویدادها (۷ روز): "
        f"{c['runtime_errors_7d']:,}\n\n"
        "توجه: صفر بودن آمار خطا یا درخواست‌ها لزوماً به معنی نبود خطا "
        "نیست؛ تنها داده‌هایی گزارش می‌شوند که واقعاً در دیتابیس ثبت شده‌اند."
    )
    for message in (intro, fares, operations):
        if len(message) > 4096:
            raise ValueError("Admin report section exceeds Telegram text limit")
    return intro, fares, operations
