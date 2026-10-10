"""Regression checks: no currency-rate feature remains in active bot or Android."""

from pathlib import Path

import pytest
from telegram.ext import CommandHandler

from flightiran.config.settings import Settings
from flightiran.interfaces.telegram.handlers import TelegramDependencies, register_handlers
from flightiran.interfaces.telegram.keyboards import main_menu
from flightiran.interfaces.telegram.renderers import render_help, render_main_menu
from flightiran.main import BOT_COMMAND_DESCRIPTIONS, create_application

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_exchange_rates_absent_from_bot_menu_and_help(language):
    labels = [button.text for row in main_menu(language).inline_keyboard for button in row]
    callbacks = [
        button.callback_data for row in main_menu(language).inline_keyboard for button in row
    ]
    assert "menu:currency" not in callbacks
    assert not any(term in " ".join(labels) for term in (
        "نرخ ارز", "Exchange rates", "العملة"
    ))
    help_text = render_help(language)
    welcome_text = render_main_menu(language)
    assert "/price" not in help_text
    assert "💱" not in help_text + welcome_text
    assert "price" not in BOT_COMMAND_DESCRIPTIONS[language]
    # Airfare price alerts are independent and must remain visible.
    assert "menu:price_alerts" in callbacks
    assert "/alerts" in help_text


def test_removed_command_not_registered_and_other_features_untouched():
    app = create_application(Settings(TELEGRAM_BOT_TOKEN="123456:AA-test-token"))
    register_handlers(app, TelegramDependencies(users=object(), audit=object()))
    commands = {
        name
        for group in app.handlers.values()
        for handler in group
        if isinstance(handler, CommandHandler)
        for name in handler.commands
    }
    assert "price" not in commands
    assert {"visa", "visa_watch", "alerts", "start", "help"} <= commands


def test_currency_implementation_and_old_scraper_are_removed():
    assert not (ROOT / "src/flightiran/modules/currency").exists()
    assert not (ROOT / "src/flightiran/interfaces/telegram/currency.py").exists()
    assert not (ROOT / "old/exchange.py").exists()
    assert not (ROOT / "tests/test_currency.py").exists()
    active = [
        "src/flightiran/main.py",
        "src/flightiran/interfaces/telegram/handlers.py",
        "src/flightiran/interfaces/telegram/keyboards.py",
        "src/flightiran/config/settings.py",
        ".env.example",
    ]
    for path in active:
        contents = (ROOT / path).read_text(encoding="utf-8")
        for key in ("CURRENCY_PROVIDER_URL", "CURRENCY_PROXY_URL", "menu:currency",
                    "CurrencyService", "HttpCurrencyProvider", "price_handler"):
            assert key not in contents, (path, key)


def test_android_no_longer_offers_dead_exchange_rate_button():
    layout = (ROOT / "android/app/src/main/res/layout/activity_main.xml").read_text()
    java = (ROOT / "android/app/src/main/java/com/abolfazl260/"
            "flightiranbot24/MainActivity.java").read_text()
    for text in (layout, java):
        assert "openCurrency" not in text
        assert "/price" not in text
    for language in ("values", "values-fa"):
        strings = (ROOT / f"android/app/src/main/res/{language}/strings.xml").read_text()
        assert "open_currency" not in strings
    # Visa deep-link/copy behavior survives.
    assert 'openBotCommand("/visa")' in java
