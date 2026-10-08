# Flight Iran Bot 24 — Android

This is a lightweight **native Android companion** to the existing Telegram bot, not
a WebView of the Telegram Mini App. The Mini App currently requires signed Telegram
init data and cannot act as a standalone Android login. Visa, currency, airport and
travel-info actions therefore open the existing Telegram bot. The visa (`/visa`) and
currency (`/price`) commands are copied to the clipboard before opening the chat.

## Build

Requirements: **JDK 17**, Android SDK **API 36**, and **Gradle 8.13**.
The GitHub workflow installs a pinned Gradle distribution without a binary
wrapper JAR. For local use, install Gradle 8.13 and run:

```bash
cd android
gradle :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

The debug APK is in `app/build/outputs/apk/debug/` and uses the
`com.abolfazl260.flightiranbot24.debug` application ID.

## Production

Read [Android release instructions](../docs/ANDROID_RELEASE.md) before issuing a
`v1.0.0` tag. Signed release APK and AAB are built only in a trusted tag workflow,
after four repository signing secrets are configured. Debug jobs receive no secrets.

Current release package ID: `com.abolfazl260.flightiranbot24` (keep it stable after
first Play publication). Build configuration is in `app/build.gradle`; increment
`appVersionCode` for every release and update `appVersionName` to the release tag.

No bot token, admin ID, database URL, or signing material should be embedded in the APK.
