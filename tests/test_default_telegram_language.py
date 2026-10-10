"""Persian-default language must not replace any existing saved preference."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from flightiran.db import initialize_database
from flightiran.db.repositories import SQLiteUserRepository


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_new_user_defaults_persian_and_explicit_choice_survives_restart(tmp_path):
    database = await initialize_database(
        f"sqlite+aiosqlite:///{tmp_path / 'language.sqlite3'}"
    )
    users = SQLiteUserRepository(database)
    new_user = await users.create(telegram_id=5001)
    assert await users.get_language(new_user.id) == "fa"

    # Visa selection creates a preferences row without explicit language.
    await users.set_visa_passport(new_user.id, "TR")
    assert await users.get_language(new_user.id) == "fa"
    assert await users.get_visa_passport(new_user.id) == "TR"

    await users.set_language(new_user.id, "en")
    restarted_users = SQLiteUserRepository(database)
    assert await restarted_users.get_language(new_user.id) == "en"
    await restarted_users.set_language(new_user.id, "ar")
    assert await users.get_language(new_user.id) == "ar"
    await restarted_users.set_language(new_user.id, "fa")
    assert await users.get_language(new_user.id) == "fa"
    await database.close()


def test_schema_migration_preserves_explicit_english_and_arabic(tmp_path, monkeypatch):
    db = tmp_path / "legacy-language.sqlite3"
    url = f"sqlite:///{db}"
    alembic = Config(str(ROOT / "alembic.ini"))
    alembic.set_main_option("sqlalchemy.url", url)
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")

    # Simulate a deployed server at the previous Alembic head, with
    # saved English, Arabic and Persian choices and older default rows.
    command.upgrade(alembic, "0010_percentage_ticket_alerts")
    engine = create_engine(url)
    with engine.begin() as conn:
        for telegram_id in (5002, 5003, 5004, 5005, 5006):
            conn.execute(
                text("INSERT INTO users (telegram_id) VALUES (:id)"),
                {"id": telegram_id},
            )
        conn.execute(text(
            "INSERT INTO user_preferences (user_id, language) "
            "VALUES (1, 'en'), (2, 'ar'), (3, 'fa')"
        ))
        # Preserve pre-existing implicit English rows too: they cannot be
        # distinguished reliably from explicit English selections.
        conn.execute(text(
            "INSERT INTO user_preferences (user_id) VALUES (4)"
        ))
        assert conn.scalar(text(
            "SELECT language FROM user_preferences WHERE user_id=4"
        )) == "en"
    engine.dispose()

    command.upgrade(alembic, "head")
    engine = create_engine(url)
    try:
        language_column = next(
            col for col in inspect(engine).get_columns("user_preferences")
            if col["name"] == "language"
        )
        assert language_column["default"].strip("'\"()") == "fa"
        with engine.begin() as conn:
            existing = conn.execute(text(
                "SELECT user_id, language FROM user_preferences "
                "WHERE user_id IN (1, 2, 3, 4) ORDER BY user_id"
            )).all()
            assert existing == [(1, "en"), (2, "ar"), (3, "fa"), (4, "en")]
            conn.execute(text(
                "INSERT INTO user_preferences (user_id) VALUES (5)"
            ))
            assert conn.scalar(text(
                "SELECT language FROM user_preferences WHERE user_id=5"
            )) == "fa"
            assert conn.scalar(text("PRAGMA foreign_key_check")) is None
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0011_default_persian_language"
            )
    finally:
        engine.dispose()
