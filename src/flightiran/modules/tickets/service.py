"""Ticket search orchestration, sorting and filtering."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol

from .domain import CheapTicketDestination, CheapTicketRoute, TicketOffer, TicketQuery
from .provider import CheapTicketProvider, TicketProvider


class CheapTicketPriceHistory(Protocol):
    async def record_snapshot(
        self,
        samples: list[tuple[str, str, int]],
        *,
        captured_at: datetime,
        retention_days: int,
    ) -> None: ...

    async def get_averages(
        self, route_keys: list[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[float, int]]: ...

    async def get_latest_prices(
        self,
        route_keys: list[tuple[str, str]],
        *,
        before: datetime,
        retention_days: int,
    ) -> dict[tuple[str, str], int]: ...


@dataclass(frozen=True)
class TicketFilters:
    direct_only: bool = False
    baggage_required: bool = False
    max_price: float | None = None
    max_stops: int | None = None


class TicketService:
    def __init__(self, providers: list[TicketProvider]) -> None:
        self.providers = providers

    async def search(
        self, query: TicketQuery, filters: TicketFilters | None = None
    ) -> list[TicketOffer]:
        async def fetch(provider: TicketProvider) -> list[TicketOffer]:
            try:
                return await provider.search(query)
            except Exception:
                return []

        offers = [
            offer
            for batch in await asyncio.gather(*(fetch(p) for p in self.providers))
            for offer in batch
        ]
        filters = filters or TicketFilters()
        if filters.direct_only:
            offers = [offer for offer in offers if offer.stops == 0]
        if filters.baggage_required:
            offers = [offer for offer in offers if offer.baggage]
        if filters.max_price is not None:
            offers = [offer for offer in offers if offer.total_price <= filters.max_price]
        if filters.max_stops is not None:
            offers = [offer for offer in offers if offer.stops <= filters.max_stops]
        return sorted(
            offers, key=lambda offer: (offer.total_price, offer.duration_minutes or 10**9)
        )


def parse_toman_price(value: str) -> int:
    """Convert Persian/Arabic/Latin formatted mz724 price text to integer tomans."""

    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    normalized = value.translate(translation)
    digits = re.sub(r"[^0-9]", "", normalized)
    if not digits:
        raise ValueError(f"Invalid mz724 price: {value!r}")
    return int(digits)


class CheapTicketService:
    """Cheap-ticket feed plus hourly rolling price history."""

    def __init__(
        self,
        provider: CheapTicketProvider,
        price_history: CheapTicketPriceHistory | None = None,
        *,
        retention_days: int = 21,
    ) -> None:
        self.provider = provider
        self.price_history = price_history
        self.retention_days = retention_days

    async def capture_price_snapshot(self) -> int:
        routes = await self.provider.routes()
        samples = self._samples(routes)
        if self.price_history is not None and samples:
            now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            await self.price_history.record_snapshot(
                samples,
                captured_at=now,
                retention_days=self.retention_days,
            )
        return len(samples)

    async def routes(self) -> list[CheapTicketRoute]:
        routes = await self.provider.routes()
        if self.price_history is None:
            return routes

        samples = self._samples(routes)
        keys = [(origin, destination) for origin, destination, _price in samples]
        observed_at = datetime.now(timezone.utc)
        previous_prices = await self.price_history.get_latest_prices(
            keys,
            before=observed_at,
            retention_days=self.retention_days,
        )
        if samples:
            captured_at = observed_at.replace(minute=0, second=0, microsecond=0)
            await self.price_history.record_snapshot(
                samples,
                captured_at=captured_at,
                retention_days=self.retention_days,
            )

        averages = await self.price_history.get_averages(keys)
        enriched: list[CheapTicketRoute] = []
        for route in routes:
            destinations: list[CheapTicketDestination] = []
            for item in route.destinations:
                try:
                    current = parse_toman_price(item.price_toman)
                except ValueError:
                    destinations.append(item)
                    continue
                average = averages.get((route.origin, item.name))
                destinations.append(
                    replace(
                        item,
                        price_value_toman=current,
                        average_price_toman=average[0] if average else None,
                        average_sample_count=average[1] if average else 0,
                        previous_price_toman=previous_prices.get((route.origin, item.name)),
                    )
                )
            enriched.append(replace(route, destinations=tuple(destinations)))
        return enriched

    @staticmethod
    def _samples(routes: list[CheapTicketRoute]) -> list[tuple[str, str, int]]:
        samples: list[tuple[str, str, int]] = []
        for route in routes:
            for item in route.destinations:
                try:
                    price = parse_toman_price(item.price_toman)
                except ValueError:
                    continue
                samples.append((route.origin, item.name, price))
        return samples
