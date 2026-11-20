"""User-scoped in-widget route pickers and 21-day recorded fare history.

Every selection is revalidated against SQLite's existing daily-minimum
repository; widget requests never scrape providers, create bookings or
infer prices on missing dates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from flightiran.db.repositories import RouteDailyMinimum

LOGGER = logging.getLogger(__name__)
CHART_DAYS = 21
_PAGE_SIZE = 6
_ACTION = re.compile(
    r"(?:fare:origins:\d{1,3}|fare:origin:[a-f0-9]{10}"
    r"|fare:destinations:[a-f0-9]{10}:\d{1,3}"
    r"|fare:route:[a-f0-9]{10}:[a-f0-9]{10})\Z"
)


def route_key(value: str) -> str:
    """Bound city names to an opaque fixed-width request identifier."""
    return hashlib.blake2s(value.encode("utf-8"), digest_size=5).hexdigest()


def _state(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(raw.encode("utf-8")) > 1024:
        raise ValueError("Telegram widget state exceeds 1024 bytes")
    return raw


def _lookup(names: list[str], key: str) -> str | None:
    matches = [name for name in names if route_key(name) == key]
    return matches[0] if len(matches) == 1 else None


def _menu(view: str, names: list[str], page: int, *, origin: str | None = None) -> str:
    names = sorted(set(names))
    pages = max(1, (len(names) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = min(page, pages - 1)
    choices = names[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]
    result = {
        "view": view,
        "page": page,
        "pages": pages,
        "options": [{"n": name[:36], "k": route_key(name)} for name in choices],
    }
    if origin is not None:
        result["o"] = origin[:36]
        result["ok"] = route_key(origin)
    # A long city label must not fail the whole widget or exceed Telegram limits.
    while True:
        try:
            return _state(result)
        except ValueError:
            if not result["options"]:
                raise
            result["options"].pop()


def chart_state(
    origin: str,
    destination: str,
    samples: list[RouteDailyMinimum],
    *,
    now: datetime | None = None,
) -> str:
    """Render only actual UTC daily minima, never interpolated history."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("Naive chart time")
    today = instant.astimezone(timezone.utc).date()
    start = today - timedelta(days=CHART_DAYS - 1)
    daily = {}
    for sample in samples:
        if (
            start <= sample.day <= today
            and type(sample.min_price_toman) is int
            and sample.min_price_toman > 0
            and type(sample.sample_count) is int
            and sample.sample_count > 0
        ):
            current = daily.get(sample.day)
            if current is None or sample.min_price_toman < current.min_price_toman:
                daily[sample.day] = sample
    rows = sorted(daily.values(), key=lambda item: item.day)
    if not rows:
        return _state({
            "view": "error", "message": "برای این مسیر هنوز قیمت ثبت‌شدهٔ معتبری نیست."
        })
    last = rows[-1]
    result = {
        "view": "chart",
        "o": origin[:36],
        "d": destination[:36],
        "ok": route_key(origin),
        "dk": route_key(destination),
        "p": last.min_price_toman,
        "n": sum(row.sample_count for row in rows),
        "end": today.toordinal(),
        "series": [[row.day.toordinal(), row.min_price_toman] for row in rows],
        "updated": last.last_captured_at.astimezone(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),
    }
    return _state(result)


async def handle_route_widget_query(
    raw: dict,
    bot: object,
    service: object | None,
    answer: Callable[[str], Awaitable[None]],
) -> None:
    """Acknowledge quickly and revalidate route hashes against recorded routes."""
    action = raw.get("data")
    if not isinstance(action, str) or len(action.encode("utf-8")) > 64:
        await answer("invalid")
        return
    if not _ACTION.fullmatch(action):
        await answer("invalid")
        return

    history = getattr(service, "price_history", None)
    if history is None or not (
        callable(getattr(history, "list_chart_routes", None))
        and callable(getattr(history, "get_route_daily_minimums", None))
    ):
        await answer("unavailable")
        return

    await answer("accepted")
    chat_id, message_id = raw["chat"]["id"], raw["message_id"]

    async def edit(state: str) -> None:
        await bot._post("editMessageWidgetData", {
            "chat_id": chat_id, "message_id": message_id, "chat_data": state
        })

    try:
        raw_pairs = await history.list_chart_routes(days=CHART_DAYS)
        routes = sorted({
            (origin, destination)
            for origin, destination in raw_pairs
            if isinstance(origin, str) and isinstance(destination, str)
            and origin and destination and len(origin) <= 100 and len(destination) <= 100
        })
        origins = sorted({origin for origin, _ in routes})
        parts = action.split(":")
        command = parts[1]

        if command == "origins":
            state = _menu("origins", origins, int(parts[2]))
        else:
            origin = _lookup(origins, parts[2])
            if origin is None:
                state = _state({
                    "view": "error", "message": "مبدأ در تاریخچهٔ فعلی وجود ندارد."
                })
            else:
                destinations = sorted({d for o, d in routes if o == origin})
                if command == "origin":
                    state = _menu("destinations", destinations, 0, origin=origin)
                elif command == "destinations":
                    state = _menu(
                        "destinations", destinations, int(parts[3]), origin=origin
                    )
                else:
                    destination = _lookup(destinations, parts[3])
                    if destination is None:
                        state = _state({
                            "view": "error",
                            "message": "این مسیر دیگر در تاریخچهٔ معتبر وجود ندارد.",
                        })
                    else:
                        samples = await history.get_route_daily_minimums(
                            origin, destination, days=CHART_DAYS
                        )
                        state = chart_state(origin, destination, samples)
        await edit(state)
    except Exception as exc:
        LOGGER.warning("widget_route_action_failed type=%s", type(exc).__name__)
        try:
            await edit(_state({
                "view": "error",
                "message": "دریافت تاریخچهٔ مسیر ممکن نیست؛ دوباره تلاش کنید.",
            }))
        except Exception as edit_exc:
            LOGGER.warning(
                "widget_route_error_state_failed type=%s", type(edit_exc).__name__
            )
