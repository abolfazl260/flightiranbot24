"""Private Telegram route selection, historical chart data, and booking requests.

The widget cannot use text inputs or network APIs; every city picker action is
validated against the existing ticket feed and answered through widget_query.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Awaitable, Callable

from flightiran.modules.tickets.service import CheapTicketService, parse_toman_price

from .tickets import send_ticket_reservation_request

LOGGER = logging.getLogger(__name__)

_PAGE_SIZE = 7
_ACTION = re.compile(
    r"(?:fare:origins:\d{1,3}|fare:origin:[a-f0-9]{10}"
    r"|fare:destinations:[a-f0-9]{10}:\d{1,3}"
    r"|fare:(?:route|book):[a-f0-9]{10}:[a-f0-9]{10})\Z"
)


def route_key(value: str) -> str:
    """Stable ten-digit digest; never put unbounded Persian text in requests."""
    return hashlib.blake2s(value.encode("utf-8"), digest_size=5).hexdigest()


def _as_json(state: dict) -> str:
    raw = json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if len(raw.encode("utf-8")) > 1024:
        raise ValueError("Widget state exceeds Telegram's 1024-byte limit")
    return raw


def _find_by_key(names: list[str], key: str) -> str | None:
    matches = [name for name in names if route_key(name) == key]
    return matches[0] if len(matches) == 1 else None


def _menu_state(view: str, names: list[str], page: int, *,
                origin: str | None = None) -> str:
    names = sorted(set(names))
    pages = max(1, (len(names) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = min(page, pages - 1)
    options = [{"n": name, "k": route_key(name)}
               for name in names[page * _PAGE_SIZE:(page + 1) * _PAGE_SIZE]]
    data = {"view": view, "page": page, "pages": pages, "options": options}
    if origin is not None:
        data["o"] = origin
        data["ok"] = route_key(origin)
    # An unexpectedly long city name must never make the entire widget fail.
    while True:
        try:
            return _as_json(data)
        except ValueError:
            if not data["options"]:
                raise
            data["options"].pop()


def route_chart_state(
    origin: str, destination: str, current_price: int,
    average: float | None, average_count: int,
    history: list[tuple[datetime, int]],
    *, now: datetime | None = None,
) -> str:
    """Encode daily observed low prices, explicitly skipping missing days."""
    daily: dict[int, int] = {}
    sample_count = 0
    for captured, price in history:
        if not isinstance(captured, datetime) or not isinstance(price, int) or price <= 0:
            continue
        stamp = captured.astimezone(timezone.utc) if captured.tzinfo else captured.replace(
            tzinfo=timezone.utc
        )
        label = stamp.date().toordinal()
        daily[label] = min(daily.get(label, price), price)
        sample_count += 1
    points = [[day, value] for day, value in sorted(daily.items())]
    avg = (
        round(average)
        if isinstance(average, (float, int)) and math.isfinite(average)
        and average > 0 and average_count >= 3 else None
    )
    percent = round(100 * (current_price - avg) / avg, 1) if avg else None
    state = {
        "view": "chart", "o": origin, "d": destination,
        "ok": route_key(origin), "dk": route_key(destination),
        "p": current_price, "a": avg, "pct": percent,
        "n": sample_count, "series": points,
        "updated": (now or datetime.now(timezone.utc)).strftime("%m/%d %H:%M UTC"),
    }
    # Reduce only genuine historic points if state becomes oversized.
    while True:
        try:
            return _as_json(state)
        except ValueError:
            if not state["series"]:
                raise
            state["series"] = state["series"][::2]
            if len(state["series"]) == 1:
                state["series"] = []


class _BotMessage:
    """Adapt existing booking-presenter fallback to a widget-originated query."""

    def __init__(self, bot: object, chat_id: int) -> None:
        self.bot = bot
        self.chat_id = chat_id

    async def reply_text(self, text: str, **kwargs):
        return await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)


async def handle_route_widget_query(
    raw: dict, bot: object, service: CheapTicketService | None,
    answer: Callable[[str], Awaitable[None]],
    *, support_username: str,
) -> None:
    """Validate, acknowledge, resolve actual data and update only this widget."""
    action = raw.get("data")
    if (
        not isinstance(action, str)
        or len(action.encode("utf-8")) > 64
        or not _ACTION.fullmatch(action)
    ):
        await answer("invalid")
        return
    if service is None:
        await answer("unavailable")
        return

    await answer("accepted")
    chat_id, message_id = raw["chat"]["id"], raw["message_id"]

    async def edit(state: str) -> None:
        await bot._post("editMessageWidgetData", {
            "chat_id": chat_id, "message_id": message_id, "chat_data": state
        })

    try:
        routes = await service.routes()
        # Sort and de-duplicate for deterministic picker options.
        by_origin = {route.origin: route for route in routes}
        origins = sorted(by_origin)
        parts = action.split(":")
        command = parts[1]

        if command == "origins":
            state = _menu_state("origins", origins, int(parts[2]))
        else:
            origin = _find_by_key(origins, parts[2])
            if origin is None:
                state = _as_json({"view": "error", "message": "مبدأ در داده‌های فعلی موجود نیست."})
            else:
                route = by_origin[origin]
                destinations = sorted({item.name for item in route.destinations})
                if command == "origin":
                    state = _menu_state("destinations", destinations, 0, origin=origin)
                elif command == "destinations":
                    state = _menu_state(
                        "destinations", destinations, int(parts[3]), origin=origin
                    )
                else:
                    destination = _find_by_key(destinations, parts[3])
                    item = next(
                        (d for d in route.destinations if d.name == destination), None
                    )
                    if item is None:
                        state = _as_json({
                            "view": "error", "message": "این مسیر دیگر در فهرست قیمت‌ها نیست."
                        })
                    elif command == "book":
                        # This sends a route-specific booking enquiry, not a payment
                        # or an assertion that a seat was reserved.
                        await send_ticket_reservation_request(
                            bot, _BotMessage(bot, chat_id), origin, item, support_username
                        )
                        return
                    else:
                        current = (
                            item.price_value_toman
                            if item.price_value_toman is not None
                            else parse_toman_price(item.price_toman)
                        )
                        if current <= 0:
                            raise ValueError("Non-positive route price")
                        historical = []
                        history_service = getattr(service, "price_history", None)
                        fetch = getattr(history_service, "get_route_history", None)
                        if callable(fetch):
                            historical = await fetch(origin, destination, days=21)
                        state = route_chart_state(
                            origin, destination, current,
                            item.average_price_toman, item.average_sample_count,
                            historical,
                        )
        await edit(state)
    except Exception as exc:
        LOGGER.warning("widget_route_action_failed type=%s", type(exc).__name__)
        try:
            await edit(_as_json({
                "view": "error", "message": "دریافت اطلاعات مسیر ممکن نیست؛ دوباره تلاش کنید."
            }))
        except Exception as edit_exc:
            LOGGER.warning("widget_route_action_error_edit_failed type=%s",
                           type(edit_exc).__name__)
