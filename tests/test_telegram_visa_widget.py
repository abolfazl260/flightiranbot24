"""Private ownership, durable subscriptions, pagination and widget fallback."""

import asyncio
import json
import zlib
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.db import initialize_database
from flightiran.db.models import VisaRuleIndex
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.visa_widget import (
    Session,
    chunks,
    handle_visa_widget_query,
    pack,
    published_text,
    send_visa_widget,
    state_for,
    widget_html,
)
from flightiran.modules.visa.catalog import Country, VisaDetail, VisaRule
from flightiran.modules.visa.freshness import assess_freshness
from flightiran.modules.visa.watch import VisaWatchService


class Bot:
    platform = "telegram"

    def __init__(self):
        self.calls = []
        self.send_message = AsyncMock()

    async def _post(self, name, data):
        self.calls.append((name, data))
        return {"message_id": 55} if name == "sendWidget" else True


def catalog():
    rule = VisaRule(
        "IR",
        "TR",
        "Turkey",
        "visa-free",
        90,
        "Full published note 🛂 " * 80,
        "https://mfa.gov.tr/rule",
        "2026-10-07",
        "row",
    )
    source = {
        "name": "MFA",
        "url": rule.source_url,
        "lastVerified": rule.verified_on,
        "type": "government",
    }
    detail = VisaDetail(
        rule,
        {
            "id": "turkey",
            "meta": {"lastUpdated": "2026-10-08"},
            "entryRequirements": {"passportValidity": {"text": "Published condition 🛂 " * 100}},
            "visaPolicy": {"defaultSource": source},
        },
        {"source": source},
        (),
    )
    service = SimpleNamespace(
        ready=AsyncMock(return_value=True),
        countries=AsyncMock(return_value=[Country("IR", "Iran"), Country("TR", "Turkey")]),
        detail=AsyncMock(return_value=detail),
        freshness=AsyncMock(return_value=assess_freshness(datetime.now(timezone.utc))),
    )
    return service, detail


def query(action, owner=123, message=55, **changes):
    raw = {
        "id": "q",
        "data": action,
        "from": {"id": owner},
        "chat": {"id": owner, "type": "private"},
        "message_id": message,
        "type": {"type": "data"},
        **changes,
    }
    return Update(1, api_kwargs={"widget_query": raw})


async def setup(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'visa.db'}")
    users = SQLiteUserRepository(db)
    person = await users.get_or_create(123)
    async with db.session() as session:
        session.add(
            VisaRuleIndex(
                passport="IR",
                destination="TR",
                country_name="Turkey",
                status="visa-free",
                stay_days=90,
                source_level="row",
                notes="published",
            )
        )
    service, detail = catalog()
    bot = Bot()
    context = SimpleNamespace(bot=bot, application=SimpleNamespace(user_data=defaultdict(dict)))
    message = SimpleNamespace(chat_id=123, chat=SimpleNamespace(type="private"))
    watches = VisaWatchService(db)
    assert await send_visa_widget(message, context, service, watches, users, person.id, "fa")
    return db, users, person, service, watches, context, detail


def test_locales_widget_limits_and_lossless_utf8_chunks():
    for lang in ("fa", "en", "ar"):
        html = widget_html(lang)
        assert len(html.encode()) <= 32768 and len(zlib.compress(html.encode(), 9)) <= 4096
        assert "<input" not in html and "<select" not in html and "fetch(" not in html
        assert ".innerHTML" not in html
    text = "شرایط 🛂 / verified " * 500
    assert "".join(chunks(text)) == text
    assert all(len(p.encode()) <= 330 for p in chunks(text))


@pytest.mark.asyncio
async def test_page_all_conditions_without_loss_and_safe_sources(tmp_path):
    db, users, person, service, watches, context, detail = await setup(tmp_path)
    s = Session("1234abcd", "IR", "TR", view="tab:c")
    first = await state_for(s, service, watches, person.id, "fa")
    contents = []
    for page in range(first["pages"]):
        state = await state_for(replace(s, page=page), service, watches, person.id, "fa")
        assert len(pack(state).encode()) <= 900
        contents.append(state["text"].rsplit("\n", 1)[0])
    full = "".join(contents)
    assert published_text(detail.destination_data["entryRequirements"], "fa") in full
    assert "Published condition 🛂 " * 100 in full
    assert "user_id" not in pack(first)
    await db.close()


