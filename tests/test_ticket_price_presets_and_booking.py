"""Rich ticket booking buttons and historical, user-selectable price ceilings."""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from flightiran.db import initialize_database
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.handlers import TelegramDependencies, callback_handler
from flightiran.interfaces.telegram.price_alerts import (
    amount_keyboard,
    render_amount_prompt,
    suggested_price_ceiling_amounts,
)
from flightiran.interfaces.telegram.rich_tickets import render_rich_price_tables
from flightiran.interfaces.telegram.tickets import (
    render_ticket_reservation_request,
    send_ticket_reservation_request,
)
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute


class ChatMessage:
    chat_id = 9001

    def __init__(self):
        self.calls = []

    async def reply_text(self, text, **kwargs):
        self.calls.append((text, kwargs))


class Query:
    def __init__(self, data):
        self.data = data
        self.message = ChatMessage()
        self.edits = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


class Audit:
    def __init__(self):
        self.records = []

    async def record(self, event, **kwargs):
        self.records.append((event, kwargs))


class RouteService:
    def __init__(self):
        self.count = 0
        self.routes_data = [CheapTicketRoute(
            "تهران",
            (
                CheapTicketDestination(
                    "مشهد", "10,000,000", 10_000_000, 12_000_000, 24,
                ),
                CheapTicketDestination(
                    "استانبول", "12,000,000", 12_000_000, 13_000_000, 24,
                ),
            ),
            "https://mz724.ir/",
        )]

    async def routes(self):
        self.count += 1
        return self.routes_data


def update(query, user=8101):
    return SimpleNamespace(
        effective_user=SimpleNamespace(
            id=user, username=None, first_name="Example", last_name=None
        ),
        effective_chat=SimpleNamespace(id=user, type="private"),
        callback_query=query,
    )


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_amount_prompt_contains_actual_price_average_unit_and_valid_rich_buttons(
    language,
):
    pending = {
        "origin": "تهران & <city>",
        "destination": 'مشهد "test"',
        "current_price": 10_000_000,
        "average_price": 12_000_000,
        "average_samples": 24,
        "suggested_prices": suggested_price_ceiling_amounts(10_000_000, 12_000_000),
    }
    assert pending["suggested_prices"] == (
        10_000_000, 9_500_000, 9_000_000, 8_000_000,
    )
    plain = render_amount_prompt(language, pending)
    rich = render_amount_prompt(language, pending, rich=True)
    assert "10,000,000" in plain and "12,000,000" in plain
    assert "10,000,000" in rich and "12,000,000" in rich
    assert "24" in plain
    assert "&amp; &lt;city&gt;" in rich
    assert "mz724" not in rich.lower()
    assert {"fa": "تومان", "en": "tomans", "ar": "تومان"}[language] in rich
    root = ET.fromstring("<root>" + rich + "</root>")
    buttons = root.findall(".//tg-button")
    assert [b.attrib["data"] for b in buttons] == [
        "alerts:suggest:0", "alerts:suggest:1",
        "alerts:suggest:2", "alerts:suggest:3", "alerts:cancel",
    ]
    assert len(amount_keyboard(language, pending["suggested_prices"]).inline_keyboard) == 3


def test_suggested_ceiling_values_never_fabricate_an_unavailable_price():
    assert suggested_price_ceiling_amounts(None, None) == ()
    assert suggested_price_ceiling_amounts(None, 8_000_000) == (
        8_000_000, 7_600_000, 7_200_000, 6_400_000,
    )
    assert suggested_price_ceiling_amounts(10_000_000, 20_000_000)[0] == 10_000_000
    pending = {
        "origin": "تهران", "destination": "مشهد",
        "current_price": None, "average_price": None,
        "average_samples": 0, "suggested_prices": (),
    }
    rendered = render_amount_prompt("fa", pending, rich=True)
    assert "فعلاً موجود نیست" in rendered
    assert "هنوز داده تاریخی موجود نیست" in rendered
    assert "alerts:suggest:" not in rendered
    assert "alerts:cancel" in rendered


@pytest.mark.asyncio
async def test_rich_price_ceiling_buttons_save_selected_amount_and_use_cached_routes(
    monkeypatch, tmp_path
):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'choose.db'}")
    users = SQLiteUserRepository(db)
    service = PriceAlertService(db)
    provider = RouteService()
    deps = TelegramDependencies(
        users=users, audit=Audit(), cheap_ticket_service=provider,
        price_alert_service=service,
    )
    rich = []

    async def send(bot, chat_id, rich_message):
        rich.append((chat_id, rich_message))

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.price_alerts.send_rich_price_table", send
    )
    # Verify preset behavior in a stored, explicitly English locale.
    english_user = await users.create(8101)
    await users.set_language(english_user.id, "en")
    context = SimpleNamespace(user_data={}, bot=object())

    async def press(data):
        query = Query(data)
        await callback_handler(update(query), context, deps)
        return query

    for action in (
        "menu:price_alerts", "alerts:new",
        "alerts:origin:0", "alerts:select:0:0",
    ):
        await press(action)
    chosen = await press("alerts:mode:price")
    assert len(rich) == 1
    assert "10,000,000" in rich[0][1]["html"]
    assert "12,000,000" in rich[0][1]["html"]
    assert "suggest:2" in rich[0][1]["html"]
    assert chosen.edits[-1][0] == "👇 Suggested price options appear in the next message."
    assert provider.count == 1
    assert context.user_data["price_alert_pending"]["step"] == "price"

    invalid = await press("alerts:suggest:99")
    assert "positive price" in invalid.message.calls[-1][0]
    assert len(await service.list_user_alerts((await users.get_by_telegram_id(8101)).id)) == 0

    valid = await press("alerts:suggest:2")
    assert "9,000,000" in valid.message.calls[-1][0]
    assert context.user_data.get("price_alert_pending") is None
    owner = await users.get_by_telegram_id(8101)
    alerts = await service.list_user_alerts(owner.id)
    assert len(alerts) == 1
    assert alerts[0].target_price == 9_000_000
    assert alerts[0].threshold_type == "price"
    assert provider.count == 1

    old = await press("alerts:suggest:2")
    assert "expired" in old.edits[-1][0]
    assert len(await service.list_user_alerts(owner.id)) == 1
    await db.close()


