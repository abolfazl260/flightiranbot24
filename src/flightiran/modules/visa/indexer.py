"""Build flattened, source-aware rule records for fast SQLite lookups."""

from __future__ import annotations

from typing import Any


def index_destination(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract full passport/destination matrix without inferring missing facts."""
    policy = document.get("visaPolicy") or {}
    by_passport = policy.get("byPassport") or {}
    default_source = policy.get("defaultSource") or {}
    names = document.get("names") or {}
    destination = document.get("iso2")
    name = str(names.get("common") or document.get("id") or destination)
    records: list[dict[str, Any]] = []
    for nationality, value in by_passport.items():
        if not isinstance(value, dict) or not isinstance(nationality, str):
            continue
        source = value.get("source") or default_source
        if not isinstance(source, dict):
            source = {}
        duration = value.get("maxStayDays")
        records.append(
            {
                "passport": nationality.upper(),
                "destination": destination,
                "country_name": name[:128],
                "status": str(value.get("requirement") or "unknown")[:40],
                "stay_days": duration if type(duration) is int and duration >= 0 else None,
                "notes": (str(value["notes"]) if value.get("notes") else None),
                "source_url": (str(source["url"])[:512] if source.get("url") else None),
                "verified_on": (
                    str(source["lastVerified"])[:32] if source.get("lastVerified") else None
                ),
                "source_level": "row" if value.get("source") else "policy",
            }
        )
    if len(records) < 190:
        raise ValueError(f"Incomplete visa policy matrix: {destination}")
    return records
