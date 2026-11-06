# Bale bot (optional second messenger)

The existing Python handlers run unchanged on Telegram. Bale uses a small
`BaleBot` adapter that points python-telegram-bot at the official Bale HTTP API.
See the [official Bale Bot API](https://docs.bale.ai/).

## Credentials

1. In Bale, open [@botfather](https://ble.ir/botfather) and create a bot.
2. Add `BALE_BOT_TOKEN=<the Bale token>` to your **private** `.env` or service
   secret store. Do **not** commit tokens.
3. Keep the existing `TELEGRAM_BOT_TOKEN` for the current Telegram bot. The
   Bale runner uses the same settings class, so both tokens must be configured
   when running the two bots on the same deployment.
4. Optionally set `BALE_ADMIN_ID` to your **Bale** private user/chat ID. Do not
   put a Telegram ID here. When it is unset, administrator notifications and
   the Bale admin menu are disabled.

## Docker Compose

The original `bot`, `migrate` and `web` services are unchanged and start
normally. The Bale profile adds a **separate** migration and polling process:

```bash
docker compose --profile bale up -d --build
docker compose logs -f bot-bale
```

The Bale data file is `/data/flightiran-bale.db` in the existing Docker
volume. The Telegram database remains `/data/flightiran.db`. This prevents
Telegram and Bale user IDs from overlapping and keeps price/visa subscriptions
and audit data private to their respective platforms. Both share the same
Python modules and fare/visa data sources, not a synchronized user database.

## Without Docker

Set `BALE_DATABASE_URL` to a separate SQLite URL and run its migrations before
starting the second process:

```bash
DATABASE_URL=sqlite+aiosqlite:///./flightiran-bale.db python -m flightiran.db.migrate
flightiran-bale
```

Continue running `flightiran` for Telegram in its original service.
An optional systemd example is `deploy/flightiran-bale.service`.

## Compatibility notes

- `getUpdates` long polling, text messages, inline keyboards and callback
  actions reuse the Telegram handlers. Do not configure a Bale webhook at the
  same time as polling.
- Bale documents Markdown formatting rather than Telegram HTML; the Bale
  adapter sends readable **plain text**, including URL addresses, for HTML
  messages. Telegram retains its original HTML presentation.
- Telegram's `sendRichMessage` endpoint is **never called** with the Bale
  token; existing simple-text fallback messages are used in Bale.
- The Telegram Mini App launch button is intentionally omitted on Bale:
  Telegram Mini App authentication must not be reused for Bale sessions.
- Existing Telegram-only support, ticket-booking and cargo URLs remain
  external links when clicked in Bale; replace them separately if a
  corresponding Bale account/channel becomes available.
- Each platform's alerts are delivered to its own users. Bale must be tested
  with a real token and a real private chat before production rollout.

## Smoke test

In Bale, open the new bot and try `/start`, switching language, choosing a
price/visa menu, and returning with the inline `back` button. Verify that
Telegram still responds independently and check `bot-bale` logs for API errors.
No credentials or user IDs should appear in application logs.
