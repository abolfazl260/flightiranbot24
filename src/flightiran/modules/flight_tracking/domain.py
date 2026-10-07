"""Provider-independent flight models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FlightSearchStatus(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass(frozen=True)
class FlightPosition:
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class FlightDetails:
    flight_number: str
    callsign: str | None = None
    airline: str | None = None
    aircraft: str | None = None
    origin: str | None = None
    destination: str | None = None
    origin_terminal: str | None = None
    destination_terminal: str | None = None
    scheduled_departure: datetime | None = None
    actual_departure: datetime | None = None
    scheduled_arrival: datetime | None = None
    estimated_arrival: datetime | None = None
    actual_arrival: datetime | None = None
    position: FlightPosition | None = None


@dataclass(frozen=True)
class FlightSearchResult:
    status: FlightSearchStatus
    flight: FlightDetails | None = None
    message: str | None = None
