"""Provider-independent airport and board models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BoardStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    STALE = "stale"
    ERROR = "error"


@dataclass(frozen=True)
class Airport:
    code: str
    names: dict[str, str]
    country: str
    timezone: str = "UTC"

    def display_name(self, language: str = "en") -> str:
        return self.names.get(language, self.names.get("en", self.code))


@dataclass(frozen=True)
class BoardFlight:
    flight_number: str
    airline: str
    origin: str
    destination: str
    scheduled_at: datetime | None = None
    status: str | None = None
    terminal: str | None = None


@dataclass(frozen=True)
class AirportBoard:
    airport: Airport
    direction: str
    status: BoardStatus
    flights: tuple[BoardFlight, ...] = ()
    checked_at: datetime | None = None
    message: str | None = None
