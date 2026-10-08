import re
from datetime import date, datetime, timezone

import pytest

from flightiran.infrastructure.http.errors import ProviderInvalidResponse
from flightiran.interfaces.telegram.rich_tickets import (
    find_price_drops,
    render_price_drop_fallback_chunks,
    render_rich_price_drop_report,
    render_rich_price_tables,
    replace_disabled_buttons_with_indicators,
    send_rich_price_table_with_badge_fallback,
)
from flightiran.interfaces.telegram.tickets import (
    render_cheap_route,
    render_cheap_route_chunks,
    render_cheap_ticket_booking_hint,
    render_offer,
)
from flightiran.modules.tickets.domain import (
    CheapTicketDestination,
    CheapTicketRoute,
    TicketOffer,
    TicketQuery,
)
from flightiran.modules.tickets.mz724 import parse_routes
from flightiran.modules.tickets.service import (
    CheapTicketService,
    TicketFilters,
    TicketService,
    parse_toman_price,
)


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
    assert messages[0]["html"].count('<td align="center">') == 85
    assert "<table bordered striped compact>" in messages[0]["html"]
    assert "<th>اختلاف (تومان)</th>" in messages[0]["html"]
    assert "<th>تغییر قیمت ٪</th>" in messages[0]["html"]
    assert "<th>نسبت به ثبت قبلی</th>" in messages[0]["html"]
    assert "🟢 ↓ 20.0٪" in messages[0]["html"]
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

    assert "🟢 ↓ 20.0٪" in html
    assert "🔴 ↑ 20.0٪" in html
    assert "⚪ = 0.0٪" in html
    assert "⚪ ؟ نامشخص" in html
    assert "↓ 1,500,000" in html
    assert "↑ 2,000,000" in html
    assert "🟢 ↓ ارزان‌تر" in html
    assert "🔴 ↑ گران‌تر" in html
    assert "⚪ = برابر" in html
    assert "⚪ ؟ نامشخص" in html


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
    assert sum(item["html"].count('<td align="center">') for item in messages) == 26
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


def _price_drop_routes() -> list[CheapTicketRoute]:
    return [
        CheapTicketRoute(
            "تهران",
            (
                CheapTicketDestination("مشهد", "7,000,000", 7_000_000, 10_000_000, 14),
                CheapTicketDestination("دبی", "8,000,000", 8_000_000, 10_000_000, 14),
                CheapTicketDestination("شیراز", "9,000,000", 9_000_000, 10_000_000, 14),
                CheapTicketDestination("اصفهان", "7,000,000", 7_000_000),
            ),
            "https://mz724.ir/",
        ),
        CheapTicketRoute(
            "شیراز",
            (
                CheapTicketDestination("استانبول", "14,000,000", 14_000_000, 20_000_000, 14),
                CheapTicketDestination("کیش", "7,999,000", 7_999_000, 10_000_000, 14),
                CheapTicketDestination("کرمان", "نامشخص", None, 10_000_000, 14),
            ),
            "https://mz724.ir/",
        ),
    ]


def test_discount_report_selects_strictly_more_than_20_percent_and_sorts():
    routes = _price_drop_routes()
    drops = find_price_drops(routes)
    assert [(drop.origin, drop.destination) for drop in drops] == [
        ("شیراز", "استانبول"),
        ("تهران", "مشهد"),
        ("شیراز", "کیش"),
    ]
    assert drops[0].decrease_toman == 6_000_000
    assert drops[0].decrease_percent == 30.0
    assert "دبی" not in [drop.destination for drop in drops]


def test_discount_report_is_one_cross_origin_rich_table():
    messages = render_rich_price_drop_report(_price_drop_routes())
    assert len(messages) == 1
    html = messages[0]["html"]
    assert messages[0]["is_rtl"] is True
    assert "گزارش کاهش قیمت بیش از ۲۰٪" in html
    assert html.count("<table bordered striped compact>") == 1
    assert html.count("<tr>") == 4
    assert html.count("<td>") == 18
    assert "<th>مبدأ</th><th>مقصد</th>" in html
    assert "6,000,000" in html
    assert "🟢 ↓ 30.00٪" in html
    assert html.index("استانبول") < html.index("مشهد") < html.index("کیش")


