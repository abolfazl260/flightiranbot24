"""Rich in-message booking support actions and safe plain-HTML fallback."""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from flightiran.db import initialize_database
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.handlers import TelegramDependencies, callback_handler
from flightiran.interfaces.telegram.keyboards import ticket_result_menu
from flightiran.interfaces.telegram.tickets import (
    render_cheap_ticket_booking_hint,
    render_rich_ticket_booking_hint,
    send_ticket_booking_hint,
)
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute


@pytest.mark.parametrize(
    ("language", "intro"),
    [
        ("fa", "مسیر دلخواهتان را پیدا کرده‌اید"),
        ("en", "Found a route you like"),
        ("ar", "هل وجدت رحلة مناسبة"),
    ],
)
def test_booking_rich_message_embeds_all_real_actions(language, intro):
    support_username = "@Advertio_support"
    rich = render_rich_ticket_booking_hint(support_username, language)
    plain = render_cheap_ticket_booking_hint(support_username, language)
    keyboard = ticket_result_menu(language, support_username)
    html = rich["html"]

    assert intro in html
    assert "mz724" not in html.lower()
    assert "t.me/Advertio_support" in html
    assert "t.me/Advertio_support" in plain
    assert rich["is_rtl"] == (language in {"fa", "ar"})
    assert len(html) < 5000

    # Rich HTML is structurally valid. URL buttons and bot callback buttons
    # are real Telegram RichMessage actions, not decorative markup.
    root = ET.fromstring("<root>" + html + "</root>")
    assert root.find("h3") is not None
    assert root.findall("p")
    rendered_rows = root.findall("tg-button-row")
    assert len(rendered_rows) == len(keyboard.inline_keyboard) == 2
    assert all(len(row.findall("tg-button")) <= 2 for row in rendered_rows)
    assert all(row.get("align") == "center" for row in rendered_rows)

    for rich_row, fallback_row in zip(
        rendered_rows, keyboard.inline_keyboard, strict=True
    ):
        actual = rich_row.findall("tg-button")
        assert len(actual) == len(fallback_row)
        for button, expected in zip(actual, fallback_row, strict=True):
            assert button.text == expected.text
            if expected.url:
                assert button.attrib == {
                    "type": "url",
                    "style": "primary",
                    "url": expected.url,
                }
            else:
                assert button.attrib == {
                    "type": "callback_data", "data": expected.callback_data
                }
    assert [button.get("data") for button in root.findall(".//tg-button")
            if button.get("type") == "callback_data"] == [
        "menu:price_alerts", "tickets:menu", "back",
    ]


class FakeMessage:
    chat_id = 7001

    def __init__(self):
        self.calls = []

    async def reply_text(self, content, **kwargs):
        self.calls.append((content, kwargs))


@pytest.mark.asyncio
async def test_rich_booking_send_does_not_duplicate_text_or_inline_keyboard(monkeypatch):
    rich_messages = []

    async def send(bot, chat_id, rich):
        rich_messages.append((bot, chat_id, rich))

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.tickets.send_rich_price_table", send
    )
    message = FakeMessage()
    await send_ticket_booking_hint(
        object(), message, "@Advertio_support", "fa"
    )
    assert len(rich_messages) == 1
    assert rich_messages[0][1] == message.chat_id
    assert rich_messages[0][2]["html"].count("<tg-button ") == 4
    assert message.calls == []


@pytest.mark.asyncio
async def test_rich_booking_fails_over_to_existing_html_and_keyboard(monkeypatch, caplog):
    async def fail(*args):
        raise RuntimeError("private-token-should-not-enter-logs")

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.tickets.send_rich_price_table", fail
    )
    message = FakeMessage()
    with caplog.at_level("WARNING"):
        await send_ticket_booking_hint(
            object(), message, "@Advertio_support", "en"
        )
    assert len(message.calls) == 1
    content, kwargs = message.calls[0]
    assert "Found a route you like" in content
    assert kwargs["parse_mode"] == "HTML"
    keyboard = kwargs["reply_markup"]
    assert keyboard.inline_keyboard[0][0].url == (
        "https://t.me/Advertio_support"
    )
    assert [button.callback_data for row in keyboard.inline_keyboard
            for button in row if button.callback_data] == [
        "menu:price_alerts", "tickets:menu", "back",
    ]
    assert "private-token-should-not-enter-logs" not in caplog.text


class FakeQuery:
    data = "tickets:origin:0"

    def __init__(self):
        self.message = FakeMessage()
        self.calls = []

    async def answer(self):
        pass

    async def edit_message_text(self, content, **kwargs):
        self.calls.append((content, kwargs))


