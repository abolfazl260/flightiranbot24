"""Regression tests for the Telegram Bot API 10.4 interactive help centre."""

import zlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.help_widget import (
    COMMANDS,
    OPEN_ACTION,
    SERVICE_IDS,
    WORDS,
    PrivateChatMessage,
    handle_help_widget_query,
    help_widget_html,
    send_help_widget,
)
from flightiran.interfaces.telegram.keyboards import main_menu


class FakeBot:
    platform = "telegram"

    def __init__(self, fail_method=None):
        self.calls = []
        self.fail_method = fail_method
        self.send_message = AsyncMock()

    async def _post(self, method, data):
        self.calls.append((method, data))
        if self.fail_method == method:
            raise RuntimeError("simulated transport refusal")
        return True


class FakeMessage:
    chat = SimpleNamespace(type="private")
    chat_id = 123

    def __init__(self):
        self.reply_text = AsyncMock()


def query(data, *, who=123, chat=123, chat_type="private", widget_id=None):
    raw = {
        "id": "query-help-1", "data": data, "from": {"id": who},
        "chat": {"id": chat, "type": chat_type}, "message_id": 99,
        "type": {"type": "data"},
    }
    if widget_id is not None:
        raw["widget_id"] = widget_id
    return Update(1, api_kwargs={"widget_query": raw})


def test_all_three_language_widgets_are_self_contained_and_within_limits():
    assert set(WORDS) == {"fa", "en", "ar"}
    for locale in WORDS:
        html = help_widget_html(locale)
        assert len(html.encode("utf-8")) <= 32768
        assert len(zlib.compress(html.encode("utf-8"), 9)) <= 4096
        assert "__DATA__" not in html
        assert "__LANG__" not in html
        assert "__DIR__" not in html
        assert f'lang="{locale}"' in html
        assert 'id="tservices"' in html
        assert 'id="tcommands"' in html
        assert 'id="tfaq"' in html
        assert "W.request('hp:open:'+id)" in html
        assert 'role="tabpanel"' in html
        assert "aria-selected" in html
        assert ".tabs button.sel" in html
        assert 'role="status"' in html
    assert 'dir="rtl"' in help_widget_html("fa")
    assert 'dir="ltr"' in help_widget_html("en")


def test_service_actions_map_to_real_commands_and_have_descriptions():
    command_ids = {key for key, _ in COMMANDS}
    assert set(SERVICE_IDS).issubset(command_ids)
    for language, words in WORDS.items():
        assert [s[0] for s in words["services"]] == list(SERVICE_IDS)
        assert all(s[1] and s[2] and s[3] for s in words["services"])
        assert command_ids == set(words["commands"]), language
        assert len(words["faqs"]) == 4
        assert all(q and a for q, a in words["faqs"])
    for code in (*SERVICE_IDS, "visa_watch", "visa_list", "start", "language", "support"):
        assert OPEN_ACTION.fullmatch(f"hp:open:{code}")
    for bad in ("hp:open:visa_sync", "hp:open:admin", "hp:open:cancel",
                "hp:open:../../etc", "hp:open:foo"):
        assert not OPEN_ACTION.fullmatch(bad)


@pytest.mark.asyncio
async def test_help_widget_is_sent_inside_private_chat():
    bot = FakeBot()
    msg = FakeMessage()
    assert await send_help_widget(msg, bot, "fa", "@advertio_support")
    assert bot.calls[0][0] == "sendWidget"
    assert bot.calls[0][1]["chat_id"] == 123
    assert bot.calls[0][1]["allow_queries"] is True
    assert "چطور می‌تونیم" in bot.calls[0][1]["html"]
    msg.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_bale_group_and_unsupported_telegram_get_original_text_help():
    for platform, chat_type, fail_method in (
        ("bale", "private", None),
        ("telegram", "group", None),
        ("telegram", "private", "sendWidget"),
    ):
        bot = FakeBot(fail_method)
        bot.platform = platform
        msg = FakeMessage()
        msg.chat = SimpleNamespace(type=chat_type)
        assert not await send_help_widget(msg, bot, "fa", "@advertio_support")
        msg.reply_text.assert_awaited_once()
        assert "/start" in msg.reply_text.await_args.args[0]
        assert msg.reply_text.await_args.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_help_query_acks_first_then_opens_real_service():
    bot = FakeBot()
    op = AsyncMock()
    await handle_help_widget_query(
        query("hp:open:fares"), SimpleNamespace(bot=bot), op,
    )
    assert bot.calls == [("answerWidgetQuery", {
        "widget_query_id": "query-help-1", "data": "accepted",
    })]
    op.assert_awaited_once_with("fares", 123)


