"""Tests for free-form Telegram text handling outside guided flows."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from flightiran.interfaces.telegram import handlers
from flightiran.interfaces.telegram.handlers import TelegramDependencies, message_handler


def setup_message(language="fa", chat_type="private", *, context_data=None):
    users = SimpleNamespace(
        get_or_create=AsyncMock(return_value=SimpleNamespace(id=42)),
        get_language=AsyncMock(return_value=language),
    )
    dependencies = TelegramDependencies(
        users=users, audit=SimpleNamespace(), web_app_url=None
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        message=message,
        effective_chat=SimpleNamespace(id=42, type=chat_type),
        effective_user=SimpleNamespace(
            id=42, username="test", first_name="User", last_name=None
        ),
    )
    context = SimpleNamespace(user_data=context_data or {})
    return update, context, dependencies


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("fa", "این ربات در حال حاضر"),
        ("en", "does not process free-form messages"),
        ("ar", "لا يعالج الرسائل"),
    ],
)
async def test_free_text_shows_localized_guidance_and_menu(language, expected):
    update, context, dependencies = setup_message(language)

    await message_handler(update, context, dependencies)

    update.message.reply_text.assert_awaited_once()
    args, kwargs = update.message.reply_text.await_args
    assert expected in args[0]
    assert args[0] != "OK"
    callbacks = [
        button.callback_data
        for row in kwargs["reply_markup"].inline_keyboard
        for button in row
    ]
    assert "menu:visa" in callbacks
    assert "menu:support" in callbacks


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_type", ["group", "supergroup", "channel"])
async def test_free_text_in_nonprivate_chats_is_ignored(chat_type):
    update, context, dependencies = setup_message(chat_type=chat_type)

    await message_handler(update, context, dependencies)

    update.message.reply_text.assert_not_awaited()
    dependencies.users.get_or_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_guided_price_alert_text_retains_priority(monkeypatch):
    update, context, dependencies = setup_message(
        context_data={"price_alert_pending": {"step": "price"}}
    )
    dependencies.price_alert_service = object()
    alert_handler = AsyncMock(return_value=True)
    monkeypatch.setattr(handlers, "handle_alert_text", alert_handler)

    await message_handler(update, context, dependencies)

    alert_handler.assert_awaited_once()
    update.message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_guided_visa_search_text_retains_priority(monkeypatch):
    update, context, dependencies = setup_message(
        context_data={"visa_search_mode": "d"}
    )
    dependencies.visa_catalog = object()
    visa_handler = AsyncMock(return_value=True)
    monkeypatch.setattr(handlers, "visa_search_text", visa_handler)

    await message_handler(update, context, dependencies)

    visa_handler.assert_awaited_once()
    update.message.reply_text.assert_not_awaited()
