from datetime import date, datetime, timezone

import pytest

from flightiran.infrastructure.http.errors import ProviderInvalidResponse
from flightiran.interfaces.telegram.rich_tickets import render_rich_price_tables
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
    assert "<pre>" in rendered
    assert "میانگین     7,500,000 تومان" in rendered
    assert "اختلاف      -1,500,000 تومان" in rendered
    assert "درصد        -20.0٪" in rendered
    assert "نمونه       24" in rendered
    assert "20.0٪ ارزان‌تر از میانگین" in rendered


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
    assert all(chunk.count("<pre>") == chunk.count("</pre>") for chunk in chunks)


def test_rich_table_keeps_all_destinations_of_one_origin_in_one_message():
    destinations = tuple(
        CheapTicketDestination(
            f"مقصد {index}",
            "6,000,000",
            price_value_toman=6_000_000,
            average_price_toman=7_500_000,
        )
        for index in range(85)
    )
    route = CheapTicketRoute("تهران", destinations, "https://mz724.ir/")
    messages = render_rich_price_tables(route)

    assert len(messages) == 1
    assert messages[0]["html"].count("<tr>") == 86
    assert messages[0]["html"].count("<td>") == 85 * 5
    assert "<table bordered striped compact>" in messages[0]["html"]
    assert "<th>اختلاف (تومان)</th>" in messages[0]["html"]
    assert "<th>اختلاف ٪</th>" in messages[0]["html"]
    assert "🟢 -20.0٪" in messages[0]["html"]
    assert messages[0]["is_rtl"] is True


def test_rich_table_colors_percentage_red_green_and_white():
    destinations = (
        CheapTicketDestination(
            "مشهد", "6,000,000", 6_000_000, 7_500_000,
        ),
        CheapTicketDestination(
            "استانبول", "12,000,000", 12_000_000, 10_000_000,
        ),
        CheapTicketDestination(
            "شیراز", "6,000,000", 6_000_000, 6_000_000,
        ),
        CheapTicketDestination(
            "دبی", "6,000,000", 6_000_000,
        ),
    )
    route = CheapTicketRoute("تهران", destinations, "https://mz724.ir/")
    html = render_rich_price_tables(route)[0]["html"]

    assert "🟢 -20.0٪" in html
    assert "🔴 +20.0٪" in html
    assert "⚪ 0.0٪" in html
    assert "⚪ —" in html
    assert "-1,500,000" in html
    assert "+2,000,000" in html


def test_rich_table_only_splits_at_actual_configured_safety_limit():
    destinations = tuple(
        CheapTicketDestination(
            f"مقصد {index}", "6,000,000", 6_000_000, 7_500_000,
        )
        for index in range(26)
    )
    route = CheapTicketRoute("تهران", destinations, "https://mz724.ir/")
    messages = render_rich_price_tables(route, max_text_chars=500)

    assert len(messages) > 1
    assert sum(item["html"].count("<td>") for item in messages) == 26 * 5
    assert all(item["html"].count("<tr>") <= 491 for item in messages)
    assert all(item["html"].count("<table>") == 0 for item in messages)
    assert all(item["html"].count("</table>") == 1 for item in messages)


def test_rich_table_escapes_source_city_names():
    route = CheapTicketRoute(
        'تهران & <x>',
        (CheapTicketDestination("دبی <script>", "8,000,000", 8_000_000),),
        "https://mz724.ir/",
    )
    html = render_rich_price_tables(route)[0]["html"]
    assert "تهران &amp; &lt;x&gt;" in html
    assert "دبی &lt;script&gt;" in html
