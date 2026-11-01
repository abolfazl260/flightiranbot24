# Android publication runbook

## Implemented

Kotlin/Jetpack Compose Android app with preserved native Java offline screens, minimum SDK 24, target SDK 36, JDK 17, Gradle 8.13.
The built-in airport directory and the 12-step travel checklist are included.
Ticket fares display natively through the database-backed HTTPS API; only
separate services such as support may intentionally hand off to Telegram.
No bot token is embedded in the APK.

GitHub Actions automatically increments the build number and tests the Android
app on relevant changes. Pull requests produce a debug APK and **unsigned QA AAB**.
After a successful push to `main`, the workflow automatically generates a signed
APK and AAB with SHA-256 checksums, and publishes a versioned GitHub Release
after signing, integrity and HTTPS configuration checks pass. A temporary ticket API outage is reported as an operational warning, not a publishing blocker. No manual Git tag is needed.
Legacy manually created `vMAJOR.MINOR.PATCH` tags are still supported.

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
   Release CI probes `GET /api/v1/tickets/prices` as a monitored,
   **advisory** check. HTTP 403, timeouts and stale data produce visible
   warnings without blocking verified signed binaries. The public endpoint
   must NEVER contain a bot token.
   Run the Cloudflare Publisher on Ubuntu to populate the D1 feed.
6. Allow the trusted Android workflow's `GITHUB_TOKEN` to create its
   automatically numbered `v*` tags and publish GitHub Releases with scoped
   `contents: write` permissions. If repository tag rulesets block Actions,
   adjust the authorized workflow policy; do not disable signing checks.
7. Enroll with Google Play Console and Play App Signing if Play publication
   is intended. This requires the owner's developer account and verification.

## Verify upload signing before relying on automatic releases

The local upload keystore must remain outside the Git repository. If the
maintainer has already created `~/Desktop/flightiran-upload.jks`, reuse
that existing key; **do not generate a replacement** without first checking
whether its signing identity is already registered with Google Play.

On the maintainer's Mac (never in CI or chat), after pulling the latest
`main` branch and authenticating GitHub CLI:

```bash
git checkout main && git pull --ff-only
gh auth status
bash scripts/android-configure-signing.sh "$HOME/Desktop/flightiran-upload.jks"
gh secret list -R abolfazl260/flightiranbot24
```

The interactive setup asks for the keystore password, alias
(default `flightiran-upload`), and key password without echoing passwords.
Before uploading anything it verifies the store, alias, and private key by
signing a **temporary disposable JAR**. It then uploads four encrypted GitHub
Actions repository secrets: `ANDROID_KEYSTORE_BASE64`,
`ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and
`ANDROID_KEY_PASSWORD`. The secret list shows metadata, not values, and
**does not prove that credentials are correct**.

Run the separate **Android Signing Preflight** workflow from Actions (or use
these commands once the workflow exists on `main`):

```bash
gh workflow run android-signing-preflight.yml -R abolfazl260/flightiranbot24 --ref main
gh run list -R abolfazl260/flightiranbot24 --workflow android-signing-preflight.yml --limit 3
```

Open the newest workflow run and require the `Validate private upload key
and passwords` job to pass. The preflight restores the encrypted keystore
to a temporary runner file, verifies both passwords and the alias with
`keytool` and `jarsigner`, and discards the file without uploading an APK,
AAB, keystore, or signed test artifact. On error, correct the local
credentials and rerun setup; **do not create a release tag to test signing**.

This preflight proves the Actions secrets can unlock the upload key. It does
not validate Google Play upload-key enrollment, tag-protection rules,
operational ticket API health, a signed production APK/AAB, or Play approval.
Those require independent verification.

## Automatic builds and versions

Android now has exactly **one application ID**,
`com.abolfazl260.flightiranbot24`. The `debug` build has the standard
`.debug` suffix solely to permit concurrent installation during testing;
there are no development/staging/production product flavors.

For every Android workflow run, `versionCode=GITHUB_RUN_NUMBER` and
`versionName=<appVersionBase>.<run number>` (currently `1.0.N`).
The version is computed without editing Gradle properties.

- **Pull request:** Android tests, debug APK and unsigned AAB for QA;
  untrusted PRs never get signing credentials.
- **Push to `main` touching the Android build inputs:** after the
  `verify` job passes, build and cryptographically verify the signed APK/AAB
  with the existing private GitHub Actions secrets. Upload
  `android-release-v1.0.N` containing `FlightIranBot24-v1.0.N.apk`,
  `.aab` and `SHA256SUMS.txt` (retained 90 days).
- **Automatic publication:** after Android QA, signatures, HTTPS origin
  checks and current-`main` verification pass, create the `v1.0.N` tag
  and public GitHub Release with the same signed assets.
- **API unavailable or stale:** a failed **advisory** step and explicit
  GitHub Actions warnings are emitted, but signed release publication is
  not blocked by an unrelated service outage. The app must show that
  prices are unavailable or stale. Never generate synthetic ticket prices.
- **Manual `vMAJOR.MINOR.PATCH` tag (optional):** still supports the
  original signed-release workflow, but no longer required for standard
  `main` builds.

The workflow refuses to release an outdated `main` commit, reuse a conflicting
release tag, or skip signature verification. Automatic GitHub Releases do
**not** automatically upload to Google Play Console. Do not upload a build with
a lower/equal `versionCode` than a version already uploaded to Play.

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
username/password/query/path. Release CI strictly validates the HTTPS
origin and separately probes `GET /api/v1/tickets/prices` as an advisory
health check. Signing and GitHub Release publication do not depend on
operational data freshness.
If the Worker has no published ticket snapshots, the UI shows a real
retrieval error rather than fabricated prices.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:bundleRelease
```

Android release artifacts: `android/app/build/outputs/apk/release/app-release.apk`
and `android/app/build/outputs/bundle/release/app-release.aab`.

## Current production release gates (November 2026)

- Pull request CI produces a debug APK and an **unsigned AAB** for QA.
  `main` automatically produces a separately named signed APK/AAB artifact
  after passing Android CI; use `android-release-v1.0.N`, **not**
  `android-unsigned-release-aab`, for signed files.
- The `Android Store Screenshots` workflow must boot an accelerated emulator,
  run the instrumented tests, and upload authentic PNG screenshots. KVM access
  is configured in the workflow; review the actual artifact before using the
  pictures in a public store listing.
- A signed release requires the four owner-controlled signing secrets listed
  above. The workflow automatically creates `v1.0.N` on the current
  reviewed `main` HEAD after validating signatures and the HTTPS API configuration.
  A separately supplied manual tag must also refer to current `main`.
- The release job builds both APK and AAB with the owner upload key, runs
  `apksigner verify`, checks the AAB with `jarsigner`, saves signed assets
  and SHA-256 checksums, and probes the ticket API as an advisory check.
- Automatic generation is not Google Play approval or publication. Complete
  physical-device checks, privacy review and Play Console requirements before
  distributing the release to production users.

The automatic **public publication gate** requires signed APK/AAB files,
signature verification, a valid HTTPS production API origin and the verified
current `main` HEAD. `GET /api/v1/tickets/prices` is still checked for
`currency: TOMAN`, a nonempty `routes` array, a recent `observed_at` and
`stale: false`, but its failure is an **operational advisory**, never silent
success. A Cloudflare HTTP 403 warrants checking Access/WAF rules, account
restrictions, and Worker logs from a trusted external network. Do not claim
live price data is healthy without verifying the source.
