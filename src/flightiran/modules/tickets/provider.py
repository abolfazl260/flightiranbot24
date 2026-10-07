"""Ticket provider contract and normalized adapter helper."""

from typing import Protocol

from .domain import CheapTicketRoute, TicketOffer, TicketQuery


class TicketProvider(Protocol):
    async def search(self, query: TicketQuery) -> list[TicketOffer]: ...


class CheapTicketProvider(Protocol):
    async def routes(self) -> list[CheapTicketRoute]: ...
