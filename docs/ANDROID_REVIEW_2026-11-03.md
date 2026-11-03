# Android code and release-workflow review — 2026-11-03

Scope: `android/app`, its production navigation and state management, Android
tests, Gradle configuration, and the two GitHub Actions Android workflows.
This is a **source-level review**; no claim of a successful device build or
visual inspection of captured PNGs is made until Actions completes.

## Current state

- The app is a single native Android package with a Compose RTL home,
  services and ticket-prices surface; a Java/XML persisted travel checklist;
  a Compose in-app privacy notice; and an in-app FIDS WebView.
- The live in-app airport directory remains disabled in navigation even though
  a non-exported Activity and its offline catalogue still exist.
- Visa, useful travel information, bot features and support currently
  hand off to external Telegram/browser URLs. They are not native screens.
- Persian-only RTL is enforced by the Compose theme and Persian context.
- A shared HTTPS public price origin, 12-second HTTP timeout, bounded route
  parsing, explicit stale/error states and no fabricated prices are in place.
- Production signing, checksum generation, release-tag handling, Room schema
  validation and a live API readiness check exist in the main build workflow.

## Findings and recommended follow-up

| Priority | Finding | Evidence / impact | Proposed acceptance criterion |
| --- | --- | --- | --- |
| P1 | Different screen-navigation models | `TicketPricesScreen` has persistent four-item bottom navigation, but `ChecklistActivity`, `PrivacyPolicyScreen`, and `IranFlightsWebScreen` do not. Moving between core destinations requires backing out to home. | Offer consistent native home/back navigation or a shared bottom bar on every first-party screen; verify back stack. |
| P1 | Significant services are external handoffs | `MainActivity.navigateTo` opens Telegram for visa, useful content and support; it has no in-app state or offline alternative. | Mark each row as an external handoff before launch; native features should have separately tested first-party screens. |
| P1 | Image-embedded Persian text cannot scale | `PremiumHomeHero` and `PremiumServiceTile` render WebP images containing visible text. Semantics exist, but magnification, font scaling and content edits cannot reflow the baked-in lettering. | Test 200% font / narrow screens and either move critical words to native `Text` or supply approved accessible large-text variants. |
| P1 | Visual regression coverage was incomplete | Original screenshot script captured home/services/checklist only and was not invoked automatically. | **Addressed:** capture all six reachable in-app views, verify navigation, and attach 10 authentic PNGs to an independent screenshot workflow triggered by pushes to `main`. |
| P1 | Limited connected UI tests | The instrumentation suite currently includes `PersianUiTest` and `PrivacyPolicyUiTest`, but no end-to-end assertions of ticket filter/search, checklist persistence/reset, FIDS error/retry, or bar navigation across Activities. | Add deterministic connected tests for each critical interaction using a mock API, including large-font and small-screen configurations. |
| P1 | Ticket screenshot is environment-dependent | `TicketPricesViewModel` fetches the live price API; when unavailable, it correctly shows an error instead of sample fares. A screenshot may therefore depict an error state. | Keep error-state images in QA artifacts, but publish store listing screenshots only after confirming real populated prices and verified freshness. |
| P2 | FIDS screenshot is environment-dependent | The `IranFlightsActivity` WebView loads `fids.airport.ir`; without internet or third-party availability, the real screen shows an error. | Validate actual FIDS content before publishing store artwork; preserve SSL-error cancellation and host restrictions. |
| P2 | Accessibility sizing and touch targets need device tests | Home feature text includes hard-coded 10–14sp sizes; image cards and icon-only affordances rely on semantics. | Run screenshot/a11y checks on 320dp screens and 200% font; ensure actions meet 48dp touch area and screen-reader names are distinct. |
| P2 | Old airport code remains reachable only internally | `AirportDirectoryActivity` is still declared but navigation intentionally routes airport selection to Services/coming-soon messaging. | Remove the obsolete route when no longer needed, or reactivate only after product approval; do not capture it as a live store feature. |
| P2 | Release optimization is disabled | `android/app/build.gradle` has `minifyEnabled false` in release. | Add controlled R8/resource-shrinking rollout, checking Room/Gson/Retrofit compatibility and deterministic smoke tests. |
| P2 | Mixed Java/XML and Compose design systems | Checklist is XML while other primary views use Compose; this increases risk of inconsistent insets, styling and navigation. | Align spacing, typography, status/navigation-bar behavior, and accessibility via device QA; migrate only if justified. |

## Release screenshot contract

The independent `Android Store Screenshots` workflow runs on every push to `main`
(and can be manually rerun on `main`). It is not called by the Android Build
and Release workflow and does not run for PRs or other branches. It captures:

- Home (initial and scrolled)
- Services (initial and scrolled)
- Ticket prices (real data or real API error)
- Checklist (initial and scrolled)
- Iran flight information / FIDS WebView
- Privacy policy (initial and scrolled)

Exactly ten PNGs are required in `android-real-screenshots`. Image presence,
PNG dimensions, user-visible navigation and the existing Android instrumented
tests are checked. A screenshot failure does **not** prevent signed releases;
the screenshot artifact and workflow status are checked separately. CI artefacts
are *not* an automatic approval for app-store publication: dynamic feeds and
external WebViews require human review.

## Further QA still needed

1. Confirm GitHub Actions results for this PR on a hardware-accelerated API 35
   emulator, including all screenshot artifacts and failures/diagnostics.
2. Inspect every image for clipping, status-bar overlap, RTL and legibility.
3. Repeat on a small screen, large font, and an offline device.
4. Add mock-server UI tests so prices and FIDS scenarios are reproducible
   independent of third-party uptime.