class Audit:
    async def record(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_selected_ticket_origin_sends_support_buttons_as_rich_message(
    monkeypatch, tmp_path
):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'rich-booking.db'}"
    )
    route = CheapTicketRoute(
        "تهران",
        (CheapTicketDestination("استانبول", "10,000,000"),),
        "https://mz724.ir/",
    )
    dependency = TelegramDependencies(
        users=SQLiteUserRepository(database),
        audit=Audit(),
        ticket_support_username="@Advertio_support",
    )
    query = FakeQuery()
    context = SimpleNamespace(
        user_data={"ticket_routes": [route]},
        bot=SimpleNamespace(token="unused"),
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=111, username=None, first_name="User", last_name=None
        ),
        effective_chat=SimpleNamespace(id=111, type="private"),
        callback_query=query,
    )
    tables = []
    booking = []

    async def send_table(bot, chat_id, rich):
        tables.append(rich)

    async def send_booking(bot, chat_id, rich):
        booking.append(rich)

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.handlers."
        "send_rich_price_table_with_badge_fallback",
        send_table,
    )
    monkeypatch.setattr(
        "flightiran.interfaces.telegram.tickets.send_rich_price_table",
        send_booking,
    )
    await callback_handler(update, context, dependency)
    assert len(query.calls) == 1
    assert len(tables) == 1
    assert booking == []  # The guidance is integrated into the fare table.
    html = tables[0]["html"]
    assert "مسیر دلخواهتان را پیدا کرده‌اید" in html
    assert "برای انتخاب مسیر یا رزرو" in html
    assert "<table bordered striped compact>" in html
    assert html.index("</table>") < html.index("مسیر دلخواهتان")
    assert '<a href="https://t.me/Advertio_support">@Advertio_support</a>' in html
    from xml.etree import ElementTree as ET
    xml = html.replace(
        "<table bordered striped compact>",
        '<table bordered="true" striped="true" compact="true">',
    )
    root = ET.fromstring("<root>" + xml + "</root>")
    rows = root.findall("tg-button-row")
    assert [len(row.findall("tg-button")) for row in rows] == [2, 2]
    buttons = [button for row in rows for button in row.findall("tg-button")]
    assert buttons[0].attrib["url"] == "https://t.me/Advertio_support"
    assert [button.attrib["data"] for button in buttons[1:]] == [
        "tickets:alert:0", "tickets:menu", "back",
    ]
    assert not any("tickets:book:" in button.attrib.get("data", "") for button in buttons)
    assert query.message.calls == []
    await database.close()


@pytest.mark.asyncio
async def test_bell_from_selected_fares_uses_cached_origin_without_new_fetch(
    monkeypatch, tmp_path,
):
    from flightiran.modules.tickets.alerts import PriceAlertService

    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'rich-bell.db'}"
    )
    route = CheapTicketRoute(
        "تهران",
        (
            CheapTicketDestination("مشهد", "10,000,000"),
            CheapTicketDestination("کیش", "8,000,000"),
        ),
        "https://mz724.ir/",
    )
    deps = TelegramDependencies(
        users=SQLiteUserRepository(database),
        audit=Audit(),
        price_alert_service=PriceAlertService(database),
        # No provider is configured: a second fetch would be impossible.
        cheap_ticket_service=None,
    )
    context = SimpleNamespace(
        bot=SimpleNamespace(token="unused"),
        user_data={"ticket_routes": [route], "alert_routes": [
            CheapTicketRoute("مشهد", (), "https://mz724.ir/")
        ]},
    )

    bells = []
    async def send_table(_bot, _chat_id, payload):
        bells.append(payload)

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.handlers."
        "send_rich_price_table_with_badge_fallback",
        send_table,
    )

    async def press(data):
        query = FakeQuery()
        query.data = data
        await callback_handler(
            SimpleNamespace(
                effective_user=SimpleNamespace(
                    id=111, username=None, first_name="User", last_name=None
                ),
                effective_chat=SimpleNamespace(id=111, type="private"),
                callback_query=query,
            ),
            context,
            deps,
        )
        return query

    await press("tickets:origin:0")
    assert len(bells) == 1
    assert 'data="tickets:alert:0"' in bells[0]["html"]
    query = await press("tickets:alert:0")
    assert context.user_data["alert_routes"] == [route]
    assert query.calls
    markup = query.calls[-1][1]["reply_markup"]
    assert [button.text for row in markup.inline_keyboard
            for button in row if button.callback_data.startswith("alerts:select:")] == [
        "مشهد", "کیش",
    ]
    assert query.message.calls == []
    await database.close()


@pytest.mark.asyncio
async def test_rich_ticket_table_failure_sends_one_combined_fallback_with_four_actions(
    monkeypatch, tmp_path, caplog,
):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'fare-fallback.db'}"
    )
    route = CheapTicketRoute(
        "تهران",
        (CheapTicketDestination("مشهد", "10,000,000"),),
        "https://mz724.ir/",
    )
    deps = TelegramDependencies(
        users=SQLiteUserRepository(database), audit=Audit(),
        ticket_support_username="@Advertio_support",
    )
    context = SimpleNamespace(
        bot=SimpleNamespace(token="topsecret"),
        user_data={"ticket_routes": [route]},
    )
    async def fail(*_args):
        raise RuntimeError("private-bot-token-unprintable")

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.handlers."
        "send_rich_price_table_with_badge_fallback",
        fail,
    )
    query = FakeQuery()
    with caplog.at_level("WARNING"):
        await callback_handler(
            SimpleNamespace(
                effective_user=SimpleNamespace(
                    id=111, username=None, first_name="User", last_name=None
                ),
                effective_chat=SimpleNamespace(id=111, type="private"),
                callback_query=query,
            ),
            context,
            deps,
        )
    # No duplicate explanatory message; the help belongs to the last fare
    # chunk, with one combined keyboard, at most two actions per row.
    assert len(query.message.calls) == 1
    content, kw = query.message.calls[0]
    assert "مشهد" in content
    assert "مسیر دلخواهتان را پیدا کرده‌اید" in content
    assert content.index("مشهد") < content.index("مسیر دلخواهتان")
    assert len(content) <= 4096
    assert content.count("@Advertio_support") == 1
    assert kw["parse_mode"] == "HTML"
    rows = kw["reply_markup"].inline_keyboard
    assert [len(row) for row in rows] == [2, 2]
    assert rows[0][0].url == "https://t.me/Advertio_support"
    assert rows[0][1].callback_data == "tickets:alert:0"
    assert rows[1][0].callback_data == "tickets:menu"
    assert rows[1][1].callback_data == "back"
    assert "private-bot-token-unprintable" not in caplog.text
    await database.close()
