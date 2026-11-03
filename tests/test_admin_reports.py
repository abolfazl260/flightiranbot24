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
    VisaWatch,
)
from flightiran.interfaces.telegram.admin_report import render_admin_report
from flightiran.interfaces.telegram.admin_report_rich import (
    render_admin_report_fallback,
    render_rich_admin_report,
    render_rich_user_activity_reports,
    render_user_activity_fallback,
)
from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    start_handler,
)
from flightiran.interfaces.telegram.keyboards import main_menu
from flightiran.modules.admin.reports import BotReportRepository, UserActivityRow


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
    first_user = next(u for u in report.user_activity if u.telegram_id == 700123)
    second_user = next(u for u in report.user_activity if u.telegram_id == 800456)
    assert first_user.username == "sensitive_user_name"
    assert first_user.events_total == 1  # system.error is not an interaction.
    assert first_user.active_price_alerts == 1
    assert first_user.active_visa_watches == 0
    assert first_user.last_active_at is not None
    assert second_user.events_total == second_user.active_price_alerts == 0
    assert second_user.last_active_at is None
    private_pages = render_rich_user_activity_reports(report)
    assert len(private_pages) == 1
    assert "sensitive_user_name" in private_pages[0]["html"]
    assert "700123" in private_pages[0]["html"]
    assert "آخرین استفاده" in private_pages[0]["html"]
    assert render_user_activity_fallback(report)

    rich = render_rich_admin_report(report)
    assert rich["is_rtl"] is True
    assert rich["html"].count("<table bordered striped compact>") >= 8
    assert "گزارش جامع" in rich["html"]
    assert "هشدارهای قیمت" in rich["html"]
    assert "سرویس‌دهنده‌ها" in rich["html"]
    assert "ticket.origin.selected" in rich["html"]
    assert "sensitive_user_name" not in rich["html"]
    assert "do-not-show" not in rich["html"]
    assert "700123" not in rich["html"]
    assert len(render_admin_report_fallback(report)) == 1
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


def test_admin_reports_remain_visible_with_mini_app_launch():
    url = "https://flightiran.example.com"
    keyboard = main_menu("fa", web_app_url=url, is_admin=True)
    assert any(
        button.callback_data == "menu:admin_reports"
        for row in keyboard.inline_keyboard for button in row
    )
    assert [
        button.web_app.url
        for row in keyboard.inline_keyboard for button in row
        if button.web_app is not None
    ] == [url]


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
    assert "در دسترس نیست" in query.calls[0][0][0]


