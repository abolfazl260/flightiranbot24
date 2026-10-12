# FlightIranBot24 — Telegram Mini App (Persian, RTL)

The Telegram Mini App is served by the **existing** FastAPI `web` Docker
service over a public HTTPS domain with TLS termination at the existing
reverse proxy. It shares the bot's **same persistent SQLite Docker volume**;
it does **not** connect directly to SQLite from JavaScript or expose private
SQL tables to browsers. No additional database or Cloudflare R2 is necessary.

## Implemented screens

- **Home:** Persian greeting, compact last-recorded ticket fare preview, service shortcuts.
- **Tickets:** current recorded fare list, origin selection, destination search,
  comparison change indicator, timestamp and explicit stale warning. The booking
  button opens `@Advertio_support`; the price is not a guaranteed booking.
- **Visa:** defaults to **Iranian passport (IR)** for new visitors, with a
  synchronized stored passport preference and searchable destinations sourced
  from the indexed visa dataset, source links, verification date, and visa alerts.
- **Alerts:** create percentage-based ticket alerts, follow visa rule
  changes, pause/resume/delete **your own** alerts using the same bot services.
  Notifications are delivered through the existing Telegram bot scheduler.
- **Useful information:** curated categorized links shared with Telegram;
  international cargo channel at `https://t.me/advertio_cargo`.
- **Airports:** explicitly “به‌زودی”, consistent with the Telegram bot.

The interface is **Persian-only, right-to-left**, responsive, adapts to
Telegram theme colors, and uses Telegram BackButton/HapticFeedback where
supported. No external UI framework, no front-end API secrets, and no raw
user HTML injection.

## Configure the existing Ubuntu server

1. Point an HTTPS-enabled domain or subdomain to the **existing** FastAPI web
   service (Docker published port 8000). Prefer a dedicated subdomain such as
   `app.YOUR-DOMAIN` to avoid conflicting with an existing website. The
   Mini App is available at `https://YOUR-HTTPS-HOST/mini/`; static assets
   under `/assets/`, JSON endpoints under `/api/`. The TLS certificate
   must be valid, and the URL reachable from the public Internet, not just
   localhost or `http://YOUR-DOMAIN:8086/`. Cloudflare Worker HTTPS for
   public Android prices does **not** automatically serve this Mini App.
2. Keep the current nginx / Caddy TLS configuration. Reverse-proxy all
   relevant paths to `http://127.0.0.1:8000` (or the Docker web service)
   **without path stripping**. Example nginx **inside an existing HTTPS
   server block**, not an additional competing virtual host:

   ```nginx
   location /mini/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   }
   location /assets/ {
       proxy_pass http://127.0.0.1:8000;
   }
   location /api/ {
       proxy_pass http://127.0.0.1:8000;
   }
   ```

   If the HTTPS host is **dedicated** to the Mini App, an all-paths
   `location /` reverse proxy is simpler. Adjust `proxy_pass` address
   to your deployment and restrict external port 8000 with firewall/TLS
   proxy rules. Do not overwrite an existing website's unrelated `/api/`
   routes without auditing them.

3. In the **server-side** `.env`, set:

   ```dotenv
   WEB_APP_ENABLED=true
   WEB_APP_URL=https://YOUR-HTTPS-HOST/mini/
   TELEGRAM_BOT_USERNAME=Flightiranbot
   SUPPORT_USERNAME=@Advertio_support
   ```

   The `WEB_APP_URL` must be public HTTPS. Both bot and web use the same
   `TELEGRAM_BOT_TOKEN` and `DATABASE_URL` from existing settings.
   **No new Telegram secret** is required. Never put the bot token,
   Cloudflare publishing secret or SQLite DB file in web assets.

4. Deploy using your existing Docker Compose setup:

   ```sh
   cd /opt/Flightiran/flightiranbot24
   git pull --ff-only origin main
   docker compose --profile cloudflare up -d --build
   docker compose --profile cloudflare ps
   docker compose logs --tail=60 web bot
   ```

   The `cloudflare` profile is only necessary if you already use
   `cloudflare-publisher`; otherwise `docker compose up -d --build`
   is sufficient.

5. Verify:

   ```sh
   curl -i https://YOUR-HTTPS-HOST/healthz
   curl -i https://YOUR-HTTPS-HOST/mini/
   curl -i https://YOUR-HTTPS-HOST/assets/mini.js
   ```

   Opening `/mini/` directly in an ordinary browser displays a
   **Telegram sign-in required** notice. This is expected. Real data
   and subscription actions require a valid Telegram signed `initData`
   payload, which the official Telegram webview supplies.

## Telegram integration

- Send `/start` to `@Flightiranbot` to refresh the inline keyboard.
  When `WEB_APP_ENABLED=true` and `WEB_APP_URL` is valid HTTPS, a
  **🚀 ورود به مینی‌اپ سفر** button appears in the bot main menu.
- Optional persistent Mini App entry: in `@BotFather`, choose
  `/setmenubutton`, select the bot and enter the same HTTPS Mini App URL
  as the menu-button Web App. You must configure this manually in the owner
  account; merging code does not change BotFather configuration.
- Telegram `/start alerts` is a safe deep link to the existing bot alert
  manager, useful when a user prefers Telegram messages.

## API and security contract

- Public, unpersonalized: `GET /api/v1/tickets/prices` (also used by Android).
- **Every** `/api/mini/*` call requires valid
  `X-Telegram-Init-Data` HMAC signed with the bot token, checked
  **server-side**, and up to 24 hours old (future timestamps rejected).
- The authenticated user ID comes **only** from validated Telegram
  initData. Client supplied user IDs are ignored and other users' alert IDs
  fail with 404. Mutations use server-side alert/visa service validation.
- `GET /api/mini/bootstrap`: first name, country choices, stored passport,
  bot/cargo/support URLs; **no numeric user ID, Telegram token or admin data**.
- `POST /api/mini/passport`: save your own passport preference.
- `GET /api/mini/visa` and `GET /api/mini/visa/rule`: bounded,
  indexed visa facts; never raw upstream documents or private data.
- `GET /api/mini/useful`: shared curated HTTPS links.
- `GET /api/mini/alerts`, `POST /api/mini/alerts/prices`,
  `PATCH|DELETE /api/mini/alerts/prices/{id}`,
  `POST /api/mini/alerts/visa`,
  `PATCH|DELETE /api/mini/alerts/visa/{id}`: own alert management only.
- Mini App session responses set `Cache-Control: no-store`. Static
  shell has a restrictive CSP; the webview loads the official
  `https://telegram.org/js/telegram-web-app.js` integration.
- It does **not** allow logging in through a random browser, unvalidated
  `initDataUnsafe`, Telegram username alone, a query-string token,
  or a shared application-wide API key.

## Operational cautions

- D1/Workers power the **public Android API** from the prior work.
  This **authenticated** Mini App uses existing FastAPI + primary SQLite;
  do not proxy these private Mini App endpoints to the public Cloudflare
  Worker and do not expose SQLite/D1 credentials to the client.
- The Mini App requires both existing `web` and `bot` containers:
  the web process reads/writes the same SQLite DB; Telegram bot continues
  to perform price captures and send notifications.
- If the visa index is empty, sync it via Telegram `/visa_sync`
  with administrator privileges. Ticket previews require recorded prices;
  no synthetic fares or confirmations are generated.
- External users cannot invoke Admin Reports via the Mini App.
  Only the bot's existing private admin menu may access such data.

## Local tests

```sh
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_telegram_mini_app.py tests/test_webapp_api.py tests/test_webapp.py
node --check src/flightiran/webapp/static/mini.js
```
