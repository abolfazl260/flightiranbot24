# FlightIranBot24 Telegram Mini App — Cloudflare workers.dev (no custom domain)

## What is deployed

The Persian-only RTL Telegram Mini App runs on **the same free Cloudflare
Worker** already serving the Android read-only API.

**Mini App URL:**

```text
https://flightiran-public-api.abolfazl260.workers.dev/mini/
```

- **No** custom domain, DNS edits, certbot, nginx, Cloudflare Tunnel, R2
  subscription or payment card is needed.
- Existing `https://advertio.ir` stays on its current unrelated service.
- The Worker serves the existing `index.html`, `mini.css` and `mini.js`
  as first-party static assets. The existing Android endpoints
  `/api/v1/tickets/prices` and `/api/v1/visa/*` still read D1 unchanged.
- Public visa listings and actual recorded ticket prices read the
  **compact D1 public projection**; no synthetic prices or raw source JSON links.
- For user-specific actions (passport settings, alerts, links, home profile)
  the Worker validates Telegram-signed `initData` using a **Worker secret**,
  queues a minimal request in a **private, short-lived D1 table**, and returns
  a job handle. A new `cloudflare-mini-bridge` Docker container on Ubuntu
  polls Worker **outbound using HTTPS 443**, then executes the request via the
  *existing authenticated FastAPI domain service in memory* against the
  existing authoritative SQLite database. The result is delivered only to
  the same validated Telegram user via job polling.

**Architecture**

```text
Telegram webview
       |
       | HTTPS (public Cloudflare domain, no new DNS)
       v
flightiran-public-api.<account>.workers.dev
  |-- /mini/ + /assets/*   Worker static HTML/CSS/JS
  |-- /api/v1/*            existing public D1 prices/visa/airports (Android)
  |-- /api/mini/visa*      HMAC-authenticated D1 visa read
  |-- /api/mini/*          HMAC-authenticated private job queue (D1)
       ^
       | outbound-only polling every 5 seconds (PUBLISH_TOKEN)
       |
Ubuntu: cloudflare-mini-bridge -> existing FastAPI Mini APIs -> SQLite
Ubuntu: bot                    -> Telegram notifications
Ubuntu: cloudflare-publisher   -> existing D1 public data
```

No browser or Worker endpoint has direct access to the original SQLite
database, bot admin reports, private tokens or user's other subscriptions.

## 1. Update the Ubuntu checkout

SSH into the existing server:

```sh
cd /opt/Flightiran/flightiranbot24
git status --short
```

If you previously edited `cloudflare/wrangler.toml` locally to set the D1
ID, preserve it before pulling the tracked file:

```sh
git stash push -m "local Cloudflare D1 ID" -- cloudflare/wrangler.toml
git pull --ff-only origin main
```

Then restore the **same previously created** D1 database ID in the new
`cloudflare/wrangler.toml`. Do **not** run `wrangler d1 create`.
Keep `binding = "PUBLIC_DB"`; do not use the CLI-generated lowercase binding.

```sh
sed -i 's/REPLACE_WITH_CLOUDFLARE_D1_DATABASE_ID/84874cc1-8283-40fc-aa71-2a3697abeec8/' cloudflare/wrangler.toml
```

This ID is the existing database created earlier for this project; no
additional Cloudflare database is provisioned. If the local file already has
the correct ID, this command does nothing.

## Cloudflare D1 Free quota caution

Before applying pending Migrations 0003 and 0004, **stop the existing
cloudflare-publisher** if your account has just hit error `7500`:

```sh
cd /opt/Flightiran/flightiranbot24
docker compose --profile cloudflare stop cloudflare-publisher
```

