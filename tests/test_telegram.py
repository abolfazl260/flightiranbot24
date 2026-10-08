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
        self.passports = {}

    async def get_or_create(self, telegram_id, **fields):
        self.users.setdefault(telegram_id, SimpleNamespace(id=telegram_id, **fields))
        return self.users[telegram_id]

    async def get_or_create_with_status(self, telegram_id, **fields):
        is_new = telegram_id not in self.users
        return await self.get_or_create(telegram_id, **fields), is_new

    async def get_language(self, user_id):
        return self.languages.get(user_id, "en")

    async def set_language(self, user_id, language):
        self.languages[user_id] = language

    async def get_visa_passport(self, user_id):
        return self.passports.get(user_id, "IR")

    async def set_visa_passport(self, user_id, passport):
        self.passports[user_id] = passport


class MemoryAudit:
    def __init__(self):
        self.events = []

    async def record(self, event_type, user_id=None, payload=None):
        self.events.append((event_type, user_id, payload))


class Message:
    def __init__(self):
        self.calls = []
        self.chat_id = 12345

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
    assert "🎫" in rendered
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
    commands = ("/start", "/help", "/language", "/price", "/visa")
    assert all(command in rendered for command in commands)
    assert message.calls[0][1]["parse_mode"] == "HTML"
    assert deps.audit.events[-1][0] == "user.help"


@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_flight_tracking_is_not_advertised(language):
    from flightiran.interfaces.telegram.keyboards import main_menu
    from flightiran.interfaces.telegram.renderers import render_help, render_main_menu

    callbacks = [
        button.callback_data
        for row in main_menu(language).inline_keyboard
        for button in row
    ]
    assert "menu:flights" not in callbacks
    assert "/flight" not in render_help(language)
    welcome = render_main_menu(language)
    assert "Flight alerts and notifications" not in welcome
    assert "اطلاعات پرواز و وضعیت پروازها" not in welcome
    assert "معلومات الرحلات وحالتها" not in welcome