@pytest.mark.asyncio
async def test_admin_callback_sends_one_rich_message(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    class FakeReport:
        calls = 0

        async def collect(self):
            self.calls += 1
            return SimpleNamespace()

    report = FakeReport()
    deps = TelegramDependencies(
        users=MemoryUsers(),
        audit=MemoryAudit(),
        admin_chat_id=42,
        admin_reports=report,
    )
    sent = []

    async def fake_send(bot, chat_id, rich):
        sent.append((bot, chat_id, rich))

    monkeypatch.setattr(
        handlers, "render_rich_admin_report",
        lambda data: {"html": "<h3>گزارش جامع</h3>", "is_rtl": True},
    )
    monkeypatch.setattr(handlers, "send_rich_price_table", fake_send)

    query = Query()
    query.data = "menu:admin_reports"
    query.message = Message()
    bot = SimpleNamespace(token="fake")
    await callback_handler(
        _update(42, 42, query=query), SimpleNamespace(bot=bot), deps
    )

    assert report.calls == 1
    assert sent == [(bot, 42, {"html": "<h3>گزارش جامع</h3>", "is_rtl": True})]
    assert query.message.calls == []
    assert query.calls == []  # The old menu is not replaced with a progress message.
    assert deps.audit.events[-1][0] == "admin.report.viewed"


@pytest.mark.asyncio
async def test_admin_report_rich_failure_falls_back_to_one_html_message(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    class FakeReport:
        async def collect(self):
            return SimpleNamespace()

    deps = TelegramDependencies(
        users=MemoryUsers(),
        audit=MemoryAudit(),
        admin_chat_id=42,
        admin_reports=FakeReport(),
    )

    async def cannot_send(*args, **kwargs):
        raise RuntimeError("sendRichMessage unsupported")

    monkeypatch.setattr(handlers, "send_rich_price_table", cannot_send)
    monkeypatch.setattr(
        handlers, "render_rich_admin_report",
        lambda report: {"html": "<h3>گزارش</h3>", "is_rtl": True},
    )
    monkeypatch.setattr(
        handlers, "render_admin_report_fallback",
        lambda report: ("گزارش کامل با <b>قالب HTML</b>",),
    )
    query = Query()
    query.data = "menu:admin_reports"
    query.message = Message()
    await callback_handler(
        _update(42, 42, query=query),
        SimpleNamespace(bot=SimpleNamespace(token="fake")),
        deps,
    )

    assert len(query.message.calls) == 1
    (payload,), options = query.message.calls[0]
    assert "گزارش کامل" in payload
    assert options["parse_mode"] == "HTML"
    assert deps.audit.events[-1][0] == "admin.report.viewed"


def test_rich_admin_report_escapes_database_labels():
    from flightiran.modules.admin.reports import BotReport
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    keys = (
        "users_total", "new_users_24h", "new_users_7d", "new_users_30d",
        "active_users_24h", "active_users_7d", "active_users_30d",
        "audit_total", "events_24h", "events_7d", "events_30d",
        "tracked_routes", "origins", "price_snapshots", "price_samples_24h",
        "saved_routes", "price_alerts", "price_notifications",
        "provider_requests", "failed_provider_7d", "job_runs",
        "failed_jobs_7d", "runtime_errors_7d",
    )
    report = BotReport(
        generated_at=now, counts=dict.fromkeys(keys, 0),
        language_counts=(("fa", 1),),
        top_events=(("<script>alert(1)</script>", 10),),
        top_origins=(("تهران & مشهد", 3),),
        price_alert_status=(("active", 1),),
        provider_status=(("api<provider>", "failed", 1),),
        job_status=(("capture", "success", 3),),
        last_price_capture=None,
    )
    rich = render_rich_admin_report(report)
    assert "&lt;script&gt;" in rich["html"]
    assert "<script>" not in rich["html"]
    assert "تهران &amp; مشهد" in rich["html"]
    assert "api&lt;provider&gt;" in rich["html"]
    assert "هنوز ثبت نشده" in rich["html"]



@pytest.mark.asyncio
async def test_per_user_counts_track_active_price_and_visa_bells_without_duplication(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'users.db'}")
    now = datetime.now(timezone.utc)
    async with db.session() as session:
        first = User(
            telegram_id=45001, username="<bad&handle>",
            first_name="<Ali>", last_active_at=now - timedelta(hours=1),
        )
        idle = User(telegram_id=45002, first_name="Idle")
        session.add_all([first, idle])
        await session.flush()
        route = SavedRoute(user_id=first.id, origin="IKA", destination="MHD")
        session.add(route)
        await session.flush()
        session.add_all([
            AuditLog(user_id=first.id, event_type="user.start",
                     created_at=now - timedelta(days=1)),
            AuditLog(user_id=first.id, event_type="menu.back",
                     created_at=now - timedelta(days=12)),
            AuditLog(user_id=first.id, event_type="user.registered"),
            AuditLog(user_id=first.id, event_type="system.error"),
            PriceAlert(user_id=first.id, route_id=route.id, status="active",
                       target_price=2000, currency="IRR"),
            PriceAlert(user_id=first.id, route_id=route.id, status="active",
                       target_price=4000, currency="IRR"),
            PriceAlert(user_id=first.id, route_id=route.id, status="paused",
                       target_price=5000, currency="IRR"),
            VisaWatch(user_id=first.id, passport="IR", destination="TR", active=True),
            VisaWatch(user_id=first.id, passport="IR", destination="FR", active=False),
        ])
    report = await BotReportRepository(db).collect(now)
    first_user = next(u for u in report.user_activity if u.telegram_id == 45001)
    idle_user = next(u for u in report.user_activity if u.telegram_id == 45002)
    assert (first_user.events_total, first_user.events_7d) == (2, 1)
    assert (first_user.active_price_alerts, first_user.active_visa_watches) == (2, 1)
    assert first_user.last_active_at is not None
    assert first_user.last_active_at.hour == (now - timedelta(hours=1)).hour
    assert (idle_user.events_total, idle_user.events_7d) == (0, 0)
    assert (idle_user.active_price_alerts, idle_user.active_visa_watches) == (0, 0)
    assert idle_user.last_active_at is None
    html = render_rich_user_activity_reports(report)[0]["html"]
    assert "&lt;Ali&gt;" in html
    assert "&lt;bad&amp;handle&gt;" in html
    assert "<Ali>" not in html
    assert "45002" in html
    await db.close()


@pytest.mark.asyncio
async def test_admin_report_delivers_individual_rich_pages_only_to_private_admin(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    now = datetime.now(timezone.utc)
    fake = SimpleNamespace(
        generated_at=now,
        user_activity=(UserActivityRow(
            telegram_id=77, username="tester", first_name="Test", last_name=None,
            events_total=5, events_7d=3, active_price_alerts=2,
            active_visa_watches=1, last_active_at=now,
        ),),
    )

    class FakeReports:
        async def collect(self):
            return fake

    sent = []

    async def fake_send(bot, chat_id, message):
        sent.append((chat_id, message))

    monkeypatch.setattr(
        handlers, "render_rich_admin_report",
        lambda report: {"html": "<h3>گزارش جامع</h3>", "is_rtl": True},
    )
    monkeypatch.setattr(handlers, "send_rich_price_table", fake_send)
    deps = TelegramDependencies(
        users=MemoryUsers(), audit=MemoryAudit(), admin_chat_id=42,
        admin_reports=FakeReports(),
    )
    query = Query()
    query.data = "menu:admin_reports"
    query.message = Message()
    await callback_handler(
        _update(42, 42, query=query),
        SimpleNamespace(bot=SimpleNamespace(token="fake")), deps,
    )
    assert len(sent) == 2
    assert all(chat_id == 42 for chat_id, _ in sent)
    assert "گزارش جامع" in sent[0][1]["html"]
    assert "tester" in sent[1][1]["html"]
    assert query.message.calls == []


def test_user_activity_pages_have_size_limits_and_no_missing_users():
    from flightiran.modules.admin.reports import BotReport

    now = datetime.now(timezone.utc)
    users = tuple(UserActivityRow(
        telegram_id=1000 + i, username=f"user{i}", first_name="Test",
        last_name=None, events_total=i, events_7d=i // 2,
        active_price_alerts=1, active_visa_watches=0,
        last_active_at=now,
    ) for i in range(27))
    report = BotReport(
        generated_at=now, counts={}, language_counts=(), top_events=(),
        top_origins=(), price_alert_status=(), provider_status=(),
        job_status=(), last_price_capture=None, user_activity=users,
    )
    rich_pages = render_rich_user_activity_reports(report)
    fallback_pages = render_user_activity_fallback(report)
    assert len(rich_pages) == len(fallback_pages) == 3
    for i in range(27):
        assert sum(str(1000+i) in p["html"] for p in rich_pages) == 1
    assert all(len(page) < 4096 for page in fallback_pages)
