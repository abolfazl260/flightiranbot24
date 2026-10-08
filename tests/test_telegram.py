from types import SimpleNamespace

import pytest

from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    language_handler,
    start_handler,
)
from flightiran.modules.airport.catalog import AirportCatalog


class MemoryUsers:
    def __init__(self):
        self.users = {}
        self.languages = {}

    async def get_or_create(self, telegram_id, **fields):
        self.users.setdefault(telegram_id, SimpleNamespace(id=telegram_id, **fields))
        return self.users[telegram_id]

    async def get_language(self, user_id):
        return self.languages.get(user_id, "en")

    async def set_language(self, user_id, language):
        self.languages[user_id] = language


class MemoryAudit:
    def __init__(self):
        self.events = []

    async def record(self, event_type, user_id=None, payload=None):
        self.events.append((event_type, user_id, payload))


class Message:
    def __init__(self):
        self.calls = []

    async def reply_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class Query(Message):
    data = "language:fa"

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def dependencies(**kwargs):
    return TelegramDependencies(MemoryUsers(), MemoryAudit(), **kwargs)


def update(message=None, query=None):
    user = SimpleNamespace(id=42, username="user", first_name="Test", last_name=None)
    return SimpleNamespace(effective_user=user, message=message, callback_query=query)


@pytest.mark.asyncio
async def test_start_and_language_change_are_persistent():
    deps = dependencies()
    message = Message()
    await start_handler(update(message=message), None, deps)
    assert "Welcome" in message.calls[0][0][0]
    assert message.calls[0][1]["parse_mode"] == "HTML"

    language_message = Message()
    await language_handler(update(message=language_message), None, deps)
    assert "Choose your language" in language_message.calls[0][0][0]

    query = Query()
    await callback_handler(update(query=query), None, deps)
    assert deps.users.languages[42] == "fa"
    assert deps.audit.events[-1][0] == "language.changed"


@pytest.mark.asyncio
async def test_unknown_callback_has_safe_fallback():
    deps = dependencies()
    query = Query()
    query.data = "unexpected"
    await callback_handler(update(query=query), None, deps)
    assert "unavailable" in query.calls[0][0][0]


@pytest.mark.asyncio
async def test_airport_menu_routes_to_catalog_and_selection():
    catalog = AirportCatalog.from_json(
        __import__("pathlib").Path("src/flightiran/modules/airport/data/airports.json")
    )
    deps = dependencies(airport_catalog=catalog)
    query = Query()
    query.data = "menu:airports"
    await callback_handler(update(query=query), None, deps)
    assert "فرودگاه" in query.calls[0][0][0]
    assert query.calls[0][1]["reply_markup"].inline_keyboard

    selected = Query()
    selected.data = "airport:IKA"
    await callback_handler(update(query=selected), None, deps)
    assert "IKA" in selected.calls[0][0][0]


@pytest.mark.asyncio
@pytest.mark.parametrize("language, greeting", [("fa", "سلام"), ("en", "Hello"), ("ar", "مرحباً")])
async def test_welcome_localized_and_html_escaped(language, greeting):
    from flightiran.interfaces.telegram.renderers import render_main_menu
    rendered = render_main_menu(language, "<Test>")
    assert greeting in rendered
    assert "&lt;Test&gt;" in rendered
    assert "<b>" in rendered
    assert "✈️" in rendered
    assert "💱" in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["fa", "en", "ar"])
async def test_help_handler_for_supported_languages(language):
    from flightiran.interfaces.telegram.handlers import help_handler
    deps = dependencies()
    deps.users.languages[42] = language
    message = Message()
    await help_handler(update(message=message), None, deps)
    rendered = message.calls[0][0][0]
    commands = ("/start", "/help", "/language", "/flight", "/price")
    assert all(command in rendered for command in commands)
    assert message.calls[0][1]["parse_mode"] == "HTML"
    assert deps.audit.events[-1][0] == "user.help"



@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_support_menu_has_correct_link_and_back_button(language):
    from flightiran.interfaces.telegram.keyboards import support_menu
    from flightiran.interfaces.telegram.support import render_support_message, support_url

    assert support_url("@advertio_support") == "https://t.me/advertio_support"
    markup = support_menu(language, "@advertio_support")
    assert markup.inline_keyboard[0][0].url == "https://t.me/advertio_support"
    assert markup.inline_keyboard[1][0].callback_data == "back"

    rendered = render_support_message(language, "@advertio_support")
    assert '<a href="https://t.me/advertio_support">@advertio_support</a>' in rendered
    assert "<b>" in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["fa", "en", "ar"])
async def test_support_callback_opens_advertio_contact(language):
    deps = dependencies()
    deps.users.languages[42] = language
    query = Query()
    query.data = "menu:support"
    await callback_handler(update(query=query), None, deps)

    rendered = query.calls[0][0][0]
    markup = query.calls[0][1]["reply_markup"]
    assert "@advertio_support" in rendered
    assert "https://t.me/advertio_support" in rendered
    assert markup.inline_keyboard[0][0].url == "https://t.me/advertio_support"
    assert deps.audit.events[-1][0] == "support.opened"


def test_support_username_rejects_invalid_handles():
    from flightiran.interfaces.telegram.support import support_url

    with pytest.raises(ValueError):
        support_url("<script>alert(1)</script>")


@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_help_displays_unified_support_contact(language):
    from flightiran.interfaces.telegram.renderers import render_help

    rendered = render_help(language)
    assert '<a href="https://t.me/advertio_support">@advertio_support</a>' in rendered



@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_cargo_marketplace_button_opens_advertio_cargo_channel(language):
    from flightiran.interfaces.telegram.keyboards import main_menu

    keyboard = main_menu(language)
    cargo_buttons = [
        button
        for row in keyboard.inline_keyboard
        for button in row
        if button.url == "https://t.me/advertio_cargo"
    ]
    assert len(cargo_buttons) == 1
    assert cargo_buttons[0].callback_data is None
    assert any(
        button.callback_data == "menu:useful"
        for row in keyboard.inline_keyboard
        for button in row
    )
