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
    assert len(rendered_rows) == len(keyboard.inline_keyboard) == 4
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
        "tickets:menu", "menu:price_alerts", "back",
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
    assert [
        row[0].callback_data for row in keyboard.inline_keyboard[1:]
    ] == ["tickets:menu", "menu:price_alerts", "back"]
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
    assert len(booking) == 1
    assert "<tg-button-row" in booking[0]["html"]
    assert 'data="menu:price_alerts"' in booking[0]["html"]
    assert query.message.calls == []
    await database.close()
