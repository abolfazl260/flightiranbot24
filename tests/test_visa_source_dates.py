"""Source provenance must remain separate from server refresh timestamps."""

import pytest

from flightiran.interfaces.telegram.visa_presentation import (
    detail_keyboard,
    render_overview,
    render_rich_report,
    render_section,
)
from flightiran.modules.visa.catalog import VisaDetail, VisaRule
from flightiran.modules.visa.provenance import (
    link_html,
    safe_source_url,
    source_date,
    visa_provenance,
)


def detail(
    *,
    verified: str | None = "2026-08-26",
    changed: str | None = "2026-08-18",
    updated: str | None = "2026-10-07",
    include_record_source: bool = False,
) -> VisaDetail:
    source = {
        "name": "Official <Foreign> Ministry",
        "url": "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa",
        "type": "government",
    }
    if verified:
        source["lastVerified"] = verified
    if changed:
        source["lastChanged"] = changed
    source["archiveUrl"] = "https://web.archive.org/web/202608260000/https://www.mfa.gov.tr"
    row = {
        "requirement": "embassy-visa",
        "notes": "Visa conditions <vary> by supporting documents.",
        "visaTypes": ["tourist-visa"],
    }
    if include_record_source:
        row["source"] = dict(source)
    meta = {
        "lastFullReview": "2026-09-26",
        "primarySources": [dict(source)],
    }
    if updated:
        meta["lastUpdated"] = updated
    data = {
        "id": "turkey", "iso2": "TR", "names": {"common": "Turkey"},
        "meta": meta,
        "visaPolicy": {
            "byPassport": {"AF": row},
            "defaultSource": source,
        },
        "visaTypes": [
            {
                "id": "tourist-visa",
                "name": "Tourist Visa",
                "fee": {"amount": 60, "currency": "EUR", "notes": "Fees can vary."},
                "method": "embassy",
                "processing": {"minDays": 5, "maxDays": 10, "unit": "calendar-days"},
                "stayDays": 30,
                "applyUrl": "https://www.mfa.gov.tr/apply",
                "source": dict(source),
            }
        ],
        "entryRequirements": {
            "passportValidity": {
                "text": "At least 60 days beyond the visa or exemption period.",
                "source": {
                    "name": "Visa regulation",
                    "url": "https://www.mfa.gov.tr/passport",
                    "lastVerified": "2026-10-03",
                },
            }
        },
        "countryFacts": {
            "currency": {"code": "TRY", "name": "Turkish lira"},
        },
        "tips": [{"text": "Use the official portal."}],
        "faq": [],
    }
    rule = VisaRule(
        passport="AF",
        destination="TR",
        country_name="Turkey",
        status="embassy-visa",
        stay_days=None,
        notes=row["notes"],
        source_url=source["url"],
        verified_on=verified,
        source_level="row" if include_record_source else "policy",
    )
    return VisaDetail(rule, data, row, tuple(data["visaTypes"]))


def test_source_dates_are_real_iso_calendar_dates_only():
    assert source_date("2026-10-07") == "2026-10-07"
    assert source_date("2026-02-30") is None
    assert source_date("2026-10-07T12:00:00Z") is None
    assert source_date(None) is None


def test_provenance_uses_publisher_dates_not_server_sync_date():
    p = visa_provenance(detail())
    assert p.source_verified_on == "2026-08-26"
    assert p.source_changed_on == "2026-08-18"
    assert p.destination_updated_on == "2026-10-07"
    assert p.last_full_review_on == "2026-09-26"
    assert p.destination_json_url.endswith("/destinations/turkey.json")


def test_card_has_all_named_source_dates_clickable_links_and_no_false_expiration():
    card = render_overview(detail(), "fa")
    assert "آخرین تأیید منبع مقررات" in card
    assert "2026-08-26" in card
    assert "آخرین تغییر ثبت‌شده در منبع" in card
    assert "2026-08-18" in card
    assert "آخرین به‌روزرسانی فایل مقصد" in card
    assert "2026-10-07" in card
    assert '<a href="https://www.mfa.gov.tr/' in card
    assert "travelrequirements.info/data/destinations/turkey.json" not in card
    assert "فایل اصلی اطلاعات مقصد (JSON)" not in card
    assert "&lt;vary&gt;" in card
    assert "2026-10-08" not in card


