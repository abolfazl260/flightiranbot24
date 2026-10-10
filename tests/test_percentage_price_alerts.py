"""Percentage ticket alerts: UI, persistence, 21-day baseline, and privacy."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from flightiran.db import initialize_database
from flightiran.db.migrate import main as run_migration
from flightiran.db.models import Mz724RouteAverage, PriceAlert, PriceSnapshot
from flightiran.db.repositories import (
    SQLiteMz724PriceHistoryRepository,
    SQLiteUserRepository,
)
from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    message_handler,
)
from flightiran.interfaces.telegram.price_alerts import WORDS, percent_keyboard
from flightiran.interfaces.telegram.price_notifications import render_ticket_alert
from flightiran.interfaces.telegram.rich_tickets import (
    render_rich_price_drop_report,
    render_rich_price_tables,
)
from flightiran.interfaces.telegram.tickets import render_cheap_route
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute

ROOT = Path(__file__).resolve().parents[1]


class Query:
    def __init__(self, data):
        self.data = data
        self.calls = []
        self.message = SimpleNamespace(chat_id=123)

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.calls.append((text, kwargs))


class Message:
    def __init__(self, text):
        self.text = text
        self.calls = []

    async def reply_text(self, text, **kwargs):
        self.calls.append((text, kwargs))


class Audit:
    async def record(self, *args, **kwargs):
        pass


class TicketProvider:
    async def routes(self):
        return [CheapTicketRoute(
            "تهران", (CheapTicketDestination("استانبول", "6,000,000"),),
            "https://mz724.ir/",
        )]


def update(*, query=None, message=None, user=42, chat_type="private"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(
            id=user, first_name="Example", last_name=None, username=None,
        ),
        effective_chat=SimpleNamespace(type=chat_type, id=user),
        callback_query=query, message=message,
    )


async def press(data, context, deps, *, user=42, chat_type="private"):
    query = Query(data)
    await callback_handler(
        update(query=query, user=user, chat_type=chat_type), context, deps
    )
    return query


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_percent_selection_buttons_cover_five_to_fifty_only(language):
    buttons = [
        btn for row in percent_keyboard(language).inline_keyboard for btn in row
        if btn.callback_data.startswith("alerts:percent:")
    ]
    assert len(buttons) == 10
    assert [int(b.callback_data.rsplit(":", 1)[1]) for b in buttons] == [
        5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
    ]
    assert "mz724" not in " ".join(str(value) for value in WORDS[language].values())


@pytest.mark.asyncio
async def test_percentage_alert_ui_create_manage_and_isolate_users(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'ui.db'}")
    users = SQLiteUserRepository(db)
    service = PriceAlertService(db)
    deps = TelegramDependencies(
        users=users, audit=Audit(), price_alert_service=service,
        cheap_ticket_service=TicketProvider(),
    )
    ctx = SimpleNamespace(user_data={})
    for data, expected in (
        ("menu:price_alerts", "Ticket price alerts"),
        ("alerts:new", "Select the departure"),
        ("alerts:origin:0", "Select the destination"),
        ("alerts:select:0:0", "Choose the alert type"),
        ("alerts:mode:percent", "up to 50%"),
    ):
        query = await press(data, ctx, deps)
        assert expected in query.calls[-1][0]
    assert ctx.user_data["price_alert_pending"]["step"] == "percent"
    assert len(query.calls[-1][1]["reply_markup"].inline_keyboard) == 6

    # A price text sent during button mode must not create a bogus amount alert.
    response = Message("2000000")
    await message_handler(update(message=response), ctx, deps)
    assert "Choose the alert type" in response.calls[-1][0]
    assert await service.list_user_alerts((await users.get_by_telegram_id(42)).id) == []

    # Reject forgery that tries to bypass the maximum allowed percentage.
    rejected = await press("alerts:percent:51", ctx, deps)
    assert "between 5% and 50%" in rejected.calls[-1][0]
    assert ctx.user_data["price_alert_pending"]["step"] == "percent"
    accepted = await press("alerts:percent:50", ctx, deps)
    assert "at least 50%" in accepted.calls[-1][0]
    assert ctx.user_data.get("price_alert_pending") is None

    owner = await users.get_by_telegram_id(42)
    existing = await service.list_user_alerts(owner.id)
    assert len(existing) == 1
    assert (existing[0].threshold_type, existing[0].target_percent) == ("percent", 50)
    listing = await press("alerts:menu", ctx, deps)
    assert "50% below the 21-day average" in listing.calls[-1][0]
    assert "TOMAN" not in listing.calls[-1][0]

    foreign = await press(f"alerts:delete:{existing[0].id}", ctx, deps, user=43)
    assert "not owned by you" in foreign.calls[-1][0]
    assert len(await service.list_user_alerts(owner.id)) == 1

    await press(f"alerts:toggle:{existing[0].id}", ctx, deps)
    assert (await service.list_user_alerts(owner.id))[0].status == "paused"
    await press(f"alerts:toggle:{existing[0].id}", ctx, deps)
    assert (await service.list_user_alerts(owner.id))[0].status == "active"
    await press(f"alerts:delete:{existing[0].id}", ctx, deps)
    assert await service.list_user_alerts(owner.id) == []
    await db.close()


@pytest.mark.asyncio
async def test_pct_alert_needs_history_then_fires_at_exact_threshold(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'history.db'}")
    user = await SQLiteUserRepository(db).create(700)
    service = PriceAlertService(db)
    route = await service.save_route(user.id, "تهران", "مشهد")
    rule = await service.create_percent(user.id, route.id, 20)
    received = []

    async def notify(telegram_id, origin, destination, alert, snapshot):
        received.append((telegram_id, origin, destination, alert, snapshot))

    feed = [("تهران", "مشهد", 8_000_000)]
    assert await service.process_feed(feed, notify) == 0
    # A single historical observation does not establish a valid average.
    async with db.session() as session:
        session.add(Mz724RouteAverage(
            origin="تهران", destination="مشهد",
            average_price_toman=10_000_000, sample_count=1,
        ))
    assert await service.process_feed(feed, notify) == 0
    async with db.session() as session:
        mean = await session.scalar(select(Mz724RouteAverage))
        mean.sample_count = 2
    assert await service.process_feed([("تهران", "مشهد", 8_000_001)], notify) == 0
    assert await service.process_feed(feed, notify) == 1
    assert await service.process_feed(feed, notify) == 0
    assert len(received) == 1
    assert received[0][0] == 700
    assert received[0][4].reference_average_toman == 10_000_000
    assert "20.0%" in render_ticket_alert(
        "تهران", "مشهد", received[0][3], received[0][4], "en"
    )
    assert await service.process_feed([("تهران", "مشهد", 7_000_000)], notify) == 1
    assert len(received) == 2
    assert await service.set_user_status(user.id, rule.id, "paused")
    assert await service.process_feed([("تهران", "مشهد", 6_000_000)], notify) == 0
    assert await service.set_user_status(user.id, rule.id, "active")
    assert await service.process_feed(feed, notify) == 1
    await db.close()


@pytest.mark.asyncio
async def test_moving_average_can_make_same_price_eligible_later(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'moving.db'}")
    user = await SQLiteUserRepository(db).create(123)
    service = PriceAlertService(db)
    route = await service.save_route(user.id, "ایران", "فرانسه")
    await service.create_percent(user.id, route.id, 30)
    async with db.session() as session:
        session.add(Mz724RouteAverage(
            origin="ایران", destination="فرانسه",
            average_price_toman=10_000_000, sample_count=21,
        ))
    called = []

    async def notify(*args):
        called.append(args)
    sample = [("ایران", "فرانسه", 7_500_000)]
    assert await service.process_feed(sample, notify) == 0
    async with db.session() as session:
        mean = await session.scalar(select(Mz724RouteAverage))
        mean.average_price_toman = 12_000_000
    assert await service.process_feed(sample, notify) == 1
    assert await service.process_feed(sample, notify) == 0
    assert called[0][4].reference_average_toman == 12_000_000
    await db.close()


@pytest.mark.asyncio
async def test_percent_alert_retries_and_invalid_inputs_are_rejected(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'validation.db'}")
    users = SQLiteUserRepository(db)
    user = await users.create(333)
    stranger = await users.create(444)
    service = PriceAlertService(db)
    route = await service.save_route(user.id, "تهران", "دبی")
    for percent in (0, -1, 51, 100, 1.5, True, None):
        with pytest.raises(ValueError):
            await service.create_percent(user.id, route.id, percent)
    with pytest.raises(ValueError, match="belong"):
        await service.create_percent(stranger.id, route.id, 20)
    alert = await service.create_percent(user.id, route.id, 50)
    async with db.session() as session:
        session.add(Mz724RouteAverage(
            origin="تهران", destination="دبی",
            average_price_toman=10_000_000, sample_count=2,
        ))
    calls = []

    async def flaky(_id, _from, _to, _alert, snapshot):
        calls.append(snapshot.id)
        if len(calls) == 1:
            raise RuntimeError("temporary Telegram failure")

    sample = [("تهران", "دبی", 5_000_000)]
    assert await service.process_feed(sample, flaky) == 0
    assert await service.process_feed(sample, flaky) == 1
    assert await service.process_feed(sample, flaky) == 0
    assert calls[0] == calls[1]
    async with db.session() as session:
        row = await session.get(PriceAlert, alert.id)
        assert row.threshold_type == "percent"
        assert row.target_percent == 50
        snapshots = (await session.scalars(
            select(PriceSnapshot).where(PriceSnapshot.alert_id == alert.id)
        )).all()
        assert len(snapshots) == 1 and snapshots[0].notified
    await db.close()


@pytest.mark.asyncio
async def test_percent_rule_uses_existing_21_day_history_storage(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'snapshots.db'}")
    user = await SQLiteUserRepository(db).create(777)
    service = PriceAlertService(db)
    route = await service.save_route(user.id, "شیراز", "استانبول")
    await service.create_percent(user.id, route.id, 20)
    history = SQLiteMz724PriceHistoryRepository(db)
    first = datetime(2026, 10, 9, 8, tzinfo=timezone.utc)
    await history.record_snapshot(
        [("شیراز", "استانبول", 10_000_000)],
        captured_at=first, retention_days=21,
    )
    await history.record_snapshot(
        [("شیراز", "استانبول", 6_000_000)],
        captured_at=first + timedelta(hours=1), retention_days=21,
    )
    average = await history.get_averages([("شیراز", "استانبول")])
    assert average[("شیراز", "استانبول")] == (8_000_000, 2)
    received = []

    async def notify(*args):
        received.append(args)
    assert await service.process_feed(
        [("شیراز", "استانبول", 6_000_000)], notify
    ) == 1
    assert received[0][-1].reference_average_toman == 8_000_000
    await db.close()


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_user_facing_ticket_outputs_never_reveal_provider(language):
    route = CheapTicketRoute(
        "تهران", (
            CheapTicketDestination("مشهد", "7,000,000", 7_000_000, 10_000_000, 30),
        ), "https://mz724.ir/",
    )
    alert = PriceAlert(
        user_id=1, route_id=1, target_price=0, currency="TOMAN",
        threshold_type="percent", target_percent=20,
    )
    sample = PriceSnapshot(
        alert_id=1, price=7_000_000, reference_average_toman=10_000_000,
        snapshot_hash="example", notified=True,
    )
    amount_alert = PriceAlert(
        user_id=1, route_id=1, target_price=8_000_000, currency="TOMAN",
        threshold_type="price",
    )
    messages = [
        render_ticket_alert("تهران", "مشهد", alert, sample, language),
        render_ticket_alert("تهران", "مشهد", amount_alert, sample, language),
        render_cheap_route(route, language=language),
        render_rich_price_tables(route, language=language)[0]["html"],
        *[item["html"] for item in render_rich_price_drop_report(
            [route], language=language
        )],
        *WORDS[language].values(),
    ]
    assert all("mz724" not in message.lower() for message in messages)
    assert any("20" in message for message in messages)
    assert all("https://mz724.ir/" not in message for message in messages)


def test_migration_upgrades_existing_price_alert_rows_without_deleting_data(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "existing.sqlite3"
    url = f"sqlite:///{db_path}"
    alembic = Config(str(ROOT / "alembic.ini"))
    alembic.set_main_option("sqlalchemy.url", url)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    command.upgrade(alembic, "0009_visa_watch_notifications")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO users (telegram_id) VALUES (98765)"))
        conn.execute(text(
            "INSERT INTO saved_routes (user_id, origin, destination, passengers) "
            "VALUES (1, 'Tehran', 'Istanbul', 1)"
        ))
        conn.execute(text(
            "INSERT INTO price_alerts (user_id, route_id, target_price, currency, status) "
            "VALUES (1, 1, 5000000, 'TOMAN', 'active')"
        ))
        conn.execute(text(
            "INSERT INTO price_snapshots (alert_id, price, snapshot_hash, notified) "
            "VALUES (1, 4800000, 'legacy', 1)"
        ))
    engine.dispose()

    run_migration()
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT target_price, threshold_type, target_percent "
                "FROM price_alerts WHERE id=1"
            )).one()
            snapshot = conn.execute(text(
                "SELECT price, reference_average_toman FROM price_snapshots WHERE id=1"
            )).one()
            assert row == (5_000_000, "price", None)
            assert snapshot == (4_800_000, None)
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0011_default_persian_language"
            )
    finally:
        engine.dispose()
