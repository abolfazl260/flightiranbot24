"""Current upstream status categories and source-backed stay rules."""

from types import SimpleNamespace

import pytest

from flightiran.db import initialize_database
from flightiran.db.models import VisaRuleIndex
from flightiran.interfaces.telegram.visa_flow import handle_visa_callback
from flightiran.interfaces.telegram.visa_presentation import (
    detail_keyboard,
    groups_keyboard,
    render_overview,
    render_rich_report,
    render_section,
    status_label,
)
from flightiran.modules.visa.catalog import (
    LEGACY_STATUSES,
    STATUS_GROUPS,
    UPSTREAM_STATUSES,
    VisaCatalogService,
    VisaDetail,
    VisaRule,
)
from flightiran.modules.visa.stay import stay_rule_for

SOURCE = {
    "url": "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa",
    "name": "Turkish MFA",
    "lastVerified": "2026-10-07",
}


def detail(
    status="visa-free",
    *,
    stay_days=90,
    stay_window=None,
    default_stay=None,
    residence=None,
):
    record = {"requirement": status, "maxStayDays": stay_days}
    if stay_window is not None:
        record["stayWindow"] = stay_window
    data = {
        "id": "turkey",
        "iso2": "TR",
        "visaPolicy": {
            "byPassport": {"IR": record},
            "defaultSource": SOURCE,
            "defaultStayWindow": default_stay,
        },
        "meta": {"lastUpdated": "2026-10-10"},
    }
    rule = VisaRule("IR", "TR", "Turkey", status, stay_days, None, SOURCE["url"],
                    "2026-10-07", "policy")
    return VisaDetail(rule, data, record, ())


def window(
    *,
    basis="rolling",
    allowance=90,
    days=180,
    reset=False,
    source=SOURCE,
    text="A rolling 90/180 rule from an official source.",
):
    return {
        "basis": basis,
        "allowanceDays": allowance,
        "windowDays": days,
        "resetsOnExit": reset,
        "minGapDays": None,
        "arrivalDayCounts": None,
        "departureDayCounts": None,
        "text": text,
        "source": source,
    }


def test_all_current_and_legacy_statuses_in_exactly_one_filter_group():
    assert len(set(UPSTREAM_STATUSES)) == 9
    for status in UPSTREAM_STATUSES + LEGACY_STATUSES:
        assert sum(status in statuses for statuses in STATUS_GROUPS.values()) == 1
    assert "unconfirmed" in STATUS_GROUPS["other"]
    assert "banned" in STATUS_GROUPS["restricted"]
    assert "travel-permit" in STATUS_GROUPS["permit"]


@pytest.mark.parametrize(
    ("status", "fa", "en", "ar"),
    [
        ("unconfirmed", "تأیید نشده", "unconfirmed", "غير مؤكدة"),
        ("banned", "ممنوع", "banned", "محظور"),
        ("travel-permit", "مجوز سفر", "permit", "تصريح"),
    ],
)
def test_new_status_labels_are_explicit_in_three_languages(status, fa, en, ar):
    assert fa in status_label(status, "fa")
    assert en.lower() in status_label(status, "en").lower()
    assert ar in status_label(status, "ar")
    card = render_overview(detail(status=status, stay_days=None), "fa")
    assert fa in card
    assert "⚠️" in card


