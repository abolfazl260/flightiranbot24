"""Verify Android fares come from the bot database, never upstream HTML."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from flightiran.config import Settings
from flightiran.db import initialize_database
from flightiran.db.repositories import (
    RecordedTicketBatch,
    RecordedTicketQuote,
    SQLiteMz724PriceHistoryRepository,
)
from flightiran.webapp.app import create_app
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed


def settings():
    return Settings(TELEGRAM_BOT_TOKEN="123456:AA-valid-token")


@pytest.mark.asyncio
async def test_api_reads_latest_hourly_database_prices_and_real_average(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'prices.db'}")
    repo = SQLiteMz724PriceHistoryRepository(db)
    newest = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    await repo.record_snapshot(
        [("تهران", "کیش", 5_000_000), ("مشهد", "اهواز", 2_000_000)],
        captured_at=newest - timedelta(hours=1),
        retention_days=21,
    )
    await repo.record_snapshot(
        [("تهران", "کیش", 4_000_000), ("تهران", "تبریز", 3_000_000)],
        captured_at=newest,
        retention_days=21,
    )
    app = create_app(settings(), activity_database=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/api/v1/tickets/prices")
        second = await client.get("/api/v1/tickets/prices")
    assert first.status_code == 200
    assert second.json() == first.json()
    assert first.headers["cache-control"] == "public, max-age=60"
    body = first.json()
    assert body["currency"] == "TOMAN"
    assert body["stale"] is False
    assert datetime.fromisoformat(body["observed_at"]) == newest
    assert [route["origin"] for route in body["routes"]] == ["تهران"]
    rows = {r["name"]: r for r in body["routes"][0]["destinations"]}
    assert rows["کیش"] == {
        "name": "کیش",
        "price_toman": 4_000_000,
        "average_price_toman": 4_500_000,
        "change_percent": -11.1,
        "average_sample_count": 2,
    }
    assert rows["تبریز"]["price_toman"] == 3_000_000
    assert rows["تبریز"]["average_price_toman"] == 3_000_000
    assert "source_url" not in str(body)
    assert "user_id" not in body
    await db.close()


@pytest.mark.asyncio
async def test_database_missing_averages_are_not_fabricated(tmp_path):
    from sqlalchemy import insert

    from flightiran.db.models import Mz724PriceSnapshot

    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'no-average.db'}")
    observed = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    async with db.session() as session:
        await session.execute(insert(Mz724PriceSnapshot).values(
            origin="تهران", destination="کیش", price_toman=7_000_000,
            captured_at=observed,
        ))
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings(), activity_database=db)),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tickets/prices")
    assert response.status_code == 200
    quote = response.json()["routes"][0]["destinations"][0]
    assert quote["price_toman"] == 7_000_000
    assert quote["average_price_toman"] is None
    assert quote["change_percent"] is None
    assert quote["average_sample_count"] == 0
    await db.close()


@pytest.mark.asyncio
async def test_old_database_quotes_are_marked_stale(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'stale.db'}")
    observed = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    await SQLiteMz724PriceHistoryRepository(db).record_snapshot(
        [("تهران", "مشهد", 2_500_000)],
        captured_at=observed - timedelta(hours=5),
        retention_days=21,
    )
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings(), activity_database=db)),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tickets/prices")
    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert datetime.fromisoformat(response.json()["observed_at"]) < observed
    await db.close()


@pytest.mark.asyncio
async def test_missing_database_or_empty_table_fails_closed(tmp_path):
    with TestClient(create_app(settings())) as client:
        assert client.get("/api/v1/tickets/prices").status_code == 503
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=create_app(settings(), activity_database=db)),
        base_url="http://test",
    ) as client:
        assert (await client.get("/api/v1/tickets/prices")).status_code == 503
    await db.close()


def test_cached_failure_is_explicitly_stale_and_no_provider_is_involved():
    class Stub:
        def __init__(self):
            self.calls = 0

        async def get_latest_prices(self):
            self.calls += 1
            if self.calls > 1:
                raise RuntimeError("db down")
            return RecordedTicketBatch(
                captured_at=datetime.now(timezone.utc),
                quotes=(RecordedTicketQuote("تهران", "کیش", 5_000_000, None, 0),),
            )

    async def scenario():
        stub = Stub()
        feed = PublicTicketPriceFeed(stub)
        fresh = await feed.get()
        await feed.get()
        assert stub.calls == 1
        feed._expires_at = 0
        stale = await feed.get()
        assert stale["stale"] is True
        assert stale["observed_at"] == fresh["observed_at"]
        assert stub.calls == 2

    asyncio.run(scenario())
