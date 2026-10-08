"""Regression tests for visa dataset synchronization and admin reporting."""

from datetime import datetime, timezone

from flightiran.modules.visa.sync import (
    BASE,
    VisaSyncResult,
    _canonical_hash,
    _safe_destination_url,
)


def test_canonical_hash_ignores_key_order():
    assert _canonical_hash({"b": 2, "a": 1}) == _canonical_hash({"a": 1, "b": 2})


def test_sync_rejects_external_urls():
    assert _safe_destination_url(BASE + "destinations/turkey.json")
    assert not _safe_destination_url("https://example.com/data/destinations/turkey.json")
    assert not _safe_destination_url("https://travelrequirements.info.evil.com/data/destinations/turkey.json")
    assert not _safe_destination_url("http://travelrequirements.info/data/destinations/turkey.json")


def test_manual_report_has_download_links():
    report = VisaSyncResult(
        status="updated",
        checked=199,
        downloaded=1,
        changed=("turkey",),
        checked_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        version="1.3.0",
    ).render(manual=True)
    assert "/visa_sync" in report
    assert BASE + "destinations/turkey.json" in report
    assert "index.json" in report


def test_hyperlinked_admin_report_separates_published_and_local_dates():
    report = VisaSyncResult(
        status="updated",
        checked=199,
        downloaded=2,
        changed=("turkey",),
        checked_at=datetime(2026, 10, 8, 11, 40, tzinfo=timezone.utc),
        version="1.3.0",
        latest_source_update="2026-10-07",
    ).render(manual=True, html=True)
    assert "<b>🛂 گزارش همگام‌سازی اطلاعات ویزا</b>" in report
    assert "زمان بررسی توسط ربات (UTC)" in report
    assert "2026-10-08 11:40" in report
    assert "تازه‌ترین تاریخ بروزرسانی فایل‌های منبع" in report
    assert "2026-10-07" in report
    assert '<a href="https://travelrequirements.info/data/index.json">' in report
    assert '<a href="https://travelrequirements.info/data/visa-matrix.csv">' in report
    assert '<a href="https://travelrequirements.info/data/destinations/turkey.json">' in report
    assert report.count("<a href=") == report.count("</a>")


def test_unmodified_admin_report_is_explicit_about_unknown_source_date():
    report = VisaSyncResult(
        status="unchanged",
        checked=199,
        downloaded=0,
        changed=(),
        checked_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
        version="1.3.0",
    ).render(manual=False, html=True)
    assert "بدون تغییر" in report
    assert "اعلام نشده" in report
    assert "کشورهای تغییرکرده" not in report
