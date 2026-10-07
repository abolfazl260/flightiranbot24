"""Versioned visa profiles with stale-content protection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class VisaStatus(StrEnum):
    REQUIRED = "required"
    VISA_FREE = "visa_free"
    E_VISA = "e_visa"
    ON_ARRIVAL = "visa_on_arrival"
    EMBASSY = "embassy"


@dataclass(frozen=True)
class VisaProfile:
    nationality: str
    destination: str
    status: VisaStatus
    required_documents: tuple[str, ...]
    source_url: str
    checked_on: date
    valid_until: date | None = None
    fee: str | None = None
    processing_time: str | None = None
    stay_duration: str | None = None
    passport_validity: str | None = None
    insurance_required: bool | None = None
    return_ticket_required: bool | None = None
    hotel_required: bool | None = None
    version: str = "1"

    @property
    def is_expired(self) -> bool:
        return self.valid_until is not None and self.valid_until < date.today()


class VisaKnowledgeRepository:
    def __init__(self, profiles: list[VisaProfile] | None = None) -> None:
        self._profiles = list(profiles or [])

    def add(self, profile: VisaProfile) -> None:
        self._profiles.append(profile)

    def find(
        self, nationality: str, destination: str, *, include_expired: bool = False
    ) -> VisaProfile | None:
        for profile in reversed(self._profiles):
            if (
                profile.nationality.casefold() == nationality.casefold()
                and profile.destination.casefold() == destination.casefold()
            ):
                if include_expired or not profile.is_expired:
                    return profile
                return None
        return None

    def search(self, query: str) -> list[VisaProfile]:
        normalized = query.casefold()
        return [
            p
            for p in self._profiles
            if normalized in p.destination.casefold() or normalized in p.nationality.casefold()
        ]
