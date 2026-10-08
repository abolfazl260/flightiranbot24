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


## Daily 24-hour active users report

Every day at **09:00 Asia/Tehran** (by default), the bot sends a **private HTML list**
of unique users active within the preceding rolling 24 hours to `TELEGRAM_ADMIN_ID`.
The report shows the total, UTC-window equivalents converted to the configured time zone,
each user's first/last name, username, numeric Telegram ID, clickable Telegram profile,
and last seen time. The bot sends the full report in multiple messages if needed to
respect Telegram's 4096-character limit, and reports zero activity explicitly.

`ACTIVE_USERS_REPORT_ENABLED=true` enables the task.
`ACTIVE_USERS_REPORT_TIME=09:00` sets the local 24-hour `HH:MM` send time.
`ACTIVE_USERS_REPORT_TIMEZONE=Asia/Tehran` sets the IANA time zone for scheduling
and displayed times. An administrator must start the bot in a private chat to receive
notifications. Only the bot process schedules the job; the web process writes activity
to the **same SQLite volume**.

The database migration `0008_user_last_active` adds an indexed, nullable
`users.last_active_at` timestamp. Interactions with Telegram (commands, buttons,
searches, and inline queries) and verified Web App endpoints update this field. Only
the most recent activity is retained per Telegram ID, so there are no duplicate users
in the report and no unbounded per-click audit rows. Tracking runs **after** the
normal bot update handler, so the first-/start registration notification is unaffected.

Existing rows start with an unknown last activity time; they appear in the report
only after interacting following deployment. The report is sent automatically at the
next scheduled time, not immediately at startup. A stopped bot cannot send a
scheduled report during its downtime. Failed sends are logged and marked in
`job_runs`; future days continue on schedule.
