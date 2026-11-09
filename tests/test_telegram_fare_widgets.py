"""Regression tests for Telegram's Bot API 10.4 HTML fare widget."""

import json
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.handlers import TelegramDependencies, start_handler
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
    # Refresh feedback stays within the button, without footer paragraphs.
    assert 'id="status"' not in FARE_WIDGET_HTML
    assert "به‌روزرسانی انجام شد؛ قیمت‌ها" not in FARE_WIDGET_HTML
    assert "button.textContent='در حال تازه‌سازی...'" in FARE_WIDGET_HTML


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
    service = SimpleNamespace(
        routes=AsyncMock(return_value=[route("تهران", ("کیش", "۲,۸۰۰,۰۰۰ تومان"))])
    )
    message = FakeMessage()
    bot = FakeBot()
    assert await send_fare_widget(message, bot, service)
    method, data = bot.calls[0]
    assert method == "sendWidget"
    assert data["allow_queries"] is True
    assert data["chat_id"] == 123
    assert "caption" not in data
    assert json.loads(data["public_data"])["items"][0]["p"] == 2_800_000

    broken = FakeBot("sendWidget")
    assert not await send_fare_widget(message, broken, service)
    message.reply_text.assert_awaited_once()
    assert "تهران" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_widget_query_immediately_answers_then_edits_only_own_message():
    bot = FakeBot()
    service = SimpleNamespace(
        routes=AsyncMock(return_value=[route("تهران", ("مشهد", "۳۰۰۰۰۰۰ تومان"))])
    )
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


def test_widget_contains_two_in_place_tabs_and_persian_percentages():
    assert 'id="cheap"' in FARE_WIDGET_HTML
    assert 'id="drops"' in FARE_WIDGET_HTML
    assert "switchTab('drops')" in FARE_WIDGET_HTML
    assert "fa(fare.x)+'٪ کاهش نسبت به میانگین'" in FARE_WIDGET_HTML
    assert "var active='cheap'" in FARE_WIDGET_HTML
    assert "W.request('fare:refresh')" in FARE_WIDGET_HTML
    # No duplicated disclaimer below refresh button.
    assert "قیمت‌ها پیش از رزرو باید تأیید شوند" not in FARE_WIDGET_HTML


def test_price_drop_tab_sorts_by_percent_not_absolute_price():
    rows = [
        CheapTicketRoute(
            origin="تهران",
            source_url="https://example.org",
            destinations=(
                CheapTicketDestination(
                    "مشهد", "۴۰۰۰۰۰۰ تومان",
                    average_price_toman=5_000_000, average_sample_count=4,
                ),
                CheapTicketDestination(
                    "کیش", "۱۰۰۰۰۰۰ تومان",
                    average_price_toman=1_100_000, average_sample_count=5,
                ),
            ),
        ),
    ]
    data = json.loads(fare_widget_data(rows))
    assert [item["d"] for item in data["items"]] == ["کیش", "مشهد"]
    assert [item["d"] for item in data["drops"]] == ["مشهد", "کیش"]
    assert [item["x"] for item in data["drops"]] == [20.0, 9.1]
    assert data["items"][0]["x"] == 9.1


def test_discounts_require_enough_real_history_and_positive_decrease():
    row = CheapTicketRoute(
        origin="تهران",
        source_url="https://example.org",
        destinations=(
            CheapTicketDestination("الف", "۱۰۰۰۰۰۰ تومان"),
            CheapTicketDestination(
                "ب", "۱۵۰۰۰۰۰ تومان",
                average_price_toman=2_000_000, average_sample_count=2,
            ),
            CheapTicketDestination(
                "ج", "۲۵۰۰۰۰۰ تومان",
                average_price_toman=2_000_000, average_sample_count=9,
            ),
            CheapTicketDestination(
                "د", "۸۰۰۰۰۰ تومان",
                average_price_toman=float("nan"), average_sample_count=8,
            ),
        ),
    )
    data = json.loads(fare_widget_data([row]))
    assert len(data["items"]) == 4
    assert data["drops"] == []
    assert all("x" not in item for item in data["items"])


def test_large_persian_data_stays_within_widget_payload_limit():
    rows = [
        CheapTicketRoute(
            origin="مبدأ بسیار طولانی با نام فارسی برای آزمون محدودیت اندازه",
            source_url="https://example.org",
            destinations=tuple(
                CheapTicketDestination(
                    "مقصد بسیار طولانی با نام فارسی شماره" + str(i),
                    f"{i+1}۰۰۰۰۰۰ تومان",
                    average_price_toman=(i + 2) * 1_000_000,
                    average_sample_count=10,
                )
                for i in range(20)
            ),
        )
    ]
    state = fare_widget_data(rows)
    assert len(state.encode("utf-8")) <= 1024
    result = json.loads(state)
    assert result["items"]
    assert result["drops"]
    assert all(item["x"] > 0 for item in result["drops"])


