"""Upstream visa provenance, dates and safe Telegram hyperlinks.

These dates come only from the published destination JSON/source citations.
Never substitute the bot's own download/import timestamp for a verification date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html import escape
from urllib.parse import urlparse

from .catalog import VisaDetail

_DESTINATION_SLUG = re.compile(r"^[a-z0-9-]{1,100}$")


def source_date(value: object) -> str | None:
    """Return a real ISO calendar date, or None when upstream does not supply one."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def safe_source_url(value: object) -> str | None:
    """Only allow genuine HTTPS links, without embedded credentials or unsafe tags."""
    if not isinstance(value, str) or len(value) > 900:
        return None
    value = value.strip()
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or any(ord(char) < 32 for char in value)
    ):
        return None
    return value


def link_html(value: object, label: str) -> str:
    url = safe_source_url(value)
    if url is None:
        return ""
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


@dataclass(frozen=True)
class VisaProvenance:
    source_url: str | None
    source_name: str | None
    source_verified_on: str | None
    source_changed_on: str | None
    destination_updated_on: str | None
    last_full_review_on: str | None
    destination_json_url: str | None
    source_level: str
    source_unverifiable: bool = False

    @property
    def verified_is_stale(self) -> bool:
        if not self.source_verified_on:
            return False
        return (date.today() - date.fromisoformat(self.source_verified_on)).days > 30


def visa_provenance(detail: VisaDetail) -> VisaProvenance:
    """Prefer passport-specific source, then the shared destination-policy citation."""
    data = detail.destination_data or {}
    policy = data.get("visaPolicy") or {}
    record_source = detail.record.get("source")
    default_source = policy.get("defaultSource")
    candidate = record_source if isinstance(record_source, dict) else default_source
    source = candidate if isinstance(candidate, dict) else {}
    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    slug = data.get("id")
    original_url = (
        f"https://travelrequirements.info/data/destinations/{slug}.json"
        if isinstance(slug, str) and _DESTINATION_SLUG.fullmatch(slug)
        else None
    )
    return VisaProvenance(
        source_url=safe_source_url(source.get("url") or detail.rule.source_url),
        source_name=source.get("name") if isinstance(source.get("name"), str) else None,
        source_verified_on=(
            source_date(source.get("lastVerified"))
            or source_date(detail.rule.verified_on)
        ),
        source_changed_on=source_date(source.get("lastChanged")),
        destination_updated_on=source_date(meta.get("lastUpdated")),
        last_full_review_on=source_date(meta.get("lastFullReview")),
        destination_json_url=original_url,
        source_level=detail.rule.source_level,
        source_unverifiable=bool(source.get("unverifiable")),
    )
