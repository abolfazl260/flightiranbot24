"""End-to-end catalog navigation, ownership, refresh and safe fallback."""

import asyncio
import json
import shutil
import subprocess
import zlib
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import Update

from flightiran.interfaces.telegram.handlers import (
    TelegramDependencies,
    _all_widget_queries,
    callback_handler,
    register_handlers,
    start_handler,
    useful_command_handler,
)
from flightiran.interfaces.telegram.useful_widget import (
    ERROR,
    LABELS,
    Session,
    detail_chunks,
    filters,
    handle_useful_widget_query,
    pack,
    safe_url,
    selected_links,
    send_useful_widget,
    state_for,
    widget_html,
)
from flightiran.modules.useful_content import UsefulContentCatalog, UsefulLink, default_catalog


class Bot:
    platform = "telegram"

    def __init__(self):
        self.calls = []
        self.fail = set()
        self.send_message = AsyncMock()

    async def _post(self, method, data):
        self.calls.append((method, data))
        if method in self.fail:
            raise RuntimeError("unavailable")
        return {"message_id": 55} if method == "sendWidget" else True


def context():
    return SimpleNamespace(bot=Bot(), user_data={}, args=[])


def message(chat_type="private"):
    return SimpleNamespace(
        chat=SimpleNamespace(type=chat_type), chat_id=123, reply_text=AsyncMock()
    )


def query(action, **overrides):
    return Update(
        1,
        api_kwargs={
            "widget_query": {
                "id": "query",
                "from": {"id": 123},
                "chat": {"id": 123, "type": "private"},
                "message_id": 55,
                "data": action,
                **overrides,
            }
        },
    )


async def setup():
    ctx = context()
    holder = [default_catalog()]

    def current():
        return holder[0]

    assert await send_useful_widget(message(), ctx, current)
    return ctx, holder, current


async def act(ctx, current, command):
    session = ctx.user_data["useful_widget_sessions"][55]
    action = f"uf:{session.token}:{session.rev}:{command}"
    await handle_useful_widget_query(query(action), ctx, current)
    return ctx.user_data["useful_widget_sessions"][55]


def test_all_resources_categories_and_metadata_preserved_with_bounded_pages():
    catalog = default_catalog()
    snapshot = catalog.all()
    s = Session()
    home = state_for(s, catalog)
    assert len(home["rows"]) == 7  # Six categories, plus the complete archive.
    assert home["total"] == 21
    assert set(LABELS) == {
        "documents",
        "flights",
        "baggage",
        "international",
        "payments",
        "tips",
        "flight-rules",
        "travel-sites",
    }
    s.view, s.category = "list", ""
    first = state_for(s, catalog)
    seen = []
    for page in range(first["pages"]):
        s.page = page
        state = state_for(s, catalog)
        assert len(pack(state).encode()) <= 1024
        for row in state["rows"]:
            index = int(row["a"].split(":")[1])
            seen.append(s.ids[index])
    assert seen == [x.id for x in snapshot]
    assert catalog.all() == snapshot
    assert all(
        len(("uf:" + s.token + ":999999999:" + row["a"]).encode()) <= 64 for row in home["rows"]
    )
    raw = widget_html().encode()
    assert len(raw) <= 32768 and len(zlib.compress(raw, 9)) <= 4096
    assert "<input" not in widget_html() and "innerHTML" not in widget_html()
    assert "fetch(" not in widget_html() and "https://" not in widget_html()


def test_full_long_text_round_trips_without_invented_dates_or_html():
    title, desc = "<script>نام طولانی 🛂</script>" * 50, "توضیح & واقعی 🧳 " * 500
    link = UsefulLink("long", title, "https://example.org", "tips", desc, date(2026, 11, 9))
    catalog = UsefulContentCatalog([link])
    s = Session(view="detail", link_id=link.id)
    first = state_for(s, catalog)
    parts = []
    for page in range(first["pages"]):
        s.page = page
        state = state_for(s, catalog)
        parts.append(state["text"])
        assert len(pack({**state, "error": ERROR}).encode()) <= 1024
        assert state["checked"] == "2026-11-09"
    assert "".join(parts) == title + "\n" + desc
    assert (
        state_for(
            Session(view="detail", link_id="long"),
            UsefulContentCatalog([replace(link, checked_on="invalid")]),
        )["checked"]
        == ""
    )
    with pytest.raises(ValueError):
        pack({"text": "🛂" * 1000})


