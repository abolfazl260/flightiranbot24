"""Persistent flight alert lifecycle and idempotent snapshot processing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import select

from flightiran.db.engine import Database
from flightiran.db.models import FlightAlert, FlightAlertEvent


class AlertService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def create(self, user_id: int, flight_number: str, event_types: list[str]) -> FlightAlert:
        async with self.database.session() as session:
            alert = FlightAlert(
                user_id=user_id, flight_number=flight_number, event_types=event_types
            )
            session.add(alert)
            await session.flush()
            return alert

    async def list(self, user_id: int) -> list[FlightAlert]:
        async with self.database.session() as session:
            return list(
                (
                    await session.scalars(select(FlightAlert).where(FlightAlert.user_id == user_id))
                ).all()
            )

    async def _set_status(self, alert_id: int, status: str) -> None:
        async with self.database.session() as session:
            alert = await session.get(FlightAlert, alert_id)
            if alert:
                alert.status = status

    async def pause(self, alert_id: int) -> None:
        await self._set_status(alert_id, "paused")

    async def resume(self, alert_id: int) -> None:
        await self._set_status(alert_id, "active")

    async def delete(self, alert_id: int) -> None:
        await self._set_status(alert_id, "deleted")

    async def process_snapshot(
        self,
        alert_id: int,
        snapshot: dict,
        notify: Callable[[FlightAlert, FlightAlertEvent], Awaitable[None]],
    ) -> bool:
        digest = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        async with self.database.session() as session:
            alert = await session.get(FlightAlert, alert_id)
            if alert is None or alert.status != "active" or alert.last_snapshot_hash == digest:
                return False
            if alert.last_snapshot_hash is None:
                alert.last_snapshot_hash = digest
                return False
            event = FlightAlertEvent(
                alert_id=alert.id,
                event_type=snapshot.get("event_type", "schedule_change"),
                snapshot_hash=digest,
                delivery_status="pending",
            )
            session.add(event)
            alert.last_snapshot_hash = digest
            await session.flush()
        try:
            await notify(alert, event)
        except Exception as exc:
            async with self.database.session() as session:
                stored = await session.get(FlightAlertEvent, event.id)
                if stored:
                    stored.delivery_status = "failed"
                    stored.error_message = str(exc)
            return False
        async with self.database.session() as session:
            stored = await session.get(FlightAlertEvent, event.id)
            if stored:
                stored.delivery_status = "delivered"
                stored.delivered_at = datetime.now(timezone.utc)
        return True