@pytest.mark.asyncio
async def test_catalog_filters_cover_all_data_including_unknown_future_statuses(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'status.db'}")
    statuses = UPSTREAM_STATUSES + LEGACY_STATUSES + ("future-new-status",)
    async with db.session() as session:
        session.add_all([
            VisaRuleIndex(
                passport="IR",
                destination=chr(65 + i // 26) + chr(65 + i % 26),
                country_name=f"Country {i:02d}",
                status=status,
                stay_days=None, notes=None, source_url=None,
                verified_on=None, source_level="policy",
            )
            for i, status in enumerate(statuses)
        ])
    service = VisaCatalogService(db)
    all_rows, total = await service.listing("IR", page_size=30)
    assert len(all_rows) == total == len(statuses)
    grouped_statuses = []
    for group in STATUS_GROUPS:
        rows, count = await service.listing("IR", group, page_size=30)
        assert len(rows) == count
        grouped_statuses.extend((row.destination, row.status) for row in rows)
    assert len(grouped_statuses) == len(statuses)
    assert len({code for code, _ in grouped_statuses}) == len(statuses)
    other, _ = await service.listing("IR", "other")
    assert {item.status for item in other} == {
        "unconfirmed", "unknown", "future-new-status"
    }
    counts = await service.distribution("IR")
    keyboard = groups_keyboard("fa", counts)
    titles = [button.text for row in keyboard.inline_keyboard for button in row]
    assert any("مجوز سفر" in label and "· 1" in label for label in titles)
    assert any("ممنوعیت" in label and "· 2" in label for label in titles)
    assert any("سایر" in label and "· 3" in label for label in titles)
    await db.close()


def test_default_visa_exempt_stay_window_reports_90_in_180_with_source():
    sample = detail(default_stay=window())
    stay = stay_rule_for(sample)
    assert stay is not None and stay.scope == "destination"
    card = render_overview(sample, "fa")
    assert "90 روز در هر بازه شناور 180 روزه" in card
    assert "خروج و ورود دوباره" in card
    assert "قانون عمومی مقصد" in card
    assert '<a href="https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa">' in card
    assert "اطلاعات تکمیلی سفر" in card
    full = render_section(sample, "fa", "stay")
    assert "نحوه شمارش روز ورود و خروج" in full
    assert "A rolling 90/180 rule" in full
    keyboard = detail_keyboard("fa", sample)
    assert any(
        button.callback_data == "visa:section:stay"
        for row in keyboard.inline_keyboard for button in row
        if button.callback_data
    )
    rich = render_rich_report(sample, "fa")
    assert "90 روز در هر بازه شناور 180 روزه" in rich["html"]


def test_per_passport_rule_overrides_default_and_keeps_per_entry_limit():
    russian = detail(
        stay_days=60,
        stay_window=window(
            allowance=90, days=180, text="60 per entry, 90 across 180 days"
        ),
        default_stay=window(allowance=30, days=180),
    )
    assert stay_rule_for(russian).scope == "passport"
    output = render_overview(russian, "en")
    assert "60 days" in output
    assert "90 days in any rolling 180-day window" in output
    assert "30 days in any rolling" not in output


def test_visa_holder_does_not_inherit_visa_exemption_stay_rule():
    holder = detail(status="embassy-visa", stay_days=30, default_stay=window())
    assert stay_rule_for(holder) is None
    output = render_overview(holder, "fa")
    assert "180 روزه" not in output
    assert "نحوه محاسبه دقیق" in output
    assert "90 روز" not in render_section(holder, "fa", "stay")


def test_incomplete_window_never_fabricates_days_and_escapes_source_text():
    source = dict(SOURCE)
    source["url"] = "javascript:alert(1)"
    partial = detail(default_stay=window(days=None, source=source, text="<bad> & text"))
    rendered = render_section(partial, "fa", "stay")
    assert "90 روز در هر بازه" not in rendered
    assert "نحوه محاسبه دقیق" in rendered
    assert "&lt;bad&gt; &amp; text" in rendered
    assert "javascript:" not in rendered
    assert "استناد مستقل قانون اقامت" in rendered


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        ("per-entry", "per entry"),
        ("calendar-year", "calendar year"),
        ("per-12-months-from-first-entry", "12 months from first entry"),
    ],
)
def test_other_stay_period_types_have_specific_labels(basis, expected):
    sample = detail(stay_window=window(basis=basis, allowance=45, days=None))
    assert expected in render_section(sample, "en", "stay")


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_trip_inputs_are_explicitly_informational_in_all_outputs(language):
    sample = detail()
    overview = render_overview(
        sample, language, purpose="business", residence="DE"
    )
    rich = render_rich_report(
        sample, language, purpose="transit", residence="DE"
    )["html"]
    text = {
        "fa": "بدون تأثیر بر نتیجه ویزا",
        "en": "not used in the visa determination",
        "ar": "لا تدخل في تحديد التأشيرة",
    }[language]
    assert text in overview
    assert text in rich
    assert "DE" in overview and "DE" in rich
    assert "eligibility" in rich if language == "en" else True


@pytest.mark.asyncio
async def test_new_stay_tab_callback_routes_to_source_based_section():
    sample = detail(default_stay=window())
    class Catalog:
        async def ready(self):
            return True

        async def detail(self, passport, destination):
            assert passport == "IR" and destination == "TR"
            return sample

    class Query:
        data = "visa:section:stay"

        def __init__(self):
            self.calls = []

        async def edit_message_text(self, text, **options):
            self.calls.append((text, options))

    query = Query()
    context = SimpleNamespace(user_data={
        "visa_passport": "IR", "visa_destination": "TR",
        "visa_residence": "DE", "visa_purpose": "business",
    })
    await handle_visa_callback(
        SimpleNamespace(callback_query=query), context, Catalog(), "fa"
    )
    assert len(query.calls) == 1
    assert "90 روز در هر بازه شناور 180 روزه" in query.calls[0][0]
    assert query.calls[0][1]["parse_mode"] == "HTML"
