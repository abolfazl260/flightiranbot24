"""Ticket search orchestration, sorting and filtering."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .domain import CheapTicketRoute, TicketOffer, TicketQuery
from .provider import CheapTicketProvider, TicketProvider


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


class CheapTicketService:
    """Application use case for the menu's cheap-ticket feed."""

    def __init__(self, provider: CheapTicketProvider) -> None:
        self.provider = provider

    async def routes(self) -> list[CheapTicketRoute]:
        return await self.provider.routes()
