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

# Conservative and auditable hostname -> jurisdiction mappings. Only these
# hostnames are labeled as a destination or foreign government. Other
# government-typed citations remain "jurisdiction not established", never
# misrepresented as the destination's own immigration authority.
_GOVERNMENT_HOSTS: tuple[tuple[str, str], ...] = (
    ("mfa.gov.tr", "TR"), ("evisa.gov.tr", "TR"), ("gov.tr", "TR"),
    ("mfa.ir", "IR"), ("gov.ir", "IR"),
    ("auswaertiges-amt.de", "DE"), ("bund.de", "DE"), ("gov.de", "DE"),
    ("gov.uk", "GB"), ("state.gov", "US"), ("usa.gov", "US"),
    ("gov.af", "AF"), ("gov.au", "AU"), ("gov.ca", "CA"),
    ("gc.ca", "CA"), ("canada.ca", "CA"), ("gov.az", "AZ"),
    ("gov.ge", "GE"), ("gov.in", "IN"), ("gov.sa", "SA"),
    ("gov.ae", "AE"), ("gov.jp", "JP"), ("mofa.go.jp", "JP"),
    ("gov.sg", "SG"), ("gov.kr", "KR"), ("gov.cn", "CN"),
    ("gov.fr", "FR"), ("gouv.fr", "FR"), ("gov.qa", "QA"),
    ("gov.om", "OM"), ("gov.ru", "RU"), ("gov.pk", "PK"),
)


def source_authority(source: object, destination: str) -> tuple[str, str | None]:
    """Classify by upstream source type and explicit jurisdiction evidence.

    This classifies the *citation*, not the accuracy of an immigration rule.
    """
    if not isinstance(source, dict):
        return "unspecified", None
    kind = source.get("type")
    if kind == "igo":
        return "intergovernmental", None
    if kind == "official-airline-db":
        return "airline_database", None
    if kind != "government":
        return "unspecified", None
    url = safe_source_url(source.get("url"))
    host = urlparse(url).hostname.lower() if url else None
    if host:
        for suffix, country in _GOVERNMENT_HOSTS:
            if host == suffix or host.endswith("." + suffix):
                return (
                    "destination_government" if country == destination.upper()
                    else "foreign_government",
                    country,
                )
    return "government_unverified_jurisdiction", None



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
    authority: str = "unspecified"
    authority_country: str | None = None
    source_type: str | None = None

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
    authority, country = source_authority(source, detail.rule.destination)
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
        authority=authority,
        authority_country=country,
        source_type=source.get("type") if isinstance(source.get("type"), str) else None,
    )
