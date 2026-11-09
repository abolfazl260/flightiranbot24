# Telegram HTML fare widget (Bot API 10.4)

The Telegram bot has an opt-in **interactive fare card** displayed directly in a
private chat. This is a small native Telegram HTML widget, **not** a Mini App
or external web page. The existing Android, Mini App, Bale transport, and
ticket-search flow are unchanged.

## How users open it

- Start a private conversation with the Telegram bot and send `/start`.
- Choose **📊 کارت تعاملی قیمت بلیت** in the Telegram menu, or send `/fares`.
- The widget displays up to five of the cheapest **actual source-feed prices**.
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

Manually test in Telegram: `/start`, tap the new card, refresh it, and
confirm that no extra chat message is sent by the refresh. Disconnect the fare
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
