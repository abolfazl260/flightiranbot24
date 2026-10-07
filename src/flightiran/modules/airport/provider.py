"""Provider ports and an adapter that normalizes external payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from flightiran.infrastructure.http import ProviderClient

from .domain import Airport, AirportBoard, BoardFlight, BoardStatus


class AirportProvider(Protocol):
    async def board(self, airport: Airport, direction: str) -> AirportBoard: ...


class HttpAirportProvider:
    """Thin adapter; provider-specific JSON parsing stays here."""

    def __init__(
        self, client: ProviderClient, endpoint: str, provider_name: str = "airport"
    ) -> None:
        self.client = client
        self.endpoint = endpoint
        self.provider_name = provider_name

    async def board(self, airport: Airport, direction: str) -> AirportBoard:
        payload = await self.client.get_json(
            self.endpoint,
            provider=self.provider_name,
            params={"code": airport.code, "direction": direction},
            cache_key=f"airport:{airport.code}:{direction}",
        )
        flights = tuple(self._flight(item) for item in payload.get("flights", []))
        status = (
            BoardStatus(payload.get("status", "ok")) if payload.get("status") else BoardStatus.OK
        )
        return AirportBoard(
            airport=airport,
            direction=direction,
            status=status if flights or status != BoardStatus.OK else BoardStatus.EMPTY,
            flights=flights,
            checked_at=datetime.fromisoformat(payload["checked_at"])
            if payload.get("checked_at")
            else None,
        )

    @staticmethod
    def _flight(item: dict[str, Any]) -> BoardFlight:
        return BoardFlight(
            flight_number=str(item.get("flight_number", "N/A")),
            airline=str(item.get("airline", "N/A")),
            origin=str(item.get("origin", "N/A")),
            destination=str(item.get("destination", "N/A")),
            scheduled_at=datetime.fromisoformat(item["scheduled_at"])
            if item.get("scheduled_at")
            else None,
            status=item.get("status"),
            terminal=item.get("terminal"),
        )
