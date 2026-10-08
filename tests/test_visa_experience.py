"""Visa persistence, rendering and interactive navigation tests without network."""

from types import SimpleNamespace

import pytest

from flightiran.db import initialize_database
from flightiran.db.models import VisaDatasetState, VisaDestinationData, VisaRuleIndex
from flightiran.interfaces.telegram.visa_flow import (
    handle_visa_callback,
    visa_command,
    visa_search_text,
)
from flightiran.interfaces.telegram.visa_presentation import (
    country_keyboard,
    render_overview,
    render_rich_report,
    render_section,
    safe_href,
)
from flightiran.modules.visa.catalog import Country, VisaCatalogService
from flightiran.modules.visa.indexer import index_destination


def document():
    return {
        "id": "turkey",
        "iso2": "TR",
        "names": {"common": "Turkey"},
        "meta": {"lastUpdated": "2026-10-08", "primarySources": []},
        "visaPolicy": {
            "defaultSource": {
                "name": "Turkish MFA",
                "url": "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa",
                "lastVerified": "2026-10-07",
            },
            "byPassport": {
                code: {
                    "requirement": "embassy-visa" if code == "AF" else "visa-free",
                    "maxStayDays": 90 if code != "AF" else None,
                    "notes": "<unsafe> A supporting visa can change the result"
                    if code == "AF" else "90 days in a 180-day period.",
                    "visaTypes": ["embassy-tourist"] if code == "AF" else [],
                }
                for code in ["AF", "IR", "TR", "US", "DE"]
            },
            "conditionalWaivers": [{
                "text": "Supporting visa may qualify; confirm official rules."
            }],
        },
        "visaTypes": [
            {"id": "embassy-tourist", "name": "Sticker Visa",
             "method": "embassy", "fee": None,
             "documents": {"items": [{"name": "Passport"}]},
             "applyUrl": "https://www.mfa.gov.tr/"},
        ],
        "entryRequirements": {
            "passportValidity": {
                "text": "60 days beyond the visa or exemption period",
                "source": {
                    "url": "https://www.mfa.gov.tr/passport",
                    "lastVerified": "2026-10-07",
                },
            },
            "onwardTicket": {
                "required": False,
                "text": "No official confirmation of a return ticket exemption.",
            },
        },
        "countryFacts": {
            "currency": {"code": "TRY", "name": "Turkish lira"},
            "timezone": "UTC+3",
        },
        "tips": [{"text": "Official information only."}],
        "faq": [{"question": "Visa needed?", "answer": "Check official sources."}],
    }


def test_normalization_inherits_policy_source_but_marks_scope():
    sample = document()
    sample["visaPolicy"]["byPassport"].update({
        f"P{x:02d}": {"requirement": "visa-required"}
        for x in range(190)
    })
    records = index_destination(sample)
    assert len(records) == 195
    af = next(row for row in records if row["passport"] == "AF")
    assert af["source_level"] == "policy"
    assert af["verified_on"] == "2026-10-07"
    assert af["stay_days"] is None
    assert af["status"] == "embassy-visa"


def test_html_source_links_and_user_text_are_escaped():
    assert safe_href("javascript:alert(1)") is None
    assert safe_href("https://example.com/ok") is not None


def test_country_callback_data_fits_telegram_limit():
    all_countries = [Country(f"{i:02d}", f"Country {i}") for i in range(199)]
    keyboard = country_keyboard(all_countries, "fa", purpose="d", page=10)
    assert all(
        len(button.callback_data.encode("utf-8")) <= 64
        for row in keyboard.inline_keyboard for button in row
        if button.callback_data
    )


@pytest.mark.asyncio
async def test_catalog_renders_sourced_record(tmp_path):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'visa.db'}"
    )
    sample = document()
    async with database.session() as session:
        session.add(VisaDestinationData(
            slug="turkey", iso2="TR", source_url="https://travelrequirements.info/",
            manifest_updated="2026-10-08", content_hash="test",
            last_fetched_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
            raw_data=sample,
        ))
        for item in sample["visaPolicy"]["byPassport"]:
            entry = sample["visaPolicy"]["byPassport"][item]
            session.add(VisaRuleIndex(
                passport=item, destination="TR", country_name="Turkey",
                status=entry["requirement"], stay_days=entry["maxStayDays"],
                notes=entry["notes"], source_url="https://www.mfa.gov.tr/",
                verified_on="2026-10-07", source_level="policy",
            ))
        session.add(VisaDatasetState(id=1, source_url="https://travelrequirements.info/data/"))
    service = VisaCatalogService(database)
    detail = await service.detail("AF", "TR")
    assert detail.rule.status == "embassy-visa"
    assert detail.visa_types[0]["id"] == "embassy-tourist"
    assert "&lt;unsafe&gt;" in render_overview(detail, "fa")
    assert "<b>" in render_section(detail, "fa", "entry")
    assert "No official confirmation" in render_section(detail, "en", "entry")
    assert "<table" in render_rich_report(detail, "fa")["html"]
    await database.close()


class Message:
    def __init__(self):
        self.calls = []
        self.chat_id = 12

    async def reply_text(self, message, **kwargs):
        self.calls.append((message, kwargs))


class Query:
    def __init__(self, data):
        self.data = data
        self.calls = []
        self.message = Message()

    async def edit_message_text(self, message, **kwargs):
        self.calls.append((message, kwargs))


class FakeCatalog:
    async def ready(self):
        return True

    async def countries(self):
        return [Country("AF", "Afghanistan"), Country("TR", "Turkey"), Country("IR", "Iran")]

    async def detail(self, passport, destination):
        return None

    async def listing(self, *args, **kwargs):
        return [], 0


@pytest.mark.asyncio
async def test_wizard_picks_passport_and_destination():
    data = {}
    context = SimpleNamespace(user_data=data)
    service = FakeCatalog()
    pick = SimpleNamespace(callback_query=Query("visa:p:AF"))
    await handle_visa_callback(pick, context, service, "fa")
    assert data["visa_passport"] == "AF"
    select = SimpleNamespace(callback_query=Query("visa:d:TR"))
    await handle_visa_callback(select, context, service, "fa")
    assert data["visa_destination"] == "TR"
    assert "پاسپورت" not in select.callback_query.calls[0][0] or select.callback_query.calls


@pytest.mark.asyncio
async def test_command_sets_selected_route():
    data = {}
    message = Message()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data=data, args=["AF", "TR"])
    await visa_command(update, context, FakeCatalog(), "en")
    assert data["visa_passport"] == "AF"
    assert data["visa_destination"] == "TR"


@pytest.mark.asyncio
async def test_country_search_matches_persian():
    data = {"visa_search_mode": "d"}
    message = Message()
    message.text = "ایران"
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data=data)
    assert await visa_search_text(update, context, FakeCatalog(), "fa")
    buttons = message.calls[0][1]["reply_markup"].inline_keyboard
    assert any(button.callback_data == "visa:d:IR" for row in buttons for button in row)