@pytest.mark.asyncio
async def test_fallback_amount_keyboard_on_rich_transport_failure(monkeypatch, tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'fallback.db'}")
    deps = TelegramDependencies(
        users=SQLiteUserRepository(db), audit=Audit(),
        cheap_ticket_service=RouteService(), price_alert_service=PriceAlertService(db),
    )

    async def fail(bot, chat_id, rich_message):
        raise RuntimeError("fake-secret-http-error")

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.price_alerts.send_rich_price_table", fail
    )
    context = SimpleNamespace(user_data={}, bot=object())

    async def press(data):
        query = Query(data)
        await callback_handler(update(query), context, deps)
        return query

    for action in ("menu:price_alerts", "alerts:new", "alerts:origin:0",
                   "alerts:select:0:0"):
        await press(action)
    prompt = await press("alerts:mode:price")
    assert "10,000,000" in prompt.edits[-1][0]
    assert "12,000,000" in prompt.edits[-1][0]
    buttons = prompt.edits[-1][1]["reply_markup"].inline_keyboard
    assert buttons[0][0].callback_data == "alerts:suggest:0"
    assert buttons[1][0].callback_data == "alerts:suggest:2"
    await db.close()


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_price_list_rich_buttons_are_route_specific_and_all_visible(language):
    route = CheapTicketRoute(
        "تهران",
        tuple(CheapTicketDestination(
            f"مقصد <{i}>", "6,000,000", 6_000_000, 7_000_000, 18
        ) for i in range(75)),
        "https://mz724.ir/",
    )
    pages = render_rich_price_tables(route, language=language, booking_route_index=2)
    assert len(pages) == 2
    indices = []
    for page in pages:
        html = page["html"]
        assert html.index("</table>") < html.index("<tg-button-row")
        assert "mz724" not in html
        # Telegram accepts shorthand boolean table attributes, while XML
        # parsers require explicit values. Normalize only for this assertion.
        valid_xml = html.replace(
            "<table bordered striped compact>",
            '<table bordered="true" striped="true" compact="true">',
        )
        root = ET.fromstring("<root>" + valid_xml + "</root>")
        buttons = root.findall(".//tg-button[@type='callback_data']")
        assert buttons
        for button in buttons:
            assert button.text.startswith("🎫 ")
            assert "مقصد <" in button.text
            indices.append(int(button.attrib["data"].split(":")[-1]))
            assert button.attrib["data"].startswith("tickets:book:2:")
        assert html.count("<tr>") - 1 == len(buttons)
    assert indices == list(range(75))
    assert [p["is_rtl"] for p in pages] == [language != "en"] * 2
    # Legacy price table callers without index are unchanged.
    assert len(render_rich_price_tables(route, language=language)) == 1


@pytest.mark.asyncio
async def test_booking_button_resolves_exact_fare_and_support_without_new_fetch(
    monkeypatch, tmp_path
):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'reserve.db'}")
    routes = RouteService()
    audit = Audit()
    deps = TelegramDependencies(
        users=SQLiteUserRepository(db), audit=audit,
        ticket_support_username="@Advertio_support",
    )
    sent = []

    async def send(bot, chat_id, rich_message):
        sent.append(rich_message)

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.tickets.send_rich_price_table", send
    )
    context = SimpleNamespace(user_data={"ticket_routes": routes.routes_data}, bot=object())
    query = Query("tickets:book:0:0")
    await callback_handler(update(query), context, deps)
    assert len(sent) == 1
    html = sent[0]["html"]
    assert "تهران" in html and "مشهد" in html
    assert "10,000,000" in html and "12,000,000" in html
    root = ET.fromstring("<root>" + html + "</root>")
    assert root.find(".//tg-button").attrib["url"] == (
        "https://t.me/Advertio_support"
    )
    assert "mz724" not in html
    assert "ticket.booking.requested" in [evt for evt, _ in audit.records]
    assert routes.count == 0  # No price provider request for the booking button.
    assert query.message.calls == []

    wrong = Query("tickets:book:0:999")
    await callback_handler(update(wrong), context, deps)
    assert "منقضی" in wrong.message.calls[-1][0]
    assert len(sent) == 1
    await db.close()


@pytest.mark.asyncio
async def test_booking_support_rich_request_has_html_fallback(monkeypatch):
    async def fail(*args):
        raise RuntimeError("transient")

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.tickets.send_rich_price_table", fail
    )
    message = ChatMessage()
    item = CheapTicketDestination("مشهد", "5,000,000", 5_000_000, 6_000_000, 12)
    await send_ticket_reservation_request(
        object(), message, "تهران", item, "@Advertio_support", "fa"
    )
    assert len(message.calls) == 1
    text, options = message.calls[0]
    assert "تهران" in text and "مشهد" in text
    assert "5,000,000" in text and "6,000,000" in text
    assert options["reply_markup"].inline_keyboard[0][0].url == (
        "https://t.me/Advertio_support"
    )
    assert "<tg-button" not in text
    assert "رزرو" in render_ticket_reservation_request(
        "تهران", item, "@Advertio_support", "fa"
    )
