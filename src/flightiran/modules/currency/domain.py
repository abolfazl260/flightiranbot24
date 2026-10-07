"""Normalized currency quote models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class QuoteStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class CurrencyQuote:
    symbol: str
    label: str
    price: float | None
    change_percent: float | None = None
    direction: str = "flat"
    updated_at: datetime | None = None
    source_url: str | None = None
    status: QuoteStatus = QuoteStatus.FRESH
