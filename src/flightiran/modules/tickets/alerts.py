"""Persistent saved routes and price-drop alert service."""

from __future__ import annotations

import hashlib
import json
from typing import Awaitable, Callable

from sqlalchemy import select

from flightiran.db.engine import Database
from flightiran.db.models import PriceAlert, PriceSnapshot, SavedRoute


class PriceAlertService:
    def __init__(self, database: Database, max_alerts_per_user: int = 20) -> None:
        self.database = database
        self.max_alerts_per_user = max_alerts_per_user

    async def save_route(
        self, user_id: int, origin: str, destination: str, passengers: int = 1
    ) -> SavedRoute:
        async with self.database.session() as session:
            route = SavedRoute(
                user_id=user_id,
                origin=origin.upper(),
                destination=destination.upper(),
                passengers=passengers,
            )
            session.add(route)
            await session.flush()
            return route

    async def create(
        self, user_id: int, route_id: int, target_price: float, currency: str
    ) -> PriceAlert:
        async with self.database.session() as session:
            count = await session.scalar(
                select(PriceAlert.id).where(
                    PriceAlert.user_id == user_id, PriceAlert.status == "active"
                )
            )
            if count is not None:
                active = len(
                    (
                        await session.scalars(
                            select(PriceAlert).where(
                                PriceAlert.user_id == user_id, PriceAlert.status == "active"
                            )
                        )
                    ).all()
                )
                if active >= self.max_alerts_per_user:
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
