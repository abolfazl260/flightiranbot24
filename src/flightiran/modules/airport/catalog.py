"""Config-backed airport catalog and replaceable repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .domain import Airport


class AirportRepository(Protocol):
    def all(self) -> list[Airport]: ...
    def get(self, code: str) -> Airport | None: ...
    def search(self, query: str, language: str = "en") -> list[Airport]: ...


class AirportCatalog:
    def __init__(self, airports: list[Airport]) -> None:
        self._airports = {airport.code.upper(): airport for airport in airports}

    @classmethod
    def from_json(cls, path: Path) -> "AirportCatalog":
        records = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            [
                Airport(
                    code=record["code"].upper(),
                    names=record["names"],
                    country=record.get("country", "IR"),
                    timezone=record.get("timezone", "UTC"),
                )
                for record in records
            ]
        )

    def all(self) -> list[Airport]:
        return list(self._airports.values())

    def get(self, code: str) -> Airport | None:
        return self._airports.get(code.strip().upper())

    def search(self, query: str, language: str = "en") -> list[Airport]:
        normalized = query.strip().casefold()
        return [
            airport
            for airport in self._airports.values()
            if normalized in airport.code.casefold()
            or any(normalized in name.casefold() for name in airport.names.values())
        ]


CatalogAirportRepository = AirportCatalog
