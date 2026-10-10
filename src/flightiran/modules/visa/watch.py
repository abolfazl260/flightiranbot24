"""User-owned visa subscriptions and semantic-change notification outbox."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from flightiran.db.engine import Database
from flightiran.db.models import User, VisaRuleIndex, VisaWatch, VisaWatchEvent

LOGGER = logging.getLogger(__name__)
MAX_WATCHES = 20
MAX_DELIVERY_ATTEMPTS = 8
RETRY_AFTER = timedelta(minutes=15)

# Only meaningful rule/requirement fields are considered. The source metadata,
# lastVerified, lastUpdated, FAQ, tips, country facts and editorial changes do not
# generate user notifications.
ENTRY_FIELDS = (
    "passportValidity", "onwardTicket", "travelInsurance", "proofOfFunds",
    "vaccinations", "health",
)
VISA_TYPE_FIELDS = (
    "method", "category", "validityDays", "stayDays", "entries", "fee",
    "processing", "documents", "applyUrl",
)
WINDOW_FIELDS = (
    "basis", "allowanceDays", "windowDays", "resetsOnExit",
    "minGapDays", "arrivalDayCounts", "departureDayCounts",
)


def _strip_metadata(value: object) -> object:
    """Preserve substantive published requirements without citation/date churn."""
    if isinstance(value, dict):
        return {
            key: _strip_metadata(item)
            for key, item in sorted(value.items())
            if key not in {"source", "sources", "evidence", "quote", "lastVerified",
                           "lastChanged", "archiveUrl", "unverifiable", "alsoStatedOn"}
        }
    if isinstance(value, list):
        return [_strip_metadata(item) for item in value]
    return value


def _matching_waivers(policy: dict, status: str) -> list[dict]:
    """Select only waiver rules potentially applicable to this status."""
    result = []
    for waiver in policy.get("conditionalWaivers") or []:
        if not isinstance(waiver, dict):
            continue
        applies_to = waiver.get("appliesTo")
        relevant = (
            applies_to in (status, "all")
            or (applies_to == "visa-required" and status in (
                "embassy-visa", "visa-required"
            ))
            or (applies_to == "visa-exempt" and status == "visa-free")
        )
        if relevant:
            result.append(_strip_metadata(waiver))
    return result


def semantic_rule(document: dict, passport: str) -> dict | None:
    policy = document.get("visaPolicy") or {}
    record = (policy.get("byPassport") or {}).get(passport)
    if not isinstance(record, dict):
        return None
    status = record.get("requirement")
    if not isinstance(status, str):
        return None

    # A general visa-exempt stay allowance must not be assigned to visa holders.
    stay_window = record.get("stayWindow")
    if stay_window is None and status == "visa-free":
        stay_window = policy.get("defaultStayWindow")
    window = (
        {key: stay_window.get(key) for key in WINDOW_FIELDS}
        if isinstance(stay_window, dict) else None
    )
    chosen = sorted(set(record.get("visaTypes") or []))
    visa_types = {
        item.get("id"): {
            key: _strip_metadata(item.get(key))
            for key in VISA_TYPE_FIELDS if key in item
        }
        for item in document.get("visaTypes") or []
        if isinstance(item, dict) and item.get("id") in chosen
    }
    entry = document.get("entryRequirements") or {}
    entry_rules = {
        key: _strip_metadata(entry[key])
        for key in ENTRY_FIELDS if key in entry
    }
    return {
        "status": status,
        "stay_days": record.get("maxStayDays"),
        "stay_window": window,
        "valid_until": record.get("validUntil"),
        "extendable_days": record.get("extendableDays"),
        "notes": record.get("notes"),
        "visa_types": visa_types,
        "entry_requirements": entry_rules,
        "conditional_waivers": _matching_waivers(policy, status),
    }


def rule_changes(previous: dict, current: dict) -> tuple[str, ...]:
    categories: list[str] = []
    if previous["status"] != current["status"]:
        categories.append("status")
    if any(previous[key] != current[key] for key in (
        "stay_days", "stay_window", "valid_until", "extendable_days"
    )):
        categories.append("stay")
    if any(previous[key] != current[key] for key in (
        "notes", "visa_types", "entry_requirements", "conditional_waivers"
    )):
        categories.append("conditions")
    return tuple(categories)


def _digest_change(passport: str, destination: str, old: dict, new: dict) -> str:
    serialized = json.dumps(
        [passport, destination, old, new], sort_keys=True,
        ensure_ascii=False, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WatchInfo:
    id: int
    passport: str
    destination: str
    active: bool


@dataclass(frozen=True)
class PendingNotification:
    event_id: int
    telegram_id: int
    passport: str
    destination: str
    payload: dict


class VisaWatchService:
    """Atomic subscriptions, transactional event creation, and retryable delivery."""

    def __init__(self, database: Database, *, max_watches: int = MAX_WATCHES) -> None:
        self.database = database
        self.max_watches = max_watches
        self._delivery_lock = asyncio.Lock()

    async def list_user(self, user_id: int) -> list[WatchInfo]:
        async with self.database.session() as session:
            records = (
                await session.scalars(
                    select(VisaWatch).where(VisaWatch.user_id == user_id)
                    .order_by(VisaWatch.id.desc())
                )
            ).all()
            return [
                WatchInfo(item.id, item.passport, item.destination, item.active)
                for item in records
            ]

    async def subscribe(self, user_id: int, passport: str, destination: str) -> WatchInfo:
        passport, destination = passport.upper(), destination.upper()
        if not all(
            len(value) == 2 and value.isascii() and value.isalpha()
            for value in (passport, destination)
        ):
            raise ValueError("Invalid passport/destination")
        async with self.database.session() as session:
            exists = await session.get(
                VisaRuleIndex, {"passport": passport, "destination": destination}
            )
            if exists is None:
                raise ValueError("No verified route data to follow")
            query = select(VisaWatch).where(
                VisaWatch.user_id == user_id,
                VisaWatch.passport == passport,
                VisaWatch.destination == destination,
            )
            watch = await session.scalar(query)
            if watch is not None and watch.active:
                return WatchInfo(watch.id, passport, destination, True)
            count = await session.scalar(
                select(func.count()).select_from(VisaWatch).where(
                    VisaWatch.user_id == user_id, VisaWatch.active.is_(True)
                )
            )
            if (count or 0) >= self.max_watches:
                raise ValueError("Visa watch limit reached")
            if watch is None:
                statement = sqlite_insert(VisaWatch).values(
                    user_id=user_id, passport=passport, destination=destination,
                    active=True,
                ).on_conflict_do_nothing(
                    index_elements=["user_id", "passport", "destination"]
                )
                await session.execute(statement)
                watch = await session.scalar(query)
                if watch is None:
                    raise RuntimeError("Could not create visa watch")
            else:
                watch.active = True
            return WatchInfo(watch.id, passport, destination, True)

    async def set_active(self, user_id: int, watch_id: int, active: bool) -> bool:
        async with self.database.session() as session:
            watch = await session.scalar(
                select(VisaWatch).where(
                    VisaWatch.id == watch_id, VisaWatch.user_id == user_id
                )
            )
            if watch is None:
                return False
            if active and not watch.active:
                count = await session.scalar(
                    select(func.count()).select_from(VisaWatch).where(
                        VisaWatch.user_id == user_id, VisaWatch.active.is_(True)
                    )
                )
                if (count or 0) >= self.max_watches:
                    raise ValueError("Visa watch limit reached")
            watch.active = active
            return True

    async def remove(self, user_id: int, watch_id: int) -> bool:
        async with self.database.session() as session:
            watch = await session.scalar(
                select(VisaWatch).where(
                    VisaWatch.id == watch_id, VisaWatch.user_id == user_id
                )
            )
            if watch is None:
                return False
            # SQLite foreign_keys is enabled; pending events are deleted as well.
            await session.delete(watch)
            return True

    @staticmethod
    async def enqueue_changes(
        session: AsyncSession,
        previous: dict | None,
        current: dict,
        destination: str,
        *,
        source_url: str,
    ) -> int:
        """Run inside the same database transaction as a successful destination import."""
        if previous is None:
            # The very first import is not an actual rules change for subscribers.
            return 0
        watches = (
            await session.scalars(
                select(VisaWatch).where(
                    VisaWatch.destination == destination, VisaWatch.active.is_(True)
                )
            )
        ).all()
        if not watches:
            return 0
        published = (current.get("meta") or {}).get("lastUpdated")
        created = 0
        for watch in watches:
            old = semantic_rule(previous, watch.passport)
            new = semantic_rule(current, watch.passport)
            if old is None or new is None:
                continue
            categories = rule_changes(old, new)
            if not categories:
                continue
            change_hash = _digest_change(watch.passport, destination, old, new)
            policy = current.get("visaPolicy") or {}
            new_row = (policy.get("byPassport") or {}).get(watch.passport) or {}
            citation = new_row.get("source") or policy.get("defaultSource") or {}
            citation_url = citation.get("url") if isinstance(citation, dict) else None
            payload = {
                "categories": list(categories),
                "before": {
                    "status": old["status"], "stay_days": old["stay_days"]
                },
                "after": {
                    "status": new["status"], "stay_days": new["stay_days"]
                },
                "source_url": source_url,
                "official_source_url": citation_url if isinstance(citation_url, str) else None,
                "published": published if isinstance(published, str) else None,
            }
            statement = sqlite_insert(VisaWatchEvent).values(
                watch_id=watch.id, change_hash=change_hash, payload=payload,
                attempts=0,
            ).on_conflict_do_nothing(index_elements=["watch_id", "change_hash"])
            result = await session.execute(statement)
            created += int(result.rowcount or 0)
        return created

    async def deliver_pending(
        self,
        notify: Callable[[PendingNotification], Awaitable[None]],
        *,
        now: datetime | None = None,
        batch_size: int = 50,
    ) -> int:
        """Retry unsent Telegram messages, with a local lock to avoid overlapping jobs."""
        if self._delivery_lock.locked():
            return 0
        async with self._delivery_lock:
            current = (now or datetime.now(timezone.utc)).replace(tzinfo=None)
            async with self.database.session() as session:
                result = await session.execute(
                    select(VisaWatchEvent, VisaWatch, User.telegram_id)
                    .join(VisaWatch, VisaWatch.id == VisaWatchEvent.watch_id)
                    .join(User, User.id == VisaWatch.user_id)
                    .where(
                        VisaWatch.active.is_(True),
                        VisaWatchEvent.sent_at.is_(None),
                        VisaWatchEvent.attempts < MAX_DELIVERY_ATTEMPTS,
                    )
                    .order_by(VisaWatchEvent.id)
                    .limit(batch_size)
                )
                candidates = [
                    (
                        PendingNotification(
                            event.id, telegram_id, watch.passport,
                            watch.destination, event.payload
                        ),
                        event.last_attempt_at,
                    )
                    for event, watch, telegram_id in result.all()
                ]
            delivered = 0
            for pending, last_attempt in candidates:
                if last_attempt is not None and current - last_attempt < RETRY_AFTER:
                    continue
                try:
                    await notify(pending)
                except Exception as exc:
                    # Do not log Telegram API endpoint strings (bot token may be present).
                    LOGGER.warning(
                        "visa_watch_delivery_failed event=%s kind=%s",
                        pending.event_id, type(exc).__name__,
                    )
                    async with self.database.session() as session:
                        event = await session.get(VisaWatchEvent, pending.event_id)
                        if event is not None and event.sent_at is None:
                            event.attempts += 1
                            event.last_attempt_at = current
                else:
                    async with self.database.session() as session:
                        event = await session.get(VisaWatchEvent, pending.event_id)
                        if event is not None and event.sent_at is None:
                            event.sent_at = current
                            event.last_attempt_at = current
                    delivered += 1
            return delivered
