# Telegram private interactive travel checklist

A native, self-contained **Telegram Bot API 10.4 HTML widget** for tracking
trip preparation. It is not a Telegram Mini App and does not load an external
website. The original fare widget, Bale bot, Android app, and visa/ticket
services are unchanged.

## User journey

1. Open a private chat with the Telegram bot and send `/checklist`, or tap
   **🧳 چک‌لیست تعاملی سفر** after `/start`.
2. Select **پرواز داخلی** or **سفر خارجی**. Both plans are saved independently.
3. Switch between **مدارک / برنامه سفر / وسایل ضروری**.
4. Tap any task once to check or uncheck it. The progress bar, done count,
   and motivational message update with the authoritative server response.
5. On a new device, new widget message or after a restart, the previous
   progress is restored automatically. Use **همگام‌سازی** to manually re-read
   the newest state from the bot.
6. **بازنشانی** requires a second explicit confirmation tap and clears only
   the currently selected mode, never the other travel plan.

The 15 preset tasks have stable IDs: domestic flights show 11, international
travel shows all 15, including passport, visa, foreign currency and roaming.
The lists are general preparation reminders, not authoritative information
about a particular airline, destination or legal requirement.

## Implementation

- `src/flightiran/modules/travel_checklist.py`: validated task catalog and
  SQLite repository; changes use atomic bit operations (no lost updates from
  concurrent taps).
- `src/flightiran/db/models.py`: `travel_checklists` with Telegram user ID,
  independent progress bitsets, active mode and monotonically increasing
  revision. No personal identity documents, route history or uploaded files
  are collected.
- `src/flightiran/db/migrate.py`: an idempotent creation of this isolated
  table after the existing Alembic upgrades. No existing table is altered or
  dropped; the existing `flightiran-data` volume is retained.
- `src/flightiran/interfaces/telegram/checklist_widget.py`: compact,
  RTL, theme-aware QuickJS/HTML widget, validation of widget requests and
  silent message state updates.
- `/checklist` and the private Telegram main-menu button are Telegram-only.
  The existing `widget_query` handler dispatches checklist actions separately
  from fare refresh actions.

## State, privacy and resilience

Only the authenticated Telegram private-chat participant can modify their
own checklist. The server validates `from.id == chat.id`, message ID, query
type, mode and item ID on every interaction. State is held in the existing
Telegram SQLite volume, not browser localStorage, and never shared with
other users or with the Bale bot.

Each interaction returns the updated compact state through
`answerWidgetQuery`, then silently writes `chat_data` using
`editMessageWidgetData`. The revision number prevents a delayed old widget
state from overwriting a newer state in the client. A freshly reopened widget
reads the DB; an already-open second widget can sync explicitly or when it
becomes visible again.

No new secrets, external APIs, network permissions or ports are needed.
On a Telegram client that does not support the widget API, the bot falls back
to a simple text summary.

## Deploy to the existing server

```sh
cd /opt/Flightiran/flightiranbot24
git status --short
git pull --ff-only origin main
docker compose up -d --build migrate bot
docker compose logs --tail=100 bot
```

The `migrate` service creates the new table in the **existing database**.
Do not delete the volume or SQLite file. Use `/checklist` in Telegram
private chat after the bot restarts.

## Validation

```sh
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_telegram_checklist_widget.py
pytest
```

Manual checks: compare domestic vs foreign tasks, uncheck items, complete a
list, reset one plan after confirmation, reopen in a second widget, and verify
that the other plan and another user's progress remain intact. Verify
Bale's menu and its database are unaffected.

Official API: https://core.telegram.org/bots/widgets