D1 Free limits reset at **00:00 UTC (03:30 Iran)**. Wait for reset before
re-running `wrangler d1 migrations apply ... --remote`. The bot and its
original SQLite DB are unaffected. Keep the publisher stopped until
you have deployed the quota-efficient Worker and rebuilt the
compact passport-snapshot publisher from `main`. Migration 0004 creates
a public visa JSON table containing ~199 rows instead of ~40k relational
records. The new Worker forbids the old high-write importer; the publisher
defaults to at most 220 compact passport documents per UTC day.
Existing D1 data and publisher checkpoints are preserved.
Do not repeatedly retry 7500, reset your checkpoint or delete the D1
database. Check Cloudflare D1 Dashboard > Metrics > Row Metrics.

## 2. Deploy migrations 0003 + 0004 and the Worker static assets

Wrangler must use the Cloudflare **management** API token in your current
SSH shell. It is NOT the app publisher token.

```sh
cd /opt/Flightiran/flightiranbot24/cloudflare
read -rsp "Cloudflare API Token: " CLOUDFLARE_API_TOKEN
echo
export CLOUDFLARE_API_TOKEN
npx wrangler whoami
npx wrangler d1 migrations apply flightiran-public-data --remote
```

The pending migrations should include:

```text
0003_telegram_mini_jobs.sql
0004_visa_passport_snapshots.sql
```

Confirm with `Y`. Migrations 0001 and 0002 remain applied.
Migration 0003 holds transient Mini App requests; 0004 holds compact
public visa documents. No existing visa, user, or ticket rows are deleted.
If 0003 was already applied on a prior day, only 0004 will be pending.

Install two **different** Worker secrets. The first should already be
configured from the existing public API publisher deployment:

```sh
# Existing private server-to-Worker publishing secret (leave unchanged):
# PUBLISH_TOKEN

# Additional Telegram bot secret for validating authentic Mini App sessions:
npx wrangler secret put TELEGRAM_BOT_TOKEN
```

At the interactive prompt enter the **same actual Telegram bot token**
already configured in your server's `TELEGRAM_BOT_TOKEN` in `.env`.
Never paste the token into GitHub, the Android app, a chat, or a public URL.
Wrangler stores it as a Cloudflare secret; it is not a public `[vars]` value.

Finally:

```sh
npx wrangler deploy
```

The deploy should list:

```text
ASSETS             Static Assets
PUBLIC_DB          D1 Database
```

The Worker name and URL are unchanged. The upload now includes HTML, CSS and
JavaScript static assets. `PUBLISH_TOKEN` remains a separate Worker secret.

## 3. Enable the Telegram bot's Mini App menu and outbound bridge

In the existing server `/opt/Flightiran/flightiranbot24/.env`:

```dotenv
WEB_APP_ENABLED=true
WEB_APP_URL=https://flightiran-public-api.abolfazl260.workers.dev/mini/
TELEGRAM_BOT_USERNAME=Flightiranbot

# Keep your existing secret values unchanged:
# TELEGRAM_BOT_TOKEN=...
# CLOUDFLARE_PUBLISH_TOKEN=...
CLOUDFLARE_PUBLIC_API_ORIGIN=https://flightiran-public-api.abolfazl260.workers.dev/
CLOUDFLARE_SYNC_CHECKPOINT=/data/cloudflare-sync.json
```

`TELEGRAM_BOT_TOKEN` must be the same token stored in the Worker secret;
`CLOUDFLARE_PUBLISH_TOKEN` must equal the *other* Worker
`PUBLISH_TOKEN` secret. Never use the Cloudflare management API token as
either of these secrets.

Build/start the **existing** services plus the new outbound-only bridge:

```sh
cd /opt/Flightiran/flightiranbot24
docker compose --profile cloudflare up -d --build
docker compose --profile cloudflare ps
docker compose logs --tail=100 cloudflare-mini-bridge
```

The new bridge connects to Worker every five seconds. It has **no published
Docker port** and does not require an HTTPS certificate on Ubuntu.
Keep `cloudflare-publisher` running for public tickets, airports and visa
data. Both services use the existing `flightiran-data:/data` volume.
Do not delete that volume or any stored bot database.

## 4. Verify without Telegram credentials

