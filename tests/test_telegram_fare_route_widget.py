"""Safe, source-backed route history inside the existing private fare widget."""

import json
import zlib
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.db.repositories import RouteDailyMinimum
from flightiran.interfaces.telegram.fare_route_widget import chart_state, route_key
from flightiran.interfaces.telegram.widgets import FARE_WIDGET_HTML, widget_query_handler


class FakeBot:
    def __init__(self):
        self.calls = []

    async def _post(self, method, data):
        self.calls.append((method, data))
        return True


def query(action, *, user_id=123, chat_id=123, message_id=87):
    return Update(11, api_kwargs={"widget_query": {
        "id": "route-widget-query",
        "data": action,
        "type": {"type": "data"},
        "from": {"id": user_id},
        "chat": {"id": chat_id, "type": "private"},
        "message_id": message_id,
    }})


def sample(day, price, count=1):
    instant = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    return RouteDailyMinimum(
        day=day, min_price_toman=price, sample_count=count, last_captured_at=instant
    )


def test_embedded_route_picker_keeps_existing_fare_tabs_and_widget_limits():
    raw = FARE_WIDGET_HTML.encode("utf-8")
    assert len(raw) <= 32768
    assert len(zlib.compress(raw, level=9)) <= 4096
    assert "fare:origins:0" in FARE_WIDGET_HTML
    assert 'id="route-origin"' in FARE_WIDGET_HTML
    assert 'id="route-destination"' in FARE_WIDGET_HTML
    assert "chatDataChanged" in FARE_WIDGET_HTML
    assert "valid[k][0]===last[0]+1" in FARE_WIDGET_HTML
    assert 'role="tablist"' in FARE_WIDGET_HTML
    assert "W.request('fare:refresh')" in FARE_WIDGET_HTML


@pytest.mark.asyncio
async def test_widget_picker_uses_only_recorded_sqlite_route_pairs():
    now = datetime.now(timezone.utc)
    rows = [
        sample((now - timedelta(days=2)).date(), 2_450_000, 4),
        sample(now.date(), 2_100_000, 2),
    ]
    history = SimpleNamespace(
        list_chart_routes=AsyncMock(return_value=[
            ("تهران", "مشهد"), ("شیراز", "کیش")
        ]),
        get_route_daily_minimums=AsyncMock(return_value=rows),
    )
    service = SimpleNamespace(price_history=history)
    bot = FakeBot()
    context = SimpleNamespace(bot=bot)

    await widget_query_handler(query("fare:origins:0"), context, service)
    assert [method for method, _ in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData"
    ]
    assert bot.calls[0][1]["data"] == "accepted"
    origins = json.loads(bot.calls[-1][1]["chat_data"])
    assert origins["view"] == "origins"
    assert {x["n"] for x in origins["options"]} == {"تهران", "شیراز"}
    history.get_route_daily_minimums.assert_not_awaited()

    await widget_query_handler(
        query("fare:origin:" + route_key("تهران")), context, service
    )
    destinations = json.loads(bot.calls[-1][1]["chat_data"])
    assert destinations["view"] == "destinations"
    assert [item["n"] for item in destinations["options"]] == ["مشهد"]

    await widget_query_handler(
        query("fare:route:" + route_key("تهران") + ":" + route_key("مشهد")),
        context, service,
    )
    chart = json.loads(bot.calls[-1][1]["chat_data"])
    assert chart["view"] == "chart"
    assert chart["p"] == 2_100_000
    assert chart["n"] == 6
    assert len(chart["series"]) == 2
    assert chart["series"][1][0] - chart["series"][0][0] == 2
    assert len(bot.calls[-1][1]["chat_data"].encode("utf-8")) <= 1024
    history.get_route_daily_minimums.assert_awaited_once_with(
        "تهران", "مشهد", days=21
    )


@pytest.mark.asyncio
async def test_forged_or_cross_chat_selection_cannot_read_history():
    history = SimpleNamespace(
        list_chart_routes=AsyncMock(return_value=[("تهران", "مشهد")]),
        get_route_daily_minimums=AsyncMock(),
    )
    service = SimpleNamespace(price_history=history)
    bot = FakeBot()
    await widget_query_handler(
        query("fare:route:" + route_key("تهران") + ":0000000000"),
        SimpleNamespace(bot=bot), service,
    )
    result = json.loads(bot.calls[-1][1]["chat_data"])
    assert result["view"] == "error"
    history.get_route_daily_minimums.assert_not_awaited()

    before = len(bot.calls)
    await widget_query_handler(
        query("fare:origins:0", chat_id=456), SimpleNamespace(bot=bot), service
    )
    assert len(bot.calls) == before + 1
    assert bot.calls[-1][1]["data"] == "invalid"

    await widget_query_handler(
        query("fare:book:0000000000:0000000000"),
        SimpleNamespace(bot=bot), service,
    )
    assert bot.calls[-1][1]["data"] == "invalid"
    history.get_route_daily_minimums.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_recorded_history_fails_closed_without_live_provider_access():
    history = SimpleNamespace(
        list_chart_routes=AsyncMock(return_value=[("تهران", "مشهد")]),
        get_route_daily_minimums=AsyncMock(return_value=[]),
    )
    service = SimpleNamespace(price_history=history, routes=AsyncMock())
    bot = FakeBot()
    await widget_query_handler(
        query("fare:route:" + route_key("تهران") + ":" + route_key("مشهد")),
        SimpleNamespace(bot=bot), service,
    )
    assert json.loads(bot.calls[-1][1]["chat_data"])["view"] == "error"
    service.routes.assert_not_awaited()


def test_chart_state_keeps_only_real_daily_minima_in_21_day_window():
    now = datetime(2026, 11, 20, 11, 0, tzinfo=timezone.utc)
    values = [
        sample(date(2026, 10, 29), 700_000),
        sample(date(2026, 11, 18), 2_000_000, 3),
        sample(date(2026, 11, 20), 1_800_000, 2),
        sample(date(2026, 11, 21), 500_000),
    ]
    result = json.loads(chart_state("تهران", "مشهد", values, now=now))
    assert result["p"] == 1_800_000
    assert result["n"] == 5
    assert result["series"] == [
        [date(2026, 11, 18).toordinal(), 2_000_000],
        [date(2026, 11, 20).toordinal(), 1_800_000],
    ]
    assert result["end"] == date(2026, 11, 20).toordinal()
    assert "pct" not in result