@pytest.mark.asyncio
async def test_old_flight_menu_callback_no_longer_opens_flight_tracking():
    deps = dependencies()
    query = Query()
    query.data = "menu:flights"
    await callback_handler(update(query=query), None, deps)
    assert "/flight" not in query.calls[0][0][0]


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


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["fa", "en", "ar"])
async def test_ticket_origin_selection_sends_only_selected_city(monkeypatch, language):
    from flightiran.interfaces.telegram import handlers
    from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute

    class Feed:
        calls = 0

        async def routes(self):
            self.calls += 1
            return [
                CheapTicketRoute(
                    "تهران",
                    (CheapTicketDestination("مشهد", "7,000", 7_000, 10_000),),
                    "https://mz724.ir/",
                ),
                CheapTicketRoute(
                    "شیراز",
                    (CheapTicketDestination("کیش", "9,000", 9_000, 10_000),),
                    "https://mz724.ir/",
                ),
            ]

    sent = []

    async def send_rich(_bot, _chat_id, rich):
        sent.append(rich["html"])

    monkeypatch.setattr(handlers, "send_rich_price_table_with_badge_fallback", send_rich)
    feed = Feed()
    deps = dependencies(cheap_ticket_service=feed)
    deps.users.languages[42] = language
    state = SimpleNamespace(
        user_data={}, bot=SimpleNamespace(token="fake"),
    )

    chooser = Query()
    chooser.data = "menu:tickets"
    chooser.message = Message()
    await callback_handler(update(query=chooser), state, deps)
    assert feed.calls == 1
    assert sent == []
    keyboard = chooser.calls[-1][1]["reply_markup"]
    assert [button.text for row in keyboard.inline_keyboard
            for button in row if (button.callback_data or "").startswith("tickets:origin:")] == [
        "تهران", "شیراز"
    ]

    selected = Query()
    selected.data = "tickets:origin:1"
    selected.message = Message()
    await callback_handler(update(query=selected), state, deps)
    assert feed.calls == 1
    assert len(sent) == 1
    assert "شیراز" in sent[0]
    assert "تهران" not in sent[0]
    assert "مشهد" not in sent[0]
    assert "کیش" in sent[0]
    assert selected.message.calls[-1][1]["reply_markup"].inline_keyboard[1][0].callback_data == (
        "tickets:menu"
    )

    another = Query()
    another.data = "tickets:menu"
    await callback_handler(update(query=another), state, deps)
    assert feed.calls == 1
    assert any(
        button.callback_data == "tickets:origin:0"
        for row in another.calls[-1][1]["reply_markup"].inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_ticket_origin_invalid_index_and_expired_state_do_not_send():
    deps = dependencies()
    context = SimpleNamespace(user_data={}, bot=None)
    query = Query()
    query.data = "tickets:origin:999"
    await callback_handler(update(query=query), context, deps)
    assert query.calls[0][1]["reply_markup"].inline_keyboard
    assert "expired" in query.calls[0][0][0].lower()


def test_ticket_origin_keyboard_pagination_and_safe_callback_data():
    from flightiran.interfaces.telegram.keyboards import ticket_origins_menu

    cities = [f"شهر {i}" for i in range(38)]
    first = ticket_origins_menu("fa", cities)
    assert first.inline_keyboard[0][0].callback_data == "tickets:origin:0"
    assert first.inline_keyboard[0][1].callback_data == "tickets:origin:1"
    assert any(
        button.callback_data == "tickets:page:1"
        for row in first.inline_keyboard for button in row
    )
    last = ticket_origins_menu("fa", cities, page=2)
    assert last.inline_keyboard[0][0].callback_data == "tickets:origin:32"
    assert all(len(button.callback_data.encode()) <= 64
               for row in last.inline_keyboard for button in row
               if button.callback_data)


class MemoryVisaCatalog:
    async def ready(self):
        return True

    async def countries(self):
        from flightiran.modules.visa.catalog import Country
        return [
            Country("IR", "Iran"), Country("AF", "Afghanistan"), Country("TR", "Turkey")
        ]

    async def detail(self, passport, destination):
        return None

    async def distribution(self, passport):
        return {"visa-free": 1}


@pytest.mark.asyncio
@pytest.mark.parametrize("language, expected", [
    ("fa", "ایران"), ("en", "Iran"), ("ar", "إيران")
])
async def test_visa_menu_defaults_to_iran_and_allows_changing_passport(language, expected):
    from flightiran.interfaces.telegram.handlers import visa_handler, visa_list_handler
    deps = dependencies(visa_catalog=MemoryVisaCatalog())
    deps.users.languages[42] = language
    context = SimpleNamespace(user_data={}, args=[])
    entry = Query()
    entry.data = "menu:visa"
    await callback_handler(update(query=entry), context, deps)
    assert context.user_data["visa_passport"] == "IR"
    assert expected in entry.calls[0][0][0]
    buttons = [button.callback_data for row in entry.calls[0][1]["reply_markup"].inline_keyboard
               for button in row]
    assert "visa:pick:d:0" in buttons
    assert "visa:pick:p:0" in buttons

    chosen = Query()
    chosen.data = "visa:p:AF"
    await callback_handler(update(query=chosen), context, deps)
    assert deps.users.passports[42] == "AF"

    # Simulate a bot restart: Telegram user_data no longer exists.
    restored = SimpleNamespace(user_data={}, args=[])
    reopened = Query()
    reopened.data = "menu:visa"
    await callback_handler(update(query=reopened), restored, deps)
    assert restored.user_data["visa_passport"] == "AF"
    assert "AF" in reopened.calls[0][0][0]
    assert "IR" not in reopened.calls[0][0][0]

    list_message = Message()
    await visa_list_handler(update(message=list_message), restored, deps)
    assert "<code>AF</code>" in list_message.calls[0][0][0]

    # /visa without arguments must preserve an explicitly changed passport.
    visa_message = Message()
    await visa_handler(update(message=visa_message), restored, deps)
    assert "AF" in visa_message.calls[0][0][0]


@pytest.mark.asyncio
async def test_visa_list_defaults_to_iran_and_explicit_commands_are_saved():
    from flightiran.interfaces.telegram.handlers import visa_handler, visa_list_handler
    deps = dependencies(visa_catalog=MemoryVisaCatalog())
    context = SimpleNamespace(user_data={}, args=[])
    message = Message()
    await visa_list_handler(update(message=message), context, deps)
    assert "<code>IR</code>" in message.calls[0][0][0]
    assert deps.users.passports == {}

    context.args = ["AF", "TR"]
    await visa_handler(update(message=Message()), context, deps)
    assert deps.users.passports[42] == "AF"
    assert context.user_data["visa_destination"] == "TR"

    context.args = []
    reopened = Query()
    reopened.data = "menu:visa"
    await callback_handler(update(query=reopened), context, deps)
    assert context.user_data["visa_passport"] == "AF"


class AdminNotifications:
    def __init__(self, *, should_fail=False):
        self.calls = []
        self.should_fail = should_fail

    async def send_message(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("Telegram admin delivery failed")
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_new_user_start_alert_sent_once_with_profile_fields():
    deps = dependencies(admin_chat_id=987654)
    admin_bot = AdminNotifications()
    context = SimpleNamespace(bot=admin_bot, user_data={})
    incoming = update(message=Message())
    incoming.effective_user.username = "new_member_42"
    incoming.effective_user.language_code = "fa"
    incoming.effective_user.last_name = "<Admin>"
    incoming.effective_user.is_premium = True

    await start_handler(incoming, context, deps)
    assert len(admin_bot.calls) == 1
    notification = admin_bot.calls[0]
    assert notification["chat_id"] == 987654
    assert notification["parse_mode"] == "HTML"
    assert notification["disable_web_page_preview"] is True
    html = notification["text"]
    assert "🆕 کاربر جدید ربات" in html
    assert 'href="https://t.me/new_member_42"' in html
    assert "@new_member_42" in html
    assert "<code>42</code>" in html
    assert "&lt;Admin&gt;" in html
    assert "fa" in html
    assert "UTC" in html
    assert "تلگرام پریمیوم: بله" in html
    assert 'href="tg://user?id=42"' in html
    assert any(event[0] == "user.registered" for event in deps.audit.events)

    await start_handler(update(message=Message()), context, deps)
    assert len(admin_bot.calls) == 1
    assert sum(event[0] == "user.registered" for event in deps.audit.events) == 1


@pytest.mark.asyncio
async def test_existing_user_and_no_username_do_not_produce_false_alert():
    deps = dependencies()
    existing_user = await deps.users.get_or_create(42, username="previous")
    assert existing_user.id == 42
    admin_bot = AdminNotifications()
    await start_handler(
        update(message=Message()), SimpleNamespace(bot=admin_bot, user_data={}), deps
    )
    assert admin_bot.calls == []

    deps_new = dependencies()
    admin_bot = AdminNotifications()
    newcomer = update(message=Message())
    newcomer.effective_user.username = None
    newcomer.effective_user.first_name = "<b>Ali & Sara</b>"
    newcomer.effective_user.language_code = None
    await start_handler(
        newcomer, SimpleNamespace(bot=admin_bot, user_data={}), deps_new
    )
    assert len(admin_bot.calls) == 1
    html = admin_bot.calls[0]["text"]
    assert "یوزرنیم: ندارد" in html
    assert "&lt;b&gt;Ali &amp; Sara&lt;/b&gt;" in html
    assert "زبان تلگرام: ثبت نشده" in html


@pytest.mark.asyncio
async def test_new_user_alert_delivery_failure_does_not_break_start():
    deps = dependencies()
    user_message = Message()
    await start_handler(
        update(message=user_message),
        SimpleNamespace(bot=AdminNotifications(should_fail=True), user_data={}),
        deps,
    )
    assert len(user_message.calls) == 1
    assert "Welcome" in user_message.calls[0][0][0]
    assert 42 in deps.users.users