@pytest.mark.asyncio
async def test_refresh_updates_both_tab_datasets_at_once():
    bot = FakeBot()
    service = SimpleNamespace(routes=AsyncMock(return_value=[
        CheapTicketRoute(
            origin="تهران",
            source_url="https://example.org",
            destinations=(CheapTicketDestination(
                "مشهد", "۲۰۰۰۰۰۰ تومان",
                average_price_toman=4_000_000, average_sample_count=6,
            ),),
        )
    ]))
    query = {
        "id": "query-tab-refresh",
        "data": "fare:refresh",
        "type": {"type": "data"},
        "from": {"id": 123},
        "chat": {"id": 123, "type": "private"},
        "message_id": 321,
    }
    await widget_query_handler(
        Update(11, api_kwargs={"widget_query": query}),
        SimpleNamespace(bot=bot),
        service,
    )
    payload = json.loads(bot.calls[1][1]["public_data"])
    assert payload["items"][0]["p"] == 2_000_000
    assert payload["drops"][0]["x"] == 50.0
    assert len(bot.calls) == 2


class StartTestUsers:
    async def get_or_create_with_status(self, user_id, **fields):
        return SimpleNamespace(id=user_id), False

    async def get_language(self, user_id):
        return "fa"


class StartTestAudit:
    def __init__(self):
        self.events = []

    async def record(self, event, **kwargs):
        self.events.append(event)


@pytest.mark.asyncio
async def test_fares_deep_link_opens_widget_without_main_menu():
    service = SimpleNamespace(
        routes=AsyncMock(return_value=[route("تهران", ("کیش", "۲,۸۰۰,۰۰۰ تومان"))])
    )
    bot = FakeBot()
    msg = FakeMessage()
    audit = StartTestAudit()
    dependencies = TelegramDependencies(
        users=StartTestUsers(), audit=audit,
        cheap_ticket_service=service, admin_chat_id=None,
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=123, username="traveler", first_name="Test", last_name=None
        ),
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=msg,
    )
    context = SimpleNamespace(args=["fares"], bot=bot, user_data={})

    await start_handler(update, context, dependencies)

    assert [method for method, _data in bot.calls] == ["sendWidget"]
    service.routes.assert_awaited_once()
    msg.reply_text.assert_not_awaited()
    assert "ticket.widget.opened" in audit.events


@pytest.mark.asyncio
async def test_fares_deep_link_on_bale_falls_back_to_original_main_menu():
    service = SimpleNamespace(routes=AsyncMock())
    bot = FakeBot()
    bot.platform = "bale"
    msg = FakeMessage()
    deps = TelegramDependencies(
        users=StartTestUsers(), audit=StartTestAudit(),
        cheap_ticket_service=service, admin_chat_id=None,
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=123, username="traveler", first_name="Test", last_name=None
        ),
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=msg,
    )
    await start_handler(
        update, SimpleNamespace(args=["fares"], bot=bot, user_data={}), deps
    )

    service.routes.assert_not_awaited()
    assert not bot.calls
    msg.reply_text.assert_awaited_once()
    assert "سلام" in msg.reply_text.await_args.args[0]


def test_fare_tabs_have_clear_selected_and_unselected_states():
    """Tabs need a persistent label, contrast and an explicit selected marker."""
    assert "مرتب‌سازی بلیت‌ها بر اساس:" in FARE_WIDGET_HTML
    assert 'role="tablist"' in FARE_WIDGET_HTML
    assert 'role="tabpanel"' in FARE_WIDGET_HTML
    assert 'aria-selected="true"' in FARE_WIDGET_HTML
    assert 'aria-selected="false"' in FARE_WIDGET_HTML
    assert "✓ ارزان‌ترین بلیت‌ها" in FARE_WIDGET_HTML
    assert "✓ بیشترین کاهش قیمت" in FARE_WIDGET_HTML
    assert "cheap.setAttribute('aria-selected'" in FARE_WIDGET_HTML
    assert "drops.setAttribute('aria-selected'" in FARE_WIDGET_HTML
    assert "fares.setAttribute('aria-labelledby',which)" in FARE_WIDGET_HTML
    assert ".tabs button.active" in FARE_WIDGET_HTML
    assert "var(--tg-theme-button-color" in FARE_WIDGET_HTML
    assert "var(--tg-theme-button-text-color" in FARE_WIDGET_HTML
    assert "var(--tg-theme-bg-color" in FARE_WIDGET_HTML
