"""Single native Telegram Rich Message for the private administrator report."""

from __future__ import annotations

from html import escape

from flightiran.modules.admin.reports import BotReport

from .admin_report import _timestamp, render_admin_report
from .rich_tickets import MAX_RICH_TEXT_CHARS, _plain_text_length

MAX_TELEGRAM_HTML_CHARS = 4096


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    """Escape every database-derived value before adding Telegram rich markup."""
    columns = "".join(f"<th>{escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table bordered striped compact><tr>{columns}</tr>{body}</table>"


def _count(value: int) -> str:
    return f"{value:,}"


def _rows(items: tuple[tuple[str, int], ...], *, empty: str) -> list[tuple[str, str]]:
    if not items:
        return [(empty, "—")]
    return [(str(name), _count(total)) for name, total in items]


def _status_rows(
    items: tuple[tuple[str, str, int], ...], *, empty: str
) -> list[tuple[str, str, str]]:
    if not items:
        return [(empty, "—", "—")]
    return [(str(name), str(status), _count(total)) for name, status, total in items]


def render_rich_admin_report(report: BotReport) -> dict:
    """Render all sections in one right-to-left table-rich Telegram message."""
    c = report.counts
    summary = [
        ("مجموع کاربران", _count(c["users_total"])),
        ("کاربران جدید / ۲۴ ساعت", _count(c["new_users_24h"])),
        ("کاربران جدید / ۷ روز", _count(c["new_users_7d"])),
        ("کاربران جدید / ۳۰ روز", _count(c["new_users_30d"])),
        ("کاربران فعال ثبت‌شده / ۲۴ ساعت", _count(c["active_users_24h"])),
        ("کاربران فعال ثبت‌شده / ۷ روز", _count(c["active_users_7d"])),
        ("کاربران فعال ثبت‌شده / ۳۰ روز", _count(c["active_users_30d"])),
        ("مجموع رویدادها", _count(c["audit_total"])),
        ("رویدادهای ۲۴ ساعت", _count(c["events_24h"])),
        ("رویدادهای ۷ روز", _count(c["events_7d"])),
        ("رویدادهای ۳۰ روز", _count(c["events_30d"])),
    ]
    prices = [
        ("مسیرهای دارای میانگین", _count(c["tracked_routes"])),
        ("شهرهای مبدأ", _count(c["origins"])),
        ("ثبت‌های قیمت در بازه نگهداری", _count(c["price_snapshots"])),
        ("ثبت‌های قیمت در ۲۴ ساعت اخیر", _count(c["price_samples_24h"])),
        ("آخرین ثبت قیمت", _timestamp(report.last_price_capture)),
        ("مسیرهای ذخیره‌شده کاربران", _count(c["saved_routes"])),
    ]
    alerts = [
        ("کل هشدارهای قیمت", _count(c["price_alerts"])),
        *_rows(report.price_alert_status, empty="وضعیتی ثبت نشده"),
        ("اعلان‌های موفق قیمت", _count(c["price_notifications"])),
    ]
    operational = [
        ("کل درخواست‌های ثبت‌شده سرویس‌دهنده‌ها", _count(c["provider_requests"])),
        ("درخواست‌های ناموفق / ۷ روز", _count(c["failed_provider_7d"])),
        ("مجموع اجراهای وظایف", _count(c["job_runs"])),
        ("اجراهای ناموفق / ۷ روز", _count(c["failed_jobs_7d"])),
        ("خطاهای سیستمی ثبت‌شده / ۷ روز", _count(c["runtime_errors_7d"])),
    ]
    html = "".join([
        "<h3>📊 گزارش جامع FlightIranBot24</h3>",
        f"<p>زمان تهیه: {escape(_timestamp(report.generated_at))} | "
        "مبنای آمار: دیتابیس ربات</p>",
        "<h3>👥 کاربران و فعالیت</h3>",
        _table(("شاخص", "مقدار"), summary),
        "<h3>🌐 زبان کاربران دارای تنظیم زبان</h3>",
        _table(("زبان", "تعداد"), _rows(report.language_counts, empty="داده‌ای ثبت نشده")),
        "<h3>📈 پرمراجعه‌ترین بخش‌ها | ۷ روز</h3>",
        _table(("بخش", "تعداد"), _rows(report.top_events, empty="داده‌ای ثبت نشده")),
        "<h3>🎫 بلیط و پایش قیمت</h3>",
        _table(("شاخص", "مقدار"), prices),
        "<h3>🛫 شهرهای مبدأ پرتقاضا | ۳۰ روز</h3>",
        _table(("مبدأ", "انتخاب"), _rows(report.top_origins, empty="داده‌ای ثبت نشده")),
        "<h3>🔔 هشدارهای قیمت</h3>",
        _table(("وضعیت / شاخص", "تعداد"), alerts),
        "<h3>🛠 وضعیت سرویس‌دهنده‌ها | ۷ روز</h3>",
        _table(("سرویس‌دهنده", "وضعیت", "تعداد"),
               _status_rows(report.provider_status, empty="داده‌ای ثبت نشده")),
        "<h3>⏱ وظایف زمان‌بندی‌شده | ۷ روز</h3>",
        _table(("وظیفه", "وضعیت", "تعداد"),
               _status_rows(report.job_status, empty="داده‌ای ثبت نشده")),
        "<h3>⚠️ جمع‌بندی فنی</h3>",
        _table(("شاخص", "مقدار"), operational),
        "<p>کاربر فعال یعنی کاربری که حداقل یک رویداد قابل‌اندازه‌گیری داشته است. "
        "نبود درخواست یا خطای ثبت‌شده به معنی سالم‌بودن قطعی سرویس نیست؛ "
        "تنها داده‌های ثبت‌شده در دیتابیس گزارش می‌شوند.</p>",
    ])
    if _plain_text_length(html) > MAX_RICH_TEXT_CHARS:
        raise ValueError("Admin rich report exceeds Telegram rich-text limit")
    return {"html": html, "is_rtl": True}


def render_admin_report_fallback(report: BotReport) -> tuple[str, ...]:
    """Send one regular HTML message whenever Telegram's limit permits."""
    sections = render_admin_report(report)
    combined = "\n\n──────────────\n\n".join(sections)
    if len(combined) <= MAX_TELEGRAM_HTML_CHARS:
        return (combined,)
    # Never truncate metrics when native rich transport is unavailable.
    return sections
