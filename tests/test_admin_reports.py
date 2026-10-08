"""Admin-only report collection, rendering and callback authorization."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from test_telegram import MemoryAudit, MemoryUsers, Message, Query

from flightiran.db import initialize_database
from flightiran.db.models import (
    AuditLog,
    JobRun,
    Mz724PriceSnapshot,
    Mz724RouteAverage,
    PriceAlert,
    PriceSnapshot,
    ProviderRequest,
    SavedRoute,
    User,
    UserPreference,
)
from flightiran.interfaces.telegram.admin_report import render_admin_report
from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    start_handler,
)
from flightiran.interfaces.telegram.keyboards import main_menu
from flightiran.modules.admin.reports import BotReportRepository


@pytest.mark.asyncio
async def test_full_admin_report_aggregates_persisted_metrics_without_personal_data(
    tmp_path,
):
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'report.db'}")
    repository = BotReportRepository(database)
    now = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
    async with database.session() as session:
        first = User(telegram_id=700123, username="sensitive_user_name")
        session.add(first)
        await session.flush()
        session.add(UserPreference(user_id=first.id, language="fa"))
        session.add(User(telegram_id=800456))
        session.add(
            AuditLog(
                user_id=first.id,
                event_type="ticket.origin.selected",
                payload={"origin": "تهران", "secret": "do-not-show"},
            )
        )
        session.add(AuditLog(user_id=first.id, event_type="system.error"))
        saved = SavedRoute(user_id=first.id, origin="IKA", destination="MHD")
        session.add(saved)
        await session.flush()
        session.add(
            PriceAlert(
                user_id=first.id, route_id=saved.id, target_price=5000, currency="IRR"
            )
        )
        session.add(
            Mz724PriceSnapshot(
                origin="تهران",
                destination="مشهد",
                price_toman=5000,
                captured_at=now - timedelta(hours=2),
            )
        )
        session.add(
            Mz724RouteAverage(
                origin="تهران", destination="مشهد",
                average_price_toman=6000, sample_count=2,
            )
        )
        session.add(ProviderRequest(provider="mz724", operation="routes", status="failed"))
        session.add(JobRun(job_name="price-capture", status="failed"))
        await session.flush()

        price_id = (
            await session.scalar(
                __import__("sqlalchemy").select(PriceAlert.id).limit(1)
            )
        )
        session.add(
            PriceSnapshot(
                alert_id=price_id, price=4500, snapshot_hash="test", notified=True
            )
        )

    # The present-day window must include rows inserted by SQLite now().
    report = await repository.collect()
    counts = report.counts
    assert counts["users_total"] == 2
    assert counts["saved_routes"] == 1
    assert counts["tracked_routes"] == 1
    assert counts["origins"] == 1
    assert counts["price_snapshots"] == 1
    assert counts["price_alerts"] == 1
    assert "flight_alerts" not in counts
    assert "flight_deliveries" not in counts
    assert counts["price_notifications"] == 1
    assert counts["provider_requests"] == 1
    assert counts["job_runs"] == 1
    assert ("fa", 1) in report.language_counts
    assert ("تهران", 1) in report.top_origins
    assert ("ticket.origin.selected", 1) in report.top_events
    assert report.last_price_capture is not None

    messages = render_admin_report(report)
    assert len(messages) == 3
    assert all(0 < len(m) < 4096 for m in messages)
    assert "کاربران" in messages[0]
    assert "هشدارهای قیمت" in messages[1]
    assert "هشدارهای پرواز" not in messages[1]
    assert "سرویس‌دهنده" in messages[2]
    combined = "\n".join(messages)
    assert "sensitive_user_name" not in combined
    assert "do-not-show" not in combined
    assert "700123" not in combined
    await database.close()


def test_report_button_visible_only_with_explicit_admin_flag():
    for language in ("fa", "en", "ar"):
        ordinary = main_menu(language)
        admin = main_menu(language, is_admin=True)
        assert not any(
            button.callback_data == "menu:admin_reports"
            for row in ordinary.inline_keyboard for button in row
        )
        assert sum(
            button.callback_data == "menu:admin_reports"
            for row in admin.inline_keyboard for button in row
        ) == 1


def test_admin_reports_appear_alongside_optional_webapp_button():
    keyboard = main_menu(
        "fa", web_app_url="https://flightiran.example.com", is_admin=True
    )
    assert any(
        button.callback_data == "menu:admin_reports"
        for row in keyboard.inline_keyboard for button in row
    )
    assert any(
        button.web_app is not None
        for row in keyboard.inline_keyboard for button in row
    )


def _update(user_id: int, chat_id: int, *, chat_type="private", query=None, message=None):
    user = SimpleNamespace(
        id=user_id, username="test", first_name="Admin", last_name=None
    )
    chat = SimpleNamespace(id=chat_id, type=chat_type)
    return SimpleNamespace(
        effective_user=user, effective_chat=chat,
        callback_query=query, message=message,
    )


@pytest.mark.asyncio
async def test_admin_sees_report_button_on_start_only_in_private_chat():
    deps = TelegramDependencies(
        users=MemoryUsers(), audit=MemoryAudit(), admin_chat_id=42
    )
    for chat_id, chat_type, expected in (
        (42, "private", True),
        (-9000, "supergroup", False),
        (43, "private", False),
    ):
        message = Message()
        await start_handler(_update(42, chat_id, chat_type=chat_type, message=message), None, deps)
        keyboard = message.calls[0][1]["reply_markup"]
        present = any(
            button.callback_data == "menu:admin_reports"
            for row in keyboard.inline_keyboard for button in row
        )
        assert present is expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_id,chat_id,chat_type",
    [
        (999, 999, "private"),  # Ordinary user
        (999, 42, "private"),  # Forged admin-chat identity
        (42, -100123, "supergroup"),  # Admin in a group cannot disclose report
    ],
)
async def test_forged_admin_report_callback_never_queries_or_sends(
    user_id, chat_id, chat_type,
):
    class FakeReport:
        calls = 0

        async def collect(self):
            self.calls += 1
            raise AssertionError("Unauthorized callback accessed report data")

    store = FakeReport()
    deps = TelegramDependencies(
        users=MemoryUsers(),
        audit=MemoryAudit(),
        admin_chat_id=42,
        admin_reports=store,
    )
    query = Query()
    query.data = "menu:admin_reports"
    query.message = Message()
    await callback_handler(
        _update(user_id, chat_id, chat_type=chat_type, query=query),
        None,
        deps,
    )
    assert store.calls == 0
    assert not query.message.calls
    assert "unavailable" in query.calls[0][0][0]


@pytest.mark.asyncio
async def test_admin_callback_sends_three_private_report_sections():
    class FakeReport:
        calls = 0

        async def collect(self):
            self.calls += 1
            return SimpleNamespace()

    fake = FakeReport()
    deps = TelegramDependencies(
        users=MemoryUsers(),
        audit=MemoryAudit(),
        admin_chat_id=42,
        admin_reports=fake,
    )
    from flightiran.interfaces.telegram import handlers

    old_renderer = handlers.render_admin_report
    handlers.render_admin_report = lambda _data: ("first", "second", "third")
    try:
        query = Query()
        query.data = "menu:admin_reports"
        query.message = Message()
        await callback_handler(_update(42, 42, query=query), None, deps)
    finally:
        handlers.render_admin_report = old_renderer

    assert fake.calls == 1
    assert [call[0][0] for call in query.message.calls] == [
        "first", "second", "third"
    ]
    assert all(
        kwargs["parse_mode"] == "HTML"
        for _args, kwargs in query.message.calls
    )
    assert deps.audit.events[-1][0] == "admin.report.viewed"