@pytest.mark.asyncio
async def test_real_watch_is_owned_durable_idempotent_and_stale_actions_do_not_toggle(tmp_path):
    db, users, person, service, watches, context, detail = await setup(tmp_path)
    s = context.application.user_data[123]["visa_widget_sessions"][55]
    open_existing = AsyncMock()

    async def run(command, rev=None):
        await handle_visa_widget_query(
            query(f"vi:{s.token}:{s.rev if rev is None else rev}:{command}"),
            context,
            service,
            watches,
            users,
            open_existing,
        )

    await run("d:TR")
    revision = s.rev
    await asyncio.gather(run("on", revision), run("on", revision))
    owned = await watches.list_user(person.id)
    assert len(owned) == 1 and owned[0].active
    assert (await VisaWatchService(db).list_user(person.id))[0].active
    await run("off")
    assert not (await watches.list_user(person.id))[0].active
    await run("on", revision)  # old request cannot resurrect a stopped watch
    assert not (await watches.list_user(person.id))[0].active
    assert context.bot.calls[1][0] == "answerWidgetQuery"
    assert all(
        "public_data" not in data
        for name, data in context.bot.calls
        if name == "editMessageWidgetData"
    )
    await run("link:0")
    context.bot.send_message.assert_awaited_once()
    assert context.bot.send_message.call_args.kwargs["text"].startswith("https://")
    await run("legacy")
    open_existing.assert_awaited_once_with("legacy", 123)
    await db.close()


@pytest.mark.asyncio
async def test_foreign_invalid_and_expired_widget_requests_fail_closed(tmp_path):
    db, users, person, service, watches, context, detail = await setup(tmp_path)
    s = context.application.user_data[123]["visa_widget_sessions"][55]
    cb = AsyncMock()
    for changes in (
        {"from": {"id": 124}},
        {"chat": {"id": 123, "type": "group"}},
        {"widget_id": "shared"},
        {"type": {"type": "sign_data"}},
        {"message_id": True},
    ):
        await handle_visa_widget_query(
            query(f"vi:{s.token}:0:on", **changes), context, service, watches, users, cb
        )
        assert context.bot.calls[-1][1]["data"] == "invalid"
    await handle_visa_widget_query(
        query(f"vi:{s.token}:0:on", owner=124), context, service, watches, users, cb
    )
    assert not await watches.list_user(person.id)
    assert "منقضی" in context.bot.calls[-1][1]["chat_data"]
    context.bot.platform = "bale"
    assert not await send_visa_widget(
        SimpleNamespace(chat_id=123, chat=SimpleNamespace(type="private")),
        context,
        service,
        watches,
        users,
        person.id,
        "fa",
    )
    await db.close()


@pytest.mark.asyncio
async def test_failed_send_falls_back_and_failed_actions_keep_last_good_state(tmp_path):
    db, users, person, service, watches, context, detail = await setup(tmp_path)
    sessions = context.application.user_data[123]["visa_widget_sessions"]
    s = sessions[55]
    await handle_visa_widget_query(
        query(f"vi:{s.token}:0:d:TR"), context, service, watches, users, AsyncMock()
    )
    previous = dict(s.last)
    service.detail.side_effect = RuntimeError("unavailable")
    await handle_visa_widget_query(
        query(f"vi:{s.token}:{s.rev}:tab:c:0"), context, service, watches, users, AsyncMock()
    )
    failed = json.loads(context.bot.calls[-1][1]["chat_data"])
    assert failed["text"] == previous["text"]
    assert failed["error"] and failed["rev"] > previous["rev"]
    assert sessions[55].view == "tab:s"
    message = SimpleNamespace(chat_id=123, chat=SimpleNamespace(type="group"))
    assert not await send_visa_widget(message, context, service, watches, users, person.id, "fa")
    context.bot._post = AsyncMock(side_effect=RuntimeError("unsupported"))
    message.chat.type = "private"
    assert not await send_visa_widget(message, context, service, watches, users, person.id, "fa")
    await db.close()
