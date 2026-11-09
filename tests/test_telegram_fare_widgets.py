"""Regression tests for Telegram's Bot API 10.4 HTML fare widget."""

import json
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.widgets import (
    FARE_WIDGET_HTML,
    fare_widget_data,
    send_fare_widget,
    widget_query_handler,
)
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute


def route(origin, *pairs):
    return CheapTicketRoute(
        origin=origin,
        source_url="https://example.org",
        destinations=tuple(CheapTicketDestination(name, price) for name, price in pairs),
    )


class FakeBot:
    platform = "telegram"

    def __init__(self, fail_method=None):
        self.calls = []
        self.fail_method = fail_method

    async def _post(self, method, data):
        self.calls.append((method, data))
        if method == self.fail_method:
            raise RuntimeError("simulated failure")
        return True


class FakeMessage:
    chat = SimpleNamespace(type="private")
    chat_id = 123

    def __init__(self):
        self.reply_text = AsyncMock()


def test_html_widget_is_within_telegram_limits():
    raw = FARE_WIDGET_HTML.encode("utf-8")
    assert len(raw) <= 32768
    assert len(zlib.compress(raw, level=9)) <= 4096
    assert "TelegramWidget.request" not in FARE_WIDGET_HTML  # W.request is used
    assert "W.request('fare:refresh')" in FARE_WIDGET_HTML
    assert "publicDataChanged" in FARE_WIDGET_HTML


def test_fare_widget_data_is_real_sorted_and_bounded():
    rows = [
        route("تهران", ("مشهد", "۲,۵۰۰,۰۰۰ تومان"), ("تبریز", "۲۰۰۰۰۰۰ تومان")),
        route("شیراز", ("کیش", "۳,۱۰۰,۰۰۰ تومان")),
    ]
    payload = fare_widget_data(rows)
    result = json.loads(payload)
    assert len(payload.encode("utf-8")) <= 1024
    assert [x["p"] for x in result["items"]] == [2_000_000, 2_500_000, 3_100_000]
    assert result["items"][0]["o"] == "تهران"
    assert "updated" in result


@pytest.mark.asyncio
async def test_send_widget_and_fallback_when_telegram_rejects():
    service = SimpleNamespace(routes=AsyncMock(return_value=[route("تهران", ("کیش", "۲,۸۰۰,۰۰۰ تومان"))]))
    message = FakeMessage()
    bot = FakeBot()
    assert await send_fare_widget(message, bot, service)
    method, data = bot.calls[0]
    assert method == "sendWidget"
    assert data["allow_queries"] is True
    assert data["chat_id"] == 123
    assert json.loads(data["public_data"])["items"][0]["p"] == 2_800_000

    broken = FakeBot("sendWidget")
    assert not await send_fare_widget(message, broken, service)
    message.reply_text.assert_awaited_once()
    assert "تهران" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_widget_query_immediately_answers_then_edits_only_own_message():
    bot = FakeBot()
    service = SimpleNamespace(routes=AsyncMock(return_value=[route("تهران", ("مشهد", "۳۰۰۰۰۰۰ تومان"))]))
    query = {
        "id": "query-1", "data": "fare:refresh",
        "type": {"type": "data"},
        "from": {"id": 123}, "chat": {"id": 123, "type": "private"},
        "message_id": 987,
    }
    update = Update(update_id=1, api_kwargs={"widget_query": query})
    await widget_query_handler(update, SimpleNamespace(bot=bot), service)
    assert [name for name, _ in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData",
    ]
    assert bot.calls[0][1] == {
        "widget_query_id": "query-1", "data": "accepted",
    }
    edit = bot.calls[1][1]
    assert (edit["chat_id"], edit["message_id"]) == (123, 987)
    assert json.loads(edit["public_data"])["items"][0]["p"] == 3_000_000
    service.routes.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_or_cross_chat_widget_query_never_reads_prices():
    bot = FakeBot()
    service = SimpleNamespace(routes=AsyncMock())
    bad = {
        "id": "query-2", "data": "fare:refresh",
        "from": {"id": 123}, "chat": {"id": 456, "type": "private"},
        "message_id": 10,
    }
    await widget_query_handler(
        Update(2, api_kwargs={"widget_query": bad}),
        SimpleNamespace(bot=bot),
        service,
    )
    assert bot.calls == [("answerWidgetQuery", {
        "widget_query_id": "query-2", "data": "invalid",
    })]
    service.routes.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_refresh_keeps_existing_fares_and_sets_error():
    bot = FakeBot()
    service = SimpleNamespace(routes=AsyncMock(side_effect=RuntimeError("provider down")))
    query = {
        "id": "query-3", "data": "fare:refresh",
        "from": {"id": 123}, "chat": {"id": 123, "type": "private"},
        "message_id": 10,
    }
    await widget_query_handler(
        Update(3, api_kwargs={"widget_query": query}),
        SimpleNamespace(bot=bot),
        service,
    )
    assert [name for name, _ in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData",
    ]
    assert bot.calls[1][1]["chat_data"] == '{"status":"error"}'
    assert "public_data" not in bot.calls[1][1]
