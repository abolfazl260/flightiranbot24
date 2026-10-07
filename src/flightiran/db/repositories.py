"""Replaceable repository contracts and SQLite implementations."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select

from .engine import Database
from .models import AuditLog, User, UserPreference


class UserRepository(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...
    async def create(self, telegram_id: int, **fields: str | None) -> User: ...

    async def get_or_create(self, telegram_id: int, **fields: str | None) -> User: ...

    async def set_language(self, user_id: int, language: str) -> None: ...

    async def get_language(self, user_id: int) -> str: ...


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

    async def get_or_create(self, telegram_id: int, **fields: str | None) -> User:
        existing = await self.get_by_telegram_id(telegram_id)
        return existing or await self.create(telegram_id, **fields)

    async def set_language(self, user_id: int, language: str) -> None:
        async with self.database.session() as session:
            preference = await session.scalar(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            if preference is None:
                session.add(UserPreference(user_id=user_id, language=language))
            else:
                preference.language = language

    async def get_language(self, user_id: int) -> str:
        async with self.database.session() as session:
            language = await session.scalar(
                select(UserPreference.language).where(UserPreference.user_id == user_id)
            )
            return language or "en"


class SQLiteAuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record(
        self, event_type: str, user_id: int | None = None, payload: dict | None = None
    ) -> None:
        async with self.database.session() as session:
            session.add(AuditLog(user_id=user_id, event_type=event_type, payload=payload or {}))
