"""Replaceable repository contracts and SQLite implementations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .engine import Database
from .models import (
    AuditLog,
    Mz724PriceSnapshot,
    Mz724RouteAverage,
    User,
    UserPreference,
)


class UserRepository(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...
    async def create(self, telegram_id: int, **fields: str | None) -> User: ...

    async def get_or_create(self, telegram_id: int, **fields: str | None) -> User: ...

    async def set_language(self, user_id: int, language: str) -> None: ...

    async def get_language(self, user_id: int) -> str: ...

    async def get_visa_passport(self, user_id: int) -> str: ...

    async def set_visa_passport(self, user_id: int, passport: str) -> None: ...


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

    async def get_visa_passport(self, user_id: int) -> str:
        async with self.database.session() as session:
            passport = await session.scalar(
                select(UserPreference.visa_passport).where(UserPreference.user_id == user_id)
            )
            return passport or "IR"

    async def set_visa_passport(self, user_id: int, passport: str) -> None:
        passport = passport.upper()
        if len(passport) != 2 or not passport.isascii() or not passport.isalpha():
            raise ValueError("Passport must be a valid two-letter country code")
        async with self.database.session() as session:
            preference = await session.scalar(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            if preference is None:
                session.add(UserPreference(user_id=user_id, visa_passport=passport))
            else:
                preference.visa_passport = passport


class SQLiteAuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def record(
        self, event_type: str, user_id: int | None = None, payload: dict | None = None
    ) -> None:
        async with self.database.session() as session:
            session.add(AuditLog(user_id=user_id, event_type=event_type, payload=payload or {}))


class SQLiteMz724PriceHistoryRepository:
    """Persist one mz724 sample per route/hour and maintain rolling averages."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def record_snapshot(
        self,
        samples: list[tuple[str, str, int]],
        *,
        captured_at: datetime,
        retention_days: int,
    ) -> None:
        cutoff = captured_at - timedelta(days=retention_days)
        async with self.database.session() as session:
            if samples:
                statement = sqlite_insert(Mz724PriceSnapshot).values(
                    [
                        {
                            "origin": origin,
                            "destination": destination,
                            "price_toman": price_toman,
                            "captured_at": captured_at,
                        }
                        for origin, destination, price_toman in samples
                    ]
                )
                statement = statement.on_conflict_do_nothing(
                    index_elements=["origin", "destination", "captured_at"]
                )
                await session.execute(statement)

            await session.execute(
                delete(Mz724PriceSnapshot).where(Mz724PriceSnapshot.captured_at < cutoff)
            )
            await session.flush()

            aggregate_result = await session.execute(
                select(
                    Mz724PriceSnapshot.origin,
                    Mz724PriceSnapshot.destination,
                    func.avg(Mz724PriceSnapshot.price_toman),
                    func.count(Mz724PriceSnapshot.id),
                ).group_by(
                    Mz724PriceSnapshot.origin,
                    Mz724PriceSnapshot.destination,
                )
            )
            aggregates = aggregate_result.all()

            await session.execute(delete(Mz724RouteAverage))
            session.add_all(
                [
                    Mz724RouteAverage(
                        origin=origin,
                        destination=destination,
                        average_price_toman=float(average),
                        sample_count=int(sample_count),
                    )
                    for origin, destination, average, sample_count in aggregates
                ]
            )

    async def get_averages(
        self, route_keys: list[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[float, int]]:
        if not route_keys:
            return {}
        requested = set(route_keys)
        async with self.database.session() as session:
            result = await session.execute(
                select(
                    Mz724RouteAverage.origin,
                    Mz724RouteAverage.destination,
                    Mz724RouteAverage.average_price_toman,
                    Mz724RouteAverage.sample_count,
                )
            )
            return {
                (origin, destination): (float(average), int(sample_count))
                for origin, destination, average, sample_count in result.all()
                if (origin, destination) in requested
            }
