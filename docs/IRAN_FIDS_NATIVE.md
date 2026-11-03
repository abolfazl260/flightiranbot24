# Iran flight information (FIDS) — Android website view and separate data API

## User-facing Android behavior

The **«اطلاعات پرواز ایران»** card opens \`IranFlightsActivity\` inside the Android application. As of this change, it displays the **original FIDS website** \`https://fids.airport.ir/\` in an Android WebView instead of attempting to fetch flight rows via the unconfigured first-party Worker.

- The original website chooses the airport, arrivals/departures, filtering and flight display. The previous native airport chips and search field have been removed to avoid showing an independent UI backed by an unavailable JSON feed.
- This is **not an external Chrome/Custom Tab handoff** and **not a copy/scrape of official flight data**.
- JavaScript and DOM storage are enabled for the website. WebView loads over HTTPS only; mixed HTTP content and file/content access are disabled.
- Top-level navigation stays on the exact HTTPS host \`fids.airport.ir\`. Cross-domain/unsafe navigations are blocked rather than launching another app. SSL errors are never ignored.
- Refresh and in-page Android Back navigation work. Offline mode is detected with Android's normal network-state permission; main-frame DNS/network/HTTP/SSL failures, blocked redirects, 20-second loading stalls and successfully loaded but blank documents show a Persian explanation and retry action instead of an indefinite white screen. The error view also offers an optional external-browser handoff and the flight information number 199. On exit the WebView is destroyed.
- Android already has \`android.permission.INTERNET\`, so this change does not add new permissions or change signing configuration.

**Network availability is not guaranteed.** On 2026-11-01, the official website did not respond from the research environment; the WebView directly accesses it from the user's device/network. A timeout, site policy restricting embedded browsing, TLS error or regional block may still prevent loading. Do not claim the board is verified live until tested on a physical Android device using a network that can open the official site.

## Separate Telegram Mini App / Cloudflare Worker implementation

PR #114 previously added a native-data FIDS screen in the Telegram Mini App and a Cloudflare Worker JSON adapter at \`/api/v1/iran/fids/{airport}/{direction}\`. **This Android-only WebView change does not modify them.** That API is still deliberately unavailable (HTTP 503) without a source-proven, approved \`FIDS_SOURCE_URL_TEMPLATE\` on the Worker.

Issue #115 continues to track a genuinely authorized source endpoint, response schema, real-data examples and upstream terms. Do not set a guessed endpoint, present fabricated flights, or claim that the separate Telegram Mini App can already fetch live FIDS rows.

The similarly named Cirium/FlightStats commercial FIDS feed is not the official Iranian airport operator.

## Validation

- Run \`gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:bundleRelease\`.
- Unit tests \`FidsWebNavigationTest\` verify that only the trusted official HTTPS domain may navigate inside WebView.
- Smoke-test the released Android APK on a **real device**: tap the flight information tile, verify the original site actually appears, select an airport and arrivals/departures on the site's own UI, refresh, navigate back, disable network, and verify Persian error/retry behavior.
- Verify that external URLs, non-HTTPS pages and bad TLS certificates are not bypassed.
- Android signing and publishing follow \`docs/ANDROID_RELEASE.md\`; merging into \`main\` triggers an automatic signed APK/AAB artifact once CI passes.
