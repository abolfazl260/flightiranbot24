# Android publication runbook

## Implemented

Kotlin/Jetpack Compose Android app with preserved native Java offline screens, minimum SDK 24, target SDK 36, JDK 17, Gradle 8.13.
The built-in airport directory and the 12-step travel checklist are included.
Ticket fares display natively through the database-backed HTTPS API; only
separate services such as support may intentionally hand off to Telegram.
No bot token is embedded in the APK.

APK/AAB builds are **manual only**. Go to Actions → **Android Build and Release** →
**Run workflow**, select `main`, then start the run. Pushes, pull requests,
merges and tags never trigger the build workflow. Both build jobs are guarded
to accept only a manual `workflow_dispatch` on `main`.

**Android Store Screenshots** is also manual-only on `main`; its emulator
builds the app and must not run after every merge. The standard Python and
Cloudflare CI checks remain automatic and do not build Android packages.

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
   before **publishing the GitHub Release**, not before creating the signed
   workflow artifact. The endpoint is public and must NEVER contain a bot token.
   Run the Cloudflare Publisher on Ubuntu to populate the D1 feed.
6. Allow the trusted Android workflow's `GITHUB_TOKEN` to create its
   manually requested build's numbered `v*` tags and publish GitHub Releases with scoped
   `contents: write` permissions. If repository tag rulesets block Actions,
   adjust the authorized workflow policy; do not disable signing checks.
7. Enroll with Google Play Console and Play App Signing if Play publication
   is intended. This requires the owner's developer account and verification.

## Verify upload signing before manually requested releases

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
not validate Google Play upload-key enrollment, tag-protection rules, a fresh
ticket API, a signed production APK/AAB, or Play approval. Those are separate
publication gates.

## On-demand builds and versions

Android has one application ID, `com.abolfazl260.flightiranbot24`.
The debug variant uses the `.debug` suffix for side-by-side installation.
Each manually started Android workflow uses `GITHUB_RUN_NUMBER` as the
`versionCode` and derives `versionName` from `appVersionBase` (e.g. `1.0.N`).

1. Open [Android Build and Release](https://github.com/abolfazl260/flightiranbot24/actions/workflows/android.yml).
2. Select **Run workflow** on branch **main**.
3. The verification job runs Android unit tests, lint and builds a debug APK.
4. After verification passes, the release job creates signed APK/AAB artifacts,
   verifies their signatures, and uploads `android-release-v1.0.N` with checksums.
5. Only for this user-initiated build, a GitHub Release is published if the
   deployed ticket API freshness check passes; otherwise signed files remain
   available as GitHub Actions artifacts (90-day retention).

The workflow refuses to publish an outdated `main` commit. A manual run on
another branch skips the jobs. Neither pushes, pull requests, merges nor
`v*` tag creation launch a build; standard CI remains separate.

To capture emulator screenshots separately, open [Android Store Screenshots](https://github.com/abolfazl260/flightiranbot24/actions/workflows/android-screenshots.yml),
select `main`, and choose **Run workflow**. This workflow is never triggered
by a push to `main`.

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
`GET /api/v1/tickets/prices` serves fresh saved fares before **public
GitHub Release publication**; signing and uploading the workflow Artifact
do not depend on data freshness.
If the Worker has no published ticket snapshots, the UI shows a real
retrieval error rather than fabricated prices.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:bundleRelease
```

Android release artifacts: `android/app/build/outputs/apk/release/app-release.apk`
and `android/app/build/outputs/bundle/release/app-release.aab`.

## Current production release gates (November 2026)

- Standard Python/Cloudflare CI continues on pull requests and pushes without Android APK/AAB creation.
- Android packages and emulator screenshots require a manual Run workflow on `main`.
- The Android build verifies tests, lint, the version, signed artifacts, and SHA-256 digests.
- The signing secrets are required for signed APK/AAB creation.
- Public GitHub Release publication also requires fresh data from the ticket API; if unavailable,
  signed APK/AAB files remain available in the manually started workflow's artifacts.
- Google Play upload, real-device testing and store review remain separate owner actions.
