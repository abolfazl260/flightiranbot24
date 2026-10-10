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


## Ticket price bell and automatic alerts

Users can open **🔔 Ticket price alerts** from the main menu, ticket listings,
or the **/alerts** command. Select a route and then choose **price ceiling** or
**percentage drop**. Price ceilings accept positive values in tomans with
English, Persian or Arabic numerals. Percentage thresholds use 10 button
presets: 5%, 10%, ... 50%. Saved alerts persist in SQLite; each user can
list, pause, resume or delete their own alerts (maximum 20 active alerts).
Use `/cancel` to abandon price input.

`PRICE_ALERTS_ENABLED=true` enables the menu and scheduler integration.
The existing `TICKET_HISTORY_INTERVAL_MINUTES=60` scheduled mz724 capture
also matches newly fetched route prices to active user alerts, avoiding a
second crawl. If the currently listed price is at or below the chosen
threshold, the bot sends the user a private Telegram message and deduplicates
identical price notifications. Failed Telegram delivery is retried on a
subsequent price scan. Pausing suppresses notifications; resuming re-arms
the threshold even if the price is unchanged.

No departure date, seats, fare availability, or booking confirmation is
provided by this feed. The alert represents only the published route price,
which can change before booking. Users must first start a private chat with
the bot to receive push notifications. SQLite does not enforce VARCHAR length limits, so the existing saved-routes
schema already stores full Persian city names safely. The ORM declaration
uses 128 characters without rebuilding a referenced production table.

### Percentage-based ticket price alerts and provider privacy

Discount alerts are evaluated against the route's recorded **21-day rolling
mean** using `current_price <= average_price * (1 - selected_percent / 100)`.
At least **two valid historic price samples** are required. Until sufficient
history has accumulated, no percent-based alert is sent (the subscription
remains enabled). The capture job updates route averages before comparing
thresholds; the provider is never queried again just for alerts.

Users choose a discount percentage using buttons from **5% to 50% in 5-point
steps**; the backend additionally rejects percentages outside 1–50 even if a
Telegram callback is forged. Delivered percent alerts display the actual fare,
21-day average, percentage reduction and chosen threshold. Existing absolute
alerts, pause/resume/delete, delivery retry, per-user access checks, dedup and
20-alert limit are preserved. A fare that did not meet a percentage criterion
is not recorded as notified: it can qualify on a later scan if the moving
average changes. A successfully notified identical fare is not repeatedly
sent until resumed.

Additive Alembic migration `0010_percentage_ticket_alerts` preserves
existing saved alert rows and historical snapshots; back up the SQLite volume
before deploying. The upstream ticket provider's identity and links are
**internal only**, never shown in ticket or alert messages. The bot's own
booking and support links remain available. Original source verification
links in unrelated visa features are unaffected.
