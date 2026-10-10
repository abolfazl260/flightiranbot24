"""Source-preserving stay allowance and rolling-window rules.

Do not apply a destination's visa-exemption default to embassy visas or
eVisas. Per-passport rules always override the shared default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .catalog import VisaDetail

_BASES = {"per-entry", "rolling", "calendar-year", "per-12-months-from-first-entry"}


def _positive_int(value: object) -> int | None:
    return value if type(value) is int and value > 0 else None


@dataclass(frozen=True)
class StayRule:
    basis: str
    allowance_days: int | None
    window_days: int | None
    resets_on_exit: bool | None
    min_gap_days: int | None
    arrival_day_counts: bool | None
    departure_day_counts: bool | None
    text: str | None
    source: dict[str, Any] | None
    scope: str


def stay_rule_for(detail: VisaDetail) -> StayRule | None:
    """Prefer passport-specific policy and cautiously inherit visa-free defaults.

    The shared destination default describes visa-exempt stays. Applying its
    90/180 quota to a tourist visa with a different stay entitlement would be
    misleading. Non-visa-free statuses therefore require an explicit row rule.
    """
    row_window = detail.record.get("stayWindow")
    if row_window is not None:
        raw, scope = row_window, "passport"
    elif detail.rule.status == "visa-free":
        policy = detail.destination_data.get("visaPolicy") or {}
        raw, scope = policy.get("defaultStayWindow"), "destination"
    else:
        return None

    if not isinstance(raw, dict) or raw.get("basis") not in _BASES:
        return None
    source = raw.get("source")
    text = raw.get("text")
    return StayRule(
        basis=raw["basis"],
        allowance_days=_positive_int(raw.get("allowanceDays")),
        window_days=_positive_int(raw.get("windowDays")),
        resets_on_exit=raw["resetsOnExit"]
        if type(raw.get("resetsOnExit")) is bool else None,
        min_gap_days=raw["minGapDays"]
        if type(raw.get("minGapDays")) is int and raw["minGapDays"] >= 0 else None,
        arrival_day_counts=raw["arrivalDayCounts"]
        if type(raw.get("arrivalDayCounts")) is bool else None,
        departure_day_counts=raw["departureDayCounts"]
        if type(raw.get("departureDayCounts")) is bool else None,
        text=text if isinstance(text, str) and text.strip() else None,
        source=source if isinstance(source, dict) else None,
        scope=scope,
    )
