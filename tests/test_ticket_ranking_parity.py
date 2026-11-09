"""One language-neutral fixture drives Python, Node and Kotlin rankings."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from flightiran.db.repositories import RecordedTicketBatch, RecordedTicketQuote
from flightiran.interfaces.telegram.widgets import _recorded_widget_data, fare_widget_data
from flightiran.modules.tickets.domain import CheapTicketDestination, CheapTicketRoute
from flightiran.modules.tickets.ranking import valid_drop_percent
from flightiran.webapp.ticket_prices import PublicTicketPriceFeed

FIXTURE = json.loads(Path("docs/fixtures/ticket-ranking-v1.json").read_text())


def test_widget_matches_shared_fixture_top_n_and_half_up_rounding():
    routes = [CheapTicketRoute(row["origin"], tuple(CheapTicketDestination(
        name=f["name"], price_toman=str(f["price_toman"])+" تومان",
        price_value_toman=f["price_toman"], average_price_toman=f["average_price_toman"],
        average_sample_count=f["average_sample_count"],
    ) for f in row["destinations"]), "") for row in FIXTURE["routes"]]
    result = json.loads(fare_widget_data(routes))
    for key, expected in (("items", "expected_cheap"), ("drops", "expected_drops")):
        assert [r["o"]+"/"+r["d"] for r in result[key]] == FIXTURE[expected][:len(result[key])]
    assert [r["x"] for r in result["drops"]] == (
        FIXTURE["expected_percentages"][:len(result["drops"])]
    )
    assert valid_drop_percent(79, 80, 3) == 1.3
    for average in (float("nan"), float("inf"), True, "100", None):
        assert valid_drop_percent(79, average, 3) is None
    for count in (True, 2.5, "3", 100001):
        assert valid_drop_percent(79, 100, count) is None


def test_public_feed_keeps_exact_mean_without_breaking_rounded_field():
    batch = RecordedTicketBatch(datetime.now(timezone.utc), (
        RecordedTicketQuote("A", "B", 79, 80.25, 3),
        RecordedTicketQuote("A", "C", 100, float("inf"), 3),
    ))
    fares = PublicTicketPriceFeed._serialize(batch)["routes"][0]["destinations"]
    assert fares[0]["average_price_toman"] == 80
    assert fares[0]["historical_average_toman"] == 80.25
    assert fares[1]["average_price_toman"] is None
    assert fares[1]["historical_average_toman"] is None


@pytest.mark.asyncio
async def test_widget_uses_stored_cohort_and_real_timestamp_without_crawling():
    observed = datetime.now(timezone.utc) - timedelta(hours=5)
    batch = RecordedTicketBatch(observed, (RecordedTicketQuote("A", "B", 80, 100, 3),))
    service = SimpleNamespace(routes=AsyncMock(side_effect=AssertionError("no crawl")),
        price_history=SimpleNamespace(get_latest_prices=AsyncMock(return_value=batch)))
    data = json.loads(await _recorded_widget_data(service))
    assert data["drops"][0]["x"] == 20.0
    assert observed.strftime("%Y-%m-%d %H:%M UTC") in data["updated"]
    assert "قدیمی" in data["updated"]
    service.routes.assert_not_awaited()
