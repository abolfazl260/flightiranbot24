"""Regressions for source fare units and threshold-crossing ticket alerts."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from flightiran.db import initialize_database
from flightiran.db.models import PriceSnapshot, User
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.service import parse_toman_price

ROOT = Path(__file__).resolve().parents[1]


def test_bare_mz724_quotes_are_thousands_of_tomans():
    assert parse_toman_price("20,351") == 20_351_000
    assert parse_toman_price("۱۳,۲۸۲") == 13_282_000
    assert parse_toman_price("7,756") == 7_756_000
    assert parse_toman_price("20,351 هزار تومان") == 20_351_000
    assert parse_toman_price("20,351,000 تومان") == 20_351_000
    assert parse_toman_price("20,351,000") == 20_351_000
    assert parse_toman_price("20,351 تومان") == 20_351
    assert parse_toman_price("203,510,000 ریال") == 20_351_000


@pytest.mark.asyncio
async def test_alert_sends_once_while_below_ceiling_then_rearms(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'threshold.db'}")
    try:
        async with db.session() as session:
            user = User(telegram_id=220)
            session.add(user)
            await session.flush()
            user_id = user.id

        service = PriceAlertService(db)
        route = await service.save_route(user_id, "استانبول", "تهران")
        alert = await service.create(user_id, route.id, 19_800_000, "TOMAN")
        received = []

        async def notify(_alert, snapshot):
            received.append((snapshot.id, snapshot.price, snapshot.snapshot_hash))

        # The 13,282 quote is 13,282,000 tomans, not 13,282 tomans.
        assert await service.process_price(alert.id, parse_toman_price("13,282"), notify)
        assert not await service.process_price(alert.id, parse_toman_price("13,150"), notify)
        assert not await service.process_price(alert.id, parse_toman_price("13,282"), notify)
        assert len(received) == 1

        assert not await service.process_price(alert.id, 20_351_000, notify)
        # Crossing below the threshold again must notify, even at the exact
        # price delivered before the alert was rearmed.
        assert await service.process_price(alert.id, parse_toman_price("13,282"), notify)
        assert len(received) == 2
        assert received[0][0] != received[1][0]
        assert received[0][2] != received[1][2]
        async with db.session() as session:
            snapshots = (await session.scalars(
                select(PriceSnapshot).where(PriceSnapshot.alert_id == alert.id)
            )).all()
            assert len([snapshot for snapshot in snapshots if snapshot.notified]) == 2
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_pct_alert_avoids_duplicate_drop_messages(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'percent.db'}")
    try:
        async with db.session() as session:
            user = User(telegram_id=221)
            session.add(user)
            await session.flush()
            user_id = user.id
        service = PriceAlertService(db)
        route = await service.save_route(user_id, "تهران", "استانبول")
        alert = await service.create_percent(user_id, route.id, 20)
        received = []

        async def notify(_alert, snapshot):
            received.append(snapshot.price)

        async def scan(price):
            return await service.process_price(
                alert.id, price, notify,
                reference_average_toman=20_000_000, average_sample_count=10,
            )

        assert await scan(15_000_000)
        assert not await scan(14_900_000)
        assert not await scan(15_000_000)
        assert received == [15_000_000]
        assert not await scan(17_000_000)
        assert await scan(15_000_000)
        assert received == [15_000_000, 15_000_000]
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_bidirectional_routes_are_not_confused(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'routes.db'}")
    try:
        async with db.session() as session:
            user = User(telegram_id=222)
            session.add(user)
            await session.flush()
            user_id = user.id

        service = PriceAlertService(db)
        forward = await service.save_route(user_id, "تهران", "استانبول")
        reverse = await service.save_route(user_id, "استانبول", "تهران")
        await service.create(user_id, forward.id, 19_800_000, "TOMAN")
        await service.create(user_id, reverse.id, 19_800_000, "TOMAN")
        delivered = []

        async def notify(_id, origin, destination, _alert, snapshot):
            delivered.append((origin, destination, snapshot.price))

        assert await service.process_feed([
            ("تهران", "استانبول", parse_toman_price("20,351")),
            ("استانبول", "تهران", parse_toman_price("13,282")),
        ], notify) == 1
        assert delivered == [("استانبول", "تهران", 13_282_000)]
    finally:
        await db.close()


def test_migration_corrects_history_and_disarms_previously_notified(tmp_path, monkeypatch):
    db_path = tmp_path / "previous.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    alembic = Config(str(ROOT / "alembic.ini"))
    alembic.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic, "0011_default_persian_language")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (telegram_id) VALUES (223)"))
            connection.execute(text(
                "INSERT INTO saved_routes (user_id, origin, destination, passengers) "
                "VALUES (1, 'Istanbul', 'Tehran', 1)"
            ))
            connection.execute(text(
                "INSERT INTO price_alerts (user_id, route_id, target_price, currency, status) "
                "VALUES (1, 1, 19800000, 'TOMAN', 'active')"
            ))
            connection.execute(text(
                "INSERT INTO price_snapshots (alert_id, price, snapshot_hash, notified) "
                "VALUES (1, 13282, 'legacy-hash', 1)"
            ))
            connection.execute(text(
                "INSERT INTO mz724_price_snapshots "
                "(origin, destination, price_toman, captured_at) "
                "VALUES ('Istanbul', 'Tehran', 13282, '2026-10-11 12:00:00')"
            ))
            connection.execute(text(
                "INSERT INTO mz724_route_averages "
                "(origin, destination, average_price_toman, sample_count) "
                "VALUES ('Istanbul', 'Tehran', 14000, 10)"
            ))
    finally:
        engine.dispose()
    command.upgrade(alembic, "head")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text(
                "SELECT price_toman FROM mz724_price_snapshots"
            )) == 13_282_000
            assert connection.scalar(text(
                "SELECT average_price_toman FROM mz724_route_averages"
            )) == 14_000_000
            assert connection.scalar(text(
                "SELECT price FROM price_snapshots"
            )) == 13_282_000
            assert connection.scalar(text(
                "SELECT is_armed FROM price_alerts"
            )) == 0
    finally:
        engine.dispose()
