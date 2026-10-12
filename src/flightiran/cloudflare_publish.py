"""Publish a strict public projection to Cloudflare without replicating private SQLite.

The application remains the single writer of bot data; only server-side code
holds PUBLISH_TOKEN. A checkpoint avoids re-writing unchanged D1 rows and
resumes safely after a partially failed import.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select

from flightiran.db.engine import Database, create_database
from flightiran.db.models import VisaRuleIndex
from flightiran.db.repositories import SQLiteMz724PriceHistoryRepository
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed

LOGGER = logging.getLogger(__name__)


def validate_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or not value.endswith("/")
    ):
        raise ValueError("CLOUDFLARE_PUBLIC_API_ORIGIN must be a bare HTTPS origin ending in /")
    return value


def encode_public(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def clean_source_url(value: str | None) -> str | None:
    if not isinstance(value, str) or len(value) > 600:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return value


def public_airports() -> dict:
    """The bundled public reference dataset is never sourced from private users."""
    path = files("flightiran").joinpath("modules/airport/data/airports.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "airports": [
            {
                "code": item["code"],
                "country": item["country"],
                "name": item["names"].get("fa") or item["names"]["en"],
                "timezone": item["timezone"],
            }
            for item in raw
        ]
    }


def public_visa_row(row: VisaRuleIndex) -> dict:
    """Explicit field allowlist; never serialize SQLAlchemy models wholesale."""
    notes = row.notes.strip()[:2500] if row.notes else None
    return {
        "passport": row.passport,
        "country_name": row.country_name,
        "status": row.status,
        "stay_days": row.stay_days if row.stay_days is not None and row.stay_days > 0 else None,
        "notes": notes or None,
        "source_url": clean_source_url(row.source_url),
        "verified_on": row.verified_on[:32] if row.verified_on else None,
        "source_level": row.source_level,
    }


async def public_visa_destinations(database: Database) -> dict[str, dict]:
    async with database.session() as session:
        result = await session.scalars(
            select(VisaRuleIndex).order_by(VisaRuleIndex.destination, VisaRuleIndex.passport)
        )
        rows = result.all()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.destination].append(public_visa_row(row))
    # Fail closed while the initial upstream dataset is incomplete.
    if (
        len(grouped) < 190
        or sum(map(len, grouped.values())) < 190 * 190
        or any(len(rules) < 190 for rules in grouped.values())
    ):
        raise ValueError("Visa rules are not fully indexed; refusing partial publication")
    return {dest: {"destination": dest, "rules": rules} for dest, rules in grouped.items()}


async def public_visa_passports(database: Database) -> dict[str, dict]:
    """Compact D1 projection: one public JSON document per passport.

    The original 199×199 SQL projection wrote ~40k D1 table rows plus index
    writes during its first sync; document-by-passport publishes only ~199
    rows. Each document contains the same allowlisted visa facts, with no
    bot users or private subscriptions.
    """
    async with database.session() as session:
        result = await session.scalars(
            select(VisaRuleIndex).order_by(VisaRuleIndex.passport, VisaRuleIndex.destination)
        )
        rows = result.all()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rule = public_visa_row(row)
        rule.pop("passport")
        grouped[row.passport].append({"destination": row.destination, **rule})
    if (
        len(grouped) < 190
        or sum(map(len, grouped.values())) < 190 * 190
        or any(len(rules) < 190 for rules in grouped.values())
    ):
        raise ValueError("Visa rules are not fully indexed; refusing partial publication")
    return {
        passport: {"passport": passport, "rules": rules}
        for passport, rules in grouped.items()
    }


class PublicPublisher:
    def __init__(
        self, database: Database, origin: str, token: str, checkpoint: Path,
        client: httpx.AsyncClient, *, max_visa_destinations_per_day: int = 220,
    ) -> None:
        self.database = database
        self.origin = validate_origin(origin)
        if len(token) < 32:
            raise ValueError("CLOUDFLARE_PUBLISH_TOKEN must contain at least 32 characters")
        self.token = token
        self.client = client
        self.checkpoint = checkpoint
        # Compact snapshots cost about 199 initial D1 rows, not ~40k.
        # Retain a configurable per-UTC-day safety ceiling for the whole account.
        if not 1 <= max_visa_destinations_per_day <= 250:
            raise ValueError("max_visa_destinations_per_day must be between 1 and 250")
        self.max_visa_destinations_per_day = max_visa_destinations_per_day
        self.visa_budget_day = self._utc_day()
        self.visa_published_today = 0
        self._visa_limit_logged_day: str | None = None
        # Version the checkpoint scope across backends. Pre-D1 (R2) uploads
        # must NOT suppress the initial ticket import when the Worker changes.
        self.scope = hashlib.sha256(("d1-v2:" + self.origin).encode()).hexdigest()[:16]
        self.state = self._read_state()

    @staticmethod
    def _utc_day() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_visa_budget_if_needed(self) -> None:
        current = self._utc_day()
        if current != self.visa_budget_day:
            self.visa_budget_day = current
            self.visa_published_today = 0
            self._visa_limit_logged_day = None

    def _read_state(self) -> dict[str, str]:
        try:
            doc = json.loads(self.checkpoint.read_text(encoding="utf-8"))
            if doc.get("scope") == self.scope and isinstance(doc.get("fingerprints"), dict):
                count = doc.get("visa_published_today")
                if (
                    doc.get("visa_budget_day") == self.visa_budget_day
                    and type(count) is int and count >= 0
                ):
                    self.visa_published_today = count
                return doc["fingerprints"]
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        return {}

    def _save(self) -> None:
        self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        staged = self.checkpoint.with_name(self.checkpoint.name + ".tmp")
        staged.write_text(
            json.dumps({
                "scope": self.scope,
                "fingerprints": self.state,
                "visa_budget_day": self.visa_budget_day,
                "visa_published_today": self.visa_published_today,
            }, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        staged.replace(self.checkpoint)

    async def publish(self, key: str, endpoint: str, payload: dict) -> bool:
        data = encode_public(payload)
        digest = hashlib.sha256(data).hexdigest()
        if self.state.get(key) == digest:
            return False
        is_visa = key.startswith("visa:") or key.startswith("visa-passport:")
        if is_visa:
            self._reset_visa_budget_if_needed()
            if self.visa_published_today >= self.max_visa_destinations_per_day:
                if self._visa_limit_logged_day != self.visa_budget_day:
                    LOGGER.warning(
                        "cloudflare_visa_daily_budget_reached day=%s limit=%s; "
                        "remaining visa documents will resume after 00:00 UTC",
                        self.visa_budget_day, self.max_visa_destinations_per_day,
                    )
                    self._visa_limit_logged_day = self.visa_budget_day
                return False
        response = await self.client.post(
            self.origin + endpoint,
            content=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        confirmation = response.json()
        if not isinstance(confirmation, dict) or confirmation.get("published") is not True:
            raise ValueError("Cloudflare import endpoint did not acknowledge publication")
        self.state[key] = digest
        if is_visa:
            self.visa_published_today += 1
        self._save()
        LOGGER.info("cloudflare_published key=%s", key)
        return True

    async def sync_once(self) -> int:
        failed = 0
        jobs: list[tuple[str, str, dict]] = []
        try:
            prices = await PublicTicketPriceFeed(
                SQLiteMz724PriceHistoryRepository(self.database)
            ).get()
            jobs.append(("tickets", "internal/v1/tickets/prices", prices))
        except Exception:
            LOGGER.exception("cloudflare_prices_source_unavailable")
            failed += 1
        try:
            jobs.append(("airports", "internal/v1/airports", public_airports()))
        except Exception:
            LOGGER.exception("cloudflare_airports_source_unavailable")
            failed += 1
        try:
            visa = await public_visa_passports(self.database)
            # The bot defaults to Iranian passports: restore IR quickly after
            # deployment before bulk-publishing the other public documents.
            for passport, payload in sorted(
                visa.items(), key=lambda item: (item[0] != "IR", item[0])
            ):
                jobs.append((
                    f"visa-passport:{passport}",
                    f"internal/v1/visa/passport/{passport}",
                    payload,
                ))
        except Exception:
            LOGGER.exception("cloudflare_visa_source_unavailable")
            failed += 1
        for key, endpoint, payload in jobs:
            try:
                await self.publish(key, endpoint, payload)
            except Exception:
                LOGGER.exception("cloudflare_import_failed key=%s", key)
                failed += 1
        return failed


async def run(*, once: bool, interval_seconds: int) -> int:
    origin = os.environ.get("CLOUDFLARE_PUBLIC_API_ORIGIN", "")
    token = os.environ.get("CLOUDFLARE_PUBLISH_TOKEN", "")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    checkpoint = Path(os.environ.get("CLOUDFLARE_SYNC_CHECKPOINT", "/data/cloudflare-sync.json"))
    # The previous destination-based limit does not apply to compact passport
    # snapshots. A fresh installation can safely import the whole catalog.
    daily_limit = int(os.environ.get("CLOUDFLARE_VISA_PASSPORT_DAILY_LIMIT", "220"))
    database = create_database(database_url)
    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=httpx.Timeout(35),
        ) as client:
            publisher = PublicPublisher(
                database, origin, token, checkpoint, client,
                max_visa_destinations_per_day=daily_limit,
            )
            while True:
                failed = await publisher.sync_once()
                if once:
                    return 1 if failed else 0
                await asyncio.sleep(interval_seconds)
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replicate only public bot data to Cloudflare")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 60 <= args.interval_seconds <= 86400:
        parser.error("interval must be between 60 and 86400 seconds")
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(run(once=args.once, interval_seconds=args.interval_seconds)))


if __name__ == "__main__":
    main()
