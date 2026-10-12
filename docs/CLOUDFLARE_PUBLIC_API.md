# Cloudflare public Android API: R2 ticket snapshots + D1 indexes

The production SQLite database on the FlightIranBot24 server is **authoritative**.
The `cloudflare-publisher` service reads only recorded public prices, bundled
public airport data, and the normalized `visa_rule_index` table. It never copies
the SQLite database, users, saved routes, price/visa alert subscriptions,
Telegram IDs, admin information, secrets or raw visa documents.

Mobile access is **GET-only**, does not require a Telegram session, and uses a
public HTTPS Worker endpoint. Database changes always originate on the server.
Do not expose the R2 bucket publicly or place the publisher token in an APK.

## 1. Provision the Cloudflare resources (owner)

Install Node.js and Wrangler, then authenticate to your own Cloudflare account:

```sh
cd cloudflare
npm install
npx wrangler login
npx wrangler r2 bucket create flightiran-public-snapshots
npx wrangler d1 create flightiran-public-data
```

Copy the **database_id returned by D1 create** into
`cloudflare/wrangler.toml` (replace the placeholder). This account-specific
ID must not be guessed.

```sh
npx wrangler d1 migrations apply flightiran-public-data --remote
npx wrangler deploy
```

Generate a high-entropy token locally (never paste its value in a chat or Git):

```sh
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
npx wrangler secret put PUBLISH_TOKEN
```

Install the identical token only in the server's private `.env` file. Rotate
both installations together if compromised. The public Worker URL is displayed
by Wrangler; a `*.workers.dev` HTTPS address is sufficient. A custom domain is
optional and must have valid Cloudflare TLS. R2 remains private via the Worker
binding. D1 SQL is bound to Worker code, not exposed directly to Android.

## 2. Enable the server-side publisher

On the production server, after updating source and Docker containers:

```dotenv
CLOUDFLARE_PUBLIC_API_ORIGIN=https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/
CLOUDFLARE_PUBLISH_TOKEN=YOUR-LOCALLY-GENERATED-SECRET
CLOUDFLARE_SYNC_CHECKPOINT=/data/cloudflare-sync.json
```

```sh
docker compose --profile cloudflare up -d --build
docker compose logs -f --tail=50 cloudflare-publisher
```

The publisher checks every 300 seconds. It publishes new ticket snapshots,
the bundled airport directory, and destination-scoped visa rule indexes only
when their public content checksum changes. Each D1 destination replacement is
transactional. The checkpoint file contains SHA-256 fingerprints only and
resides inside the server data volume. Failed uploads are retried on the next
iteration; never update the checkpoint before a successful remote response.

For a one-time manual refresh inside the running Docker service:

```sh
docker compose --profile cloudflare exec cloudflare-publisher \
  flightiran-cloudflare-publish --once
```

The initial visa export requires the main database's complete validated visa
index (at least 190 destinations and 190² rule entries). Run the existing
`/visa_sync` in Telegram first if the visa index is not populated. Ticket
publication similarly requires recorded price data; empty data is never
substituted with synthetic prices.

## 3. Point Android release builds at the Worker

In GitHub repository `Settings > Secrets and variables > Actions > Variables`
set:

```dotenv
ANDROID_PRODUCTION_API_ORIGIN=https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/
```

The existing Retrofit `GET api/v1/tickets/prices` contract stays unchanged;
the Android release pipeline tests this route before signing. **Never** set
`CLOUDFLARE_PUBLISH_TOKEN` or other server tokens as an Android build input.

Public API examples:

```sh
curl -fsS https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/healthz
curl -fsS https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/api/v1/tickets/prices
curl -fsS https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/api/v1/airports
curl -fsS 'https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/api/v1/visa/rule?passport=IR&destination=TR'
curl -fsS 'https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev/api/v1/visa/list?passport=IR'
```

The visa and airport endpoints are backend-ready for future native Android
screens; the current native app displays ticket prices, a bundled offline airport
catalog and a checklist. Visa screens still hand off to Telegram, and no claim
of native parity is made here.

## Read-only, correctness, resilience

- Only documented public GET routes exist. Writes under `/internal/v1/` require
  a 32+ character secret Bearer token, accept strictly limited JSON bodies, and
  validate a fixed whitelist of public fields.
- The R2 snapshot `public/v1/tickets/prices.json` contains only current recorded
  fares and aggregate values; Cloudflare checks price age **on every GET**.
  Quotes older than three hours remain available but are explicitly `stale`.
  API clients also validate dates and must show stale warnings. Regression to an
  older observed timestamp is rejected with HTTP 409.
- Public visa rules retain `verified_on` and `source_level`; they are not a
  substitute for current official immigration requirements. The publisher
  uploads only destination-level indexed rules, not upstream raw JSON.
- D1 and R2 contents are copies, never sources of truth. No general-purpose SQL
  endpoint, arbitrary public object key, password reset, booking submission, user
  account, or push notification APIs are provided.
- Publisher failures leave the last successfully published snapshot intact.
  During prolonged server outages that snapshot is readable, but fares are
  marked stale after three hours. D1 visa rows expose publication timestamps.
- The Worker returns HTTP 503 rather than fabricate prices or return private
  data when R2/D1 are missing. The publisher uses TLS and disables redirects.
- Set Cloudflare WAF rate-limiting rules on public API paths as usage grows.
  Configure monitoring for publisher errors and Cloudflare Worker/D1 limits.
  Review Cloudflare usage quotas and the privacy policy before production launch.
- Deploying the Cloudflare resources, configuring owner secrets and publishing
  signed Android builds require the owner's account credentials; merging code
  alone does **not** deploy or connect a live Cloudflare service.

## Local verification

```sh
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_cloudflare_publisher.py
node --test cloudflare/test/*.test.mjs
```
