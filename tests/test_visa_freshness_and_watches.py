"""Visa freshness, sourced citations, semantic watches and concise Telegram flow."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from flightiran.db import initialize_database
from flightiran.db.models import VisaDatasetState, VisaRuleIndex, VisaWatchEvent
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.visa_flow import open_visa_menu
from flightiran.interfaces.telegram.visa_presentation import (
    detail_keyboard,
    render_overview,
    render_rich_report,
    render_section,
)
from flightiran.interfaces.telegram.visa_quality import render_freshness
from flightiran.interfaces.telegram.visa_watches import (
    handle_watch_callback,
    render_change_alert,
)
from flightiran.modules.visa.catalog import Country, VisaCatalogService, VisaDetail, VisaRule
from flightiran.modules.visa.freshness import assess_freshness
from flightiran.modules.visa.provenance import source_authority, visa_provenance
from flightiran.modules.visa.watch import (
    VisaWatchService,
    rule_changes,
    semantic_rule,
)

SOURCE_URL = "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa"


def document(
    *,
    status: str = "visa-free",
    stay: int = 90,
    notes: str = "Official travel requirement",
) -> dict:
    return {
        "id": "turkey",
        "iso2": "TR",
        "names": {"common": "Turkey"},
        "meta": {"lastUpdated": "2026-10-08", "lastFullReview": "2026-10-01"},
        "visaPolicy": {
            "defaultSource": {
                "name": "Turkish MFA", "type": "government",
                "url": SOURCE_URL, "lastVerified": "2026-10-07",
            },
            "defaultStayWindow": {
                "basis": "rolling", "windowDays": 180, "allowanceDays": 90,
                "resetsOnExit": False, "minGapDays": None,
                "arrivalDayCounts": None, "departureDayCounts": None,
                "text": "90/180 days", "source": {
                    "type": "government", "url": SOURCE_URL, "lastVerified": "2026-10-07",
                },
            },
            "byPassport": {
                "IR": {
                    "requirement": status, "maxStayDays": stay, "notes": notes,
                    "visaTypes": ["evisa"] if status == "evisa" else [],
                },
                "AF": {"requirement": "embassy-visa", "maxStayDays": None, "notes": None},
            },
        },
        "visaTypes": [
            {"id": "evisa", "method": "evisa", "name": "Electronic visa",
             "fee": {"amount": 100, "currency": "USD"}},
        ],
        "entryRequirements": {
            "passportValidity": {
                "text": "Passport must be valid 6 months",
                "source": {"type": "government", "url": SOURCE_URL},
            },
        },
        "countryFacts": {"timezone": "UTC+3"},
        "tips": [{"text": "General information"}],
        "faq": [],
    }


def visa_detail(data: dict | None = None, *, passport: str = "IR") -> VisaDetail:
    data = data or document()
    record = data["visaPolicy"]["byPassport"][passport]
    return VisaDetail(
        VisaRule(
            passport, "TR", "Turkey", record["requirement"],
            record["maxStayDays"], record["notes"], SOURCE_URL, "2026-10-07", "policy",
        ),
        data, record, (),
    )


async def database_with_users(tmp_path):
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'visa-watches.db'}")
    users = SQLiteUserRepository(database)
    a = await users.create(10001)
    b = await users.create(10002)
    async with database.session() as session:
        session.add_all([
            VisaRuleIndex(
                passport=passport, destination="TR", country_name="Turkey",
                status="visa-free", stay_days=90, notes=None, source_url=SOURCE_URL,
                verified_on=None, source_level="policy",
            )
            for passport in ("IR", "AF")
        ])
    return database, users, a, b


def test_freshness_threshold_and_separate_local_check_clock():
    now = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
    assert assess_freshness(None, now=now).status == "unknown"
    fresh = assess_freshness(now - timedelta(hours=2), now=now)
    assert fresh.status == "fresh"
    assert "2026-10-10 10:00 UTC" in render_freshness(fresh, "fa")
    assert "تاریخ اعتبار مقررات" in render_freshness(fresh, "fa")
    stale = assess_freshness(now - timedelta(hours=25), now=now)
    assert stale.stale and stale.status == "stale"
    assert "بیش از 24 ساعت" in render_freshness(stale, "fa")
    assert "over 24 hours" in render_freshness(stale, "en")
    assert "ساعة" in render_freshness(stale, "ar")
    # SQLite naive datetimes represent UTC, not server local timezone.
    naive = assess_freshness((now - timedelta(hours=25)).replace(tzinfo=None), now=now)
    assert naive.status == "stale"
    assert assess_freshness(now + timedelta(days=1), now=now).status == "unknown"


@pytest.mark.asyncio
async def test_catalog_uses_last_successful_sync_time(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'fresh.db'}")
    catalog = VisaCatalogService(db, stale_after_hours=12)
    assert (await catalog.freshness()).status == "unknown"
    async with db.session() as session:
        session.add(VisaDatasetState(
            id=1, source_url="https://travelrequirements.info/data/index.json",
            last_checked_at=datetime.now(timezone.utc) - timedelta(days=2),
        ))
    result = await catalog.freshness()
    assert result.status == "stale" and result.threshold_hours == 12
    await db.close()


def test_citation_origin_categories_are_conservative():
    assert source_authority({
        "type": "government", "url": SOURCE_URL,
    }, "TR") == ("destination_government", "TR")
    assert source_authority({
        "type": "government", "url": SOURCE_URL,
    }, "IR") == ("foreign_government", "TR")
    assert source_authority({
        "type": "government", "url": "https://www.auswaertiges-amt.de/visa",
    }, "IR") == ("foreign_government", "DE")
    assert source_authority({
        "type": "government", "url": "https://unrecognized-authority.example",
    }, "IR") == ("government_unverified_jurisdiction", None)
    assert source_authority({
        "type": "igo", "url": "https://www.un.org",
    }, "IR") == ("intergovernmental", None)
    assert source_authority({
        "type": "government", "url": "https://fakegov.tr.example.com",
    }, "TR") == ("government_unverified_jurisdiction", None)


def test_provenance_and_compact_rich_report_are_visible_and_sourced():
    detail = visa_detail()
    p = visa_provenance(detail)
    assert p.authority == "destination_government"
    overview = render_overview(detail, "fa")
    assert "مرجع دولتی کشور مقصد" in overview
    assert "استناد عمومی" in overview
    sources = render_section(detail, "fa", "sources")
    assert "مرجع دولتی کشور مقصد" in sources
    assert "دامنه شناخته‌شده" in sources

    detail.destination_data["tips"] = [
        {"text": "Repeated general travel advice " * 70}
        for _ in range(75)
    ]
    alert = "⚠️ داده‌های محلی بیش از 24 ساعت بدون همگام‌سازی هستند."
    report = render_rich_report(detail, "fa", freshness_notice=alert)
    html = report["html"]
    assert len(html) < 8000
    assert "90 روز در هر بازه شناور 180 روزه" in html
    assert "راهنمای ویزا" in html
    assert "مرجع دولتی کشور مقصد" in html
    assert alert in html
    assert "Repeated general travel advice" not in html
    assert html.count("<p>") == html.count("</p>")
    assert html.count("<h3>") == html.count("</h3>")
    assert html.count("<a href=") == html.count("</a>")
    assert "href=\"https://www.mfa.gov.tr/" in html
    assert any(
        button.callback_data == "visa:watch:add"
        for row in detail_keyboard("fa", detail).inline_keyboard
        for button in row
        if button.callback_data
    )
    third_party = deepcopy(detail.destination_data)
    third_party["visaPolicy"]["defaultSource"]["url"] = (
        "https://www.auswaertiges-amt.de/de/"
    )
    third_party["visaPolicy"]["defaultSource"]["name"] = "German foreign ministry"
    iran = visa_detail(third_party)
    assert "کشور ثالث (DE)" in render_overview(iran, "fa")


def test_only_semantic_changes_trigger_alerts():
    old = document()
    editorial = deepcopy(old)
    editorial["meta"]["lastUpdated"] = "2026-10-10"
    editorial["visaPolicy"]["defaultSource"]["lastVerified"] = "2026-10-10"
    editorial["visaPolicy"]["byPassport"]["IR"]["source"] = {
        "url": SOURCE_URL, "type": "government", "lastVerified": "2026-10-10"
    }
    editorial["tips"][0]["text"] = "Totally rewritten editorial article"
    assert semantic_rule(editorial, "IR") == semantic_rule(old, "IR")
    assert not rule_changes(semantic_rule(old, "IR"), semantic_rule(editorial, "IR"))
    changed = deepcopy(old)
    changed["visaPolicy"]["byPassport"]["IR"]["requirement"] = "embassy-visa"
    changed["visaPolicy"]["byPassport"]["IR"]["maxStayDays"] = 30
    changed["entryRequirements"]["passportValidity"]["text"] = "Requires 12 months"
    before = semantic_rule(old, "IR")
    after = semantic_rule(changed, "IR")
    assert rule_changes(before, after) == ("status", "stay", "conditions")
    assert after["stay_window"] is None  # Visa-free default must not leak into visa holder.


@pytest.mark.asyncio
async def test_visa_watches_are_owned_capped_and_persist(tmp_path):
    db, _users, a, b = await database_with_users(tmp_path)
    watch_service = VisaWatchService(db, max_watches=1)
    first = await watch_service.subscribe(a.id, "ir", "tr")
    assert first.active
    assert (await watch_service.subscribe(a.id, "IR", "TR")).id == first.id
    assert len(await watch_service.list_user(a.id)) == 1
    assert await watch_service.list_user(b.id) == []
    assert not await watch_service.set_active(b.id, first.id, False)
    assert not await watch_service.remove(b.id, first.id)
    second = await watch_service.subscribe(b.id, "AF", "TR")
    assert second.id != first.id
    assert await watch_service.set_active(a.id, first.id, False)
    assert not (await watch_service.list_user(a.id))[0].active
    assert await watch_service.set_active(a.id, first.id, True)
    new_service = VisaWatchService(db)
    assert (await new_service.list_user(a.id))[0].active
    with pytest.raises(ValueError):
        await watch_service.subscribe(a.id, "ZZ", "TR")
    assert await watch_service.remove(a.id, first.id)
    assert await new_service.list_user(a.id) == []
    await db.close()


@pytest.mark.asyncio
async def test_transactional_outbox_detects_meaningful_changes_and_retries(tmp_path):
    db, _users, a, b = await database_with_users(tmp_path)
    service = VisaWatchService(db)
    watch = await service.subscribe(a.id, "IR", "TR")
    await service.subscribe(b.id, "AF", "TR")
    old = document()
    editorial = deepcopy(old)
    editorial["meta"]["lastUpdated"] = "2026-10-09"
    editorial["visaPolicy"]["defaultSource"]["lastVerified"] = "2026-10-09"
    async with db.session() as session:
        assert not await service.enqueue_changes(
            session, None, old, "TR", source_url=SOURCE_URL
        )
        assert not await service.enqueue_changes(
            session, old, editorial, "TR", source_url=SOURCE_URL
        )
    changed = deepcopy(old)
    changed["visaPolicy"]["byPassport"]["IR"]["requirement"] = "evisa"
    changed["visaPolicy"]["byPassport"]["IR"]["maxStayDays"] = 30
    changed["visaPolicy"]["byPassport"]["IR"]["notes"] = "Updated official route conditions"
    async with db.session() as session:
        assert await service.enqueue_changes(
            session, old, changed, "TR", source_url=SOURCE_URL
        ) == 1
    # Duplicate imports must not enqueue duplicate notifications.
    async with db.session() as session:
        assert await service.enqueue_changes(
            session, old, changed, "TR", source_url=SOURCE_URL
        ) == 0
    calls = []
    now = datetime(2026, 10, 10, 10, tzinfo=timezone.utc)

    async def unreliable(notification):
        calls.append(notification)
        if len(calls) == 1:
            raise RuntimeError("Telegram temporarily unavailable")

    assert await service.deliver_pending(unreliable, now=now) == 0
    assert await service.deliver_pending(unreliable, now=now + timedelta(minutes=5)) == 0
    assert await service.deliver_pending(unreliable, now=now + timedelta(minutes=16)) == 1
    assert len(calls) == 2
    assert calls[0].telegram_id == 10001
    assert calls[0].payload["categories"] == ["status", "stay", "conditions"]
    assert await service.deliver_pending(unreliable, now=now + timedelta(hours=1)) == 0
    async with db.session() as session:
        events = (await session.scalars(
            __import__("sqlalchemy").select(VisaWatchEvent)
        )).all()
        assert len(events) == 1
        assert events[0].watch_id == watch.id
        assert events[0].sent_at is not None
    assert "visa-free" not in render_change_alert(calls[0], "en")
    assert "Visa-free" in render_change_alert(calls[0], "en")
    assert "eVisa" in render_change_alert(calls[0], "en")
    assert "confirmed change in law" in render_change_alert(calls[0], "en")
    await db.close()


@pytest.mark.asyncio
async def test_paused_subscription_skips_enqueue_and_deleting_clears_outbox(tmp_path):
    db, _users, a, _b = await database_with_users(tmp_path)
    service = VisaWatchService(db)
    watch = await service.subscribe(a.id, "IR", "TR")
    old = document()
    changed = document(stay=60)
    assert await service.set_active(a.id, watch.id, False)
    async with db.session() as session:
        assert not await service.enqueue_changes(
            session, old, changed, "TR", source_url=SOURCE_URL
        )
    assert await service.set_active(a.id, watch.id, True)
    async with db.session() as session:
        assert await service.enqueue_changes(
            session, old, changed, "TR", source_url=SOURCE_URL
        ) == 1
    assert await service.remove(a.id, watch.id)
    async with db.session() as session:
        count = await session.scalar(
            __import__("sqlalchemy").select(
                __import__("sqlalchemy").func.count()
            ).select_from(VisaWatchEvent)
        )
    assert count == 0
    await db.close()


@pytest.mark.asyncio
async def test_private_watch_callbacks_and_other_user_cannot_remove(tmp_path):
    db, _users, a, b = await database_with_users(tmp_path)
    service = VisaWatchService(db)
    class Query:
        def __init__(self, data):
            self.data = data
            self.calls = []

        async def edit_message_text(self, message, **kwargs):
            self.calls.append((message, kwargs))

    def context():
        return SimpleNamespace(user_data={
            "visa_passport": "IR", "visa_destination": "TR"
        })

    def update(data, typ="private"):
        query = Query(data)
        return SimpleNamespace(
            callback_query=query, effective_chat=SimpleNamespace(type=typ)
        )
    chosen = update("visa:watch:add")
    await handle_watch_callback(chosen, context(), service, a.id, "fa")
    assert "زنگوله تغییرات ویزا" in chosen.callback_query.calls[-1][0]
    first = (await service.list_user(a.id))[0]
    blocked = update(f"visa:watch:delete:{first.id}")
    await handle_watch_callback(blocked, context(), service, b.id, "fa")
    assert "تعلق ندارد" in blocked.callback_query.calls[-1][0]
    assert (await service.list_user(a.id))[0].id == first.id
    group = update("visa:watch:add", "supergroup")
    await handle_watch_callback(group, context(), service, b.id, "fa")
    assert "خصوصی" in group.callback_query.calls[-1][0]
    paused = update(f"visa:watch:toggle:{first.id}")
    await handle_watch_callback(paused, context(), service, a.id, "fa")
    assert not (await service.list_user(a.id))[0].active
    await db.close()


@pytest.mark.asyncio
async def test_stale_warning_is_visible_from_visa_menu(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'menu.db'}")
    async with db.session() as session:
        session.add(VisaDatasetState(
            id=1, source_url="https://travelrequirements.info/data/index.json",
            last_checked_at=datetime.now(timezone.utc) - timedelta(hours=48),
        ))
    class Catalog:
        async def ready(self):
            return True

        async def countries(self):
            return [Country("IR", "Iran"), Country("TR", "Turkey")]

        async def freshness(self):
            return await VisaCatalogService(db).freshness()

    class Query:
        def __init__(self):
            self.calls = []

        async def edit_message_text(self, message, **kwargs):
            self.calls.append((message, kwargs))

    query = Query()
    update = SimpleNamespace(callback_query=query)
    await open_visa_menu(
        update, SimpleNamespace(user_data={}), Catalog(), "fa"
    )
    assert "بیش از 24 ساعت" in query.calls[0][0]
    assert "IR" in query.calls[0][0]
    await db.close()
