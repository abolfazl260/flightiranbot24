# Cloudflare public Android API — Workers + D1 (no R2 / payment card)

**Status:** Code is ready in GitHub. The account owner still needs to deploy
the Worker, configure a private publishing secret and start the server publisher.
This guide is for the D1-only version; **do not activate R2 or add a bank card.**

The bot's SQLite database on the Ubuntu server is authoritative. The
`cloudflare-publisher` container reads only:
- last recorded public ticket prices/aggregate averages,
- the bundled public Persian airport catalog,
- public visa requirements grouped into ~199 passport JSON snapshots.

It sends these projections **outbound over HTTPS** to a Worker, which stores
them in an existing D1 database. No HTTPS certificate or inbound port is needed
on your Ubuntu server. The Android app does public GET requests over HTTPS to
the Worker. Bot users, Telegram IDs, subscriptions, secret tokens, raw private
SQLite, and billing information are **never** replicated.

## 1. Prepare the already-created D1 database

You already created `flightiran-public-data` using Wrangler. **Do not run
`wrangler d1 create` again or delete the database.**

The local machine running Wrangler (SSH server) needs an authorized
`CLOUDFLARE_API_TOKEN` for deployment. It is a *management credential*, not
the publishing secret. For non-interactive SSH sessions:

```sh
cd /opt/Flightiran/flightiranbot24/cloudflare
read -rsp "Cloudflare management API token: " CLOUDFLARE_API_TOKEN; echo
export CLOUDFLARE_API_TOKEN
# If needed, set your Account ID from the Cloudflare dashboard:
# export CLOUDFLARE_ACCOUNT_ID="YOUR_ACCOUNT_ID"
npx wrangler whoami
```

Update GitHub code on the Ubuntu server, then verify that
`cloudflare/wrangler.toml` still points at the **existing** D1 database ID.
This file is tracked by Git: if edited locally, preserve the real ID before
`git pull`; if Git reports local changes, safely copy/stash that config first.
Only the `database_id` field should be replaced. Leave
`binding = "PUBLIC_DB"` intact. There must be **no** `[[r2_buckets]]` block.

```sh
cd /opt/Flightiran/flightiranbot24
git pull origin main
cd cloudflare
nano wrangler.toml
```

**Important:** Replace
`REPLACE_WITH_CLOUDFLARE_D1_DATABASE_ID` with the ID printed by your earlier
`wrangler d1 create flightiran-public-data` command. The ID identifies a
database, not a secret; nevertheless it does not belong in an APK. Your local
config must have:

```toml
[[d1_databases]]
binding = "PUBLIC_DB"
database_name = "flightiran-public-data"
database_id = "YOUR_EXISTING_D1_DATABASE_ID"
migrations_dir = "migrations"
```

Apply both migrations. `0001` sets up visa/airports; `0002` creates a
**single-row** ticket snapshot table. Both migrations are idempotent when run
through Wrangler migration tracking; D1 state is preserved.

```sh
npx wrangler d1 migrations apply flightiran-public-data --remote
npx wrangler deploy
```

Wrangler prints a public HTTPS `https://...workers.dev` URL. R2 is not used
or required at deployment.

## 2. Create the Worker publishing secret

This secret is **different** from your Cloudflare management API token.
Generate it locally and copy it securely to the Ubuntu server's `.env` file.
Do not commit it, paste it in chat, or embed it in Android.

```sh
# Run on your trusted machine; save the output privately:
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
cd /opt/Flightiran/flightiranbot24/cloudflare
npx wrangler secret put PUBLISH_TOKEN
```

When Wrangler prompts, enter the newly generated publishing secret. Keep the
management API token only for Wrangler administration and preferably revoke or
rotate it after deployment. Store no management token in Docker or Android.

In the **existing** server `/opt/Flightiran/flightiranbot24/.env` add:

```dotenv
CLOUDFLARE_PUBLIC_API_ORIGIN=https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/
CLOUDFLARE_PUBLISH_TOKEN=YOUR_SEPARATELY_GENERATED_PUBLISHING_SECRET
CLOUDFLARE_SYNC_CHECKPOINT=/data/cloudflare-sync.json
```

