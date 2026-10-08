"""Daily 24-hour active-user tracking and private report tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from flightiran.db import initialize_database
from flightiran.db.models import User
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.interfaces.telegram.handlers import user_activity_handler
from flightiran.modules.admin.daily_active import (
    ActiveUser,
    ActiveUsersReportRepository,
    render_active_users_report,
)


@pytest.mark.asyncio
async def test_activity_tracks_unique_users_across_sources_and_exact_24h_window(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'activity.db'}")
    users = SQLiteUserRepository(db)
    now = datetime(2026, 10, 8, 9, tzinfo=timezone.utc)
    await users.mark_active(
        101, username="member_101", first_name="Ali",
        at=now - timedelta(hours=1),
    )
    await users.mark_active(
        101, first_name="Ali", at=now - timedelta(hours=2)
    )
    await users.mark_active(
        102, username="member_102", at=now - timedelta(hours=24)
    )
    await users.mark_active(
        103, username="old_member", at=now - timedelta(hours=24, seconds=1)
    )
    await users.mark_active(
        104, first_name="Future", at=now + timedelta(minutes=1)
    )
    report = await ActiveUsersReportRepository(db).collect(now=now)
    assert [item.telegram_id for item in report] == [101, 102]
    assert report[0].username == "member_101"
    assert report[0].last_active_at.replace(tzinfo=timezone.utc) == (
        now - timedelta(hours=1)
    )
    assert [user.telegram_id for user in report].count(101) == 1
    async with db.session() as session:
        assert len((await session.scalars(select(User))).all()) == 4
    await db.close()


@pytest.mark.asyncio
async def test_activity_observer_handles_callback_and_excludes_bots(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'observer.db'}")
    deps = SimpleNamespace(users=SQLiteUserRepository(db))
    human = SimpleNamespace(
        id=123, first_name="User", last_name=None,
        username="example123", is_bot=False,
    )
    update = SimpleNamespace(effective_user=human, callback_query=object())
    await user_activity_handler(update, None, deps)
    report = await ActiveUsersReportRepository(db).collect()
    assert len(report) == 1
    assert report[0].telegram_id == 123
    update.effective_user = SimpleNamespace(id=124, is_bot=True)
    await user_activity_handler(update, None, deps)
    assert len(await ActiveUsersReportRepository(db).collect()) == 1
    await db.close()


def test_daily_report_escapes_names_and_splits_for_telegram():
    now = datetime(2026, 10, 8, 9, tzinfo=timezone.utc)
    users = [
        ActiveUser(
            telegram_id=i + 10, first_name="<user> &", last_name="Test",
            username=f"member_{i:04d}", last_active_at=now,
        )
        for i in range(150)
    ]
    pages = render_active_users_report(users, now=now)
    assert len(pages) > 1
    assert all(len(page) <= 4096 for page in pages)
    assert all("تعداد کاربران یکتا: <b>150</b>" in page for page in pages)
    assert pages[0].count("ID:") < 150
    joined = "\n".join(pages)
    assert joined.count("ID:") == 150
    assert "&lt;user&gt; &amp;" in joined
    assert "<user>" not in joined
    assert 'href="https://t.me/member_0000"' in joined
    assert 'href="tg://user?id=10"' in joined
    assert "بخش 1 از" in pages[0]


def test_empty_report_is_still_sent_and_missing_username_is_safe():
    now = datetime(2026, 10, 8, 9, tzinfo=timezone.utc)
    assert "فعالیتی ثبت نشده" in render_active_users_report([], now=now)[0]
    data = [ActiveUser(123456, "سلام", None, None, now)]
    rendered = render_active_users_report(data, now=now)[0]
    assert "ندارد" in rendered
    assert "123456" in rendered
    assert "Asia/Tehran" in rendered
