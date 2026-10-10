# Flight Iran Bot 24 — Android

Native Android travel companion, incrementally moving from Java/XML to Kotlin/Jetpack Compose.

## Current implementation (AND-001)
- The launcher is a **Kotlin + Jetpack Compose** screen, retaining the original package ID and existing deep links.
- The **offline airport directory** and **offline travel checklist** remain native Java Activities; no migration of their working data storage is necessary for this task.
- The Java airport catalogue/parser and native checklist continue to run without network permissions.
- Other online actions intentionally open the Telegram bot or support account. The visa command is copied to the clipboard; the user pastes it into the Telegram chat.
- The app does not authenticate directly to the Telegram Mini App: it must not embed a bot token or fabricate Telegram `initData`.

The airport data is packaged from
`src/flightiran/modules/airport/data/airports.json`.

## Build

JDK 17, Gradle 8.13, Android SDK 36. Android Gradle Plugin 8.13.2,
Kotlin 2.2.20, and Compose compiler plugin 2.2.20 are pinned in Gradle files.

From the repository root:

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:bundleRelease
```

Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`
Main application ID: `com.abolfazl260.flightiranbot24`
(debug suffix: `.debug`).

For releases see `docs/ANDROID_RELEASE.md` and
`docs/PLAY_STORE_LISTING.md`. Signed release builds still require a
private upload keystore outside the repository. Existing GitHub Actions
continues to build and validate the Android artifacts.

## Next task

**AND-002:** introduce an MVVM + domain/repository boundary with
dependency injection before connecting Android to backend API endpoints.
The launcher currently uses static shortcuts intentionally; online
features must not be advertised as fully native until the API is built.
