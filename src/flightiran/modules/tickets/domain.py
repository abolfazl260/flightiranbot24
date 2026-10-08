"""Normalized ticket search models."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TicketQuery:
    origin: str
    destination: str
    departure_date: date
    return_date: date | None = None
    passengers: int = 1

    def __post_init__(self) -> None:
        if not self.origin or not self.destination or self.passengers < 1:
            raise ValueError("origin, destination and passengers are required")
        if self.return_date and self.return_date < self.departure_date:
            raise ValueError("return date must not precede departure date")


@dataclass(frozen=True)
class TicketOffer:
    provider: str
    source_url: str
    price: float
    currency: str
    airline: str
    departure_at: datetime
    arrival_at: datetime
    stops: int = 0
    duration_minutes: int | None = None
    baggage: str | None = None
    refund_policy: str | None = None
    fees: float | None = None

    @property
    def total_price(self) -> float:
        return self.price + (self.fees or 0)


@dataclass(frozen=True)
class CheapTicketDestination:
    """A destination and its advertised price from the cheap-ticket source."""

    name: str
    price_toman: str
    price_value_toman: int | None = None
    average_price_toman: float | None = None
    average_sample_count: int = 0
    previous_price_toman: int | None = None


@dataclass(frozen=True)
class CheapTicketRoute:
    """One origin row and all destinations exposed by the provider."""

    origin: str
    destinations: tuple[CheapTicketDestination, ...]
    source_url: str
