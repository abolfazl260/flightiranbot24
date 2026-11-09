# Public recorded route history (v1)

`GET /api/v1/tickets/history/routes?offset=0` returns up to 100 exact origin /
destination pairs with retained observations and `next_offset` (null at the end).
Offset is bounded to 0..10000. `GET /api/v1/tickets/history?origin=...&destination=...`
returns only that route: TOMAN, daily_minimum, days=21, UTC `as_of`, up to 21 unique
ordered points (`day`, `price_toman`, `sample_count`, `last_observed_at`), actual
`observed_at` and `stale`. Names are bounded to 128 characters and SQL-bound.
Empty history has no points and a null observation time; errors are 4xx/503,
never synthetic data. Clients reject route mismatches and invalid observations.

The source is the existing `mz724_price_snapshots` SQLite repository. Both the
Telegram chart and public projection use minimum/count/max grouped by UTC date,
within 21 calendar days including today, excluding future observations. Server
reads never crawl upstream. Direct FastAPI reads have a 60-second bounded LRU;
Worker reads use public HTTP caching plus Cache API where available. No auth,
initData, bot token or private user data is required for public history reads.

The existing authenticated publisher aggregates all routes in one bounded SQL
query and uploads one whitelisted public document per changed route. SHA256
checkpoints skip unchanged documents. D1 stores one JSON row per route, at most
21 daily points per row; conditional writes reject older observations and skip
identical documents. Lists/reads exclude expired days; indexed expiry sweeps run
only on changed publications. For 150 routes with hourly changes this is at most
3,600 document writes/day, plus small indexed expiry checks and one daily window
rollover. Visa budgets and private mini jobs are unchanged. Larger deployments
must account for their actual route/write count under their D1 plan.

Android draws a native Compose Canvas with accessible daily text buttons and
point taps; Mini App draws SVG with keyboard/touch points and daily text buttons.
Both preserve calendar spacing, draw links only between consecutive observed days,
show min/max, sample/day counts, last real observation and stale labels. Empty,
one-day and flat-price series have explicit states. Filters remain when closing
or changing chart routes. The common fixture spans a year boundary and is executed
by Python (including Telegram), Node and Kotlin.

## Deployment and rollback

1. Back up existing D1/SQLite normally. Apply additive D1 migration
   `0005_ticket_history.sql` with `wrangler d1 migrations apply ... --remote`.
   No SQLite migration or deletion is required.
2. Deploy Worker plus Mini App assets together, including both ticket modules.
3. Update/restart the existing `flightiran-cloudflare-publish` service and run one
   sync. It needs only its existing server-side publish credential.
4. Build Android through the existing user-requested release workflow when ready.
   Merging code does not deploy the server/Worker or publish an APK.

Rollback: roll back Worker/assets and publisher/app binaries together. Leave the
additive D1 history table in place; old code ignores it. Do not delete SQLite
history, migration records or existing private/public tables.
