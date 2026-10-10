# Flight Iran Bot 24 — Android

Android travel companion, gradually migrating from Java/XML to Kotlin/Jetpack Compose.

## Current implementation (AND-001 and AND-002)

- The launcher is a Kotlin/Compose screen, with a lifecycle-aware
  **HomeViewModel + StateFlow** for Loading/Ready/Error and Retry.
- A pure Kotlin `domain` model describes launcher actions. The `HomeRepository`
  interface is implemented by `LocalHomeRepository` in `data`; the
  `AppContainer` is an explicit dependency-injection composition root.
  Tests inject fake repositories without Android Activity dependencies.
- This deliberate, lightweight manual DI design avoids pulling in a large
  Hilt/KSP graph before any production API or identity client exists. Task
  AND-003 will add the network/data persistence dependencies.
- Offline airport and travel-checklist screens remain their original native
  Java Activities; data remains available without network access.
- Online actions still hand off to the Telegram bot or support account.
  The visa command is copied; users paste it in Telegram.
- The app does **not** authenticate to the Telegram Mini App, store bot
  credentials, or create fake users/sessions.

The airport data is packaged from
`src/flightiran/modules/airport/data/airports.json`.

## Build

JDK 17, Gradle 8.13, Android SDK 36. Android Gradle Plugin 8.13.2,
Kotlin 2.2.20 and Compose compiler plugin 2.2.20.

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:bundleRelease
```

Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`
Main app ID: `com.abolfazl260.flightiranbot24` (debug suffix: `.debug`).

See `docs/ANDROID_RELEASE.md` and `docs/PLAY_STORE_LISTING.md`.
Release signing requires a private upload key outside the Git repository.

## Next task
**AND-003:** Add Retrofit, OkHttp, Kotlin Coroutines networking conventions,
DataStore and Room to the structured data layer. Do not invent authenticated
endpoints; use versioned backend APIs only once they are implemented and tested.
