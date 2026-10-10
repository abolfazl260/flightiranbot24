"""Rich ticket-alert lists with per-alert controls and neutral date wording."""

from __future__ import annotations

import re
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from flightiran.db import initialize_database
from flightiran.db.models import PriceAlert, PriceSnapshot
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    alerts_command_handler,
    callback_handler,
)
from flightiran.interfaces.telegram.price_alerts import (
    WORDS,
    render_rich_alert_pages,
)
from flightiran.interfaces.telegram.price_notifications import render_ticket_alert
from flightiran.interfaces.telegram.rich_tickets import render_rich_price_drop_report
from flightiran.interfaces.telegram.tickets import (
    render_cheap_ticket_intro,
    render_ticket_reservation_request,
)
from flightiran.modules.tickets.alerts import PriceAlertService, UserPriceAlert
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute


class Message:
    chat_id = 100
    text = "/alerts"

    def __init__(self):
        self.calls = []
        self.deleted = False

    async def delete(self):
        self.deleted = True

    async def reply_text(self, message, **kwargs):
        self.calls.append((message, kwargs))


class Query:
    def __init__(self, callback: str):
        self.data = callback
        self.message = Message()
        self.calls = []

    async def answer(self):
        return None

    async def edit_message_text(self, message, **kwargs):
        self.calls.append((message, kwargs))


class Audit:
    async def record(self, *_args, **_kwargs):
        pass


def update(*, query=None, message=None, uid=100):
    return SimpleNamespace(
        callback_query=query,
        message=message,
        effective_chat=SimpleNamespace(id=uid, type="private"),
        effective_user=SimpleNamespace(
            id=uid, username="traveler", first_name="Traveler", last_name=None
        ),
    )


def alert(
    identifier: int, *, kind="price", status="active", origin="تهران",
    destination="مشهد",
) -> UserPriceAlert:
    return UserPriceAlert(
        id=identifier, origin=origin, destination=destination,
        target_price=5_000_000, status=status,
        threshold_type=kind,
        target_percent=10 if kind == "percent" else None,
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("fa", "کاهش 10٪ نسبت به میانگین قیمت"),
        ("en", "10% below the recorded average"),
        ("ar", "انخفاض 10٪ عن متوسط الأسعار"),
    ],
)
def test_rich_alert_controls_immediately_follow_their_respective_alerts(language, expected):
    items = [
        alert(12, kind="percent", destination="مشهد <Test>"),
        alert(14, status="paused", destination="کیش"),
        alert(17, destination="استانبول"),
    ]
    pages = render_rich_alert_pages(items, language)
    assert len(pages) == 1
    rich = pages[0]
    assert rich["is_rtl"] == (language in {"fa", "ar"})
    html = rich["html"]
    assert expected in html
    assert "مشهد &lt;Test&gt;" in html
    assert "<script" not in html
    assert "21-day" not in html
    assert "۲۱" not in html
    assert "٢١" not in html
    root = ET.fromstring("<root>" + html + "</root>")
    assert root.find("h3") is not None
    rows = root.findall("tg-button-row")
    assert [len(row.findall("tg-button")) for row in rows] == [2, 2, 2, 1, 1]
    assert all(row.get("align") == "center" for row in rows)
    assert root.findall("p")
    for item, row in zip(items, rows[:3], strict=False):
        buttons = row.findall("tg-button")
        assert [b.get("data") for b in buttons] == [
            f"alerts:toggle:{item.id}", f"alerts:delete:{item.id}",
        ]
        assert all(b.get("type") == "callback_data" for b in buttons)
        # The alert's details occur before its button row and before the next
        # alert's details. Buttons are not collected at the bottom of a keyboard.
        assert html.index(f"#{item.id}") < html.index(
            f'data="alerts:toggle:{item.id}"'
        )
        if item.id != items[-1].id:
            next_item = items[items.index(item) + 1]
            assert html.index(f'data="alerts:delete:{item.id}"') < html.index(
                f"#{next_item.id}"
            )
    assert rows[-2].find("tg-button").get("data") == "alerts:new"
    assert rows[-1].find("tg-button").get("data") == "back"


def test_rich_alert_pages_keep_long_paused_histories_within_telegram_limits():
    items = [
        alert(i, status="paused", destination=f"مقصد {i} & <X>")
        for i in range(1, 126)
    ]
    pages = render_rich_alert_pages(items, "fa")
    assert len(pages) == 3
    assert sum(page["html"].count('data="alerts:delete:') for page in pages) == 125
    for page in pages:
        assert len(page["html"]) <= 32_000
        root = ET.fromstring("<root>" + page["html"] + "</root>")
        assert all(len(row.findall("tg-button")) <= 2
                   for row in root.findall("tg-button-row"))


