"""A route chart must display only observed prices and real missing-day gaps."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from flightiran.db.engine import initialize_database
from flightiran.db.models import Mz724PriceSnapshot
from flightiran.db.repositories import (
    RouteDailyMinimum,
    SQLiteMz724PriceHistoryRepository,
)
from flightiran.interfaces.telegram.route_chart import (
    handle_chart_callback,
    open_chart_picker,
    render_route_chart_html,
)


def sample(day: int, price: int, count: int = 1) -> RouteDailyMinimum:
    return RouteDailyMinimum(
        day=date(2026, 11, day),
        min_price_toman=price,
        sample_count=count,
        last_captured_at=datetime(2026, 11, day, 12, tzinfo=timezone.utc),
    )


def test_chart_renders_real_minimums_and_leaves_missing_days_disconnected():
    chart = render_route_chart_html(
        "تهران", "مشهد", [sample(7, 2_000_000, 3), sample(9, 2_400_000)],
        as_of=date(2026, 11, 9),
    )
    assert "تهران" in chart and "مشهد" in chart
    assert "۲٬۰۰۰٬۰۰۰" in chart and "۲٬۴۰۰٬۰۰۰" in chart
    assert 'r="4.1"' in chart
    assert chart.count('r="4.1"') == 2
    assert 'stroke="#159979"' not in chart  # no line across Nov 8
    assert "روزهای بدون ثبت" in chart
    assert "از ۲۱" in chart


def test_chart_connects_only_consecutive_real_days():
    chart = render_route_chart_html(
        "تهران", "مشهد", [sample(8, 2_000_000), sample(9, 2_400_000)],
        as_of=date(2026, 11, 9),
    )
    assert chart.count('stroke="#159979"') == 1
    assert chart.count('r="4.1"') == 2


def test_one_observation_is_not_misrepresented_as_a_trend():
    chart = render_route_chart_html(
        "شیراز", "کیش", [sample(9, 1_500_000)], as_of=date(2026, 11, 9)
    )
    assert "تنها یک روز داده موجود است" in chart
    assert 'stroke="#159979"' not in chart
    with pytest.raises(ValueError):
        render_route_chart_html("تهران", "مشهد", [])


@pytest.mark.asyncio
async def test_history_queries_exact_routes_real_daily_minimums_and_date_bounds(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path}/chart-test.db")
    try:
        async with db.session() as session:
            session.add_all([
                Mz724PriceSnapshot(
                    origin=origin, destination=destination,
                    price_toman=price,
                    captured_at=datetime(2026, month, day, hour, tzinfo=timezone.utc),
                )
                for origin, destination, price, month, day, hour in [
                    ("تهران", "مشهد", 2_500_000, 11, 7, 9),
                    ("تهران", "مشهد", 2_100_000, 11, 7, 17),
                    ("تهران", "مشهد", 2_800_000, 11, 9, 11),
                    ("تهران", "کیش", 4_000_000, 11, 8, 10),
                    ("شیراز", "کیش", 9_000_000, 10, 1, 10),
                    ("تهران", "مشهد", 8_000_000, 11, 10, 10),
                ]
            ])
        repo = SQLiteMz724PriceHistoryRepository(db)
        now = datetime(2026, 11, 9, 20, tzinfo=timezone.utc)
        routes = await repo.list_chart_routes(now=now)
        assert routes == [("تهران", "مشهد"), ("تهران", "کیش")] or routes == [
            ("تهران", "کیش"), ("تهران", "مشهد")
        ]
        days = await repo.get_route_daily_minimums("تهران", "مشهد", now=now)
        assert [(x.day.isoformat(), x.min_price_toman, x.sample_count)
                for x in days] == [
                    ("2026-11-07", 2_100_000, 2),
                    ("2026-11-09", 2_800_000, 1),
                ]
        assert await repo.get_route_daily_minimums("شیراز", "کیش", now=now) == []
        assert await repo.get_route_daily_minimums("تهران", "اصفهان", now=now) == []
    finally:
        await db.close()


class FakeBot:
    platform = "telegram"

    def __init__(self):
        self._post = AsyncMock(return_value=True)


class FakeMessage:
    chat_id = 123
    chat = SimpleNamespace(type="private")

    def __init__(self):
        self.reply_text = AsyncMock()


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()
        self.edit_message_text = AsyncMock()


@pytest.mark.asyncio
async def test_user_selects_only_recorded_origin_and_destination():
    bot = FakeBot()
    today = datetime.now(timezone.utc).date()
    rows = [
        RouteDailyMinimum(
            day=today - timedelta(days=2), min_price_toman=2_100_000,
            sample_count=2, last_captured_at=datetime.now(timezone.utc),
        ),
        RouteDailyMinimum(
            day=today, min_price_toman=2_500_000,
            sample_count=1, last_captured_at=datetime.now(timezone.utc),
        ),
    ]
    history = SimpleNamespace(
        list_chart_routes=AsyncMock(return_value=[
            ("تهران", "مشهد"), ("تهران", "کیش"), ("شیراز", "کیش")
        ]),
        get_route_daily_minimums=AsyncMock(return_value=rows),
    )
    context = SimpleNamespace(bot=bot, user_data={})
    message = FakeMessage()
    await open_chart_picker(message, bot, history, context.user_data)
    assert message.reply_text.await_count == 1
    await handle_chart_callback(FakeQuery("chart:origin:1"), context, history)
    assert context.user_data["route_chart_origin"] == "تهران"
    destination_query = FakeQuery("chart:dest:0")  # Unicode-sorted: مشهد, then کیش
    await handle_chart_callback(destination_query, context, history)

    history.get_route_daily_minimums.assert_awaited_once_with(
        "تهران", "مشهد", days=21
    )
    bot._post.assert_awaited_once()
    method, payload = bot._post.await_args.args
    assert method == "sendWidget"
    assert payload["chat_id"] == 123
    assert "تهران" in payload["html"] and "مشهد" in payload["html"]
    assert "۲٬۱۰۰٬۰۰۰" in payload["html"]


@pytest.mark.asyncio
async def test_invalid_selection_cannot_fetch_nonexistent_route():
    bot = FakeBot()
    history = SimpleNamespace(
        list_chart_routes=AsyncMock(return_value=[("تهران", "مشهد")]),
        get_route_daily_minimums=AsyncMock(),
    )
    context = SimpleNamespace(bot=bot, user_data={})
    await open_chart_picker(FakeMessage(), bot, history, context.user_data)
    await handle_chart_callback(FakeQuery("chart:origin:999"), context, history)
    await handle_chart_callback(FakeQuery("chart:dest:0"), context, history)
    history.get_route_daily_minimums.assert_not_awaited()
    bot._post.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_history_shows_empty_state_without_fake_points():
    bot = FakeBot()
    history = SimpleNamespace(list_chart_routes=AsyncMock(return_value=[]))
    message = FakeMessage()
    await open_chart_picker(message, bot, history, {})
    assert "هنوز هیچ مسیر" in message.reply_text.await_args.args[0]
    bot._post.assert_not_awaited()
