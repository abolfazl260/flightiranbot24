# Telegram HTML fare widget (Bot API 10.4)

The Telegram bot has an opt-in **interactive fare card** displayed directly in a
private chat. This is a small native Telegram HTML widget, **not** a Mini App
or external web page. The existing Android, Mini App, Bale transport, and
ticket-search flow are unchanged.

## How users open it

- Open [the direct fare link](https://t.me/Flightiranbot?start=fares): pressing **Start** sends `/start fares` and opens the interactive card directly. Existing users can launch the link again.
- Alternatively start a private conversation with the Telegram bot and send `/start`.
- Choose **📊 کارت تعاملی قیمت بلیت** in the Telegram menu, or send `/fares`.
- The widget has two locally switchable tabs inside the same Telegram message:
  **ارزان‌ترین بلیت‌ها** (five lowest actual prices) and
  **بیشترین کاهش قیمت** (five largest verified percentage reductions).
- Historical reductions use the existing hourly price history and are
  calculated as `(historical_average - current_price) / historical_average * 100`,
  rounded to one decimal. The route must have at least **three historical
  samples**, a finite positive average, and a current price lower than that
  average. No estimate is fabricated when history is missing.
- Eligible discounts are shown alongside the current ticket price in both
  tabs. Prices and percentages are displayed using Persian numerals.
- Switching tabs is client-side only, preserving the current message and
  requiring no API call. An empty discount tab explains that no validated
  decreases are currently available.
- Tap **تازه‌سازی قیمت‌ها** to request updated data in the same chat bubble.
  The bot acknowledges the interaction immediately, then silently updates the
  message's widget state. It never invents prices.
- This is an informational price feed, not a booking checkout. Prices are
  unconfirmed until validated at reservation.

## Technical design

- `src/flightiran/interfaces/telegram/widgets.py` owns the self-contained
  HTML/CSS/QuickJS, JSON state builder, Bot API calls, and request handling.
- `python-telegram-bot` currently supports forward-compatible unknown fields
  in `Update.api_kwargs`. `TypeHandler(Update, ...)` handles the raw
  `widget_query` update. We do **not** need a second poller or webhook.
- Polling explicitly includes `widget_query` in Telegram `allowed_updates`.
- The new Telegram Bot API methods (`sendWidget`, `answerWidgetQuery`,
  `editMessageWidgetData`) use the authenticated existing bot's `_post`
  transport until supported by the installed PTB version.
- Widgets are **static**, private, and user-scoped; they have `allow_queries`
  but **no shared widget ID**. The state is `public_data` with current fare
  information and `chat_data` for the last refresh status. No database table
  or new secret is needed.
- Both tab lists share one compact `public_data` payload. If it would exceed
  Telegram's 1024-byte limit, it shortens the two lists instead of dropping
  all discounts or sending invalid JSON.
- The widget uses Telegram-native theme tokens and embeds all resources in
  the HTML. It does not attempt to contact any network from QuickJS.
- Telegram enforces 32,768 bytes of HTML, 4,096 compressed bytes and 1,024
  bytes for each state field. The code checks these limits.
- A query is accepted only if it is from the user in the same private chat,
  has an original message ID and carries the allowlisted `fare:refresh`
  action. Every query is answered, including invalid ones.
- Provider errors preserve the last valid fares and set an error status.
- If the Telegram client/server rejects sending widgets, the user receives
  a readable text list; errors logged omit potentially sensitive API URLs.
- Bale never sends `sendWidget` and keeps its existing message handlers.

## Deployment on the existing server

No new environment variables, bot tokens, database migrations or ports are
needed. Deploy this commit as usual and restart **only** the Telegram bot
service. The bot's next command-menu sync adds `/fares`. Leave the Bale bot
and Cloudflare deployments untouched.

The configured Telegram bot must be served by **Bot API 10.4+**, and the
user's Telegram client must support widgets. As of November 9, 2026,
production sends are supported only in private chats.

## Verification

```sh
python -m pip install -e '.[dev]'
ruff check src/flightiran/interfaces/telegram tests/test_telegram_fare_widgets.py
pytest tests/test_telegram_fare_widgets.py
```

Manually test in Telegram: open `https://t.me/Flightiranbot?start=fares` (first-time and returning users), then switch both tabs,
verify the percentage badges against the source history, refresh it, and
confirm that no extra chat message is sent by changing tabs or refreshing. Disconnect the fare
provider and verify that the last prices remain visible with an error message.
Check the same `/start` menu in Bale: it must not show the widget option.

## Rollback

Revert this change to remove the `/fares` command, widget menu button and
new polling subscription. Existing sent widget messages may remain in the chat
but will no longer refresh. The regular ticket listings are unaffected.

Official references:
- https://core.telegram.org/bots/api-changelog#november-9-2026
- https://core.telegram.org/bots/widgets
- https://core.telegram.org/bots/api#sendwidget

## Historical route charts inside the existing /fares widget (2026-11-20)

The bot's private Telegram fare widget now includes an optional in-widget route
picker and SVG visualization of **actual recorded 21-day daily minima**.

- The price ranking tabs and refresh remain unchanged.
- The UI has only in-widget buttons, for Telegram QuickJS compatibility; the
  frontend makes no network calls and creates no extra messages.
- Queries use hashed, bounded origin/destination IDs, and both selections are
  checked against the existing SQLite `list_chart_routes(days=21)` result on
  **every request**. Forged/stale selections cannot fetch arbitrary data.
- The plot comes solely from `get_route_daily_minimums(..., days=21)`.
  Missing days remain blank; lines only connect consecutive real days.
  The last shown price is explicitly a **recorded daily minimum**, not a live
  fare or a guaranteed bookable offer.
- No redundant database schema or provider fetch is needed; if recorded
  history is unavailable, the widget displays an empty/error state.
- Telegram's HTML (32 KiB), compressed HTML (4 KiB), and per-state (1 KiB)
  caps are tested. Queries are accepted only from the author in a private
  chat using the original widget message ID. No public widget sharing.
- The old closed PR #194 was consulted but **not merged**: it used a legacy
  history API (`get_route_history`) and bundled a booking-request action.
  This version uses the modern daily-minimum repository and does **not**
  send a booking message or place an order.

### Manual verification

Send `/fares` in a private Telegram chat, select `مبدأ`, then `مقصد`,
and inspect a route with at least two actual days of price observations.
Verify that dates with no data are not connected and that refresh preserves
the existing two price tabs. Repeat with an empty history and with an older
Telegram client: the regular text fallback must still work. This change
does not affect Bale or Android. Deploy only after automated CI passes.

### Obsolete branches

The stale screenshot branches `fix/android-screenshot-adb-recovery-20261116`
and `fix/android-screenshot-capture-override-20261116` are superseded by
the already-merged PR #241 and later main changes. Do not merge these legacy
branches. The GitHub connector available here cannot delete refs, so actual
branch removal requires the repository's Branches UI or a GitHub-authorized
`git push origin --delete <branch>` command; no deletion has been claimed.
