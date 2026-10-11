# Android publication runbook

## Implemented

Kotlin/Jetpack Compose Android app with preserved native Java offline screens, minimum SDK 24, target SDK 36, JDK 17, Gradle 8.13.
Offline airport directory and offline travel checklist are included.
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
5. Configure the GitHub **Actions repository variable** `ANDROID_PRODUCTION_API_ORIGIN`
   (Settings → Secrets and variables → Actions → Variables) with the real,
   publicly accessible HTTPS API origin. Deploy `flightiran-web` behind HTTPS,
   sharing the SQLite database volume with `bot`, then check that
   `GET /api/v1/tickets/prices` returns nonempty, non-stale price data.
   The origin is public, not a bot token or password.
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

The only first-party backend setting is `ANDROID_PRODUCTION_API_ORIGIN`,
or the Gradle property `apiOrigin`. It must be a bare HTTPS origin ending
in `/`, without username/password/query/path. Release CI validates that
the deployed `GET /api/v1/tickets/prices` endpoint serves fresh saved fares
before allowing signed publication.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:bundleRelease
```

Android release artifacts: `android/app/build/outputs/apk/release/app-release.apk`
and `android/app/build/outputs/bundle/release/app-release.aab`.
