"""Database-backed, read-only price feed for the Persian Android application."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from time import monotonic
from typing import Protocol

from flightiran.db.repositories import RecordedTicketBatch

LOGGER = logging.getLogger(__name__)


class StoredTickets(Protocol):
    async def get_latest_prices(self) -> RecordedTicketBatch | None: ...


class PublicTicketPriceFeed:
    """Read only stored prices; never fetch upstream or record a sample from API calls."""

    def __init__(
        self,
        repository: StoredTickets,
        *,
        ttl_seconds: int = 60,
        max_quote_age_seconds: int = 3 * 60 * 60,
    ) -> None:
        if ttl_seconds < 1 or max_quote_age_seconds < 1:
            raise ValueError("Cache lifetime and quote age must be positive")
        self._repository = repository
        self._ttl = ttl_seconds
        self._max_quote_age_seconds = max_quote_age_seconds
        self._expires_at = 0.0
        self._snapshot: dict[str, object] | None = None
        self._lock = asyncio.Lock()

    def _with_freshness(self, payload: dict[str, object], *, failed: bool = False) -> dict:
        # Freshness is re-evaluated even when the JSON is served from API memory.
        observed_at = datetime.fromisoformat(str(payload["observed_at"]))
        age = (datetime.now(timezone.utc) - observed_at).total_seconds()
        return {
            **payload,
            "stale": failed or age > self._max_quote_age_seconds,
        }

    async def get(self) -> dict[str, object]:
        if self._snapshot is not None and monotonic() < self._expires_at:
            return self._with_freshness(self._snapshot)

        async with self._lock:
            if self._snapshot is not None and monotonic() < self._expires_at:
                return self._with_freshness(self._snapshot)
            try:
                batch = await self._repository.get_latest_prices()
                if batch is None or not batch.quotes:
                    raise ValueError("No recorded ticket prices in database")
                self._snapshot = self._serialize(batch)
                self._expires_at = monotonic() + self._ttl
                return self._with_freshness(self._snapshot)
            except Exception:
                LOGGER.exception("stored_ticket_prices_unavailable")
                if self._snapshot is not None:
                    return self._with_freshness(self._snapshot, failed=True)
                raise

    @staticmethod
    def _serialize(batch: RecordedTicketBatch) -> dict[str, object]:
        origins: dict[str, list[dict[str, object]]] = {}
        for item in batch.quotes:
            if (
                not item.origin.strip() or not item.destination.strip()
                or item.price_toman <= 0
            ):
                continue
            if len(origins) >= 150 and item.origin not in origins:
                continue
            destinations = origins.setdefault(item.origin, [])
            if len(destinations) >= 150:
                continue
            avg = item.average_price_toman
            valid_average = avg is not None and avg > 0 and item.sample_count > 0
            destinations.append({
                "name": item.destination,
                "price_toman": item.price_toman,
                "average_price_toman": round(avg) if valid_average else None,
                "change_percent": (
                    round(100 * (item.price_toman - avg) / avg, 1)
                    if valid_average else None
                ),
                "average_sample_count": max(item.sample_count, 0),
            })
        if not origins:
            raise ValueError("Database has no usable ticket quotes")
        return {
            "currency": "TOMAN",
            "observed_at": batch.captured_at.astimezone(timezone.utc).isoformat(),
            "routes": [
                {"origin": city, "destinations": values}
                for city, values in origins.items()
            ],
        }
