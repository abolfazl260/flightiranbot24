import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from flightiran.db import initialize_database
from flightiran.db.models import User
from flightiran.db.repositories import SQLiteMz724PriceHistoryRepository, SQLiteUserRepository


@pytest.mark.asyncio
async def test_database_initializes_and_repository_reads_concurrently(tmp_path) -> None:
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    repository = SQLiteUserRepository(database)
    created = await repository.create(telegram_id=100, username="tester")

    users = await asyncio.gather(*(repository.get_by_telegram_id(100) for _ in range(5)))
    assert created.id is not None
    assert all(user and user.username == "tester" for user in users)

    async with database.engine.connect() as connection:
        journal_mode = await connection.scalar(text("PRAGMA journal_mode"))
        foreign_keys = await connection.scalar(text("PRAGMA foreign_keys"))
    assert str(journal_mode).lower() == "wal"
    assert foreign_keys == 1
    await database.close()


@pytest.mark.asyncio
async def test_failed_write_rolls_back_transaction(tmp_path) -> None:
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'rollback.db'}")
    with pytest.raises(Exception):
        async with database.session() as session:
            session.add(User(telegram_id=1))
            session.add(User(telegram_id=1))
            await session.flush()

    async with database.session() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
    await database.close()



@pytest.mark.asyncio
async def test_previous_valid_route_price_precedes_current_capture(tmp_path) -> None:
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'history.db'}")
    history = SQLiteMz724PriceHistoryRepository(database)
    now = datetime(2026, 10, 8, 10, 15, tzinfo=timezone.utc)
    hour = now.replace(minute=0, second=0, microsecond=0)
    route = ("تهران", "مشهد")

    # Historical rows are ordered per route. Invalid and stale values
    # must not be used as the previous valid comparison.
    await history.record_snapshot(
        [(*route, 12_000)],
        captured_at=hour - timedelta(days=2),
        retention_days=21,
    )
    await history.record_snapshot(
        [(*route, 10_000)],
        captured_at=hour - timedelta(hours=2),
        retention_days=21,
    )
    await history.record_snapshot(
        [(*route, 0)],
        captured_at=hour - timedelta(hours=1),
        retention_days=21,
    )
    prices = await history.get_latest_prices(
        [route, ("شیراز", "کیش")], before=now, retention_days=21
    )
    assert prices == {route: 10_000}

    # The just-fetched fare has not yet been written and must never
    # compare against itself. Later requests can use its saved snapshot.
    await history.record_snapshot(
        [(*route, 8_000)], captured_at=hour, retention_days=21
    )
    later = await history.get_latest_prices(
        [route], before=now + timedelta(minutes=10), retention_days=21
    )
    assert later == {route: 8_000}
    assert await history.get_latest_prices(
        [("missing", "route")], before=now, retention_days=21
    ) == {}

    await database.close()
