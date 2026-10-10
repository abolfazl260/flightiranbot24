"""End-to-end tests for the mz724 ticket price bell."""

from types import SimpleNamespace

import pytest

from flightiran.config.settings import Settings
from flightiran.db import initialize_database
from flightiran.db.models import User
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    callback_handler,
    message_handler,
    visa_cancel_handler,
)
from flightiran.interfaces.telegram.keyboards import main_menu, ticket_result_menu
from flightiran.interfaces.telegram.price_alerts import parse_alert_price
from flightiran.modules.tickets.alerts import PriceAlertService
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute
from flightiran.modules.tickets.service import CheapTicketService


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.calls = []
        self.message = SimpleNamespace(chat_id=901)

    async def answer(self):
        pass

    async def edit_message_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.calls = []

    async def reply_text(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class Audit:
    async def record(self, *args, **kwargs):
        pass


class TicketFeed:
    def __init__(self):
        self.calls = 0

    async def routes(self):
        self.calls += 1
        return [
            CheapTicketRoute(
                "تهران",
                (CheapTicketDestination("استانبول", "۶٬۰۰۰٬۰۰۰"),),
                "https://mz724.ir/",
            )
        ]


def update(query=None, message=None, uid=901, chat_type="private"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(
            id=uid, username="client", first_name="Example", last_name=None
        ),
        effective_chat=SimpleNamespace(id=uid, type=chat_type),
        callback_query=query,
        message=message,
    )


def ctx():
    return SimpleNamespace(user_data={})


def test_price_parser_accepts_fa_ar_en_but_not_injected_or_invalid():
    assert parse_alert_price("۵٬۰۰۰٬۰۰۰") == 5_000_000
    assert parse_alert_price("٥,٠٠٠,٠٠٠") == 5_000_000
    assert parse_alert_price("5000000") == 5_000_000
    for bad in ("5 میلیون", "-1000", "0", "1.50", "50 00", "999", "1e6"):
        with pytest.raises(ValueError):
            parse_alert_price(bad)


@pytest.mark.asyncio
async def test_private_user_can_create_and_manage_alert_through_telegram(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'bot_alerts.db'}")
    users = SQLiteUserRepository(db)
    alerts = PriceAlertService(db)
    feed = TicketFeed()
    deps = TelegramDependencies(
        users=users, audit=Audit(), price_alert_service=alerts,
        cheap_ticket_service=feed,
    )
    # Explicitly chosen English must remain available after the
    # default-language change.
    owner = await users.create(901)
    await users.set_language(owner.id, "en")
    context = ctx()

    for data, expected in (
        ("menu:price_alerts", "Ticket price alerts"),
        ("alerts:new", "Select the departure"),
        ("alerts:origin:0", "Select the destination"),
        ("alerts:select:0:0", "Set a price-drop alert"),
        ("alerts:mode:price", "5,000,000"),
    ):
        q = FakeQuery(data)
        await callback_handler(update(query=q), context, deps)
        assert expected in q.calls[-1][0][0]

    assert feed.calls == 1
    assert context.user_data["price_alert_pending"]["origin"] == "تهران"

    bad = FakeMessage("۵ میلیون")
    await message_handler(update(message=bad), context, deps)
    assert "positive price" in bad.calls[-1][0][0]
    assert context.user_data.get("price_alert_pending")

    good = FakeMessage("۵٬۰۰۰٬۰۰۰")
    await message_handler(update(message=good), context, deps)
    assert "Alert saved" in good.calls[-1][0][0]
    assert context.user_data.get("price_alert_pending") is None

    user = await users.get_by_telegram_id(901)
    stored = await alerts.list_user_alerts(user.id)
    assert len(stored) == 1
    assert (stored[0].origin, stored[0].destination) == ("تهران", "استانبول")
    assert stored[0].target_price == 5_000_000
    alert_id = stored[0].id

    q = FakeQuery(f"alerts:toggle:{alert_id}")
    await callback_handler(update(query=q), context, deps)
    assert (await alerts.list_user_alerts(user.id))[0].status == "paused"

    q = FakeQuery(f"alerts:toggle:{alert_id}")
    await callback_handler(update(query=q), context, deps)
    assert (await alerts.list_user_alerts(user.id))[0].status == "active"

    q = FakeQuery(f"alerts:delete:{alert_id}")
    await callback_handler(update(query=q), context, deps)
    assert await alerts.list_user_alerts(user.id) == []
    await db.close()


@pytest.mark.asyncio
async def test_price_feed_threshold_dedup_retry_and_owner_isolation(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'scanner.db'}")
    async with db.session() as session:
        session.add_all([User(telegram_id=10), User(telegram_id=20)])
    users = SQLiteUserRepository(db)
    a = await users.get_by_telegram_id(10)
    b = await users.get_by_telegram_id(20)
    alerts = PriceAlertService(db)

    route = await alerts.save_route(a.id, "تهران", "مشهد")
    assert (await alerts.save_route(a.id, "تهران", "مشهد")).id == route.id
    with pytest.raises(ValueError, match="belong"):
        await alerts.create(b.id, route.id, 4_000_000, "TOMAN")
    saved = await alerts.create(a.id, route.id, 5_000_000, "TOMAN")
    received = []

    async def notify(telegram_id, origin, destination, alert, snapshot):
        received.append((telegram_id, origin, destination, snapshot.price))

    assert await alerts.process_feed([("تهران", "مشهد", 6_000_000)], notify) == 0
    assert await alerts.process_feed([("تهران", "مشهد", 4_500_000)], notify) == 1
    assert await alerts.process_feed([("تهران", "مشهد", 4_500_000)], notify) == 0
    assert received == [(10, "تهران", "مشهد", 4_500_000)]

    assert not await alerts.set_user_status(b.id, saved.id, "paused")
    assert not await alerts.delete_user_alert(b.id, saved.id)
    assert await alerts.set_user_status(a.id, saved.id, "paused")
    assert await alerts.process_feed([("تهران", "مشهد", 3_000_000)], notify) == 0
    assert await alerts.set_user_status(a.id, saved.id, "active")
    assert await alerts.process_feed([("تهران", "مشهد", 4_500_000)], notify) == 1
    assert len(received) == 2
    assert await alerts.delete_user_alert(a.id, saved.id)
    assert await alerts.process_feed([("تهران", "مشهد", 2_000_000)], notify) == 0
    await db.close()


@pytest.mark.asyncio
async def test_failed_send_is_retried_on_next_feed_scan(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}")
    users = SQLiteUserRepository(db)
    user = await users.create(300)
    alerts = PriceAlertService(db)
    route = await alerts.save_route(user.id, "تهران", "دبی")
    await alerts.create(user.id, route.id, 5_000_000, "TOMAN")
    attempts = []

    async def unreliable(_telegram_id, _origin, _destination, _alert, snapshot):
        attempts.append(snapshot.id)
        if len(attempts) == 1:
            raise RuntimeError("Telegram unreachable")

    sample = [("تهران", "دبی", 4_000_000)]
    assert await alerts.process_feed(sample, unreliable) == 0
    assert await alerts.process_feed(sample, unreliable) == 1
    assert await alerts.process_feed(sample, unreliable) == 0
    assert attempts[0] == attempts[1]
    await db.close()


@pytest.mark.asyncio
async def test_cancel_price_prompt_does_not_require_provider(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'cancel.db'}")
    deps = TelegramDependencies(
        users=SQLiteUserRepository(db), audit=Audit(), price_alert_service=PriceAlertService(db),
    )
    context = ctx()
    context.user_data["price_alert_pending"] = {"origin": "تهران", "destination": "دبی"}
    msg = FakeMessage("/cancel")
    await visa_cancel_handler(update(message=msg), context, deps)
    assert context.user_data.get("price_alert_pending") is None
    assert "لغو شد" in msg.calls[-1][0][0]
    await db.close()


@pytest.mark.asyncio
async def test_hourly_capture_passes_provider_samples_without_second_fetch():
    provider = TicketFeed()
    cheap = CheapTicketService(provider)
    batches = []

    async def consume(samples):
        batches.append(samples)

    assert await cheap.capture_price_snapshot(on_samples=consume) == 1
    assert provider.calls == 1
    assert batches == [[("تهران", "استانبول", 6_000_000)]]


def test_price_bell_visible_in_ticket_menus_and_default_enabled():
    settings = Settings(TELEGRAM_BOT_TOKEN="123456:AA-test-token")
    assert settings.price_alerts_enabled
    for language in ("fa", "en", "ar"):
        assert any(
            b.callback_data == "menu:price_alerts"
            for row in main_menu(language).inline_keyboard for b in row
        )
        assert any(
            b.callback_data == "menu:price_alerts"
            for row in ticket_result_menu(language, "@advertio_support").inline_keyboard
            for b in row
        )
