"""FlightRadar24 adapter and provider contract."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from datetime import timezone as dt_timezone
from typing import Any, Protocol
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flightiran.infrastructure.http import ProviderClient

from .domain import FlightDetails, FlightPosition


class FlightProvider(Protocol):
    async def search(self, flight_number: str) -> FlightDetails | None: ...


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        for key in ("text", "name", "value", "label"):
            if value.get(key) not in (None, ""):
                return str(value[key])
        return None
    return str(value)


def _airport_timezone(airport: dict[str, Any]) -> tzinfo:
    timezone_data = _mapping(airport.get("timezone"))
    name = timezone_data.get("name") or timezone_data.get("tz")
    if name:
        try:
            return ZoneInfo(str(name))
        except ZoneInfoNotFoundError:
            pass
    try:
        return dt_timezone(timedelta(seconds=float(timezone_data.get("offset", 0) or 0)))
    except (TypeError, ValueError, OverflowError):
        return dt_timezone.utc


def _timestamp(value: Any, airport: dict[str, Any]) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=_airport_timezone(airport))
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _image(aircraft: dict[str, Any]) -> str | None:
    images = _mapping(aircraft.get("images"))
    for size in ("large", "medium", "thumbnail"):
        items = images.get(size, [])
        if isinstance(items, dict):
            items = [items]
        if isinstance(items, list):
            for item in items:
                item_map = _mapping(item)
                url = item_map.get("src") or item_map.get("url")
                if url:
                    return str(url)
    return None


class HttpFlightProvider:
    """Fetch and normalize either a compatible endpoint or FR24 responses."""

    def __init__(
        self,
        client: ProviderClient,
        endpoint: str,
        provider_name: str = "flight",
        details_endpoint: str = "https://data-live.flightradar24.com/clickhandler/",
    ) -> None:
        self.client = client
        self.endpoint = endpoint
        self.provider_name = provider_name
        self.details_endpoint = details_endpoint

    async def search(self, flight_number: str) -> FlightDetails | None:
        payload = await self.client.get_json(
            self.endpoint,
            provider=self.provider_name,
            params={"query": flight_number},
            cache_key=f"flight:search:{flight_number}",
        )
        item = payload.get("flight")
        if isinstance(item, dict):
            return self._map(item, flight_number)

        results = payload.get("results")
        if not isinstance(results, list):
            return None
        match = next((candidate for candidate in results if _mapping(candidate).get("id")), None)
        if not match:
            return None
        match = _mapping(match)
        flight_id = str(match["id"])
        detail = await self.client.get_json(
            self.details_endpoint,
            provider=self.provider_name,
            params={"version": "1.5", "flight": flight_id},
            cache_key=f"flight:detail:{flight_id}",
        )
        return self._map_fr24(detail, flight_number, flight_id, match)

    @classmethod
    def _map(cls, item: dict[str, Any], flight_number: str) -> FlightDetails:
        def timestamp(key: str) -> datetime | None:
            value = item.get(key)
            return datetime.fromtimestamp(value, tz=dt_timezone.utc) if value is not None else None

        position = _mapping(item.get("position"))
        return FlightDetails(
            flight_number=flight_number,
            callsign=_text(item.get("callsign")),
            airline=_text(item.get("airline")),
            aircraft=_text(item.get("aircraft")),
            origin=_text(item.get("origin")),
            destination=_text(item.get("destination")),
            origin_terminal=_text(item.get("origin_terminal")),
            destination_terminal=_text(item.get("destination_terminal")),
            scheduled_departure=timestamp("scheduled_departure"),
            actual_departure=timestamp("actual_departure"),
            scheduled_arrival=timestamp("scheduled_arrival"),
            estimated_arrival=timestamp("estimated_arrival"),
            actual_arrival=timestamp("actual_arrival"),
            position=FlightPosition(position.get("latitude"), position.get("longitude"))
            if position
            else None,
            map_url=item.get("map_url"),
            history_url=item.get("history_url"),
        )

    @classmethod
    def _map_fr24(
        cls, detail: dict[str, Any], flight_number: str, flight_id: str, search: dict[str, Any]
    ) -> FlightDetails:
        airport = _mapping(detail.get("airport"))
        origin = _mapping(airport.get("origin"))
        destination = _mapping(airport.get("destination"))
        origin_position = _mapping(origin.get("position"))
        destination_position = _mapping(destination.get("position"))
        origin_region = _mapping(origin_position.get("region"))
        destination_region = _mapping(destination_position.get("region"))
        origin_country = _mapping(origin_position.get("country"))
        destination_country = _mapping(destination_position.get("country"))
        identification = _mapping(detail.get("identification"))
        airline = _mapping(detail.get("airline"))
        aircraft = _mapping(detail.get("aircraft"))
        times = _mapping(detail.get("time"))
        scheduled = _mapping(times.get("scheduled"))
        actual = _mapping(times.get("real"))
        estimated = _mapping(times.get("estimated"))
        search_detail = _mapping(search.get("detail"))
        trail = detail.get("trail")
        point = trail[0] if isinstance(trail, list) and trail and isinstance(trail[0], dict) else {}
        latitude = point.get("lat", search_detail.get("lat", detail.get("latitude")))
        longitude = point.get(
            "lng", point.get("lon", search_detail.get("lon", detail.get("longitude")))
        )
        callsign = _text(identification.get("callsign")) or flight_number
        return FlightDetails(
            flight_number=flight_number,
            callsign=callsign,
            airline=_text(airline.get("name")),
            aircraft=_text(_mapping(aircraft.get("model")).get("text")),
            aircraft_age=aircraft.get("age"),
            aircraft_image=_image(aircraft),
            origin=_text(origin.get("name")),
            destination=_text(destination.get("name")),
            origin_country=_text(origin_country.get("name")),
            destination_country=_text(destination_country.get("name")),
            origin_city=_text(origin_region.get("city")),
            destination_city=_text(destination_region.get("city")),
            origin_airport=_text(origin.get("name")),
            destination_airport=_text(destination.get("name")),
            origin_terminal=_text(_mapping(origin.get("info")).get("terminal")),
            destination_terminal=_text(_mapping(destination.get("info")).get("terminal")),
            scheduled_departure=_timestamp(scheduled.get("departure"), origin),
            actual_departure=_timestamp(actual.get("departure"), origin),
            scheduled_arrival=_timestamp(scheduled.get("arrival"), destination),
            estimated_arrival=_timestamp(estimated.get("arrival"), destination),
            actual_arrival=_timestamp(actual.get("arrival"), destination),
            position=FlightPosition(latitude, longitude)
            if latitude is not None or longitude is not None
            else None,
            map_url=f"https://www.flightradar24.com/{quote(flight_id, safe='')}",
            history_url=f"https://www.flightradar24.com/data/flights/{quote(callsign, safe='')}",
        )
