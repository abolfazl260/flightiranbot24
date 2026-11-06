"""Contract tests for the additive Bale transport; no real network/token needed."""

import pytest
from telegram.ext import CommandHandler, ExtBot

from flightiran.config.settings import ConfigurationError, Settings
from flightiran.interfaces.bale import BaleBot, telegram_html_to_bale_text
from flightiran.interfaces.telegram.handlers import TelegramDependencies, register_handlers
from flightiran.interfaces.telegram.rich_tickets import send_rich_price_table
from flightiran.main import create_application


def test_bale_uses_separate_token_and_database_and_original_handlers():
    settings = Settings(
        TELEGRAM_BOT_TOKEN="123456:telegram-test",
        BALE_BOT_TOKEN="654321:bale-test",
    )
    assert settings.bale_database_url != settings.database_url
    telegram = create_application(settings)
    bale = create_application(settings, platform="bale")
    assert telegram.bot.token == "123456:telegram-test"
    assert isinstance(bale.bot, BaleBot)
    assert bale.bot.token == "654321:bale-test"
    assert str(bale.bot.base_url).startswith("https://tapi.bale.ai/bot")
    assert str(bale.bot.base_file_url).startswith("https://tapi.bale.ai/file/bot")

    register_handlers(bale, TelegramDependencies(users=object(), audit=object()))
    commands = {
        command
        for handlers in bale.handlers.values()
        for handler in handlers if isinstance(handler, CommandHandler)
        for command in handler.commands
    }
    assert {"start", "help", "visa"}.issubset(commands)


def test_bale_token_required_only_for_bale(monkeypatch):
    monkeypatch.delenv("BALE_BOT_TOKEN", raising=False)
    settings = Settings(TELEGRAM_BOT_TOKEN="123456:telegram-test")
    assert create_application(settings).bot.token == "123456:telegram-test"
    with pytest.raises(ConfigurationError, match="BALE_BOT_TOKEN"):
        create_application(settings, platform="bale")


def test_html_is_plain_text_with_links_and_entities_preserved():
    result = telegram_html_to_bale_text(
        '<b>سلام</b> &amp; <a href="https://example.com/help">راهنما</a>'
        '<br>قیمت: &lt;1000&gt;'
    )
    assert "<b>" not in result
    assert result == "سلام & راهنما (https://example.com/help)\nقیمت: <1000>"


@pytest.mark.asyncio
async def test_bale_uses_plain_text_without_telegram_parse_mode(monkeypatch):
    captured = {}

    async def fake_post(_self, endpoint, data=None, **_kwargs):
        captured["endpoint"] = endpoint
        captured["data"] = data
        return True

    monkeypatch.setattr(ExtBot, "_post", fake_post)
    bot = BaleBot("654321:bale-test")
    result = await bot._post("sendMessage", {
        "chat_id": 44, "text": "<b>پرواز</b> &amp; قیمت",
        "parse_mode": "HTML", "disable_web_page_preview": True,
    })
    assert result is True
    assert captured["endpoint"] == "sendMessage"
    assert captured["data"]["text"] == "پرواز & قیمت"
    assert "parse_mode" not in captured["data"]
    assert "disable_web_page_preview" not in captured["data"]


@pytest.mark.asyncio
async def test_old_bale_callback_is_not_sent_to_unavailable_answer_endpoint(monkeypatch):
    async def must_not_post(*_args, **_kwargs):
        raise AssertionError("legacy callback must not hit Bale API")

    monkeypatch.setattr(ExtBot, "_post", must_not_post)
    bot = BaleBot("654321:bale-test")
    assert await bot._post("answerCallbackQuery", {"callback_query_id": "123456"}) is True


@pytest.mark.asyncio
async def test_bale_token_is_never_sent_to_telegram_rich_api():
    bot = BaleBot("654321:bale-test")
    with pytest.raises(NotImplementedError, match="Bale"):
        await send_rich_price_table(bot, 123, {"html": "<p>example</p>"})


def test_no_bale_admin_without_bale_admin_id():
    settings = Settings(
        TELEGRAM_BOT_TOKEN="123456:telegram-test",
        BALE_BOT_TOKEN="654321:bale-test",
    )
    assert settings.bale_admin_id is None
