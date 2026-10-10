# Android publication runbook

## Implemented

Kotlin/Jetpack Compose Android app with preserved native Java offline screens, minimum SDK 24, target SDK 36, JDK 17, Gradle 8.13.
Offline airport directory and offline travel checklist are included.
Online links explicitly hand off to Telegram. No bot token in the APK.

GitHub Actions tests Java and builds a debug APK for pull requests. Tags
matching vX.Y.Z can build signed **productionRelease only** APK and AAB, validate their signatures and
publish SHA256 checksums in GitHub Releases.

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
5. Restrict GitHub v* tag creation to trusted maintainers via repository
   rulesets. Confirm job-scoped Actions contents:write can publish Releases.
6. Enroll with Google Play Console and Play App Signing if Play publication
   is intended. This requires the owner's developer account and verification.

## Each release

1. Increment appVersionCode and set appVersionName in android/gradle.properties.
2. Merge to main; ensure Android CI and Python CI are green.
3. Tag a reviewed commit from main (for current version 1.0.0):

    git checkout main && git pull --ff-only
    git tag -a v1.0.0 -m "Android 1.0.0"
    git push origin v1.0.0

4. Check Actions -> Android Build and Release; signed APK and AAB should
   appear in the matching GitHub Release with SHA256SUMS.txt.
5. Verify the checksum and install the signed APK for direct distribution,
   or upload the signed AAB to the Google Play testing track.

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

## AND-004 environment isolation

Only `productionRelease` retains the Play Store package ID
`com.abolfazl260.flightiranbot24`. Development and Staging use suffixes
`.dev` and `.staging` and visibly identify themselves; neither displays
live Telegram/support actions, preventing accidental requests by testers.
Debug variants add `.debug`. The release tag workflow stages only signed
`app-production-release.apk` and `app-production-release.aab` artifacts,
never an experimental flavor.

API origins are optional build settings and not authentication secrets.
Production does not inherit staging or development addresses and vice versa.
Set `ANDROID_PRODUCTION_API_ORIGIN`, `ANDROID_STAGING_API_ORIGIN`, and
`ANDROID_DEVELOPMENT_API_ORIGIN` as HTTPS *origins* only; no real endpoints
are configured by this change. Builds reject equivalent environment hosts
and attempts to configure nonproduction without a production origin. These
variables are not required to build the current offline/Telegram companion.
The native app does not yet call the server's new API; that work requires
API-001 and authentication design.

For a local verified build without server configuration:

```bash
gradle --no-daemon -p android :app:bundleProductionRelease
```

Neither this local AAB nor a CI-built unsigned AAB is a signed, uploaded Play
publication. Never ship staging/dev builds to the Play production track.
