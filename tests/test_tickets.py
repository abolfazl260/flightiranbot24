from datetime import date, datetime, timezone

import pytest

from flightiran.infrastructure.http.errors import ProviderInvalidResponse
from flightiran.interfaces.telegram.tickets import (
    render_cheap_route,
    render_cheap_route_chunks,
    render_offer,
)
from flightiran.modules.tickets.domain import (
    CheapTicketDestination,
    CheapTicketRoute,
    TicketOffer,
    TicketQuery,
)
from flightiran.modules.tickets.mz724 import parse_routes
from flightiran.modules.tickets.service import TicketFilters, TicketService, parse_toman_price


def offer(provider, price, stops=0, baggage="20kg"):
    return TicketOffer(
        provider,
        f"https://{provider}.test",
        price,
        "EUR",
        "Air",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        stops,
        180,
        baggage,
        "refundable",
        5,
    )


@pytest.mark.asyncio
async def test_provider_failures_and_filters_are_independent():
    class Good:
        async def search(self, query):
            return [offer("good", 100), offer("good", 80, stops=1, baggage=None)]

    class Broken:
        async def search(self, query):
            raise RuntimeError("bad provider")

    query = TicketQuery("IKA", "FRA", date(2026, 1, 1), passengers=2)
    results = await TicketService([Good(), Broken()]).search(
        query, TicketFilters(direct_only=True, baggage_required=True, max_price=110)
    )
    assert len(results) == 1
    assert results[0].provider == "good"
    assert results[0].total_price == 105


def test_query_and_render_include_fees_and_refund_policy():
    item = offer("source", 100)
    message, keyboard = render_offer(item)
    assert "Fees included" in message
    assert "Refund" in message
    assert keyboard.inline_keyboard[0][0].url.startswith("https://")
    with pytest.raises(ValueError):
        TicketQuery("IKA", "FRA", date(2026, 1, 2), date(2026, 1, 1))


def test_mz724_parser_normalizes_each_origin_row_and_destination_price():
    html = """
    <div class="sr_table">
      <div class="t_table"> تهران </div>
      <a class="line"><span class="city"> استانبول </span><span class="price">12,500,000 </span></a>
      <a class="line"><span class="city">دبی</span><span class="price">9,800,000</span></a>
    </div>
    <div class="sr_table"><div class="t_table">مشهد</div>
      <a class="line"><span class="city">تهران</span><span class="price">4,000,000</span></a>
    </div>
    """
    routes = parse_routes(html)
    assert [route.origin for route in routes] == ["تهران", "مشهد"]
    assert routes[0].destinations[1].price_toman == "9,800,000"
    assert routes[0].source_url == "https://mz724.ir/"


def test_mz724_parser_rejects_missing_routes_and_renderer_escapes_values():
    with pytest.raises(ProviderInvalidResponse):
        parse_routes("<html><body>no tables</body></html>")
    route = CheapTicketRoute(
        "تهران <x>", (CheapTicketDestination("دبی", "1,000 تومان"),), "https://mz724.ir/"
    )
    rendered = render_cheap_route(route)
    assert "&lt;x&gt;" in rendered
    assert "1,000 تومان" in rendered


def test_parse_toman_price_supports_latin_and_persian_digits():
    assert parse_toman_price("12,500,000") == 12_500_000
    assert parse_toman_price("۱۲٬۵۰۰٬۰۰۰ تومان") == 12_500_000


def test_render_cheap_route_includes_average_difference():
    route = CheapTicketRoute(
        "تهران",
        (
            CheapTicketDestination(
                "مشهد",
                "6,000,000",
                price_value_toman=6_000_000,
                average_price_toman=7_500_000,
                average_sample_count=24,
            ),
        ),
        "https://mz724.ir/",
    )
    rendered = render_cheap_route(route)
    assert "7,500,000 تومان" in rendered
    assert "1,500,000 تومان ارزان‌تر" in rendered
    assert "20.0٪ کمتر" in rendered
    assert "24 نمونه" in rendered


def test_render_cheap_route_chunks_stay_below_telegram_limit():
    destinations = tuple(
        CheapTicketDestination(
            f"مقصد {index}",
            "12,500,000",
            price_value_toman=12_500_000,
            average_price_toman=10_000_000,
            average_sample_count=100,
        )
        for index in range(80)
    )
    route = CheapTicketRoute("تهران", destinations, "https://mz724.ir/")
    chunks = render_cheap_route_chunks(route, max_length=500)

    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert all(chunk.count("<b>") == chunk.count("</b>") for chunk in chunks)
    assert all(chunk.count("<i>") == chunk.count("</i>") for chunk in chunks)