The Worker origin must use `https://` and end in `/`. Only the publisher
holds `CLOUDFLARE_PUBLISH_TOKEN`; the Worker keeps it as a secret, never a
public variable. The server only makes **outbound HTTPS requests (port 443)**.

## 3. Start and verify publisher on Ubuntu

```sh
cd /opt/Flightiran/flightiranbot24
docker compose --profile cloudflare up -d --build
docker compose --profile cloudflare ps
docker compose logs --tail=100 cloudflare-publisher
```

To run a manual synchronization once:

```sh
docker compose --profile cloudflare exec cloudflare-publisher \
  flightiran-cloudflare-publish --once
```

It compares public payload fingerprints every 300 seconds and only uploads
changed snapshots. The checkpoint is kept in the Docker data volume. On 401,
4xx or 5xx, the checkpoint is **not** advanced; failed uploads are retried.
This does not change the upstream ticket/visa collection frequency.

The *first* visa export requires a complete validated index of at least 190
destinations per passport. If incomplete, run the existing Telegram admin
`/visa_sync` first. The ticket feed also needs recorded prices; it never
generates fake values.

When upgrading from the old R2 architecture, the publisher automatically
invalidates the old checkpoint scope and uploads the current public data again.
There is **no** need to delete any Docker data file, SQLite database, or volume.
Apply D1 migration 0002 and deploy the new Worker before starting the publisher.

## 4. Verify public endpoints (no secret required)

Replace the hostname with your actual deployed `workers.dev` host:

```sh
curl -fsS https://YOUR-WORKER.workers.dev/healthz
curl -fsS https://YOUR-WORKER.workers.dev/api/v1/tickets/prices
curl -fsS https://YOUR-WORKER.workers.dev/api/v1/airports
curl -fsS 'https://YOUR-WORKER.workers.dev/api/v1/visa/rule?passport=IR&destination=TR'
curl -fsS 'https://YOUR-WORKER.workers.dev/api/v1/visa/list?passport=IR'
```

`GET /healthz` only confirms that code is running; check actual ticket,
visa and airport responses to verify that D1 is populated and connected.
An unpopulated D1 returns `503` instead of fabricated price data.

Only safe public GET routes are allowed. The protected `POST /internal/v1/`
import paths require `Authorization: Bearer <publishing secret>`.
Older ticket batches are rejected atomically; a three-hour-old price is still
readable but reported as `stale: true`. Android independently validates
timestamp freshness. Published visa records keep source verification dates.

## 5. Point release Android at the Worker

In repository GitHub settings:
`Settings → Secrets and variables → Actions → Variables`, set:

```dotenv
ANDROID_PRODUCTION_API_ORIGIN=https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/
```

The Android Retrofit client already calls `GET api/v1/tickets/prices`.
The release pipeline checks the endpoint for fresh real ticket data before
creating the signed release. Do not put either Cloudflare token in the APK.

The visa/airport routes are available for future native screens. At present,
the Android airport list is bundled offline; visa uses Telegram handoff.

## Limits, operational notes and troubleshooting

- No R2 bucket, payment card, server SSL certificate or open inbound server
  port is needed for this design. Cloudflare may impose account-specific
  eligibility requirements on Workers/D1 independently.
- `ticket_price_snapshots` stores **one row only** containing bounded public
  JSON. D1 stores no historical ticket prices or user-specific information.
  Update = one SQL UPSERT. Read = one SQL SELECT.
- D1 Free quotas apply to *actual SQLite rows* written/read, not member
  count. The first visa import writes many rows; fingerprint-based publishing
  prevents unchanged data from being reuploaded at every 5-minute poll.
  Monitor `Workers & Pages` and `D1` usage in Cloudflare dashboard.
- If Worker returns 500/503 after deploy, first check remote D1 migrations,
  the `PUBLIC_DB` binding, and `docker compose logs cloudflare-publisher`.
- If `wrangler deploy` says the D1 database ID is invalid, verify the existing
  D1 ID and active Cloudflare account. Do not create a new D1 just to fix
  a typo.
