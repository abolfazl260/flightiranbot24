"""Async SQLite engine setup and database lifecycle helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async engine with SQLite safety pragmas."""
    engine = create_async_engine(database_url, connect_args={"timeout": 30}, pool_pre_ping=True)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


class Database:
    """Database handle exposing sessions without leaking them to handlers."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        await self.engine.dispose()


def create_database(database_url: str) -> Database:
    return Database(create_engine(database_url))


async def initialize_database(database_url: str) -> Database:
    """Prepare the database without racing Alembic migrations.

    Production startup runs ``alembic upgrade head`` before the bot. The
    metadata fallback remains for isolated library/test databases that do not
    have an Alembic version table yet.
    """
    database = create_database(database_url)
    async with database.engine.begin() as connection:
        has_alembic_version = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).has_table("alembic_version")
        )
        if not has_alembic_version:
            await connection.run_sync(Base.metadata.create_all)
    return database
