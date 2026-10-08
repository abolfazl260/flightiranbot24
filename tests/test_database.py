import asyncio

import pytest
from sqlalchemy import func, select, text

from flightiran.db import initialize_database
from flightiran.db.models import User
from flightiran.db.repositories import SQLiteUserRepository


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