def test_discount_report_empty_states_and_unavailable_averages():
    route = CheapTicketRoute(
        "تهران",
        (
            CheapTicketDestination("مشهد", "8,000,000", 8_000_000, 10_000_000),
            CheapTicketDestination("شیراز", "2,000,000", 2_000_000),
        ),
        "https://mz724.ir/",
    )
    assert find_price_drops([route]) == []
    message = render_rich_price_drop_report([route])[0]["html"]
    assert "مسیری با کاهش بیش از ۲۰٪" in message
    assert "<table" not in message
    assert "موردی پیدا نشد" in render_price_drop_fallback_chunks([route])[0]


def test_discount_report_splits_only_at_actual_rich_limits_and_escapes_html():
    destinations = tuple(
        CheapTicketDestination(f"مقصد <{i}>", "7,000,000", 7_000_000, 10_000_000)
        for i in range(45)
    )
    route = CheapTicketRoute("تهران & البرز", destinations, "https://mz724.ir/")
    messages = render_rich_price_drop_report([route], max_text_chars=700)
    assert len(messages) > 1
    assert sum(item["html"].count("<td>") for item in messages) == 45 * 6
    assert all(item["html"].count("</table>") == 1 for item in messages)
    assert all("<table bordered striped compact>" in item["html"] for item in messages)
    assert all("<h3>" in item["html"] for item in messages)
    assert "تهران &amp; البرز" in messages[0]["html"]
    assert "مقصد &lt;0&gt;" in messages[0]["html"]


def test_discount_fallback_messages_are_html_safe_and_length_bounded():
    route = CheapTicketRoute(
        "تهران & البرز",
        tuple(
            CheapTicketDestination(f"مقصد <{i}>", "7,000,000", 7_000_000, 10_000_000)
            for i in range(45)
        ),
        "https://mz724.ir/",
    )
    messages = render_price_drop_fallback_chunks([route], max_length=280)
    assert len(messages) > 1
    assert all(len(message) <= 280 for message in messages)
    assert all("<b>" in message and "</b>" in message for message in messages)
    assert all("تهران &amp; البرز" in message for message in messages)
    assert sum(message.count("مقصد &lt;") for message in messages) == 45
    assert all("\\n" not in message for message in messages)



@pytest.mark.parametrize(
    "language, snippet",
    [
        ("fa", "هنوز سؤال دارید؟"),
        ("en", "still have questions?"),
        ("ar", "أم لديك سؤال"),
    ],
)
def test_ticket_booking_hint_invites_questions_and_links_support(language, snippet):
    rendered = render_cheap_ticket_booking_hint("@advertio_support", language)
    assert snippet in rendered
    assert '<a href="https://t.me/advertio_support">@advertio_support</a>' in rendered
    assert "@vlansupport" not in rendered
    assert len(rendered) < 4000


@pytest.mark.parametrize("language, header", [
    ("fa", "نسبت به ثبت قبلی"),
    ("en", "vs last saved price"),
    ("ar", "مقارنة بالسعر السابق"),
])
def test_noninteractive_rich_buttons_follow_previous_price_not_average(language, header):
    destinations = (
        CheapTicketDestination(
            "افزایش", "12,000", price_value_toman=12_000,
            average_price_toman=15_000, previous_price_toman=10_000,
        ),
        CheapTicketDestination(
            "کاهش", "8,000", price_value_toman=8_000,
            average_price_toman=6_000, previous_price_toman=10_000,
        ),
        CheapTicketDestination(
            "ثابت", "10,000", price_value_toman=10_000,
            average_price_toman=11_000, previous_price_toman=10_000,
        ),
        CheapTicketDestination(
            "بدون سابقه", "10,000", price_value_toman=10_000,
            average_price_toman=9_000,
        ),
    )
    route = CheapTicketRoute("تهران", destinations, "https://mz724.ir/")
    messages = render_rich_price_tables(route, language=language)
    assert len(messages) == 1
    html = messages[0]["html"]
    assert header in html

    buttons = re.findall(r"<tg-button[^>]*>.*?</tg-button>", html)
    assert buttons == [
        '<tg-button type="disabled" style="danger">⬆️</tg-button>',
        '<tg-button type="disabled" style="success">⬇️</tg-button>',
        '<tg-button type="disabled">➖</tg-button>',
    ]
    assert all("url=" not in button for button in buttons)
    assert all("data=" not in button and "callback" not in button for button in buttons)
    assert html.count('<td align="center">') == 4
    assert "20.0٪" in html
    assert "—</td>" in html


