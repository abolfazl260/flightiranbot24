# Flight Iran Bot 24 — Android

Native Kotlin/Jetpack Compose travel companion, gradually migrating from Java/XML.

## Completed foundations (AND-001 and AND-002)

- The launcher uses Kotlin Compose and a lifecycle-aware HomeViewModel with
  StateFlow Loading/Ready/Error/Retry.
- Pure Kotlin domain interfaces and an explicit, testable AppContainer
  dependency-injection root protect data and presentation boundaries.
- The Java **offline airport directory** and **offline checklist** remain
  operational and unchanged. Checklist selections still use their existing
  SharedPreferences; no user data is migrated or erased.
- Online service buttons currently hand off to Telegram. No Telegram auth,
  bot token, fake Mini App session or server-side user account is embedded.

## AND-003: secure networking and local persistence

- Retrofit 2.11 + OkHttp 4.12, strict HTTPS base-url validation and a generic
  `PublicJsonRepository` built for `api/v1/<resource>` paths only.
  URLs cannot be absolute, contain traversal/query strings or redirect to
  external hosts. Timeouts, HTTP failures, invalid JSON and network loss
  produce typed results; cancellation propagates.
- Only **loopback HTTP** can be explicitly enabled to test MockWebServer.
  No real production API URL or endpoint name has been invented; the client
  is created lazily only once AND-004 provides configuration and API-001
  implements authenticated/unauthenticated contracts.
- DataStore Preferences holds **non-sensitive** language (`fa/en/ar`) and
  default passport country (`IR` by default). Credential storage is forbidden.
- Room public airport cache has a Java entity/DAO annotated with schema
  version **1**, and a Kotlin repository with atomic snapshot replacement,
  duplicate/IATA validation and explicit refusal of empty snapshots.
  The existing Java offline screen continues to read the packaged asset, not
  the new cache; migration of that screen is an AIR task.
- The normal INTERNET permission is declared for eventual first-party HTTPS
  access. Nothing is transmitted when the current launcher opens.

## Build / verification

JDK 17, Gradle 8.13, Android SDK 36, AGP 8.13.2, Kotlin 2.2.20.
Android CI runs:

```bash
gradle --no-daemon -p android :app:testDebugUnitTest :app:lintDebug :app:lintRelease :app:assembleDebug :app:bundleRelease
```

Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
Application ID `com.abolfazl260.flightiranbot24` (`.debug` suffix for debug).
Release upload signing requires private GitHub Actions secrets; no key is
included in the repository. See `docs/ANDROID_RELEASE.md`.

### Room schema evolution
`TravelCacheDatabase` starts at v1. The Java Room annotation processor exports
its schema under `android/app/schemas`. When bumping the schema, commit the
new JSON and an explicit tested Room migration. **Never** enable destructive
fallback on public or user-owned data. Existing checklist data is separate
and is not touched by this database.

### Future work / known limitations
API-001 must define the real backend endpoints and identity rules.
AND-004 adds stage-specific API origins without secrets. Full offline catalogue
sync and source verification belong to AIR-003; preferences UI and profile
sync belong to UI/AUTH tasks. Encrypted authenticated token handling is out
of scope of this deliberately **public-only** transport.

**Next task: AND-004 — separated Development, Staging and Production builds.**
