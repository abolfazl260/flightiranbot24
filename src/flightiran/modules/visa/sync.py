"""Synchronize the public TravelRequirements.info dataset into existing SQLite storage.

This is a raw, source-preserving cache, not a visa-eligibility decision engine.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from flightiran.db.engine import Database
from flightiran.db.models import VisaDatasetState, VisaDestinationData, VisaRuleIndex

from .indexer import index_destination
from .provenance import source_date

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
    latest_source_update: str | None = None

    def render(self, *, manual: bool = False, html: bool = False) -> str:
        if html:
            return self._render_html(manual=manual)
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



    def _render_html(self, *, manual: bool) -> str:
        """Clickable admin report with upstream publication and local check dates separated."""
        labels = {"updated": "به‌روزرسانی ثبت شد", "unchanged": "بدون تغییر"}
        result = labels.get(self.status, "همگام‌سازی انجام نشد")
        lines = [
            "<b>🛂 گزارش همگام‌سازی اطلاعات ویزا</b>",
            "━━━━━━━━━━━━━━━━",
            f"<b>نتیجه:</b> {result}",
            f"<b>نوع اجرا:</b> {'دستی /visa_sync' if manual else 'خودکار'}",
            f"<b>نسخه منبع:</b> {escape(self.version or 'نامشخص')}",
            f"<b>زمان بررسی توسط ربات (UTC):</b> {self.checked_at:%Y-%m-%d %H:%M}",
            f"<b>تازه‌ترین تاریخ بروزرسانی فایل‌های منبع:</b> "
            f"{escape(self.latest_source_update or 'اعلام نشده')}",
            "",
            f"• کشورهای موجود در منبع: {self.checked}",
            f"• فایل‌های دریافت‌شده: {self.downloaded}",
            f"• فایل‌های با محتوای تغییرکرده: {len(self.changed)}",
            "",
            "<b>🔗 لینک‌های دریافت اطلاعات</b>",
            f'<a href="{MANIFEST_URL}">مشاهده فهرست و نسخه داده‌ها (JSON)</a>',
            f'<a href="{MATRIX_URL}">دریافت ماتریس ویزا (CSV)</a>',
            f'<a href="{CHANGELOG_URL}">مشاهده تاریخچه تغییرات (JSON)</a>',
        ]
        if self.changed:
            lines.extend(["", "<b>📂 کشورهای تغییرکرده</b>"])
            for slug in self.changed[:10]:
                if re.fullmatch(r"[a-z0-9-]{1,100}", slug):
                    url = f"{BASE}destinations/{slug}.json"
                    lines.append(
                        f'• <a href="{url}">{escape(slug)} — دریافت JSON کشور</a>'
                    )
            if len(self.changed) > 10:
                lines.append(f"و {len(self.changed) - 10} کشور دیگر")
        if self.message:
            lines.extend(["", escape(self.message[:300])])
        lines.extend([
            "",
            'منبع: <a href="https://travelrequirements.info/data/">'
            'TravelRequirements.info</a> · '
            '<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>',
        ])
        # No half-open anchor tags when Telegram message length is exceeded.
        selected: list[str] = []
        length = 0
        for line in lines:
            if length + len(line) + 1 > 3900:
                selected.append("…")
                break
            selected.append(line)
            length += len(line) + 1
        return "\n".join(selected)


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

                source_dates = [
                    verified
                    for entry in entries
                    if isinstance(entry, dict)
                    if (verified := source_date(entry.get("lastUpdated"))) is not None
                ]
                latest_source_update = max(source_dates, default=None)

                async with self.database.session() as session:
                    current = {
                        row.slug: row
                        for row in (await session.scalars(select(VisaDestinationData))).all()
                    }
                    rule_count = int(
                        await session.scalar(
                            select(func.count()).select_from(VisaRuleIndex)
                        ) or 0
                    )
                    needs_index_bootstrap = rule_count < MIN_DESTINATIONS * MIN_DESTINATIONS
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
                        needs_index_bootstrap
                        or previous is None
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
                        # Always re-load in this write session: objects from the
                        # earlier read-only session are detached.
                        row = await session.get(VisaDestinationData, entry["id"])
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

                        # Upsert the 199 indexed passport rows for this country.
                        # Small batches remain compatible with SQLite bind limits.
                        indexed = index_destination(document)
                        for start in range(0, len(indexed), 40):
                            values = indexed[start : start + 40]
                            insert = sqlite_insert(VisaRuleIndex).values(values)
                            excluded = insert.excluded
                            statement = insert.on_conflict_do_update(
                                index_elements=["passport", "destination"],
                                set_={
                                    "country_name": excluded.country_name,
                                    "status": excluded.status,
                                    "stay_days": excluded.stay_days,
                                    "notes": excluded.notes,
                                    "source_url": excluded.source_url,
                                    "verified_on": excluded.verified_on,
                                    "source_level": excluded.source_level,
                                },
                            )
                            await session.execute(statement)
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
                    latest_source_update=latest_source_update,
                )