def test_missing_or_invalid_previous_price_is_not_reported_as_unchanged():
    route = CheapTicketRoute(
        "تهران",
        (
            CheapTicketDestination("بدون سابقه", "6,000", 6_000, 7_000),
            CheapTicketDestination("قبلی صفر", "6,000", 6_000, 7_000, 0, 0),
            CheapTicketDestination("قیمت فعلی نامعتبر", "نامشخص", None, 7_000, 0, 6_000),
        ),
        "https://mz724.ir/",
    )
    html = render_rich_price_tables(route)[0]["html"]
    assert "<tg-button" not in html
    assert html.count('<td align="center">—</td>') == 3


def test_rich_button_compatibility_fallback_keeps_table_and_is_inert():
    route = CheapTicketRoute(
        "تهران",
        (
            CheapTicketDestination("مشهد", "8,000", 8_000, 9_000, 0, 10_000),
            CheapTicketDestination("دبی", "12,000", 12_000, 10_000, 0, 10_000),
            CheapTicketDestination("شیراز", "10,000", 10_000, 10_000, 0, 10_000),
        ),
        "https://mz724.ir/",
    )
    rich = render_rich_price_tables(route)[0]
    fallback = replace_disabled_buttons_with_indicators(rich)
    assert rich["html"].count("<tg-button") == 3
    assert "<tg-button" not in fallback["html"]
    assert fallback["html"].count("<td") == rich["html"].count("<td")
    assert "🟢 ⬇️" in fallback["html"]
    assert "🔴 ⬆️" in fallback["html"]
    assert "⚪ ➖" in fallback["html"]
    assert rich["html"].count("<tg-button") == 3


@pytest.mark.asyncio
async def test_rejected_disabled_badges_retry_only_as_inert_rich_symbols(monkeypatch):
    import httpx

    import flightiran.interfaces.telegram.rich_tickets as rich_tickets

    route = CheapTicketRoute(
        "تهران",
        (CheapTicketDestination("مشهد", "8,000", 8_000, 9_000, 0, 10_000),),
        "https://mz724.ir/",
    )
    rich = render_rich_price_tables(route)[0]
    sent: list[dict] = []

    async def fake_send(_bot, _chat_id, message):
        sent.append(message)
        if len(sent) == 1:
            req = httpx.Request("POST", "https://api.telegram.org/botfake/sendRichMessage")
            resp = httpx.Response(400, request=req)
            raise httpx.HTTPStatusError("unsupported", request=req, response=resp)

    monkeypatch.setattr(rich_tickets, "send_rich_price_table", fake_send)
    await send_rich_price_table_with_badge_fallback(None, 1, rich)
    assert len(sent) == 2
    assert "<tg-button" in sent[0]["html"]
    assert "<tg-button" not in sent[1]["html"]
    assert "<table bordered striped compact>" in sent[1]["html"]



@pytest.mark.asyncio
async def test_ticket_service_reads_previous_price_before_saving_current_sample():
    events = []

    class Feed:
        async def routes(self):
            return [
                CheapTicketRoute(
                    "تهران",
                    (CheapTicketDestination("مشهد", "8,000"),),
                    "https://mz724.ir/",
                )
            ]

    class History:
        async def get_latest_prices(self, route_keys, *, before, retention_days):
            events.append("previous")
            assert route_keys == [("تهران", "مشهد")]
            assert retention_days == 21
            return {("تهران", "مشهد"): 10_000}

        async def record_snapshot(self, samples, *, captured_at, retention_days):
            events.append("record")
            assert samples == [("تهران", "مشهد", 8_000)]

        async def get_averages(self, route_keys):
            events.append("averages")
            return {("تهران", "مشهد"): (9_000.0, 4)}

    service = CheapTicketService(Feed(), History())
    routes = await service.routes()
    item = routes[0].destinations[0]
    assert item.price_value_toman == 8_000
    assert item.previous_price_toman == 10_000
    assert item.average_price_toman == 9_000
    assert events == ["previous", "record", "averages"]
