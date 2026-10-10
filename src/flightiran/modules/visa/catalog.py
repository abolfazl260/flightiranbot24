"""Read-only visa catalog: indexed passport rules and source-preserving details.

Visa flags represent the published dataset, not border approval. Residency,
passport category, purpose and third-country documents require individual checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from flightiran.db.engine import Database
from flightiran.db.models import VisaDatasetState, VisaDestinationData, VisaRuleIndex

# Match the upstream TravelRequirements.info schema; retain legacy statuses
# already persisted in older SQLite snapshots for backwards compatibility.
UPSTREAM_STATUSES = (
    "visa-free",
    "evisa",
    "eta",
    "visa-on-arrival",
    "embassy-visa",
    "freedom-of-movement",
    "banned",
    "unconfirmed",
    "travel-permit",
)
LEGACY_STATUSES = ("e-visa", "visa-required", "refused", "unknown")
STATUSES = UPSTREAM_STATUSES + LEGACY_STATUSES

# These groups are mutually exclusive. The "other" SQL filter also catches
# unknown future upstream statuses, instead of silently dropping destinations.
STATUS_GROUPS = {
    "free": ("visa-free", "freedom-of-movement"),
    "evisa": ("evisa", "e-visa", "eta"),
    "arrival": ("visa-on-arrival",),
    "required": ("embassy-visa", "visa-required"),
    "permit": ("travel-permit",),
    "restricted": ("banned", "refused"),
    "other": ("unconfirmed", "unknown"),
}
assert len(STATUSES) == len(set(STATUSES))
assert set(STATUSES) == {
    item for group in STATUS_GROUPS.values() for item in group
}



@dataclass(frozen=True)
class Country:
    code: str
    name: str


@dataclass(frozen=True)
class VisaRule:
    passport: str
    destination: str
    country_name: str
    status: str
    stay_days: int | None
    notes: str | None
    source_url: str | None
    verified_on: str | None
    source_level: str


@dataclass(frozen=True)
class VisaDetail:
    rule: VisaRule
    destination_data: dict[str, Any]
    record: dict[str, Any]
    visa_types: tuple[dict[str, Any], ...]


class VisaCatalogService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def countries(self) -> list[Country]:
        """Country choices are fetched from the local indexed dataset."""
        async with self.database.session() as session:
            rows = (
                await session.execute(
                    select(VisaRuleIndex.destination, VisaRuleIndex.country_name)
                    .distinct()
                    .order_by(VisaRuleIndex.country_name)
                )
            ).all()
        return [Country(str(code), str(name)) for code, name in rows]

    async def ready(self) -> bool:
        async with self.database.session() as session:
            count = await session.scalar(select(func.count()).select_from(VisaRuleIndex))
            return bool(count and count >= 190 * 190)

    async def dataset_state(self) -> VisaDatasetState | None:
        async with self.database.session() as session:
            return await session.get(VisaDatasetState, 1)

    async def rule(self, passport: str, destination: str) -> VisaRule | None:
        async with self.database.session() as session:
            row = await session.get(
                VisaRuleIndex,
                {"passport": passport.upper(), "destination": destination.upper()},
            )
            return self._rule(row)

    @staticmethod
    def _rule(row: VisaRuleIndex | None) -> VisaRule | None:
        if row is None:
            return None
        return VisaRule(
            row.passport,
            row.destination,
            row.country_name,
            row.status,
            row.stay_days,
            row.notes,
            row.source_url,
            row.verified_on,
            row.source_level,
        )

    async def detail(self, passport: str, destination: str) -> VisaDetail | None:
        passport, destination = passport.upper(), destination.upper()
        async with self.database.session() as session:
            rule_row = await session.get(
                VisaRuleIndex, {"passport": passport, "destination": destination}
            )
            country = (
                await session.scalar(
                    select(VisaDestinationData).where(VisaDestinationData.iso2 == destination)
                )
            )
            if rule_row is None or country is None:
                return None
            document = country.raw_data
        rule = self._rule(rule_row)
        policy = document.get("visaPolicy") or {}
        passport_row = (policy.get("byPassport") or {}).get(passport) or {}
        selected = set(passport_row.get("visaTypes") or [])
        types = tuple(
            item
            for item in document.get("visaTypes") or []
            if isinstance(item, dict) and item.get("id") in selected
        )
        return VisaDetail(rule, document, passport_row, types)

    async def listing(
        self,
        passport: str,
        group: str = "all",
        *,
        page: int = 0,
        page_size: int = 12,
    ) -> tuple[list[VisaRule], int]:
        passport = passport.upper()
        if group not in STATUS_GROUPS and group != "all":
            raise ValueError("Unknown visa grouping")
        if page < 0 or page_size < 1 or page_size > 30:
            raise ValueError("Invalid pagination")
        filters = [VisaRuleIndex.passport == passport]
        if group == "other":
            explicitly_classified = tuple(
                status
                for name, statuses in STATUS_GROUPS.items()
                if name != "other"
                for status in statuses
            )
            filters.append(~VisaRuleIndex.status.in_(explicitly_classified))
        elif group != "all":
            filters.append(VisaRuleIndex.status.in_(STATUS_GROUPS[group]))
        async with self.database.session() as session:
            count = int(
                await session.scalar(
                    select(func.count()).select_from(VisaRuleIndex).where(*filters)
                ) or 0
            )
            rows = (
                await session.scalars(
                    select(VisaRuleIndex)
                    .where(*filters)
                    .order_by(VisaRuleIndex.country_name, VisaRuleIndex.destination)
                    .offset(page * page_size)
                    .limit(page_size)
                )
            ).all()
        return [self._rule(row) for row in rows if row is not None], count

    async def distribution(self, passport: str) -> dict[str, int]:
        async with self.database.session() as session:
            rows = (
                await session.execute(
                    select(VisaRuleIndex.status, func.count())
                    .where(VisaRuleIndex.passport == passport.upper())
                    .group_by(VisaRuleIndex.status)
                )
            ).all()
        return {str(status): int(count) for status, count in rows}
