# Deployment checklist

1. Copy `.env.example` to a secret-managed environment file and set `TELEGRAM_BOT_TOKEN`.
2. Create the virtual environment and install the project with `pip install -e .`.
3. Run `alembic upgrade head` with `DATABASE_URL` set to the SQLite URL.
4. Install `deploy/flightiran.service`, enable it, and inspect `journalctl -u flightiran`.
5. Schedule `scripts/backup_db.sh` and verify a restore using `scripts/restore_db.sh`.

Production checks include secret presence, restart recovery, migration status, backup readability,
provider rate limits, Telegram message escaping, and the full CI test suite. `old/` is retained as
an archive and is not imported by the new application.