- If deployment was already performed with R2, this version can be deployed
  in place under the same Worker name; add migration 0002 first and replay the
  latest ticket snapshot. Existing visa/airport data is unaffected.
- Mobile browser/Worker `Cache-Control` headers may cache a successful fresh
  response for up to 60 seconds. This does **not** reduce the quota for each
  invocation of the Worker unless an explicit edge cache is configured.

## Local checks

```sh
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_cloudflare_publisher.py
node --test cloudflare/test/*.test.mjs
```


## D1 Free quota redesign (October 2026)

The Workers Free plan permits **100,000 rows written and 5 million rows
read per UTC day**, across the Cloudflare account. Each changed visa rule
also updates SQLite indexes and therefore costs additional row writes.
Cloudflare enforces those limits since September 2026: when exhausted,
D1 operations (including Wrangler migrations) fail until **00:00 UTC**
(03:30 in Iran); no stored rows are deleted.

**Root cause:** the old relational public visa projection used roughly
199 passports × 199 destinations = **39,601 D1 table rows** plus
secondary-index writes: roughly 79,202 writes just for initial population.
Even an upsert-only fix retains expensive bulk writes if many facts change.

**New architecture (migration 0004):** one JSON document per passport,
`visa_passport_snapshots(passport PRIMARY KEY, snapshot_json, published_at)`.
Initial publication now takes about **199 D1 table rows** (plus primary key
index maintenance), not ~40,000. Changing facts for one passport writes
one row; no-change publication writes zero rows via conditional UPSERT and
publisher fingerprints. At least 190 verified destination rules per
passport are required; invalid/partial snapshots are refused. Documents
are bounded to less than 1.6 MB, below D1's 2MB maximum row size.

The previous `visa_rules` table remains **untouched** to preserve
existing public visa reads while passport documents are populated. The
Worker prefers compact documents when present and falls back to old rules
only for passports not yet migrated. The legacy bulk importer is now
explicitly rejected (HTTP 410) to prevent recurring 40k-row writes.

The publisher's optional safety cap is now
`CLOUDFLARE_VISA_PASSPORT_DAILY_LIMIT=220` (range 1–250), so a complete
~199-passport initialization can finish in one day. The old
`CLOUDFLARE_VISA_DAILY_LIMIT=60` setting is ignored by the new
publisher. No checkpoint reset is required: new fingerprint keys
`visa-passport:<CODE>` naturally trigger the initial compact import.
Existing ticket/airport checkpoints remain intact.

For error 7500 / daily D1 writes exceeded:

```sh
cd /opt/Flightiran/flightiranbot24
docker compose --profile cloudflare stop cloudflare-publisher
# Keep bot, web and existing SQLite database running.
# Check account usage: Cloudflare dashboard > D1 > flightiran-public-data
# > Metrics > Row Metrics (Rows Written).
```

After **00:00 UTC**, with publisher still stopped:

```sh
cd /opt/Flightiran/flightiranbot24
git pull --ff-only origin main
# Preserve and restore your account-specific cloudflare/wrangler.toml D1 ID
# if you have changed that tracked file locally.
cd cloudflare
npx wrangler d1 migrations apply flightiran-public-data --remote
# Pending: 0003_telegram_mini_jobs.sql and 0004_visa_passport_snapshots.sql.
npx wrangler deploy
cd ..
docker compose --profile cloudflare up -d --build
docker compose logs --tail=100 cloudflare-publisher
```

Ensure Cloudflare CLI authentication, unchanged PUBLISH_TOKEN, and the
Worker's TELEGRAM_BOT_TOKEN secret are configured per
`docs/TELEGRAM_MINI_APP.md`. **Do not** clear
`/data/cloudflare-sync.json`, re-create D1, delete Docker volumes or
manually re-run old visa imports; all would cost extra writes. If quota
is exhausted again, stop publisher and inspect Cloudflare's actual
Rows Written metrics before resuming.

Quota documentation:
https://developers.cloudflare.com/d1/platform/pricing/
