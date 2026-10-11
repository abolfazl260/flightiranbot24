"""Public, cached, read-only price feed for the Android application."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from time import monotonic
from typing import Protocol

from flightiran.modules.tickets.domain import CheapTicketRoute
from flightiran.modules.tickets.service import parse_toman_price

LOGGER = logging.getLogger(__name__)


class TicketRoutes(Protocol):
    async def routes(self) -> list[CheapTicketRoute]: ...


class PublicTicketPriceFeed:
    """Bound upstream demand; never expose raw provider HTML or private user data."""

    def __init__(self, tickets: TicketRoutes, *, ttl_seconds: int = 120) -> None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        self._tickets = tickets
        self._ttl = ttl_seconds
        self._expires_at = 0.0
        self._snapshot: dict[str, object] | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> dict[str, object]:
        if self._snapshot is not None and monotonic() < self._expires_at:
            return self._snapshot
        async with self._lock:
            if self._snapshot is not None and monotonic() < self._expires_at:
                return self._snapshot
            try:
                routes = await self._tickets.routes()
                payload = self._serialize(routes)
            except Exception:
                LOGGER.exception("public_ticket_feed_refresh_failed")
                # A stale snapshot is explicitly marked; do not mislabel an old quote as live.
                if self._snapshot is not None:
                    return {**self._snapshot, "stale": True}
                raise
            self._snapshot = payload
            self._expires_at = monotonic() + self._ttl
            return payload

    @staticmethod
    def _serialize(routes: list[CheapTicketRoute]) -> dict[str, object]:
        origins: list[dict[str, object]] = []
        for route in routes[:150]:
            if not route.origin.strip():
                continue
            destinations: list[dict[str, object]] = []
            for item in route.destinations[:150]:
                if not item.name.strip():
                    continue
                try:
                    price = item.price_value_toman
                    if price is None:
                        price = parse_toman_price(item.price_toman)
                    if price <= 0:
                        continue
                except (ValueError, TypeError):
                    continue
                average = item.average_price_toman
                avg = round(average) if average is not None and average > 0 else None
                difference = round(100 * (price - average) / average, 1) if avg else None
                destinations.append({
                    "name": item.name,
                    "price_toman": price,
                    "average_price_toman": avg,
                    "change_percent": difference,
                    "average_sample_count": max(0, item.average_sample_count),
                })
            if destinations:
                origins.append({"origin": route.origin, "destinations": destinations})
        if not origins:
            raise ValueError("No valid public ticket prices")
        return {
            "currency": "TOMAN",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "stale": False,
            "routes": origins,
        }
