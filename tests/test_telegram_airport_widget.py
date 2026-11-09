"""Security, source parity and interaction tests for Telegram airport widgets."""

import json
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.airport_widget import (
    ACTION,
    CONTENT_LIMIT,
    STATE_LIMIT,
    AirportGuideStore,
    _pages,
    _pieces,
    _safe_url,
    airport_widget_html,
    handle_airport_widget_query,
    send_airport_widget,
)
from flightiran.interfaces.telegram.keyboards import main_menu
from flightiran.modules.airport.catalog import AirportCatalog

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "src/flightiran/modules/airport/data/airports.json"


@pytest.fixture
def store():
    return AirportGuideStore(AirportCatalog.from_json(CATALOG), ROOT / "data/airports")


class FakeBot:
    platform = "telegram"

    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail
        self.send_message = AsyncMock()

    async def _post(self, method, data):
        self.calls.append((method, data))
        if method == self.fail:
            raise RuntimeError("test refusal")
        return True


class FakeMessage:
    chat = SimpleNamespace(type="private")
    chat_id = 123

    def __init__(self):
        self.reply_text = AsyncMock()


def _query(action, *, user_id=123, chat_id=123, qid="ap-test"):
    return Update(
        1, api_kwargs={"widget_query": {
            "id": qid, "from": {"id": user_id},
            "chat": {"id": chat_id, "type": "private"},
            "message_id": 456, "data": action, "type": {"type": "data"},
        }},
    )


def test_all_29_airports_use_shared_canonical_identity_and_enabled_index(store):
    codes = store.airports()
    assert len(codes) == 29
    assert len({item[0] for item in codes}) == 29
    assert len([item for item in codes if item[2]]) == 13
    for code, name, _ in codes:
        assert name and store.catalog.get(code) is not None
        _, sections = store.sections(code)
        assert sections, code
        assert all(x["status"] == "published" for x in sections)
        assert all(x["reviewed_at"] and _pages(x) for x in sections)
    assert [row[0] for row in codes] != []


def test_airport_widget_has_full_directory_and_is_under_telegram_size_limits(store):
    html = airport_widget_html(store)
    assert len(html.encode("utf-8")) <= 32768
    assert len(zlib.compress(html.encode("utf-8"), 9)) <= 4096
    assert "__AIRPORTS__" not in html
    for code, name, _ in store.airports():
        assert f'"{code}"' in html
        assert name in html
    assert "W.request(action)" in html
    assert "chatDataChanged" in html
    assert 'id="all"' in html and 'id="iran"' in html
    assert 'id="foreign"' in html
    assert "منابع و لینک‌ها" in html


def test_published_sections_are_paginated_and_never_silently_truncated(store):
    name, sections = store.sections("THR")
    assert name
    assert len(sections) >= 8
    assert "traveler-experiences" not in {row["id"] for row in sections}
    for code, _, _ in store.airports():
        _, sections = store.sections(code)
        for section in sections:
            parts = _pieces(section)
            texts = _pages(section)
            assert all(len(page.encode("utf-8")) <= CONTENT_LIMIT for page in texts)
            # Paragraph breaks are intentional display whitespace, not omitted words.
            joined = "".join(texts).replace("\n\n", "")
            for piece in parts:
                assert piece.replace("\n\n", "") in joined
    assert "بار مجاز" in store.detail_state("THR", 0)


def test_listing_and_details_have_boundaries_and_all_pages_available(store):
    name, sections = store.sections("MHD")
    pages = (len(sections) + 3) // 4
    indices = []
    for page in range(pages):
        state = json.loads(store.list_state("MHD", page))
        indices.extend([row[0] for row in state["items"]])
        assert state["n"] == name
        assert len(store.list_state("MHD", page).encode()) <= STATE_LIMIT
    assert indices == list(range(len(sections)))
    for i, section in enumerate(sections):
        pages = _pages(section)
        for page in range(len(pages)):
            state = store.detail_state("MHD", i, page)
            assert len(state.encode()) <= STATE_LIMIT
            data = json.loads(state)
            assert data["r"] == section["reviewed_at"][:10]
            assert data["t"] == pages[page]
    with pytest.raises(ValueError):
        store.detail_state("MHD", 99)
    with pytest.raises(ValueError):
        store.list_state("MHD", 99)
    with pytest.raises(ValueError):
        store.detail_state("MHD", 0, 999)
    with pytest.raises(ValueError):
        store.sections("../etc/passwd")