def test_missing_source_dates_do_not_fabricate_today_or_local_sync_time():
    card = render_overview(detail(verified=None, changed=None, updated=None), "en")
    assert "Source last verified" in card
    assert "Not stated by source" in card
    assert "Last source-recorded change" not in card


def test_dates_and_sources_tab_cites_publisher_and_legal_expiry_unknown():
    card = render_section(detail(), "fa", "sources")
    assert "آخرین بازبینی کامل اطلاعات مقصد" in card
    assert "2026-09-26" in card
    assert "تاریخ پایان اعتبار قانونی در منبع مشخص نشده" in card
    assert 'href="https://web.archive.org/' in card
    assert 'href="https://creativecommons.org/licenses/by/4.0/"' in card


def test_entry_tab_links_directly_to_its_own_source():
    card = render_section(detail(), "en", "entry")
    assert 'href="https://www.mfa.gov.tr/passport"' in card
    assert "2026-10-03" in card


def test_rich_report_contains_dates_and_well_formed_anchors():
    report = render_rich_report(detail(), "fa")
    html = report["html"]
    assert "<table bordered striped compact>" in html
    assert "2026-08-26" in html
    assert "2026-10-07" in html
    assert html.count("<p>") == html.count("</p>")
    assert html.count("<h3>") == html.count("</h3>")
    assert html.count("<a href=") == html.count("</a>")
    assert "travelrequirements.info/data/destinations/turkey.json" not in html
    assert "<p><h3>" not in html


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_telegram_keyboard_has_direct_citation_without_raw_json(language):
    keyboard = detail_keyboard(language, detail())
    links = [b.url for row in keyboard.inline_keyboard for b in row if b.url]
    assert links == ["https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa"]
    assert not any(link.endswith(".json") for link in links)
    assert all("JSON" not in b.text for row in keyboard.inline_keyboard for b in row)


def test_rejects_untrusted_protocol_and_escapes_link_text():
    assert safe_source_url("javascript:alert(1)") is None
    assert safe_source_url("https://example.com\n/fake") is None
    assert "&lt;source&gt;" in link_html("https://example.com", "<source>")
    assert 'href="https://example.com"' in link_html("https://example.com", "<source>")


def test_long_detail_tab_always_keeps_upstream_date_and_citation_links():
    sample = detail()
    sample.destination_data["tips"] = [
        {"text": ("Travel alert: " + "check official sources. " * 30)}
        for _ in range(20)
    ]
    rendered = render_section(sample, "fa", "tips")
    assert len(rendered) < 3900
    assert "2026-10-07" in rendered
    assert "travelrequirements.info/data/destinations/turkey.json" not in rendered
    assert '<a href="https://www.mfa.gov.tr/' in rendered
    assert '<a href="https://creativecommons.org/licenses/by/4.0/">' in rendered


@pytest.mark.parametrize("language", ("fa", "en", "ar"))
def test_no_raw_destination_json_link_in_any_visa_user_view(language):
    sample = detail()
    raw_url = "travelrequirements.info/data/destinations/turkey.json"
    views = [
        render_overview(sample, language),
        render_rich_report(sample, language)["html"],
        *(
            render_section(sample, language, section)
            for section in ("types", "entry", "transit", "facts", "stay", "tips", "faq", "sources")
        ),
    ]
    for view in views:
        assert raw_url not in view
    buttons = [
        button for row in detail_keyboard(language, sample).inline_keyboard
        for button in row
    ]
    assert not any(raw_url in (button.url or "") for button in buttons)
    assert any(button.url and "mfa.gov.tr" in button.url for button in buttons)
