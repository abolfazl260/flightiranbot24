"""Safely initialize/migrate the existing SQLite database on container startup.

Run once before both bot and web services. Preserve the original volume.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from flightiran.db.models import Base


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./flightiran.db")
    if not raw_url.startswith("sqlite"):
        raise RuntimeError("Migration bootstrap currently supports the existing SQLite setup")
    url = raw_url.replace("+aiosqlite", "")
    config_file = Path(__file__).resolve().parents[3] / "alembic.ini"
    if not config_file.exists():
        config_file = Path.cwd() / "alembic.ini"
    alembic = Config(str(config_file))
    alembic.set_main_option("sqlalchemy.url", url)
    os.environ["DATABASE_URL"] = raw_url
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
        user_tables = tables - {"alembic_version"}
        if not tables or not user_tables:
            command.upgrade(alembic, "head")
        elif "alembic_version" not in tables:
            # Older images used Base.metadata.create_all without alembic_version.
            # Preserve those tables; create only missing tables, then verify
            # expected columns before marking the schema current.
            Base.metadata.create_all(engine)
            inspector = inspect(engine)
            for table in Base.metadata.sorted_tables:
                existing = {col["name"] for col in inspector.get_columns(table.name)}
                required = {col.name for col in table.columns}
                missing = required - existing
                if missing:
                    raise RuntimeError(
                        f"Legacy SQLite schema needs manual migration: "
                        f"{table.name} missing {sorted(missing)}"
                    )
            command.stamp(alembic, "head")
        else:
            command.upgrade(alembic, "head")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
