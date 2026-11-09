"""Verified route chart and booking actions in private Telegram HTML widgets."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.fare_route_chart import (
    _menu_state,
    route_chart_state,
    route_key,
)
from flightiran.interfaces.telegram.widgets import FARE_WIDGET_HTML, widget_query_handler
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute


class Bot:
    def __init__(self):
        self.calls = []

    async def _post(self, name, data):
        self.calls.append((name, data))
        return True


def route():
    return CheapTicketRoute(
        origin="تهران",
        source_url="https://example.org",
        destinations=(
            CheapTicketDestination(
                "مشهد", "۲,۰۰۰,۰۰۰ تومان", average_price_toman=2_500_000,
                average_sample_count=5,
            ),
            CheapTicketDestination("کیش", "۳,۰۰۰,۰۰۰ تومان"),
        ),
    )


def query(data: str) -> Update:
    return Update(10, api_kwargs={"widget_query": {
        "id": "route-query",
        "data": data,
        "type": {"type": "data"},
        "chat": {"id": 123, "type": "private"},
        "from": {"id": 123},
        "message_id": 45,
    }})


def make_service(history=None):
    history = history if history is not None else []
    return SimpleNamespace(
        routes=AsyncMock(return_value=[route()]),
        price_history=SimpleNamespace(get_route_history=AsyncMock(return_value=history)),
    )


def test_route_widget_contains_city_buttons_chart_svg_and_booking():
    assert 'id="route-origin"' in FARE_WIDGET_HTML
    assert 'id="route-destination"' in FARE_WIDGET_HTML
    assert 'id="route-plot"' in FARE_WIDGET_HTML
    assert "fare:origins:0" in FARE_WIDGET_HTML
    assert "fare:destinations:" in FARE_WIDGET_HTML
    assert "fare:book:" in FARE_WIDGET_HTML
    assert "id=\"cheap\"" in FARE_WIDGET_HTML
    assert "id=\"drops\"" in FARE_WIDGET_HTML


def test_chart_uses_only_observed_daily_minimum_without_interpolation():
    day = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0)
    values = [
        (day - timedelta(days=3), 2_700_000),
        (day - timedelta(days=3, hours=1), 2_400_000),
        (day - timedelta(days=1), 2_800_000),
    ]
    data = json.loads(route_chart_state(
        "تهران", "مشهد", 2_000_000, 2_500_000, 6, values,
    ))
    assert len(data["series"]) == 2
    assert data["series"][0][1] == 2_400_000
    assert data["series"][1][1] == 2_800_000
    assert data["series"][1][0] - data["series"][0][0] == 2
    assert data["pct"] == -20.0
    assert data["n"] == 3
    assert len(json.dumps(data, ensure_ascii=False).encode()) <= 1024


def test_chart_does_not_fabricate_when_history_is_missing():
    data = json.loads(route_chart_state("تهران", "مشهد", 1_000_000, None, 0, []))
    assert data["series"] == []
    assert data["a"] is None
    assert data["pct"] is None
    assert data["n"] == 0


@pytest.mark.asyncio
async def test_origin_and_destination_pick_latest_real_feed():
    bot, service = Bot(), make_service()
    origin = route_key("تهران")
    await widget_query_handler(query("fare:origins:0"), SimpleNamespace(bot=bot), service)
    assert [x[0] for x in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData",
    ]
    state = json.loads(bot.calls[1][1]["chat_data"])
    assert state["view"] == "origins"
    assert state["options"][0]["n"] == "تهران"

    bot.calls.clear()
    await widget_query_handler(
        query(f"fare:origin:{origin}"), SimpleNamespace(bot=bot), service
    )
    state = json.loads(bot.calls[1][1]["chat_data"])
    assert state["view"] == "destinations"
    assert [x["n"] for x in state["options"]] == ["مشهد", "کیش"] or sorted(
        x["n"] for x in state["options"]
    ) == ["مشهد", "کیش"]


@pytest.mark.asyncio
async def test_route_selection_returns_historical_chart_and_keeps_support_flow():
    day = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0)
    bot = Bot()
    service = make_service([(day, 2_300_000), (day - timedelta(days=1), 2_500_000)])
    await widget_query_handler(
        query(f"fare:route:{route_key('تهران')}:{route_key('مشهد')}"),
        SimpleNamespace(bot=bot), service,
    )
    state = json.loads(bot.calls[1][1]["chat_data"])
    assert state["view"] == "chart"
    assert state["o"] == "تهران"
    assert state["d"] == "مشهد"
    assert state["p"] == 2_000_000
    assert len(state["series"]) == 2
    service.price_history.get_route_history.assert_awaited_once_with(
        "تهران", "مشهد", days=21,
    )


@pytest.mark.asyncio
async def test_route_booking_calls_existing_booking_presenter(monkeypatch):
    import flightiran.interfaces.telegram.fare_route_chart as flow

    send_booking = AsyncMock()
    monkeypatch.setattr(flow, "send_ticket_reservation_request", send_booking)
    bot, service = Bot(), make_service()
    await widget_query_handler(
        query(f"fare:book:{route_key('تهران')}:{route_key('مشهد')}"),
        SimpleNamespace(bot=bot), service, support_username="advertio_support",
    )
    assert [x[0] for x in bot.calls] == ["answerWidgetQuery"]
    assert send_booking.await_args.args[2] == "تهران"
    assert send_booking.await_args.args[3].name == "مشهد"
    assert send_booking.await_args.args[4] == "advertio_support"


@pytest.mark.asyncio
async def test_unknown_route_key_and_invalid_query_are_safely_rejected():
    bot, service = Bot(), make_service()
    await widget_query_handler(
        query("fare:route:deadbeef00:ffffffff00"), SimpleNamespace(bot=bot), service
    )
    state = json.loads(bot.calls[-1][1]["chat_data"])
    assert state["view"] == "error"
    bot.calls.clear()
    await widget_query_handler(
        query("fare:book:../danger"), SimpleNamespace(bot=bot), service
    )
    assert bot.calls == [("answerWidgetQuery", {
        "widget_query_id": "route-query", "data": "invalid",
    })]


def test_pagination_stays_within_widget_data_limit():
    names = ["فرودگاه خیلی طولانی "+str(i)+" شهر از سراسر ایران"*2 for i in range(90)]
    state = _menu_state("origins", names, 1)
    assert len(state.encode("utf-8")) <= 1024
    assert json.loads(state)["pages"] > 1
