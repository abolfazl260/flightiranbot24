# Recorded fare ranking v1

The shared regression input is `docs/fixtures/ticket-ranking-v1.json`. Python,
Node and Kotlin execute it directly. Currency is TOMAN, current price is a positive
integer at most 10^12. A historical reduction requires a finite positive mean
above the current price and an integer sample count between 3 and 100,000.

Calculate `floor((mean-current)*1000/mean + 0.5)/10` (positive half-up tenths).
Suppress zero after rounding. Sort reduction percentage descending, current price
ascending, full origin then destination ascending in Unicode order. Cheapest
sorts price, origin, destination and requires no history. Cities currently use BMP
characters, for which Python code point and Kotlin/JS UTF-16 order coincide.

Filter origin and destination before sorting. Mobile lists show all matching
results; the home preview shows three cheapest; Telegram shows up to five per tab,
and may show fewer to fit Telegram's 1024-byte state limit. Full route names break
ties before Telegram's display truncation; do not rank truncated labels.

`GET /api/v1/tickets/prices` retains rounded `average_price_toman` for existing
consumers. Optional `historical_average_toman` retains the actual floating mean;
new consumers calculate from that value, falling back only when the field is
absent. `change_percent` remains signed movement metadata, never proof of a
verified reduction. Missing/invalid history cannot remove a valid cheapest rate.

Production Telegram fares, the direct API and the Cloudflare publisher read the
same newest SQLite cohort and persisted mean. No request to `/fares` starts a new
crawl when the stored repository is available. Legacy provider-only adapters keep
their previous check-time behavior. The Worker can lag the server until its next
publication; comparison requires the same `observed_at`, not identical request time.

`observed_at` is the capture time, never the HTTP request time. Data older than
three hours is stale; future capture times over five minutes are rejected or
conservatively stale. Mini App and Android retain the previous successful snapshot
on refresh error and mark it stale with an explicit warning. Newer requests win
when refresh responses arrive out of order. Filter and tab selections persist.

Recorded fares and historical reductions are informational. They are not live
inventory, a guaranteed discount or a confirmed reservation. Booking/support and
existing authenticated price alerts retain their own validation.

Validation: `pytest`, `ruff check src tests migrations`,
`node --test cloudflare/test/*.test.mjs`, and
`gradle -p android :app:testDebugUnitTest` (CI). No APK release is triggered by CI.
