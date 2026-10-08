import pytest

from flightiran.config.settings import ConfigurationError, Settings, load_settings
from flightiran.main import create_application


def test_application_bootstrap_without_starting_polling() -> None:
    settings = Settings(TELEGRAM_BOT_TOKEN="123456:AA-test-token")
    application = create_application(settings)
    assert application.bot.token == "123456:AA-test-token"


def test_missing_token_has_safe_configuration_error(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    load_settings.cache_clear()

    try:
        load_settings()
    except ConfigurationError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
        assert "AA" not in str(exc)
    else:
        raise AssertionError("missing token should fail startup validation")
    finally:
        load_settings.cache_clear()



def test_support_uses_correct_default_and_migrates_obsolete_usernames(monkeypatch):
    monkeypatch.delenv("SUPPORT_USERNAME", raising=False)
    monkeypatch.delenv("TICKET_SUPPORT_USERNAME", raising=False)
    default = Settings(TELEGRAM_BOT_TOKEN="123456:AA-test-token")
    assert default.ticket_support_username == "@advertio_support"

    legacy = Settings(
        TELEGRAM_BOT_TOKEN="123456:AA-test-token",
        TICKET_SUPPORT_USERNAME="@vlansupport",
    )
    assert legacy.ticket_support_username == "@advertio_support"

    previous = Settings(
        TELEGRAM_BOT_TOKEN="123456:AA-test-token",
        SUPPORT_USERNAME="@advertio_bot",
    )
    assert previous.ticket_support_username == "@advertio_support"

    unified = Settings(
        TELEGRAM_BOT_TOKEN="123456:AA-test-token",
        SUPPORT_USERNAME="@advertio_support",
    )
    assert unified.ticket_support_username == "@advertio_support"


def test_flight_command_is_not_registered() -> None:
    from telegram.ext import CommandHandler

    from flightiran.interfaces.telegram.handlers import TelegramDependencies, register_handlers

    application = create_application(Settings(TELEGRAM_BOT_TOKEN="123456:AA-test-token"))
    register_handlers(application, TelegramDependencies(users=object(), audit=object()))
    registered = {
        command
        for handlers in application.handlers.values()
        for handler in handlers
        if isinstance(handler, CommandHandler)
        for command in handler.commands
    }
    assert "flight" not in registered
    assert {"start", "help", "price", "visa"}.issubset(registered)


@pytest.mark.asyncio
async def test_telegram_commands_replace_legacy_command_in_all_languages() -> None:
    from types import SimpleNamespace

    from flightiran.main import _sync_telegram_commands

    recorded = {}

    async def set_my_commands(commands, language_code=None):
        recorded[language_code or "default"] = [command.command for command in commands]

    await _sync_telegram_commands(SimpleNamespace(bot=SimpleNamespace(
        set_my_commands=set_my_commands
    )))
    assert set(recorded) == {"default", "fa", "en", "ar"}
    assert all("flight" not in commands for commands in recorded.values())
    assert all("visa" in commands for commands in recorded.values())
