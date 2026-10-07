"""Ticket provider contract and normalized adapter helper."""

from typing import Protocol

from .domain import TicketOffer, TicketQuery


class TicketProvider(Protocol):
    async def search(self, query: TicketQuery) -> list[TicketOffer]: ...