def test_filters_search_title_description_country_and_empty_state():
    catalog = default_catalog()
    assert "کانادا" in filters(catalog)
    assert len(selected_links(catalog, "", "کانادا")) == 2
    assert selected_links(catalog, "", "پاسپورت")
    custom = UsefulContentCatalog(
        [UsefulLink("a", "A", "https://example.org", "tips", "توضیحات كاغذی")]
    )
    assert selected_links(custom, "", "کاغذی")
    assert state_for(Session(view="list", term="ناموجود"), custom)["empty"]
    assert state_for(Session(view="home"), UsefulContentCatalog([]))["total"] == 0


@pytest.mark.asyncio
async def test_navigation_parent_links_explicit_open_and_shared_dispatcher():
    ctx, holder, current = await setup()
    s = await act(ctx, current, "category:flights")
    assert not ctx.bot.send_message.called
    await act(ctx, current, "category:flight-rules")
    s = await act(ctx, current, "back")
    assert s.category == "flights"  # Preserve actual entry parent.
    await act(ctx, current, "category:all")
    s = await act(ctx, current, "detail:0")
    assert s.last["can_open"] and not ctx.bot.send_message.called
    deps = TelegramDependencies(None, None, useful_catalog=holder[0])
    await _all_widget_queries(query(f"uf:{s.token}:{s.rev}:open"), ctx, deps)
    sent = ctx.bot.send_message.call_args.kwargs
    assert sent["reply_markup"].inline_keyboard[0][0].url == holder[0].all()[0].url
    assert sent["parse_mode"] is None
    assert json.loads(ctx.bot.calls[-1][1]["chat_data"])["notice"]
    s = await act(ctx, current, "filters")
    i = s.terms.index("کانادا")
    s = await act(ctx, current, f"filter:{i}")
    assert len(s.ids) == 2
    assert [x[0] for x in ctx.bot.calls].count("sendWidget") == 1


@pytest.mark.asyncio
async def test_refresh_reads_current_catalog_and_preserves_last_valid_data_on_failure():
    ctx, holder, current = await setup()
    await act(ctx, current, "category:all")
    old = holder[0].all()
    holder[0] = UsefulContentCatalog(
        [
            replace(old[0], title="عنوان تازه"),
            *old[1:],
            UsefulLink("added", "جدید", "https://example.org", "tips"),
        ]
    )
    s = await act(ctx, current, "refresh")
    assert s.last["total"] == 22 and s.last["rows"][0]["n"] == "عنوان تازه"

    def fail():
        raise RuntimeError("catalog unavailable")

    before = s.last
    s = await act(ctx, fail, "refresh")
    assert s.last["rows"] == before["rows"] and s.last["error"] == ERROR
    s = await act(ctx, current, "refresh")
    assert "error" not in s.last
    await act(ctx, current, "detail:0")
    holder[0] = UsefulContentCatalog([replace(old[0], active=False), *old[1:]])
    await act(ctx, current, "open")
    assert not ctx.bot.send_message.called  # Removed source cannot be opened from stale state.


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [
        {"from": {"id": 124}},
        {"chat": {"id": 123, "type": "group"}},
        {"chat": {"id": True, "type": "private"}},
        {"message_id": True},
        {"message_id": 0},
        {"widget_id": "shared"},
        {"type": {"type": "refresh"}},
        {"data": "uf:invalid"},
        {"data": "https://evil.test"},
        {"data": "uf:" + "a" * 100},
    ],
)
async def test_untrusted_queries_answered_without_side_effects(override):
    ctx, _, current = await setup()
    s = ctx.user_data["useful_widget_sessions"][55]
    await handle_useful_widget_query(query(f"uf:{s.token}:0:open", **override), ctx, current)
    assert ctx.bot.calls[-1] == (
        "answerWidgetQuery",
        {"widget_query_id": "query", "data": "invalid"},
    )
    assert not ctx.bot.send_message.called


@pytest.mark.asyncio
async def test_missing_session_wrong_nonce_replay_and_concurrent_requests():
    ctx, _, current = await setup()
    s = ctx.user_data["useful_widget_sessions"][55]
    for action, overrides in [
        (f"uf:{s.token}:0:refresh", {"message_id": 56}),
        ("uf:00000000:0:refresh", {}),
    ]:
        await handle_useful_widget_query(query(action, **overrides), ctx, current)
        assert ctx.bot.calls[-1][1]["data"] == "invalid"
    action = f"uf:{s.token}:0:refresh"
    await asyncio.gather(
        *(handle_useful_widget_query(query(action), ctx, current) for _ in range(2))
    )
    assert s.rev == 1
    assert [method for method, _ in ctx.bot.calls].count("editMessageWidgetData") == 1


