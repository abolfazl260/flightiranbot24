# Flight Iran Bot 24 — Android

Native Kotlin/Jetpack Compose travel companion, gradually migrating from Java/XML.

## Android-only language and layout policy
The Android app is **Persian-only (fa-IR) and RTL**, regardless of the phone's
system language. Do not implement multilingual UI, user-facing language
switches, English/Arabic translations or LTR screen variants. Embedded IATA
codes and links may use locally isolated LTR text without changing the app's
RTL direction. This policy does not change the Telegram bot's language options.

The Android UI now forces a Persian resource context and RTL direction on
the Compose launcher and native screens. Default resources are Persian,
and Android DataStore no longer exposes a language selector. Existing
passport-country selections remain intact after upgrades. This change is
tracked under [#63](https://github.com/abolfazl260/flightiranbot24/issues/63). UI/CI
review tasks are tracked in [docs/ANDROID_TASK_BOARD.md](../docs/ANDROID_TASK_BOARD.md).

## Completed foundations (AND-001 and AND-002)

- The launcher uses Kotlin Compose, a Persian RTL dashboard with navigation
  and cards, and a lifecycle-aware HomeViewModel with StateFlow states.
- Pure Kotlin domain interfaces and an explicit, testable AppContainer
  dependency-injection root protect data and presentation boundaries.
- The **offline airport directory** is now a Compose LazyColumn that prefers
  a Room snapshot when populated and falls back to bundled offline records.
  The **offline checklist** remains a Java screen, with a progress indicator,
  confirmation before reset, and its existing SharedPreferences preserved.
- Online service links hand off to the Telegram bot via fixed `/start`
  entrypoints for visa, airports and travel information. No Telegram auth,
  bot token, fake Mini App session or server-side account is embedded.

## AND-003: secure networking and local persistence

- Retrofit 2.11 + OkHttp 4.12, strict HTTPS base-url validation and a generic
  `PublicJsonRepository` built for `api/v1/<resource>` paths only.
  URLs cannot be absolute, contain traversal/query strings or redirect to
  external hosts. Timeouts, HTTP failures, invalid JSON and network loss
  produce typed results; cancellation propagates.
- Only **loopback HTTP** can be explicitly enabled to test MockWebServer.
  No real production API URL or endpoint name has been invented; the client
  is created lazily only once AND-004 provides configuration and API-001
  implements authenticated/unauthenticated contracts.
- DataStore now stores the default passport country (`IR` if unset) without
  a user-selectable language. Legacy saved language values are ignored and
  cleaned up on the next passport edit; credential storage is forbidden.
- Room public airport cache has a Java entity/DAO annotated with schema
  version **1**, and a Kotlin repository with atomic snapshot replacement,
  duplicate/IATA validation and explicit refusal of empty snapshots.
  The existing Java offline screen continues to read the packaged asset, not
  the new cache; migration of that screen is an AIR task.
- The normal INTERNET permission is declared for eventual first-party HTTPS
  access. Nothing is transmitted when the current launcher opens.

## One Android app: builds and versioning

The app has **one ID**, `com.abolfazl260.flightiranbot24`, and two build
types (`debug` and `release`), not three product flavors. Debug uses
a `.debug` package suffix only to avoid replacing the installed release.

On relevant pull requests and `main` pushes, GitHub Actions tests/builds
the app and automatically generates `versionCode` from `GITHUB_RUN_NUMBER`
and `versionName=1.0.<run number>`. Tagged releases automatically adopt
`vMAJOR.MINOR.PATCH` for the version name; no manual app version edits.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug \
  :app:lintRelease :app:assembleDebug :app:bundleRelease
```

Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
Release tasks: `:app:assembleRelease :app:bundleRelease`.
The first-party API uses only `ANDROID_PRODUCTION_API_ORIGIN` or
`-PapiOrigin=https://your-real-host.example/`; the example URL is not
deployed. Missing origin produces an explicit unavailable state in the
in-app price screen. A signed release requires a live HTTPS API and the
owner's private keystore. See [release instructions](../docs/ANDROID_RELEASE.md).

Room v1 schema is stored in `android/app/schemas`; do not perform destructive
migrations. Remaining alert, visa, offline sync, auth and push work is tracked
separately and is not completed by this build-system change.

## Native ticket prices
The native Persian RTL fare screen consumes the public read-only
`GET /api/v1/tickets/prices` endpoint from `flightiran-web`. It shows current
tomans, recorded averages, percentage movement, UTC observation time, and
an explicit stale-data warning. Origin selection, destination search and
sorting work locally. Booking opens verified Advertio support.
The single app needs an HTTPS `ANDROID_PRODUCTION_API_ORIGIN` at build time.
Without it, the screen clearly reports missing API configuration rather than
showing fake prices or opening Telegram.
User-owned alerts, push, visa data and authentication remain separate tasks.


### Database-first fare contract (October 2026)
The first-party mobile prices API reads exclusively from the **shared bot SQLite
database** (`mz724_price_snapshots` + `mz724_route_averages`), rather than
performing a new upstream crawl in response to app requests. Only fares from
the latest captured hour are returned; the response timestamp is the DB
capture time, not the current API clock time. The Android screen labels the
recorded time and warns if quotes exceed the accepted age threshold or a
refresh fails. If there are no recorded fares, the API returns HTTP 503
instead of generated prices. The bot's scheduled collector remains
responsible for updating its history and averages. The web container and bot
must use the same database volume. An HTTPS `ANDROID_PRODUCTION_API_ORIGIN`
must still be set for the production APK/AAB.

### In-app ticket browsing — native only
The prominent **قیمت بلیت** bottom navigation item and the dashboard fare
shortcut both open `TicketPricesActivity` inside the Android app. The screen
retrieves the database-backed prices through its HTTPS Retrofit repository
and renders origin filters, search, fares, recorded averages and differences
in Jetpack Compose. Neither normal navigation nor connection/setup errors
offer a Telegram fallback. The separate **هماهنگی رزرو با پشتیبانی** action
is only for a deliberate booking/support handoff, not viewing
prices. Without a configured HTTPS API origin, the screen reports the missing
configuration instead of launching Telegram or showing fake fares.

### Signed-release API validation
The tagged Android release job uses the GitHub Actions repository variable
`ANDROID_PRODUCTION_API_ORIGIN` as its release build-time origin.
Before publishing, it checks that the HTTPS `api/v1/tickets/prices` endpoint
is reachable and returns nonempty, non-stale stored ticket prices. The release
fails without a configured origin or working DB-backed API, rather than
shipping a misleading in-app price screen. CI pull-request debug builds remain possible without public API configuration.
