# Android publication runbook

## Implemented

Kotlin/Jetpack Compose Android app with preserved native Java offline screens, minimum SDK 24, target SDK 36, JDK 17, Gradle 8.13.
The built-in airport directory and the 12-step travel checklist are included.
Ticket fares display natively through the database-backed HTTPS API; only
separate services such as support may intentionally hand off to Telegram.
No bot token is embedded in the APK.

GitHub Actions automatically increments the build number, tests the single
Android app and builds a debug APK and unsigned release AAB on relevant pushes.
Tags matching vX.Y.Z can build a signed release APK/AAB and publish checksums.

## Owner actions (private signing key)

1. Confirm the permanent package ID com.abolfazl260.flightiranbot24.
2. Locally generate an upload keystore OUTSIDE the Git repository:

    keytool -genkeypair -v -keystore "$HOME/flightiran-upload.jks" -alias flightiran-upload -keyalg RSA -keysize 3072 -validity 10000

3. BACK UP that file and both passwords privately, offline.
4. Install GitHub CLI, authenticate with gh auth login, then run:

    bash scripts/android-configure-signing.sh "$HOME/flightiran-upload.jks"

   It sets GitHub Actions secrets ANDROID_KEYSTORE_BASE64,
   ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_ALIAS, ANDROID_KEY_PASSWORD,
   without storing them in version control. Do not paste keys in chat.
5. Android Debug and signed Release APKs default to the already-deployed
   credential-free HTTPS origin:
   `https://flightiran-public-api.abolfazl260.workers.dev/`.
   **No Actions variable is required** for the default endpoint. To override,
   set `ANDROID_PRODUCTION_API_ORIGIN` in
   GitHub Settings → Secrets and variables → Actions → Variables.
   Release CI verifies real, fresh, nonempty `GET /api/v1/tickets/prices`
   before signing. The endpoint is public and must NEVER contain a bot token.
   Run the Cloudflare Publisher on Ubuntu to populate the D1 feed.
6. Restrict GitHub v* tag creation to trusted maintainers via repository
   rulesets. Confirm job-scoped Actions contents:write can publish Releases.
7. Enroll with Google Play Console and Play App Signing if Play publication
   is intended. This requires the owner's developer account and verification.

## Automatic builds and versions

Android now has exactly **one application ID**,
`com.abolfazl260.flightiranbot24`. The `debug` build has the standard
`.debug` suffix solely to permit concurrent installation during testing;
there are no development/staging/production product flavors.

For every Android CI workflow run, `versionCode=GITHUB_RUN_NUMBER` and
`versionName=1.0.<run number>`. Numbers increase automatically with new
workflow runs and do not need commits editing Gradle properties. PR/main
CI uploads a debug APK and an unsigned release AAB.

For a signed GitHub Release, an authorized maintainer creates a unique
`vMAJOR.MINOR.PATCH` tag on a reviewed `main` commit. The release workflow
automatically uses the tag as `versionName` and its increasing workflow
run number as `versionCode`; **no app version file editing required**.
For example, use a new unused tag such as `v1.0.123`:

```bash
git checkout main && git pull --ff-only
git tag -a v1.0.123 -m "Android v1.0.123"
git push origin v1.0.123
```

The tag must not be reused. Do not publish earlier release jobs after a
newer versionCode has been uploaded. GitHub release still requires private
signing secrets and a live HTTPS ticket API; publication to Google Play
remains a separate owner-controlled action.

## Store publication requirements

- Actual 512x512 icon, 1024x500 feature graphic, real screenshots from the
  Android build; see docs/PLAY_STORE_LISTING.md.
- Review docs/ANDROID_PRIVACY.md, third-party/Telegram processing, actual data
  retention and deletion procedures, Data safety answers, target audience,
  app access, rating, regions and ads status.
- On newer personal Play Console accounts, verify whether the 12-testers-for-
  14-days closed-testing requirement applies.
- Test native features and Telegram handoff on at least one real Android phone.

GitHub Release is not Google Play publication and no one can promise Play
acceptance without review. Private Play account steps and keystore backup
must be performed by the owner, never by untrusted CI or in a chat.

Workflows: https://github.com/abolfazl260/flightiranbot24/actions
Releases: https://github.com/abolfazl260/flightiranbot24/releases

## Single application configuration

The public API has a **known HTTPS default** in `app/build.gradle`,
so Debug APKs no longer report an unconfigured server. If a different
origin is intentionally deployed, override it with
`ANDROID_PRODUCTION_API_ORIGIN` or Gradle property `apiOrigin`.
Overrides must be bare HTTPS origins ending in `/`, without
username/password/query/path. Release CI validates that
`GET /api/v1/tickets/prices` serves fresh saved fares before signing.
If the Worker has no published ticket snapshots, the UI shows a real
retrieval error rather than fabricated prices.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:bundleRelease
```

Android release artifacts: `android/app/build/outputs/apk/release/app-release.apk`
and `android/app/build/outputs/bundle/release/app-release.aab`.

## Current production release gates (October 2026)

- Android CI on `main` produces a debug APK and an **unsigned release AAB**
  available as separate Actions artifacts (`android-debug-apk` and
  `android-unsigned-release-aab`). The unsigned AAB is for review/testing
  only, **not** a production package ready for Google Play.
- The `Android Store Screenshots` workflow must boot an accelerated emulator,
  run the instrumented tests, and upload authentic PNG screenshots. KVM access
  is configured in the workflow; review the actual artifact before using the
  pictures in a public store listing.
- A signed production release requires the four owner-controlled signing
  secrets listed above. A fresh `vMAJOR.MINOR.PATCH` tag must refer to the
  **current HEAD of `main`** at release time, not an older ancestor.
- The release job checks the live ticket API, builds both APK and AAB using
  the owner upload key, runs `apksigner verify` and checks the signed-AAB success result from
  `jarsigner` (without false failures from self-signed upload certificates), and attaches both files plus SHA-256 digests to GitHub Release.
- Never tag or claim a production release while signing secrets, endpoint
  freshness, physical-device checks, privacy review or Play Console steps
  are incomplete. A GitHub Release is not a published Google Play app.

Before tagging, verify `GET /api/v1/tickets/prices` on the configured
Cloudflare HTTPS origin returns a non-empty `routes` array, `currency` of
`TOMAN`, `observed_at`, and `stale: false`. If it does not, fix data
publishing rather than bypass the release gate.
