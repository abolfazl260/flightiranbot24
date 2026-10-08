# Deployment checklist

1. Copy `.env.example` to a secret-managed environment file and set `TELEGRAM_BOT_TOKEN`.
2. Create the virtual environment and install the project with `pip install -e .`.
3. Run `alembic upgrade head` with `DATABASE_URL` set to the SQLite URL.
4. Install `deploy/flightiran.service`, enable it, and inspect `journalctl -u flightiran`.
5. Schedule `scripts/backup_db.sh` and verify a restore using `scripts/restore_db.sh`.

## Web App

Set `WEB_APP_ENABLED=true` and `WEB_APP_URL=https://your-domain.example` only after the
domain points to this server and HTTPS is configured. Install `deploy/flightiran-web.service`
alongside the bot service, then proxy the domain to `127.0.0.1:8000` with nginx or another TLS
terminator. Telegram opens the Web App from the button added to the main menu.

Production checks include secret presence, restart recovery, migration status, backup readability,
provider rate limits, Telegram message escaping, and the full CI test suite. `old/` is retained as
an archive and is not imported by the new application.


## New-user registration alerts

On a new Telegram user's first `/start`, the bot atomically inserts their record
into `users` and sends a one-time HTML notification to the configured administrator's
private chat (`TELEGRAM_ADMIN_ID`, alias `ADMIN_ID`). The message contains the user's
Telegram ID, first and last name, username when available, Telegram language, registration
time (UTC), optional Telegram Premium flag and clickable profile/username links.

Repeated `/start` calls, concurrent updates, process restarts and existing database
users do not cause another registration alert. Username and display names are safely
escaped and missing values are labeled rather than fabricated. The bot can only report
profile fields provided by Telegram; it cannot access a user's phone number or email.

**Admin setup:** The administrator must first open the bot in a private chat and
send `/start` so the bot is allowed to message that account. If the Telegram
send fails (e.g. the bot is blocked), the failure is logged without breaking the user's
welcome flow; alerts are attempted once for each newly created user record, and
unsent alerts are not automatically replayed.
