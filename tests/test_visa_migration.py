"""Migration bootstrap tests: brand-new and legacy unversioned SQLite volumes."""

from sqlalchemy import create_engine, inspect, text

from flightiran.db.migrate import main
from flightiran.db.models import Base


def test_migrate_new_and_repeatable(tmp_path, monkeypatch):
    db = tmp_path / "new.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    main()
    main()
    engine = create_engine(f"sqlite:///{db}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert {
            "visa_rule_index", "visa_destination_data", "alembic_version",
            "visa_watches", "visa_watch_events",
        } <= tables
        assert "visa_passport" in {
            column["name"] for column in inspect(engine).get_columns("user_preferences")
        }
        assert "last_active_at" in {
            column["name"] for column in inspect(engine).get_columns("users")
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0010_percentage_ticket_alerts"
            )
    finally:
        engine.dispose()


def test_migrate_existing_metadata_without_version(tmp_path, monkeypatch):
    db = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{db}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db}")
    main()
    engine = create_engine(f"sqlite:///{db}")
    try:
        assert {
            "alembic_version", "visa_watches", "visa_watch_events",
        } <= set(inspect(engine).get_table_names())
        assert "visa_passport" in {
            column["name"] for column in inspect(engine).get_columns("user_preferences")
        }
        assert "last_active_at" in {
            column["name"] for column in inspect(engine).get_columns("users")
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0010_percentage_ticket_alerts"
            )
    finally:
        engine.dispose()