@pytest.mark.asyncio
async def test_alert_menu_toggle_delete_render_rich_and_enforce_ownership(
    monkeypatch, tmp_path
):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'rich-alert-management.sqlite3'}"
    )
    users = SQLiteUserRepository(database)
    owner = await users.create(100)
    other = await users.create(200)
    service = PriceAlertService(database)
    route = await service.save_route(owner.id, "تهران", "مشهد")
    a = await service.create(owner.id, route.id, 6_000_000, "TOMAN")
    b = await service.create_percent(owner.id, route.id, 10)
    deps = TelegramDependencies(users=users, audit=Audit(), price_alert_service=service)
    pages = []

    async def send(_bot, chat_id, rich):
        pages.append((chat_id, rich))

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.price_alerts.send_rich_price_table", send
    )
    context = SimpleNamespace(user_data={}, bot=SimpleNamespace(token="not-used"))
    initial = Query("menu:price_alerts")
    await callback_handler(update(query=initial), context, deps)
    assert initial.calls == []
    assert initial.message.deleted
    assert len(pages) == 1
    html = pages[-1][1]["html"]
    assert pages[-1][0] == 100
    assert f'data="alerts:toggle:{a.id}"' in html
    assert f'data="alerts:toggle:{b.id}"' in html
    assert "میانگین قیمت" in html

    change = Query(f"alerts:toggle:{a.id}")
    await callback_handler(update(query=change), context, deps)
    assert next(
        item.status for item in await service.list_user_alerts(owner.id)
        if item.id == a.id
    ) == "paused"
    assert "▶️ فعال‌سازی" in pages[-1][1]["html"]
    assert change.message.deleted

    foreign = Query(f"alerts:delete:{a.id}")
    await callback_handler(update(query=foreign, uid=200), context, deps)
    assert "تعلق ندارد" in foreign.calls[0][0]
    assert len(await service.list_user_alerts(owner.id)) == 2

    remove = Query(f"alerts:delete:{b.id}")
    await callback_handler(update(query=remove), context, deps)
    assert len(await service.list_user_alerts(owner.id)) == 1
    assert f'data="alerts:delete:{b.id}"' not in pages[-1][1]["html"]
    assert other.id != owner.id
    await database.close()


@pytest.mark.asyncio
async def test_rich_alert_api_failure_uses_safe_html_keyboard_without_leaking_token(
    monkeypatch, tmp_path, caplog
):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'rich-alert-fallback.sqlite3'}"
    )
    users = SQLiteUserRepository(database)
    owner = await users.create(100)
    service = PriceAlertService(database)
    route = await service.save_route(owner.id, "تهران", "استانبول")
    item = await service.create(owner.id, route.id, 5_000_000, "TOMAN")
    deps = TelegramDependencies(users=users, audit=Audit(), price_alert_service=service)

    async def fail(*_args):
        raise RuntimeError("super-secret-token-not-for-logs")

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.price_alerts.send_rich_price_table",
        fail,
    )
    context = SimpleNamespace(user_data={}, bot=SimpleNamespace(token="test"))
    query = Query("alerts:menu")
    with caplog.at_level("WARNING"):
        await callback_handler(update(query=query), context, deps)
    assert len(query.calls) == 1
    message, options = query.calls[0]
    assert "استانبول" in message
    assert "21" not in message
    assert options["parse_mode"] == "HTML"
    keyboard = options["reply_markup"].inline_keyboard
    assert len(keyboard[0]) == 2
    assert [b.callback_data for b in keyboard[0]] == [
        f"alerts:toggle:{item.id}", f"alerts:delete:{item.id}",
    ]
    assert "super-secret-token-not-for-logs" not in caplog.text
    assert not query.message.deleted
    await database.close()


@pytest.mark.asyncio
async def test_alerts_command_uses_rich_list_instead_of_plain_inline_keyboard(
    monkeypatch, tmp_path,
):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'rich-alerts-command.sqlite3'}"
    )
    users = SQLiteUserRepository(database)
    user = await users.create(100)
    await users.set_language(user.id, "en")
    service = PriceAlertService(database)
    route = await service.save_route(user.id, "Tehran", "Kish")
    await service.create(user.id, route.id, 9_000_000, "TOMAN")
    deps = TelegramDependencies(users=users, audit=Audit(), price_alert_service=service)
    rich_pages = []

    async def send(_bot, _chat_id, content):
        rich_pages.append(content)

    monkeypatch.setattr(
        "flightiran.interfaces.telegram.price_alerts.send_rich_price_table", send
    )
    message = Message()
    context = SimpleNamespace(user_data={}, bot=SimpleNamespace(token="fake"))
    await alerts_command_handler(update(message=message), context, deps)
    assert not message.calls
    assert len(rich_pages) == 1
    assert 'data="alerts:toggle:' in rich_pages[0]["html"]
    assert "recorded average" in " ".join(WORDS["en"].values())
    await database.close()


@pytest.mark.parametrize("language", ["fa", "en", "ar"])
def test_all_fare_notification_surfaces_hide_averaging_window(language):
    words = WORDS[language]
    route = CheapTicketRoute(
        "تهران",
        (CheapTicketDestination(
            "مشهد", "7,000,000", 7_000_000, 10_000_000, 3
        ),),
        "https://mz724.ir/",
    )
    percent_alert = PriceAlert(
        user_id=1, route_id=1, target_price=0, currency="TOMAN",
        threshold_type="percent", target_percent=10,
    )
    snapshot = PriceSnapshot(
        alert_id=1, price=7_000_000, reference_average_toman=10_000_000,
        snapshot_hash="test", notified=True,
    )
    messages = [
        *words.values(),
        render_ticket_alert("تهران", "مشهد", percent_alert, snapshot, language),
        render_cheap_ticket_intro(),
        render_ticket_reservation_request(
            "تهران", route.destinations[0], "@Advertio_support", language
        ),
        *[page["html"] for page in render_rich_price_drop_report([route])],
        *[page["html"] for page in render_rich_alert_pages(
            [alert(1, kind="percent")], language
        )],
    ]
    forbidden = re.compile(
        r"۲۱\s*روز|٢١\s*(?:يوماً|يوم)|21\s*[- ]\s*day",
        re.IGNORECASE,
    )
    for text in messages:
        assert not forbidden.search(text)
