"""Public, bounded daily observations using the Telegram /chart repository."""
from __future__ import annotations

import asyncio
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta, timezone
from time import monotonic

from flightiran.db.repositories import RouteDailyMinimum, SQLiteMz724PriceHistoryRepository


def history_document(origin: str, destination: str, points: list[RouteDailyMinimum],
                     *, as_of: date | None = None) -> dict:
    end = as_of or datetime.now(timezone.utc).date()
    start = end - timedelta(days=20)
    values = [p for p in points if start <= p.day <= end and p.min_price_toman > 0]
    values.sort(key=lambda p: p.day)
    if len(values) > 21 or len({p.day for p in values}) != len(values):
        raise ValueError("Invalid daily history")
    observed = max((p.last_captured_at for p in values), default=None)
    return {
        "currency": "TOMAN", "metric": "daily_minimum", "days": 21,
        "origin": origin, "destination": destination, "as_of": end.isoformat(),
        "observed_at": observed.isoformat() if observed else None,
        "points": [{"day": p.day.isoformat(), "price_toman": p.min_price_toman,
                    "sample_count": p.sample_count,
                    "last_observed_at": p.last_captured_at.isoformat()} for p in values],
    }


def with_freshness(document: dict) -> dict:
    observed = document["observed_at"]
    age = ((datetime.now(timezone.utc) - datetime.fromisoformat(observed)).total_seconds()
           if observed else float("inf"))
    return {**document, "stale": age > 10800 or age < -300}


async def public_history_documents(repo: SQLiteMz724PriceHistoryRepository) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = await repo.get_public_daily_minimums(now=now)
    grouped = defaultdict(list)
    for origin, destination, point in rows:
        grouped[(origin, destination)].append(point)
    if len(grouped) > 10000:
        raise ValueError("Too many public history routes")
    return [history_document(o, d, points, as_of=now.date())
            for (o, d), points in grouped.items()]


class PublicTicketHistory:
    def __init__(self, repository: SQLiteMz724PriceHistoryRepository):
        self.repo = repository
        self.cache: OrderedDict = OrderedDict()
        self.lock = asyncio.Lock()

    async def _cached(self, key: tuple, load):
        async with self.lock:
            item = self.cache.get(key)
            if item and monotonic() < item[0]:
                self.cache.move_to_end(key)
                return item[1]
            value = await load()
            self.cache[key] = (monotonic() + 60, value)
            self.cache.move_to_end(key)
            while len(self.cache) > 128:
                self.cache.popitem(last=False)
            return value

    async def routes(self, offset: int = 0) -> dict:
        day = datetime.now(timezone.utc).date().isoformat()
        pairs = await self._cached(("routes", day), self.repo.list_chart_routes)
        return {"routes": [{"origin": o, "destination": d} for o, d in pairs[offset:offset+100]],
                "next_offset": offset+100 if offset+100 < len(pairs) else None}

    async def get(self, origin: str, destination: str) -> dict:
        day = datetime.now(timezone.utc).date().isoformat()
        async def load():
            return history_document(origin, destination,
                await self.repo.get_route_daily_minimums(origin, destination))
        return with_freshness(await self._cached((origin, destination, day), load))
