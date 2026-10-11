"""Public Android ticket quote contract and upstream caching."""

from fastapi.testclient import TestClient

from flightiran.config import Settings
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute
from flightiran.webapp.app import create_app
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed


class FakeTickets:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    async def routes(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("upstream unavailable")
        return [CheapTicketRoute(
            origin="تهران",
            destinations=(
                CheapTicketDestination(
                    "کیش", "۴٬۵۰۰٬۰۰۰", price_value_toman=4500000,
                    average_price_toman=5000000, average_sample_count=4,
                ),
                CheapTicketDestination("تبریز", "۲٬۵۰۰٬۰۰۰"),
            ),
            source_url="https://mz724.ir/",
        )]


def settings():
    return Settings(TELEGRAM_BOT_TOKEN="123456:AA-valid-token")


def test_public_prices_does_not_require_telegram_credentials():
    tickets = FakeTickets()
    with TestClient(create_app(settings(), ticket_price_service=tickets)) as client:
        first = client.get("/api/v1/tickets/prices")
        second = client.get("/api/v1/tickets/prices")
    assert first.status_code == 200
    assert first.headers["cache-control"] == "public, max-age=60"
    assert first.json() == second.json()
    assert first.json()["currency"] == "TOMAN"
    assert first.json()["stale"] is False
    quote = first.json()["routes"][0]["destinations"][0]
    assert quote["price_toman"] == 4500000
    assert quote["average_price_toman"] == 5000000
    assert quote["change_percent"] == -10.0
    assert tickets.calls == 1
    assert "source_url" not in str(first.json())
    assert "user_id" not in first.json()


def test_empty_or_unavailable_upstream_returns_service_unavailable():
    tickets = FakeTickets(fail=True)
    with TestClient(create_app(settings(), ticket_price_service=tickets)) as client:
        assert client.get("/api/v1/tickets/prices").status_code == 503


def test_stale_cached_prices_are_explicitly_marked():
    import pytest

    async def run():
        tickets = FakeTickets()
        feed = PublicTicketPriceFeed(tickets)
        fresh = await feed.get()
        tickets.fail = True
        feed._expires_at = 0.0
        stale = await feed.get()
        assert fresh["stale"] is False
        assert stale["stale"] is True
        assert stale["observed_at"] == fresh["observed_at"]

    import asyncio
    asyncio.run(run())
