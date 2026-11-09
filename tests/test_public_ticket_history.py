"""Actual SQLite daily minima, public API, projection and Telegram parity."""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from flightiran.config import Settings
from flightiran.db import initialize_database
from flightiran.db.repositories import RouteDailyMinimum, SQLiteMz724PriceHistoryRepository
from flightiran.interfaces.telegram.route_chart import render_route_chart_html
from flightiran.webapp.app import create_app
from flightiran.webapp.ticket_history import history_document, public_history_documents


@pytest.mark.asyncio
async def test_history_api_is_public_bounded_and_matches_telegram_repository(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'history.db'}")
    repo = SQLiteMz724PriceHistoryRepository(db)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for days, hour, price in [(20, 1, 500), (2, 1, 400), (2, 2, 200), (1, 1, 300)]:
        await repo.record_snapshot([("A", "B", price), ("A", "C", price+50)],
            captured_at=today-timedelta(days=days)+timedelta(hours=hour), retention_days=21)
    expected = await repo.get_route_daily_minimums("A", "B")
    projection = await public_history_documents(repo)
    assert next(d for d in projection if d["destination"] == "B")["points"] == (
        history_document("A", "B", expected)["points"]
    )
    app = create_app(Settings(TELEGRAM_BOT_TOKEN="123456:fake"), activity_database=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        result = await client.get("/api/v1/tickets/history?origin=A&destination=B")
        assert result.status_code == 200
        body = result.json()
        assert [p["price_toman"] for p in body["points"]] == [500, 200, 300]
        assert sum(p["sample_count"] for p in body["points"]) == 4
        assert body["stale"] is True
        assert body["origin"] == "A" and body["destination"] == "B"
        assert all(set(p) == {"day", "price_toman", "sample_count", "last_observed_at"}
                   for p in body["points"])
        assert "user_id" not in str(body) and "token" not in str(body)
        assert len((await client.get("/api/v1/tickets/history/routes")).json()["routes"]) == 2
        assert (await client.get("/api/v1/tickets/history/routes?offset=-1")).status_code == 422
        assert (await client.get("/api/v1/tickets/history?origin=A")).status_code == 422
        empty = (await client.get("/api/v1/tickets/history?origin=X&destination=Y")).json()
        assert empty["points"] == [] and empty["observed_at"] is None
    await db.close()


def test_shared_year_boundary_fixture_matches_telegram_geometry_and_projection():
    raw = json.loads(Path("docs/fixtures/ticket-history-v1.json").read_text())
    rows = [RouteDailyMinimum(date.fromisoformat(p["day"]), p["price_toman"],
        p["sample_count"], datetime.fromisoformat(p["last_observed_at"])) for p in raw["points"]]
    document = history_document("A", "B", rows, as_of=date(2026, 1, 2))
    assert document["points"] == raw["points"]
    chart = render_route_chart_html("A", "B", rows, as_of=date(2026, 1, 2))
    assert chart.count("<circle") == 4
    assert chart.count('stroke="#159979"') == 2  # two consecutive links, no gap interpolation
    assert "۲۱" in chart and "۱۰" in chart
    assert history_document("A", "B", [], as_of=date(2026, 1, 2))["observed_at"] is None
