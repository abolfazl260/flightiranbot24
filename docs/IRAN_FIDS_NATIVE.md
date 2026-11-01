# Native Iran flight information — FIDS operator runbook

## Scope and status

The Android app now offers **«اطلاعات پرواز ایران»** as a native Compose screen. Selecting an airport/direction triggers a request to our first-party HTTPS Cloudflare Worker. **No WebView, browser, or website frame** is used. The app provides native search, official source label, provider and retrieval timestamps, manual refresh, missing-data notices and explicit API error states.

**Blocker on 2026-11-01:** The cited official URL https://fids.airport.ir/ timed out from our research environment. We did not verify any public JSON API, its precise fields, licensing or authorized automated-use policy. Hence **the live upstream is deliberately NOT enabled**; without valid configuration the Worker returns 503. This code does not yet prove end-to-end live FIDS delivery.

The similarly named Cirium/FlightStats commercial FIDS API is a separate service and must **not** be confused with the Iranian airport operator.

## Safe architecture

Native Android → Retrofit first-party Worker endpoint → verified source on fids.airport.ir (server side only).

Public GET endpoint: /api/v1/iran/fids/THR/departures (also arrivals).
Other currently allowlisted candidate airports: MHD, SYZ, IFN, TBZ, AWZ, BND, KER, ZAH, OMH.
These are potential FIDS-managed airports, not confirmed live coverage.
IKA (Imam Khomeini) is independently administered; it is intentionally excluded pending a separate verified integration.

Worker response keys: airport, direction, source, source_url, fetched_at, source_updated_at (nullable), freshness (reported/unverified), flights[].

Each flight is a sanitized record: flight_number, airline, city, scheduled_time, estimated_time, actual_time, status, terminal, gate. Optional fields remain null when missing; no gate or status is inferred. Empty explicit flights[] can show no listed flights, but unknown JSON structures are NOT treated as empty boards.

Dates are different: **fetched_at is when our server received the result**, while **source_updated_at is only an upstream-reported timestamp**. The Android app shows a warning when source currency is unverified or more than 15 minutes old. When upstream only returns an HH:mm time, the app cannot safely invent its date or timezone.

## Operational enablement checklist — mandatory before claiming a live feed

1. From a network with legitimate access, inspect https://fids.airport.ir/ via browser developer-network tools. Determine whether it provides a **public, authorized HTTPS JSON endpoint** (XHR/fetch), and document its exact URL, airport parameter, arrival/departure parameter, body format, timestamps and terms of reuse.
2. Confirm the airport operator's permissions/terms for automated access and republication; do not bypass blocking, CAPTCHA or authentication.
3. If a verified JSON response exists, adapt cloudflare/src/iran_fids.mjs to its **real response shape** and commit sanitized representative fixtures and adapter tests. Do not configure against an invented endpoint. If the site is HTML-only or requires a session, leave this JSON adapter disabled and implement an authorized server-side collector in a separate review.
4. Define the Worker-only environment variable **FIDS_SOURCE_URL_TEMPLATE** with the precise *verified* HTTPS URL on **fids.airport.ir** and exactly two placeholders: {airport} and {direction}. The code accepts no alternative host and no HTTP/redirects. A structural illustration, **NOT A REAL URL**, is https://fids.airport.ir/VERIFIED_PATH?airport={airport}&direction={direction}.
5. Deploy from the existing cloudflare directory and configured wrangler.toml; preserve the existing D1 ID and Worker secrets. No D1 migration is needed for this request-time API.
6. Test GET endpoints for THR/departures and THR/arrivals and a second confirmed airport against real official results. The public request for LHR must give 404; missing configuration, HTML, blocked/invalid source and malformed JSON must give 503.
7. Inspect Android on actual emulator/device for Persian RTL, no external browser, refresh, search, errors and timestamps. Confirm provider and legal review before enabling the live-source setting.

The HTTP adapter requires JSON with a top-level flights array (or data.flights) and three known fields per row: flight number, route/city and scheduled time, plus optional values. More field mappings must be source-proven.

## Security and operational behavior

- Official host enforced on server: fids.airport.ir; HTTPS only, no redirect, upstream timeout 8 seconds, streamed size max 350 KiB, no client-supplied URL, no passenger info in output.
- No unknown third-party domains, no simulated flights, no scraping of unsupported HTML, no hidden WebView or direct upstream API in the APK.
- No background polling, user location permission, booking reference, or persistent storage of flight status.
- Source failures are explicit and never silently replaced by old records.
- If no officially permitted feed becomes available, obtain a licensed data feed and keep the native API/Android UI unchanged.

## QA

Run:
- node --test cloudflare/test/*.test.mjs
- gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug :app:assembleDebug

Unit tests validate public routing, official host, no configuration, payload sanitization, bad source responses, and Android parsing. Tests with **real** official FIDS response remain an outstanding blocker until a verifiable feed is obtained.
