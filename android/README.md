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
- The **airport guide** is a native, Persian-only Compose directory.
  It shows only IATA airports enabled in the versioned GitHub JSON index;
  each airport displays only reviewed, published sections and uses on-demand
  HTTPS with the bundled asset fallback. This does not constitute a live
  flight-status provider. The existing Room airport cache remains separate
  from the content guide.
  The **offline checklist** remains a Java screen, with a progress indicator,
  confirmation before reset, and its existing SharedPreferences preserved.
- Visa and support handoffs use their configured external links. The useful
  travel information card now opens a native Persian directory sourced from the
  same GitHub JSON catalog used by Telegram, with a bundled offline fallback,
  search, category filters and explicit HTTPS website links. No Telegram auth,
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
The Android Gradle build now defaults to the deployed, credential-free
`https://flightiran-public-api.abolfazl260.workers.dev/` origin in **all**
build types, including debug. The `ANDROID_PRODUCTION_API_ORIGIN` variable or
`-PapiOrigin=https://other-verified-endpoint.example/` can override it.
A signed release still requires fresh prices from the live HTTPS endpoint
and the owner's private keystore. See [release instructions](../docs/ANDROID_RELEASE.md).

Room v1 schema is stored in `android/app/schemas`; do not perform destructive
migrations. Remaining alert, visa, offline sync, auth and push work is tracked
separately and is not completed by this build-system change.

## Native ticket prices
The native Persian RTL fare screen consumes the public read-only
`GET /api/v1/tickets/prices` endpoint from `flightiran-web`. It shows current
tomans, recorded averages, percentage movement, UTC observation time, and
an explicit stale-data warning. Origin selection, destination search and
sorting work locally. Booking opens verified Advertio support.
The single app embeds the existing, public Cloudflare Workers HTTPS base
URL by default. It reports network/API failures if D1 has not yet received
verified prices; no fake prices or Telegram fallback are used.
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
must use the same database volume. A production HTTPS origin is included in the app by default;
an override variable is optional.

### In-app ticket browsing — native only
The prominent **قیمت بلیت** bottom navigation item and the dashboard fare
shortcut both open `TicketPricesActivity` inside the Android app. The screen
retrieves the database-backed prices through its HTTPS Retrofit repository
and renders origin filters, search, fares, recorded averages and differences
in Jetpack Compose. Neither normal navigation nor connection/setup errors
offer a Telegram fallback. The separate **هماهنگی رزرو با پشتیبانی** action
is only for a deliberate booking/support handoff, not viewing
prices. If the HTTPS API is temporarily unavailable, the screen provides retry
instead of launching Telegram or showing fake fares.

### Signed-release API validation
The tagged Android release job uses the known public HTTPS Worker origin by
default, or the GitHub Actions repository variable
`ANDROID_PRODUCTION_API_ORIGIN` as an optional override.
Before publishing, it checks that the HTTPS `api/v1/tickets/prices` endpoint
is reachable and returns nonempty, non-stale stored ticket prices. The release fails without a working DB-backed API, rather than
shipping a misleading in-app price screen. CI pull-request debug builds
use the same secure public Worker endpoint.

### Android launcher artwork
The Android launcher uses the approved Advertio-inspired **A + flight trail**
mark, with blue/navy, turquoise/green and a minimal aircraft symbol. The
optimized, opaque 512 × 512 WebP source is
`app/src/main/res/drawable-nodpi/ic_launcher_brand.webp`, with a plain white
background and no pre-rendered rounded-square frame, globe or passport.
Legacy Android uses a white-backed bitmap drawable. On Android 8+ an adaptive
icon supplies a white background and a foreground inset of 12dp inside its
108dp canvas; the launcher applies its own circular/squircle mask. The
deterministic Play Store image generator reads the same WebP source so branding
remains consistent across Android and store graphics.


## Real screenshots attached to every Android build

The main **Android Build and Release** GitHub Actions workflow now invokes the
reusable **Android Store Screenshots** emulator workflow after verification on
Android-related pull requests, main pushes, release tags, and manual builds.
It installs the debug APK built from the same commit as the signed release,
navigates through **real Persian UI controls** (not direct intents to private
Activities), and uploads the `android-real-screenshots` artifact with **15
PNG screenshots** from all **eight currently reachable native/in-app views**:

| Screen | Artifact files |
| --- | --- |
| Home | `01-home.png`, `01-home-details.png` |
| Services | `02-services.png`, `02-services-bottom.png` |
| Ticket prices | `03-ticket-prices.png` |
| Offline checklist | `04-checklist.png`, `04-checklist-bottom.png` |
| Iran FIDS in-app WebView | `05-iran-flights.png` |
| In-app privacy policy | `06-privacy.png`, `06-privacy-bottom.png` |
| Native useful travel directory | `07-travel-websites.png`, `07-travel-websites-bottom.png` |
| Airport guide: index, IKA details, baggage section | `08-airports.png`, `08-airport-ika.png`, `08-airport-ika-baggage.png` |

The screenshot job checks the foreground Activity for navigated screens,
verifies visible native text where available, validates the exact image
inventory and PNG dimensions, and runs existing connected instrumented tests.
A capture/test failure blocks signed release publication, with screenshot and
UI-XML diagnostics uploaded for investigation. You can also manually run
**Android Store Screenshots** from the Actions tab without producing a release.

**Honest captures only:** if the production fare API is unavailable, the
prices image may show the real network error rather than fake sample fares.
The FIDS page similarly depends on its third-party website. Review these
images before submitting any of them to an app store. The intentionally
disabled airport directory and screens launched in external Telegram/browser
apps are not presented as working in-app screens.


## Airport content guide

The Home airport card and the Services airport row open the native
`AirportDirectoryActivity`. The footer remains visible. A versioned
`data/airports/airport-index.v1.json` enables only airports with published
content. The detail page is fetched **only after tapping the airport**;
unpublished draft sections are invisible. Android bundles the exact same
GitHub JSON under `data/airports/` for offline fallback, with a visible
notice when fallback is used.

The initial verified airport is IKA. Its static flight-status card links to
the official airport website: it is not a live feed. Images/videos have
safe external HTTPS actions but no untrusted embedded HTML playback.
An unsupported future block type requires a compatible app release.
The catalog is edited **directly in GitHub**, never through a mobile admin UI.

Run unit checks with
`gradle --no-daemon -p android :app:testDebugUnitTest`.
The screenshot CI captures the airport index and IKA details from the
real RTL app UI. Other airports can be enabled solely by changing their
published JSON content after verification.