```sh
# HTML must return HTTP 200 with Content-Type text/html
curl -i https://flightiran-public-api.abolfazl260.workers.dev/mini/

# Assets must return HTTP 200
curl -I https://flightiran-public-api.abolfazl260.workers.dev/assets/mini.js
curl -I https://flightiran-public-api.abolfazl260.workers.dev/assets/mini.css

# Health and the unchanged Android API
curl -i https://flightiran-public-api.abolfazl260.workers.dev/healthz
curl -i https://flightiran-public-api.abolfazl260.workers.dev/api/v1/tickets/prices

# Private API without signed Telegram initData MUST be rejected with 401
curl -i https://flightiran-public-api.abolfazl260.workers.dev/api/mini/bootstrap
```

A normal desktop browser shows a **Telegram login required** notice at
`/mini/` because no signed Telegram webview context is present; this is
intentional and secure.

## 5. Test through the actual Telegram bot

1. Open `@Flightiranbot` privately and send `/start`.
2. Click **🚀 ورود به مینی‌اپ سفر**. It opens the above
   `workers.dev/mini/` address.
3. Open ticket prices and search an existing origin/destination; do not
   assume every fare is current or every route is bookable.
4. Open visa requirements for Iranian passport; try searching a country
   in **Persian**. The browser localizes ISO country codes using Intl
   DisplayNames; actual visa facts and official source date still come from
   the published index.
5. Create one price alert from a real, **fresh** ticket route and subscribe to
   a verified visa rule. Open **هشدارهای من** and verify each subscription;
   pause, resume and remove your own entries.
6. Inspect `docker compose logs --tail=100 cloudflare-mini-bridge` to
   confirm real job completions. The existing Telegram bot continues to
   deliver alerts on the scheduled capture/change notifications.

**Optional persistent launch icon:** use `@BotFather` `/setmenubutton`
for `@Flightiranbot` and paste the same URL
`https://flightiran-public-api.abolfazl260.workers.dev/mini/`.
The inline button works without configuring BotFather.

## Security, accuracy and free-tier behavior

- Cloudflare Worker verifies the Telegram Web App HMAC over the actual
  signed initData, rejects invalid/expired/future/duplicate fields and
  strictly authorizes the same Telegram numeric ID when fetching a result.
  It never trusts `initDataUnsafe`, a URL user ID, username or a forged
  JavaScript object for authentication.
- A job contains its Telegram user ID, sanitized first/last name and
  username, a fixed allowlisted operation, and bounded JSON parameters.
  These are **private transient D1 rows**, deleted when the bridge polls
  after their 10-minute retention. No raw initData, bot token, session
  signature, full SQLite database or historical personal archive is
  saved to D1. Cloudflare account administrators may access D1 data.
- User preferences, alerts, ownership/limit checks and notification state
  still live **only in SQLite**. Internal jobs are accessed only through
  `Authorization: Bearer PUBLISH_TOKEN` protected endpoints; Worker and
  bridge are the only components holding the secrets. The public Android
  API cannot query private D1 tables.
- To avoid duplicate writes after lost acknowledgements, **expired leased
  mutations are not retried automatically**. If a write times out, inspect
  the Mini App **My alerts** list before attempting another creation.
  Read-only jobs may retry once. Successful results expire after 90 s.
- Requests and job polling count toward Workers Free requests and D1
  usage, and are subject to Cloudflare free-tier quotas. The bridge
  polls once every **5 seconds**, approximately 17,280 internal requests
  each 24-hour period even when idle; this is within the nominal daily
  100k Workers Free request quota, but your total load matters.
- Existing `advertio.ir` DNS, SSL, server routes and services are unchanged.
  No Cloudflare R2 or payment card is required.
- Public Android `/api/v1/*` paths continue to use the original D1 public
  projection and stay independent of the new authenticated Mini App.

## Local checks / CI

```sh
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_cloudflare_mini_bridge.py tests/test_telegram_mini_app.py
node --test cloudflare/test/*.test.mjs
node --check src/flightiran/webapp/static/mini.js
```
