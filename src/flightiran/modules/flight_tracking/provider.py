"""Provider port and adapter for flight tracking responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from flightiran.infrastructure.http import ProviderClient

from .domain import FlightDetails, FlightPosition


class FlightProvider(Protocol):
    async def search(self, flight_number: str) -> FlightDetails | None: ...


class HttpFlightProvider:
    def __init__(
        self, client: ProviderClient, endpoint: str, provider_name: str = "flight"
    ) -> None:
        self.client = client
        self.endpoint = endpoint
        self.provider_name = provider_name

    async def search(self, flight_number: str) -> FlightDetails | None:
        payload = await self.client.get_json(
            self.endpoint,
            provider=self.provider_name,
            params={"query": flight_number},
            cache_key=f"flight:{flight_number}",
        )
        item = payload.get("flight")
        if not item:
            return None
        return self._map(item, flight_number)

    @classmethod
    def _map(cls, item: dict[str, Any], flight_number: str) -> FlightDetails:
        def timestamp(key: str) -> datetime | None:
            value = item.get(key)
            return datetime.fromtimestamp(value, tz=timezone.utc) if value is not None else None

        position = item.get("position") or {}
        return FlightDetails(
            flight_number=flight_number,
            callsign=item.get("callsign"),
            airline=item.get("airline"),
            aircraft=item.get("aircraft"),
            origin=item.get("origin"),
            destination=item.get("destination"),
            origin_terminal=item.get("origin_terminal"),
            destination_terminal=item.get("destination_terminal"),
            scheduled_departure=timestamp("scheduled_departure"),
            actual_departure=timestamp("actual_departure"),
            scheduled_arrival=timestamp("scheduled_arrival"),
            estimated_arrival=timestamp("estimated_arrival"),
            actual_arrival=timestamp("actual_arrival"),
            position=FlightPosition(position.get("latitude"), position.get("longitude"))
            if position
            else None,
        )
