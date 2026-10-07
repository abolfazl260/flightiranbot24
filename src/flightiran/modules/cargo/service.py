"""Route/date/capacity matching with explicit state transitions."""

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum


class CargoStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    MATCHED = "matched"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


@dataclass(frozen=True)
class CargoRequest:
    id: int
    user_id: int
    origin: str
    destination: str
    route_date: date
    cargo_type: str
    weight_kg: float
    volume: float
    proposed_price: float
    verified: bool
    status: CargoStatus = CargoStatus.DRAFT


@dataclass(frozen=True)
class CapacityOffer:
    id: int
    user_id: int
    origin: str
    destination: str
    route_date: date
    capacity_kg: float
    verified: bool
    status: CargoStatus = CargoStatus.PUBLISHED


class CargoMarketplace:
    def __init__(self) -> None:
        self.requests: list[CargoRequest] = []
        self.offers: list[CapacityOffer] = []

    def publish_request(self, request: CargoRequest) -> CargoRequest:
        if not request.verified or request.weight_kg <= 0 or not request.cargo_type.strip():
            raise ValueError("verified, complete cargo is required")
        published = replace(request, status=CargoStatus.PUBLISHED)
        self.requests.append(published)
        return published

    def publish_offer(self, offer: CapacityOffer) -> CapacityOffer:
        if not offer.verified or offer.capacity_kg <= 0:
            raise ValueError("verified capacity is required")
        self.offers.append(offer)
        return offer

    def matches(self, request: CargoRequest) -> list[CapacityOffer]:
        return [
            offer
            for offer in self.offers
            if offer.status == CargoStatus.PUBLISHED
            and offer.origin == request.origin
            and offer.destination == request.destination
            and offer.route_date == request.route_date
            and offer.capacity_kg >= request.weight_kg
        ]

    def transition(self, request_id: int, status: CargoStatus) -> CargoRequest:
        for index, request in enumerate(self.requests):
            if request.id == request_id:
                updated = replace(request, status=status)
                self.requests[index] = updated
                return updated
        raise KeyError(request_id)
