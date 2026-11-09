"""Durable, private, and accessible Telegram travel checklist tests."""

import asyncio
import json
import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.db.engine import initialize_database
from flightiran.interfaces.telegram.handlers import TelegramDependencies, start_handler
from flightiran.interfaces.telegram.checklist_widget import (
    CHECKLIST_WIDGET_HTML,
    handle_checklist_query,
    send_checklist_widget,
)
from flightiran.modules.travel_checklist import (
    TASKS,
    VALID_BITS,
    SQLiteTravelChecklistService,
)


class FakeBot:
    platform = "telegram"

    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    async def _post(self, method, data):
        self.calls.append((method, data))
        if self.fail == method:
            raise RuntimeError("simulated Bot API error")
        return True


class FakeMessage:
    chat = SimpleNamespace(type="private")
    chat_id = 123

    def __init__(self):
        self.reply_text = AsyncMock()


def query(data, *, who=123, where=123, mid=987, kind="private"):
    return Update(update_id=55, api_kwargs={"widget_query": {
        "id": "id-1", "from": {"id": who}, "chat": {"id": where, "type": kind},
        "message_id": mid, "data": data, "type": {"type": "data"},
    }})


def test_html_widget_uses_official_limits_and_localized_accessible_controls():
    raw = CHECKLIST_WIDGET_HTML.encode("utf-8")
    assert len(raw) <= 32768
    assert len(zlib.compress(raw, 9)) <= 4096
    assert "aria-pressed" in CHECKLIST_WIDGET_HTML
    assert "aria-valuenow" in CHECKLIST_WIDGET_HTML
    assert "chatDataChanged" in CHECKLIST_WIDGET_HTML
    assert "cl:t:" in CHECKLIST_WIDGET_HTML
    assert "cl:x:" in CHECKLIST_WIDGET_HTML
    assert "پرواز داخلی" in CHECKLIST_WIDGET_HTML
    assert "سفر خارجی" in CHECKLIST_WIDGET_HTML
    assert "تأیید پاک‌سازی" in CHECKLIST_WIDGET_HTML
    assert len(TASKS) == 15
    assert VALID_BITS["d"].bit_count() == 11
    assert VALID_BITS["i"].bit_count() == 15


@pytest.mark.asyncio
async def test_persistence_isolated_by_user_and_trip_mode_after_restart(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'checklist.db'}"
    db = await initialize_database(db_url)
    service = SQLiteTravelChecklistService(db)
    assert service is not None
    a = await service.get(123)
    assert a.progress() == (0, 11)
    first = await service.apply(123, "toggle", "d", 0)
    assert first.progress() == (1, 11)
    foreign = await service.apply(123, "toggle", "i", 3)
    assert foreign.progress() == (1, 15)
    assert foreign.domestic & 1
    await service.apply(456, "toggle", "i", 4)
    assert (await service.get(456)).progress() == (1, 15)
    assert foreign.revision == 2
    await db.close()

    restored = await initialize_database(db_url)
    saved = SQLiteTravelChecklistService(restored)
    assert (await saved.get(123)).domestic == 1
    assert (await saved.get(123)).international == (1 << 3)
    assert (await saved.get(456)).domestic == 0
    cleared = await saved.apply(123, "reset", "d")
    assert cleared.domestic == 0
    assert cleared.international == (1 << 3)
    assert (await saved.get(456)).international == (1 << 4)
    await restored.close()


@pytest.mark.asyncio
async def test_checklist_changes_are_atomic_across_concurrent_widget_taps(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'concurrent.db'}")
    service = SQLiteTravelChecklistService(db)
    await asyncio.gather(
        service.apply(88, "toggle", "d", 0),
        service.apply(88, "toggle", "d", 1),
    )
    state = await service.get(88)
    assert state.progress() == (2, 11)
    assert state.revision == 2
    await db.close()


@pytest.mark.asyncio
async def test_invalid_task_or_mode_does_not_mutate(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'validate.db'}")
    service = SQLiteTravelChecklistService(db)
    with pytest.raises(ValueError):
        await service.apply(123, "toggle", "d", 4)  # International-only visa.
    with pytest.raises(ValueError):
        await service.apply(123, "toggle", "x", 0)
    with pytest.raises(ValueError):
        await service.apply(123, "toggle", "d", 100)
    with pytest.raises(ValueError):
        await service.apply(True, "mode", "d")
    assert (await service.get(123)).revision == 0
    await db.close()


