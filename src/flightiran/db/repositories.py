"""Replaceable repository contracts and SQLite implementations."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select

from .engine import Database
from .models import AuditLog, User


class UserRepository(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...
    async def create(self, telegram_id: int, **fields: str | None) -> User: ...


class AuditRepository(Protocol):
    async def record(
        self, event_type: str, user_id: int | None = None, payload: dict | None = None
    ) -> None: ...


class SQLiteUserRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self.database.session() as session:
            return await session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def create(self, telegram_id: int, **fields: str | None) -> User:
        async with self.database.session() as session:
            user = User(telegram_id=telegram_id, **fields)
            session.add(user)
            await session.flush()
            return user


class SQLiteAuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record(
        self, event_type: str, user_id: int | None = None, payload: dict | None = None
    ) -> None:
        async with self.database.session() as session:
            session.add(AuditLog(user_id=user_id, event_type=event_type, payload=payload or {}))
