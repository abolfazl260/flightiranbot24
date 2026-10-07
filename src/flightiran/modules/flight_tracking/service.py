"""Flight search use case and timezone utilities."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import FlightSearchResult, FlightSearchStatus
from .provider import FlightProvider

_FLIGHT_NUMBER = re.compile(r"^[A-Z0-9]{2,8}$")


def normalize_flight_number(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[\s-]+", "", value).upper()
    return (
        normalized
        if _FLIGHT_NUMBER.fullmatch(normalized) and any(c.isalpha() for c in normalized)
        else None
    )


def timestamp_in_timezone(timestamp: int | float | None, timezone: str) -> datetime | None:
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, tz=ZoneInfo(timezone))
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        return None


class FlightService:
    def __init__(self, provider: FlightProvider, enabled: bool = True) -> None:
        self.provider = provider
        self.enabled = enabled

    async def search(self, query: str | None) -> FlightSearchResult:
        if not self.enabled:
            return FlightSearchResult(
                FlightSearchStatus.DISABLED, message="Flight search is disabled"
            )
        flight_number = normalize_flight_number(query)
        if flight_number is None:
            return FlightSearchResult(
                FlightSearchStatus.INVALID, message="Enter a valid flight number"
            )
        try:
            flight = await self.provider.search(flight_number)
        except Exception as exc:
            return FlightSearchResult(FlightSearchStatus.ERROR, message=str(exc))
        if flight is None:
            return FlightSearchResult(FlightSearchStatus.NOT_FOUND, message="Flight not found")
        return FlightSearchResult(FlightSearchStatus.FOUND, flight=flight)