@pytest.mark.asyncio
async def test_invalid_link_index_and_category_do_not_open_external_links():
    ctx, _, current = await setup()
    for command in ["category:unknown", "detail:999", "open", "filter:999", "page:999"]:
        s = await act(ctx, current, command)
        assert s.last["error"] == ERROR
    assert not ctx.bot.send_message.called
    for url in [
        "javascript:alert(1)",
        "https://user:pass@example.org",
        "https://example.org:bad",
        "https://example.org/\nfoo",
    ]:
        assert not safe_url(url)
    assert safe_url("http://example.org/path") and safe_url("https://t.me/example/1")


class Users:
    async def get_or_create(self, *args, **kwargs):
        return SimpleNamespace(id=123)

    async def get_or_create_with_status(self, *args, **kwargs):
        return SimpleNamespace(id=123), False

    async def get_language(self, user_id):
        return "fa"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chat_type,platform,failure",
    [
        ("private", "telegram", False),
        ("private", "telegram", True),
        ("private", "bale", False),
        ("group", "telegram", False),
    ],
)
async def test_commands_menu_start_and_legacy_fallback(chat_type, platform, failure):
    ctx = context()
    ctx.bot.platform = platform
    if failure:
        ctx.bot.fail.add("sendWidget")
    deps = TelegramDependencies(Users(), SimpleNamespace(record=AsyncMock()))
    msg = message(chat_type)
    update = SimpleNamespace(
        message=msg,
        effective_user=SimpleNamespace(id=123, username="test", first_name="Test", last_name=None),
        effective_chat=SimpleNamespace(id=123, type=chat_type),
        callback_query=None,
    )
    await useful_command_handler(update, ctx, deps)
    expect = chat_type == "private" and platform == "telegram" and not failure
    assert msg.reply_text.called is not expect
    ctx.args = ["useful"]
    await start_handler(update, ctx, deps)
    assert msg.reply_text.called is not expect
    q = SimpleNamespace(
        data="menu:useful", message=msg, answer=AsyncMock(), edit_message_text=AsyncMock()
    )
    update.callback_query = q
    await callback_handler(update, ctx, deps)
    assert q.edit_message_text.called is not expect
    await useful_command_handler(update, ctx, deps, legacy=True)
    assert msg.reply_text.called
    assert len(msg.reply_text.call_args.kwargs["reply_markup"].inline_keyboard) == 7


def test_command_registration():
    app = SimpleNamespace(
        bot=Bot(),
        add_handler=lambda h, **kwargs: handlers.append(h),
        add_error_handler=lambda h: None,
    )
    handlers = []
    register_handlers(app, TelegramDependencies(Users(), None))
    commands = {c for h in handlers for c in getattr(h, "commands", [])}
    assert {"useful", "useful_legacy"} <= commands


def test_widget_javascript_interactions_use_real_generated_state():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the widget DOM interaction smoke")
    catalog = default_catalog()
    states = [
        state_for(Session(), catalog),
        state_for(Session(view="list", category="flights"), catalog),
        state_for(Session(view="detail", link_id=catalog.all()[0].id), catalog),
    ]
    subprocess.run(
        [node, str(Path(__file__).with_name("useful_widget_smoke.cjs"))],
        input=json.dumps({"html": widget_html(), "states": states}),
        text=True,
        check=True,
        capture_output=True,
        timeout=10,
    )


@pytest.mark.asyncio
async def test_legacy_selection_stays_in_old_navigation():
    ctx, holder, current = await setup()
    await act(ctx, current, "legacy")
    assert ctx.user_data["useful_widget_legacy"]
    msg = message()
    q = SimpleNamespace(
        data="menu:useful", message=msg, answer=AsyncMock(), edit_message_text=AsyncMock()
    )
    update = SimpleNamespace(
        message=None,
        callback_query=q,
        effective_user=SimpleNamespace(id=123, username="u", first_name="U", last_name=None),
        effective_chat=SimpleNamespace(id=123, type="private"),
    )
    deps = TelegramDependencies(
        Users(), SimpleNamespace(record=AsyncMock()), useful_catalog=holder[0]
    )
    await callback_handler(update, ctx, deps)
    assert q.edit_message_text.called
    assert len([x for x in ctx.bot.calls if x[0] == "sendWidget"]) == 1


@pytest.mark.asyncio
async def test_edit_failure_gives_visible_legacy_fallback():
    ctx, _, current = await setup()
    ctx.bot.fail.add("editMessageWidgetData")
    await act(ctx, current, "refresh")
    assert "/useful_legacy" in ctx.bot.send_message.call_args.kwargs["text"]


def test_detail_paging_preserves_blank_lines_without_needing_scroll():
    text = "سفر\n" * 500 + "W" * 1000
    pages = detail_chunks(text)
    assert "".join(pages) == text
    assert all(len(page) <= 160 and page.count("\n") <= 5 for page in pages)