@pytest.mark.asyncio
async def test_open_widget_with_saved_state_and_graceful_unsupported_client():
    saved = SimpleNamespace(as_json=lambda: '{"m":"i","d":1,"i":8,"v":3}',
                            progress=lambda: (1, 15))
    service = SimpleNamespace(get=AsyncMock(return_value=saved))
    bot = FakeBot()
    message = FakeMessage()
    assert await send_checklist_widget(message, bot, service)
    assert bot.calls[0][0] == "sendWidget"
    assert bot.calls[0][1]["chat_data"] == saved.as_json()
    assert bot.calls[0][1]["allow_queries"] is True
    assert "caption" not in bot.calls[0][1]
    assert "public_data" not in bot.calls[0][1]

    fail = FakeBot("sendWidget")
    assert not await send_checklist_widget(message, fail, service)
    message.reply_text.assert_awaited_once()
    assert "1 از 15" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_widget_request_returns_saved_snapshot_and_edits_same_message():
    state = SimpleNamespace(as_json=lambda: '{"m":"d","d":1,"i":0,"v":1}')
    service = SimpleNamespace(apply=AsyncMock(return_value=state))
    bot = FakeBot()
    await handle_checklist_query(
        query("cl:t:d:0"), SimpleNamespace(bot=bot), service
    )
    service.apply.assert_awaited_once_with(123, "toggle", "d", 0)
    assert [name for name, _ in bot.calls] == [
        "answerWidgetQuery", "editMessageWidgetData",
    ]
    assert json.loads(bot.calls[0][1]["data"])["d"] == 1
    assert bot.calls[1][1] == {
        "chat_id": 123, "message_id": 987,
        "chat_data": state.as_json(),
    }


@pytest.mark.asyncio
async def test_refresh_and_mode_reset_only_from_authentic_private_owner():
    bot = FakeBot()
    state = SimpleNamespace(as_json=lambda: '{"m":"i","d":1,"i":0,"v":2}')
    service = SimpleNamespace(
        get=AsyncMock(return_value=state),
        apply=AsyncMock(return_value=state),
    )
    await handle_checklist_query(query("cl:s"), SimpleNamespace(bot=bot), service)
    service.get.assert_awaited_once_with(123)
    await handle_checklist_query(
        query("cl:x:i"), SimpleNamespace(bot=bot), service
    )
    service.apply.assert_awaited_once_with(123, "reset", "i", None)

    before = len(bot.calls)
    for bad in (
        query("cl:t:d:0", who=123, where=456),
        query("cl:t:d:4", kind="group"),
        query("cl:t:d:999"),
        query("cl:t:d:0", mid=0),
    ):
        await handle_checklist_query(bad, SimpleNamespace(bot=bot), service)
    assert len(bot.calls) == before + 4
    assert all(method == "answerWidgetQuery" for method, _ in bot.calls[before:])
    assert all(data["data"] == "invalid" for _, data in bot.calls[before:])
    service.apply.assert_awaited_once()


class ChecklistStartUsers:
    async def get_or_create_with_status(self, user_id, **fields):
        return SimpleNamespace(id=user_id), False

    async def get_language(self, user_id):
        return "fa"


class ChecklistStartAudit:
    def __init__(self):
        self.events = []

    async def record(self, event, **kwargs):
        self.events.append(event)


@pytest.mark.asyncio
async def test_checklist_start_deep_link_opens_widget_without_menu(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    bot = FakeBot()
    msg = FakeMessage()
    audit = ChecklistStartAudit()
    service = object()
    mock_send = AsyncMock()
    monkeypatch.setattr(handlers, "send_checklist_widget", mock_send)
    deps = TelegramDependencies(
        users=ChecklistStartUsers(), audit=audit,
        checklist_service=service, admin_chat_id=None,
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=123, username="traveler", first_name="Test", last_name=None
        ),
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=msg,
    )
    await start_handler(
        update, SimpleNamespace(args=["checklist"], bot=bot, user_data={}), deps
    )
    mock_send.assert_awaited_once_with(msg, bot, service)
    msg.reply_text.assert_not_awaited()
    assert "checklist.opened" in audit.events


@pytest.mark.asyncio
async def test_checklist_start_deep_link_on_bale_keeps_normal_menu(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    bot = FakeBot()
    bot.platform = "bale"
    msg = FakeMessage()
    mock_send = AsyncMock()
    monkeypatch.setattr(handlers, "send_checklist_widget", mock_send)
    deps = TelegramDependencies(
        users=ChecklistStartUsers(), audit=ChecklistStartAudit(),
        checklist_service=object(), admin_chat_id=None,
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=123, username="traveler", first_name="Test", last_name=None
        ),
        effective_chat=SimpleNamespace(id=123, type="private"),
        message=msg,
    )
    await start_handler(
        update, SimpleNamespace(args=["checklist"], bot=bot, user_data={}), deps
    )
    mock_send.assert_not_awaited()
    msg.reply_text.assert_awaited_once()
