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
from jsonschema import FormatChecker, validators
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from flightiran.db.engine import Database
from flightiran.db.models import VisaDatasetState, VisaDestinationData, VisaRuleIndex

from .indexer import index_destination
from .provenance import source_date
from .watch import VisaWatchService

LOGGER = logging.getLogger(__name__)
BASE = "https://travelrequirements.info/data/"
MANIFEST_URL = BASE + "index.json"
SCHEMA_URL = BASE + "schema.json"
MATRIX_URL = BASE + "visa-matrix.csv"
CHANGELOG_URL = BASE + "changelog.json"
MIN_DESTINATIONS = 190
RECHECK_AFTER = timedelta(hours=24)  # Revalidate files daily even if manifest dates stay fixed.


def _canonical_hash(value: dict) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_destination_validator(schema: object):
    """Enforce the *complete* publisher JSON Schema before accepting any records.

    Disallow remote references so upstream schema changes cannot make our
    server resolve an untrusted URL during validation.
    """
    if not isinstance(schema, dict):
        raise ValueError("Visa schema is not a JSON object")

    def check_refs(node: object) -> None:
        if isinstance(node, dict):
            if "$ref" in node:
                raise ValueError("External or unresolved visa schema references are not allowed")
            for value in node.values():
                check_refs(value)
        elif isinstance(node, list):
            for item in node:
                check_refs(item)

    check_refs(schema)
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    if schema.get("type") != "object" or not schema.get("required"):
        raise ValueError("Visa schema does not define required destination fields")
    return cls(schema, format_checker=FormatChecker())


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
    alerts_queued: int = 0

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
            f"هشدار تغییر شرایط ویزا در صف: {self.alerts_queued}",
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
            f"• اعلان تغییر شرایط ویزا در صف: {self.alerts_queued}",
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

                # A schema mismatch must abort the whole sync before any
                # record/index/notification is committed. It is fetched only
                # when at least one destination needs revalidation.
                validator = None
                if jobs:
                    schema_response = await client.get(SCHEMA_URL)
                    schema_response.raise_for_status()
                    validator = _build_destination_validator(schema_response.json())

                semaphore = asyncio.Semaphore(6)

                async def fetch_one(entry: dict) -> tuple[dict, dict, str]:
                    async with semaphore:
                        result = await client.get(entry["url"])
                        result.raise_for_status()
                        document = result.json()
                        if not isinstance(document, dict):
                            raise ValueError(f"Invalid destination JSON for {entry['id']}")
                        if validator is None:
                            raise RuntimeError("Visa schema validation was not initialized")
                        failure = next(validator.iter_errors(document), None)
                        if failure is not None:
                            field = "/".join(map(str, failure.absolute_path)) or "root"
                            raise ValueError(
                                f"Visa schema validation failed for {entry['id']} at {field}: "
                                f"{failure.message[:160]}"
                            )
                        if (
                            document.get("id") != entry["id"]
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
                alerts_queued = 0
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
                            previous = row.raw_data if row.content_hash and row.raw_data else None
                            alerts_queued += await VisaWatchService.enqueue_changes(
                                session, previous, document, entry["iso2"],
                                source_url=entry["url"],
                            )
                            changed.append(entry["id"])
                            row.raw_data = document
                            row.content_hash = digest
                        row.iso2 = entry["iso2"]
                        row.source_url = entry["url"]
                        row.manifest_updated = entry.get("lastUpdated")
                        row.last_fetched_at = now

                        # Replace this destination's complete passport index in
                        # the *same transaction* as raw JSON and watch events.
                        # Upsert alone leaves stale rows for removed passports.
                        indexed = index_destination(document)
                        await session.execute(
                            delete(VisaRuleIndex).where(VisaRuleIndex.destination == entry["iso2"])
                        )
                        for start in range(0, len(indexed), 40):
                            await session.execute(
                                sqlite_insert(VisaRuleIndex).values(indexed[start:start + 40])
                            )
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
                    alerts_queued=alerts_queued,
                )
