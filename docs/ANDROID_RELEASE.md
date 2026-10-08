# Android build and publication guide

## What this provides

- Native Android companion source in `android/`, targeting **Android 16 / API 36**.
- Pull request and main-branch checks: Java unit tests, lint, **debug APK** artifact.
- Signed release on a `vX.Y.Z` tag: **APK** (direct GitHub installation),
  **AAB** (manual Google Play upload), and **SHA256SUMS.txt**.
- An idempotent GitHub Release publish step, limited to trusted tag builds.
- Signing kept out of source control and out of pull request builds.

This is *not* a complete independent version of the Telegram bot: the current backend
Web App endpoints require Telegram-signed initData. Features open the Telegram bot and
should be made standalone before claiming full in-app functionality in a store listing.

## One-time owner setup

1. Confirm the final, permanent Android `applicationId` in
   `android/app/build.gradle`. Once published, changing it creates a different app.
2. Generate a **private upload key locally** (not in GitHub, and not in chat).
   Example:
   ```bash
   keytool -genkeypair -v -keystore flightiran-upload.jks \
     -alias flightiran-upload -keyalg RSA -keysize 3072 -validity 10000
   ```
   Back up the keystore and passwords securely outside the repository. Prefer
   Google Play App Signing with a separate upload key.
3. In repository **Settings → Secrets and variables → Actions**, add:
   - `ANDROID_KEYSTORE_BASE64`: base64 of the full JKS file
     (e.g. `base64 < flightiran-upload.jks | tr -d '\\n'`).
   - `ANDROID_KEYSTORE_PASSWORD`: keystore password.
   - `ANDROID_KEY_ALIAS`: `flightiran-upload` (or your actual alias).
   - `ANDROID_KEY_PASSWORD`: alias password.
4. In repository Actions settings, grant the workflow sufficient permissions to
   create Releases with its scoped `contents: write` token. Restrict creation of
   `v*` tags to trusted maintainers using repository rulesets if available.
5. On Google Play Console, establish the developer account, app entry, App Signing,
   store description, real screenshots, support details, public privacy-policy URL,
   data-safety answers, content rating, target audience and testing/review requirements.
   The workflow does **not** submit to Play automatically and does not grant
   permissions to your Play Console.

## Every release

1. Increment `appVersionCode` in `android/gradle.properties` (**strictly
   increasing** versus all previous Play releases); set `appVersionName` to the
   desired semver version such as `1.0.1`.
2. Merge the update and any app changes to `main`; let Android checks pass.
3. Create and push a tag *at the tested main commit*:
   ```bash
   git checkout main && git pull --ff-only
   git tag -a v1.0.1 -m "Android v1.0.1"
   git push origin v1.0.1
   ```
   The workflow requires the tag to match `appVersionName` exactly.
4. Open GitHub **Actions → Android Build and Release** to inspect the two jobs.
   The Release page gains a signed APK, a signed AAB, and SHA-256 checksums.
5. Use the signed **AAB** for a Play Console release track and complete the
   store review there. Users installing outside Play should use the signed APK
   and may verify its checksum.

## Safety notes

- Never commit `*.jks`, `*.keystore`, a base64 key, service-account JSON,
  passwords, bot tokens, or private `local.properties`.
- Release jobs run **only** for `v*` tags; PRs get unsigned/development artifacts.
- If signing secrets are absent, a release fails rather than publishing an unsigned APK.
- Keep the same upload key for app updates; changing it without the Play Console
  recovery flow can prevent future releases.
- A GitHub Release is not Google Play publication. Store acceptance and policy
  compliance cannot be guaranteed by CI.
- The privacy summary in `docs/ANDROID_PRIVACY.md` must be reviewed against real
  bot-side collection and retention before distribution. A stable HTTPS URL is needed
  for the Google Play listing.