@pytest.mark.asyncio
async def test_help_queries_reject_wrong_chat_and_unallowlisted_actions():
    bot = FakeBot()
    op = AsyncMock()
    for q in (
        query("hp:open:fares", who=123, chat=456),
        query("hp:open:fares", chat_type="group"),
        query("hp:open:admin"),
        query("hp:open:fares", widget_id="shared-widget"),
        query("hp:open:/help"),
    ):
        bot.calls.clear()
        await handle_help_widget_query(q, SimpleNamespace(bot=bot), op)
        assert bot.calls == [("answerWidgetQuery", {
            "widget_query_id": "query-help-1", "data": "invalid",
        })]
    op.assert_not_awaited()


@pytest.mark.asyncio
async def test_help_query_failure_never_leaks_error_and_sends_fallback():
    bot = FakeBot()
    op = AsyncMock(side_effect=RuntimeError("private token must not leak"))
    await handle_help_widget_query(
        query("hp:open:airports"), SimpleNamespace(bot=bot), op,
    )
    assert bot.calls[0][1]["data"] == "accepted"
    bot.send_message.assert_awaited_once()
    sent = bot.send_message.await_args.kwargs
    assert sent["chat_id"] == 123
    assert "private token" not in sent["text"]


@pytest.mark.asyncio
async def test_private_chat_message_is_compatible_with_existing_services():
    bot = FakeBot()
    message = PrivateChatMessage(bot, 123)
    assert message.chat.type == "private"
    assert message.chat_id == 123
    await message.reply_text("hello", parse_mode="HTML")
    bot.send_message.assert_awaited_once_with(
        chat_id=123, text="hello", parse_mode="HTML",
    )


def test_help_menu_button_appears_only_when_telegram_widgets_enabled():
    def actions(keyboard):
        return [
            item.callback_data
            for row in keyboard.inline_keyboard for item in row
        ]
    assert "menu:help_widget" in actions(main_menu("fa", widgets_enabled=True))
    assert "menu:help_widget" not in actions(main_menu("fa", widgets_enabled=False))


@pytest.mark.asyncio
async def test_help_service_dispatch_opens_real_fares_handler(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    bot = FakeBot()
    service = object()
    send = AsyncMock()
    monkeypatch.setattr(handlers, "send_fare_widget", send)
    dependencies = handlers.TelegramDependencies(
        users=SimpleNamespace(
            get_by_telegram_id=AsyncMock(return_value=SimpleNamespace(id=55)),
            get_language=AsyncMock(return_value="fa"),
        ),
        audit=SimpleNamespace(record=AsyncMock()), cheap_ticket_service=service,
    )
    await handlers._open_help_service(
        "fares", 123, SimpleNamespace(bot=bot), dependencies,
    )
    send.assert_awaited_once()
    dependencies.users.get_language.assert_awaited_once_with(55)
    dependencies.audit.record.assert_awaited_once_with(
        "user.help.service", user_id=55, payload={"service": "fares"},
    )
    assert isinstance(send.await_args.args[0], PrivateChatMessage)
    assert send.await_args.args[1] is bot
    assert send.await_args.args[2] is service


@pytest.mark.asyncio
async def test_help_dispatch_visa_uses_authenticated_user_storage(monkeypatch):
    from flightiran.interfaces.telegram import handlers

    bot = FakeBot()
    user_data = {123: {"visa_passport": "IR"}}
    ctx = SimpleNamespace(
        bot=bot, application=SimpleNamespace(user_data=user_data),
    )
    open_visa = AsyncMock()
    monkeypatch.setattr(handlers, "open_visa_menu", open_visa)
    deps = handlers.TelegramDependencies(
        users=SimpleNamespace(
            get_by_telegram_id=AsyncMock(return_value=SimpleNamespace(id=55)),
            get_language=AsyncMock(return_value="fa"),
        ),
        audit=SimpleNamespace(record=AsyncMock()),
        visa_catalog=object(),
    )
    await handlers._open_help_service("visa", 123, ctx, deps)
    open_visa.assert_awaited_once()
    args = open_visa.await_args.args
    assert isinstance(args[0].message, PrivateChatMessage)
    assert args[1].user_data is user_data[123]
    assert args[2] is deps.visa_catalog
    assert open_visa.await_args.kwargs == {"edit": False}
    assert deps.users.get_language.await_args.args == (55,)



@pytest.mark.asyncio
async def test_unregistered_help_request_does_not_open_service():
    from flightiran.interfaces.telegram import handlers

    bot = FakeBot()
    deps = handlers.TelegramDependencies(
        users=SimpleNamespace(
            get_by_telegram_id=AsyncMock(return_value=None),
            get_language=AsyncMock(),
        ),
        audit=SimpleNamespace(record=AsyncMock()),
    )
    with pytest.raises(ValueError, match="not registered"):
        await handlers._open_help_service(
            "fares", 123, SimpleNamespace(bot=bot), deps,
        )
    deps.audit.record.assert_not_awaited()
    deps.users.get_language.assert_not_awaited()
