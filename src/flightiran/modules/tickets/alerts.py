"""Persistent saved routes and price-drop alert service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Awaitable, Callable

from sqlalchemy import delete, func, select

from flightiran.db.engine import Database
from flightiran.db.models import PriceAlert, PriceSnapshot, SavedRoute, User


@dataclass(frozen=True)
class UserPriceAlert:
    id: int
    origin: str
    destination: str
    target_price: int
    status: str


class PriceAlertService:
    def __init__(self, database: Database, max_alerts_per_user: int = 20) -> None:
        self.database = database
        self.max_alerts_per_user = max_alerts_per_user

    async def save_route(
        self, user_id: int, origin: str, destination: str, passengers: int = 1
    ) -> SavedRoute:
        origin, destination = origin.strip(), destination.strip()
        if not origin or not destination or len(origin) > 128 or len(destination) > 128:
            raise ValueError("Invalid route name")
        if passengers < 1:
            raise ValueError("Passengers must be positive")
        async with self.database.session() as session:
            existing = await session.scalar(
                select(SavedRoute).where(
                    SavedRoute.user_id == user_id,
                    SavedRoute.origin == origin,
                    SavedRoute.destination == destination,
                    SavedRoute.passengers == passengers,
                )
            )
            if existing is not None:
                return existing
            route = SavedRoute(
                user_id=user_id, origin=origin, destination=destination, passengers=passengers
            )
            session.add(route)
            await session.flush()
            return route

    async def create(
        self, user_id: int, route_id: int, target_price: float, currency: str
    ) -> PriceAlert:
        if target_price <= 0 or not float(target_price) < float("inf"):
            raise ValueError("Target price must be positive and finite")
        if not currency or len(currency) > 8:
            raise ValueError("Invalid currency")
        async with self.database.session() as session:
            route = await session.get(SavedRoute, route_id)
            if route is None or route.user_id != user_id:
                raise ValueError("Route does not belong to user")
            active = await session.scalar(
                select(func.count(PriceAlert.id)).where(
                    PriceAlert.user_id == user_id, PriceAlert.status == "active"
                )
            )
            if (active or 0) >= self.max_alerts_per_user:
                raise ValueError("price alert limit reached")
            alert = PriceAlert(
                user_id=user_id,
                route_id=route_id,
                target_price=target_price,
                currency=currency,
                status="active",
            )
            session.add(alert)
            await session.flush()
            return alert

    async def set_status(self, alert_id: int, status: str) -> None:
        async with self.database.session() as session:
            alert = await session.get(PriceAlert, alert_id)
            if alert:
                alert.status = status

    async def process_price(
        self,
        alert_id: int,
        price: float,
        notify: Callable[[PriceAlert, PriceSnapshot], Awaitable[None]],
    ) -> bool:
        digest = hashlib.sha256(json.dumps(price).encode()).hexdigest()
        async with self.database.session() as session:
            alert = await session.get(PriceAlert, alert_id)
            if alert is None or alert.status != "active" or alert.last_snapshot_hash == digest:
                return False
            snapshot = await session.scalar(
                select(PriceSnapshot).where(
                    PriceSnapshot.alert_id == alert_id,
                    PriceSnapshot.snapshot_hash == digest,
                )
            )
            if snapshot is not None:
                if snapshot.notified:
                    return False
            else:
                snapshot = PriceSnapshot(
                    alert_id=alert_id, price=price, snapshot_hash=digest, notified=False
                )
                session.add(snapshot)
                await session.flush()
            should_notify = price <= alert.target_price
            if not should_notify:
                alert.last_snapshot_hash = digest
                return False
        try:
            await notify(alert, snapshot)
        except Exception:
            return False
        async with self.database.session() as session:
            stored = await session.get(PriceSnapshot, snapshot.id)
            current_alert = await session.get(PriceAlert, alert_id)
            if stored:
                stored.notified = True
            if current_alert:
                current_alert.last_snapshot_hash = digest
        return True

    async def list_user_alerts(self, user_id: int) -> list[UserPriceAlert]:
        async with self.database.session() as session:
            result = await session.execute(
                select(PriceAlert, SavedRoute)
                .join(SavedRoute, PriceAlert.route_id == SavedRoute.id)
                .where(
                    PriceAlert.user_id == user_id,
                    SavedRoute.user_id == user_id,
                    PriceAlert.status.in_(("active", "paused")),
                )
                .order_by(PriceAlert.id.desc())
            )
            return [
                UserPriceAlert(
                    alert.id, route.origin, route.destination,
                    int(alert.target_price), alert.status
                )
                for alert, route in result.all()
            ]

    async def set_user_status(self, user_id: int, alert_id: int, status: str) -> bool:
        if status not in ("active", "paused"):
            raise ValueError("Invalid alert status")
        async with self.database.session() as session:
            alert = await session.scalar(
                select(PriceAlert).join(SavedRoute, PriceAlert.route_id == SavedRoute.id)
                .where(
                    PriceAlert.id == alert_id,
                    PriceAlert.user_id == user_id,
                    SavedRoute.user_id == user_id,
                )
            )
            if alert is None:
                return False
            if status == "active" and alert.status != "active":
                # Resuming re-arms the price threshold, even at the same price.
                await session.execute(
                    delete(PriceSnapshot).where(PriceSnapshot.alert_id == alert_id)
                )
                alert.last_snapshot_hash = None
            alert.status = status
            return True

    async def delete_user_alert(self, user_id: int, alert_id: int) -> bool:
        async with self.database.session() as session:
            alert = await session.scalar(
                select(PriceAlert).join(SavedRoute, PriceAlert.route_id == SavedRoute.id)
                .where(
                    PriceAlert.id == alert_id,
                    PriceAlert.user_id == user_id,
                    SavedRoute.user_id == user_id,
                )
            )
            if alert is None:
                return False
            await session.delete(alert)
            return True

    async def process_feed(
        self,
        samples: list[tuple[str, str, int]],
        notify: Callable[[int, str, str, PriceAlert, PriceSnapshot], Awaitable[None]],
    ) -> int:
        """Match live mz724 route prices to active TOMAN alerts and deliver once per price."""
        prices = {
            (origin, destination): price
            for origin, destination, price in samples
            if price > 0
        }
        if not prices:
            return 0
        async with self.database.session() as session:
            result = await session.execute(
                select(PriceAlert.id, SavedRoute.origin, SavedRoute.destination, User.telegram_id)
                .join(SavedRoute, PriceAlert.route_id == SavedRoute.id)
                .join(User, PriceAlert.user_id == User.id)
                .where(
                    PriceAlert.status == "active",
                    PriceAlert.currency == "TOMAN",
                    SavedRoute.user_id == PriceAlert.user_id,
                )
            )
            matches = [
                (alert_id, origin, destination, telegram_id, prices[(origin, destination)])
                for alert_id, origin, destination, telegram_id in result.all()
                if (origin, destination) in prices
            ]
        notified = 0
        for alert_id, origin, destination, telegram_id, price in matches:
            async def send(alert: PriceAlert, snapshot: PriceSnapshot) -> None:
                await notify(telegram_id, origin, destination, alert, snapshot)

            if await self.process_price(alert_id, price, send):
                notified += 1
        return notified