def test_official_sources_only_and_no_unsafe_urls(store):
    name, title, sources = store.sources("THR", 0)
    assert name and title
    assert sources
    assert all(url.startswith("https://") for _, url in sources)
    assert _safe_url("javascript:alert(1)") is None
    assert _safe_url("https://person:password@example.org/path") is None
    assert _safe_url("https://example.org/good") == "https://example.org/good"
    assert not ACTION.fullmatch("ap:o:../../etc")
    assert not ACTION.fullmatch("ap:d:THR:00:9999")


@pytest.mark.asyncio
async def test_send_widget_and_fallback_and_private_scope(store):
    bot = FakeBot()
    message = FakeMessage()
    assert await send_airport_widget(message, bot, store)
    method, kwargs = bot.calls[0]
    assert method == "sendWidget"
    assert kwargs["chat_id"] == 123
    assert kwargs["allow_queries"] is True
    assert json.loads(kwargs["chat_data"]) == {"v": "home"}
    rejected = FakeBot("sendWidget")
    assert not await send_airport_widget(message, rejected, store)
    message.reply_text.assert_awaited_once()
    group = FakeMessage()
    group.chat = SimpleNamespace(type="group")
    assert not await send_airport_widget(group, bot, store)
    group.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_widget_query_opens_sections_and_details_in_same_message(store):
    bot = FakeBot()
    ctx = SimpleNamespace(bot=bot)
    await handle_airport_widget_query(_query("ap:o:THR"), ctx, store)
    assert [name for name, _ in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData",
    ]
    state = json.loads(bot.calls[0][1]["data"])
    assert state["v"] == "list"
    assert state["a"] == "THR" and state["total"] > 0
    assert bot.calls[1][1]["chat_data"] == bot.calls[0][1]["data"]
    bot.calls.clear()
    await handle_airport_widget_query(_query("ap:s:THR:00"), ctx, store)
    data = json.loads(bot.calls[0][1]["data"])
    assert data["v"] == "detail" and data["s"]
    assert data["t"]
    bot.calls.clear()
    await handle_airport_widget_query(_query("ap:d:THR:00:000"), ctx, store)
    assert json.loads(bot.calls[0][1]["data"])["p"] == 0


@pytest.mark.asyncio
async def test_sources_are_sent_only_after_explicit_request(store):
    bot = FakeBot()
    await handle_airport_widget_query(_query("ap:r:THR:00"), SimpleNamespace(bot=bot), store)
    assert bot.calls == [("answerWidgetQuery", {
        "widget_query_id": "ap-test", "data": "accepted",
    })]
    bot.send_message.assert_awaited()
    assert bot.send_message.await_args.kwargs["chat_id"] == 123
    assert bot.send_message.await_args.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_malformed_or_cross_user_requests_never_read_or_edit(store):
    bot = FakeBot()
    for update in [
        _query("ap:o:THR", user_id=123, chat_id=456),
        _query("ap:o:../"),
        _query("ap:o:AAA"),
        _query("ap:d:THR:99:000"),
    ]:
        bot.calls.clear()
        await handle_airport_widget_query(update, SimpleNamespace(bot=bot), store)
        assert len(bot.calls) == 1
        assert bot.calls[0][0] == "answerWidgetQuery"
        assert bot.calls[0][1]["data"] in ("invalid", "unavailable")
    bot.send_message.assert_not_awaited()


def test_airport_button_is_telegram_only():
    def callbacks(keyboard):
        return [b.callback_data for row in keyboard.inline_keyboard for b in row]
    assert "menu:airports" in callbacks(main_menu("fa", widgets_enabled=True))
    assert "menu:airports" not in callbacks(main_menu("fa", widgets_enabled=False))
