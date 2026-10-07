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
