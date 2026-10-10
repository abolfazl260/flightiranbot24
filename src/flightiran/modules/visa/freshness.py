"""Freshness of the bot's last successfully committed visa synchronization.

These timestamps describe local data synchronization, not official rule
verification dates or legal validity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class VisaDataFreshness:
    status: str  # fresh | stale | unknown
    checked_at: datetime | None
    threshold_hours: int

    @property
    def stale(self) -> bool:
        return self.status != "fresh"


def assess_freshness(
    last_success: datetime | None,
    *,
    stale_after_hours: int = 24,
    now: datetime | None = None,
) -> VisaDataFreshness:
    if stale_after_hours < 1:
        raise ValueError("Staleness threshold must be positive")
    if last_success is None:
        return VisaDataFreshness("unknown", None, stale_after_hours)
    checked = (
        last_success.replace(tzinfo=timezone.utc)
        if last_success.tzinfo is None else last_success.astimezone(timezone.utc)
    )
    observed = now or datetime.now(timezone.utc)
    elapsed = observed - checked
    if elapsed < -timedelta(minutes=10):
        return VisaDataFreshness("unknown", checked, stale_after_hours)
    status = "stale" if elapsed > timedelta(hours=stale_after_hours) else "fresh"
    return VisaDataFreshness(status, checked, stale_after_hours)
