"""Synchronize the public TravelRequirements.info dataset into existing SQLite storage.

This is a raw, source-preserving cache, not a visa-eligibility decision engine.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from flightiran.db.engine import Database
from flightiran.db.models import VisaDatasetState, VisaDestinationData

LOGGER = logging.getLogger(__name__)
BASE = "https://travelrequirements.info/data/"
MANIFEST_URL = BASE + "index.json"
MATRIX_URL = BASE + "visa-matrix.csv"
CHANGELOG_URL = BASE + "changelog.json"
MIN_DESTINATIONS = 190
RECHECK_AFTER = timedelta(days=7)


def _canonical_hash(value: dict) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _safe_destination_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == "travelrequirements.info"
        and parsed.path.startswith("/data/destinations/")
        and parsed.path.endswith(".json")
        and not parsed.query
        and not parsed.fragment
    )


@dataclass(frozen=True)
class VisaSyncResult:
    status: str
    checked: int
    downloaded: int
    changed: tuple[str, ...]
    checked_at: datetime
    version: str | None
    message: str = ""

    def render(self, *, manual: bool = False) -> str:
        labels = {"updated": "به‌روزرسانی انجام شد", "unchanged": "تغییری پیدا نشد"}
        heading = labels.get(self.status, "همگام‌سازی انجام نشد")
        lines = [
            f"اطلاعات ویزا — {heading}",
            f"نوع اجرا: {'دستی /visa_sync' if manual else 'خودکار'}",
            f"زمان UTC: {self.checked_at:%Y-%m-%d %H:%M}",
            f"نسخه دیتاست: {self.version or 'نامشخص'}",
            f"کشورهای بررسی‌شده: {self.checked}",
            f"فایل‌های دریافت‌شده: {self.downloaded}",
            f"کشورهای دارای تغییر محتوا: {len(self.changed)}",
            "",
            f"منبع اصلی: {MANIFEST_URL}",
            f"فایل ماتریس: {MATRIX_URL}",
            f"تاریخچه: {CHANGELOG_URL}",
        ]
        if self.changed:
            lines.extend(["", "لینک فایل کشورهای تغییرکرده:"])
            for slug in self.changed[:12]:
                lines.append(f"{slug}: {BASE}destinations/{slug}.json")
            if len(self.changed) > 12:
                lines.append(f"و {len(self.changed) - 12} کشور دیگر")
        if self.message:
            lines.extend(["", self.message[:350]])
        lines.append("")
        lines.append("منبع: TravelRequirements.info (CC BY 4.0)")
        return "\n".join(lines)[:3950]


class VisaSyncService:
    """One synchronizer shared by the scheduler and the admin command."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self._lock = asyncio.Lock()

    async def sync(self) -> VisaSyncResult:
        now = datetime.now(timezone.utc)
        if self._lock.locked():
            return VisaSyncResult("busy", 0, 0, (), now, None, "همگام‌سازی دیگری در حال اجراست.")

        async with self._lock:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0), follow_redirects=False,
                headers={
                    "User-Agent": "FlightIranBot24-VisaSync/1.0",
                    "Accept": "application/json",
                },
            ) as client:
                response = await client.get(MANIFEST_URL)
                response.raise_for_status()
                manifest = response.json()
                entries = manifest.get("destinations")
                if not isinstance(entries, list) or len(entries) < MIN_DESTINATIONS:
                    raise ValueError(
                        "Visa manifest is incomplete or has an invalid destination list"
                    )
                if manifest.get("license", {}).get("spdx") != "CC-BY-4.0":
                    raise ValueError("Unexpected visa dataset licence")
                if len({e.get("id") for e in entries if isinstance(e, dict)}) != len(entries):
                    raise ValueError("Duplicate destination identifiers")

                async with self.database.session() as session:
                    current = {
                        row.slug: row
                        for row in (await session.scalars(select(VisaDestinationData))).all()
                    }
                jobs: list[dict] = []
                for entry in entries:
                    slug = entry.get("id")
                    url = entry.get("url")
                    code = entry.get("iso2")
                    if (
                        not isinstance(slug, str)
                        or not slug
                        or not isinstance(code, str)
                        or len(code) != 2
                        or not isinstance(url, str)
                        or not _safe_destination_url(url)
                        or not url.endswith("/" + slug + ".json")
                    ):
                        raise ValueError("Unsafe or malformed destination in manifest")
                    previous = current.get(slug)
                    previous_check = (
                        previous.last_fetched_at.replace(tzinfo=timezone.utc)
                        if previous and previous.last_fetched_at
                        and previous.last_fetched_at.tzinfo is None
                        else previous.last_fetched_at if previous else None
                    )
                    if (
                        previous is None
                        or previous.manifest_updated != entry.get("lastUpdated")
                        or not previous_check
                        or now - previous_check >= RECHECK_AFTER
                    ):
                        jobs.append(entry)
                if len(current) and len(current) > len(entries):
                    raise ValueError("Manifest contains fewer destinations than stored dataset")

                semaphore = asyncio.Semaphore(6)

                async def fetch_one(entry: dict) -> tuple[dict, dict, str]:
                    async with semaphore:
                        result = await client.get(entry["url"])
                        result.raise_for_status()
                        document = result.json()
                        if (
                            not isinstance(document, dict)
                            or document.get("id") != entry["id"]
                            or document.get("iso2") != entry["iso2"]
                            or not isinstance(
                                document.get("visaPolicy", {}).get("byPassport"), dict
                            )
                            or len(document["visaPolicy"]["byPassport"]) < MIN_DESTINATIONS
                        ):
                            raise ValueError(f"Invalid destination JSON for {entry['id']}")
                        return entry, document, _canonical_hash(document)

                # All downloads/validation complete before writing ANY new version.
                downloaded = await asyncio.gather(*(fetch_one(entry) for entry in jobs))
                changed: list[str] = []
                async with self.database.session() as session:
                    state = await session.get(VisaDatasetState, 1)
                    if state is None:
                        state = VisaDatasetState(id=1, source_url=MANIFEST_URL)
                        session.add(state)
                    for entry, document, digest in downloaded:
                        row = current.get(entry["id"])
                        if row is None:
                            row = VisaDestinationData(slug=entry["id"])
                            session.add(row)
                        if row.content_hash != digest:
                            changed.append(entry["id"])
                            row.raw_data = document
                            row.content_hash = digest
                        row.iso2 = entry["iso2"]
                        row.source_url = entry["url"]
                        row.manifest_updated = entry.get("lastUpdated")
                        row.last_fetched_at = now
                    state.dataset_version = str(manifest.get("version", ""))
                    state.manifest_hash = _canonical_hash(manifest)
                    state.last_checked_at = now
                    if changed:
                        state.last_changed_at = now
                return VisaSyncResult(
                    "updated" if changed else "unchanged",
                    len(entries),
                    len(downloaded),
                    tuple(sorted(changed)),
                    now,
                    str(manifest.get("version", "")),
                )
