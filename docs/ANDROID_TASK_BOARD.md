# Android full travel app — sequential delivery board

This board tracks the **64 tasks** planned for Android 1.0. An entry marked
`Done` requires a reviewed PR merged into `main` plus passing applicable
CI; `Next` is not implemented. **Completed: 4/64**. Next backend task: API-001 (#56).
UX and CI review fixes (#63–#71) can run in parallel when dependencies allow.

Do not mark Telegram-only screens as native features. Backend APIs, authentication,
push notifications and reservation workflows need their own implementation
and independent acceptance tests.

## Android product policy — locked
- **Only Persian (fa-IR) is supported in the Android UI.** All screens use a right-to-left (RTL) layout, including when the phone's system language is English or Arabic. Treat IATA codes/URLs as isolated LTR tokens only.
- **Do not develop multilingual Android UI, language switching, English or Arabic UI translations, or an LTR app mode.** Any legacy fa/en/ar preference/storage is to be retired safely under #63; unrelated saved preferences must survive the migration.
- This Android-only decision **does not alter** Telegram bot language support.
- In user-facing mobile views describe recorded averages without exposing the internal history lookback window.

## Review follow-up issues (created 2026-10-10)

| Priority | Area | Issue | Target |
| --- | --- | --- | --- |
| P0 | Persian-only RTL | #63 | All views, device locales, safe preference migration |
| P0 | Screenshot pipeline | #69 | Correct flavor-specific APK, genuine Persian screenshots |
| P1 | Advertio design system | #64 | Tokens, reusable components, branding and a11y |
| P1 | Dashboard & navigation | #65 | Compose home, service categories, explicit handoff |
| P1 | Telegram handoff | #66 | Direct visa flow without clipboard/paste |
| P1 | Offline airports | #67 | Compose list, search, Room cache and fallback |
| P1 | CI reproducibility | #70 | Data-change triggers, Gradle wrapper, production checks |
| P1 | UI/device quality | #71 | RTL, typography, accessibility, emulator tests |
| P2 | Offline checklist | #68 | Polish, persistence and reset confirmation |

Related existing work: API contracts #56; owner/Play publication actions #40.
The review follow-ups correspond to existing roadmap rows where applicable; they
**do not add completed work** or alter the 4/64 completion count.

## Milestone A — Android Foundation
| ID | Task | State | GitHub |
| --- | --- | --- | --- |
| AND-001 | Kotlin and Jetpack Compose alongside existing Java / gradual launcher migration | Done | #48, PR #50 |
| AND-002 | MVVM, Domain/Repository layers and dependency injection | Done | #49, PR #51 |
| AND-003 | Retrofit/OkHttp, Coroutines, DataStore and Room | Done | #52, PR #53 |
| AND-004 | Development/Staging/Production Android build environments | Done | #54, PR #55 |
| API-001 | Versioned REST API and OpenAPI schemas | Next | #56 |
| API-002 | Ticket price, recorded historical average and history endpoints | Planned | — |
| API-003 | User-owned price and visa alert management API | Planned | — |
| API-004 | Visa rules, provenance and airport search API | Planned | — |
| API-005 | Profile, devices, settings and booking requests API | Planned | — |
| AUTH-001 | Standalone identity provider and guest mode | Planned | — |
| AUTH-002 | Token/session rotation and secure revocation | Planned | — |
| AUTH-003 | Optional Telegram account linking with one-time proof | Planned | — |
| AUTH-004 | Profile, logout, device management and account deletion | Planned | — |
| UI-001 | Advertio visual identity and design tokens | Planned | #64 |
| UI-002 | Components (cards, inputs, tables, bottom navigation) | Planned | #64 |
| UI-003 | Persian-only fa-IR and mandatory RTL; no language selector or translations | Planned | #63 |
| UI-004 | Themes, Persian typography, accessibility and loading/error states | Planned | #64, #71 |

## Milestone B — Core travel features
| ID | Task | State |
| --- | --- | --- |
| HOME-001 | Dashboard, recents and quick actions | Planned |
| HOME-002 | Bottom navigation and deep links | Planned |
| HOME-003 | Connection status and freshness indicators | Planned |
| TICKET-001 | Origin and destination picker | Planned |
| TICKET-002 | Current fare list in tomans | Planned |
| TICKET-003 | Recorded average, price and percent changes (no window shown in UI) | Planned |
| TICKET-004 | Price history chart with sample quality | Planned |
| TICKET-005 | Sort and favorites | Planned |
| ALERT-001 | Absolute price ceiling | Planned |
| ALERT-002 | Percentage price drop (5–50%) | Planned |
| ALERT-003 | Manage alerts: pause/resume/remove | Planned |
| ALERT-004 | Notification history and threshold explanation | Planned |
| VISA-001 | Passport/destination picker, default IR | Planned |
| VISA-002 | Full visa status taxonomy | Planned |
| VISA-003 | Stay windows and entry conditions | Planned |
| VISA-004 | Provenance and stale-data warnings | Planned |
| VISA-005 | Country filters and passport comparisons | Planned |

## Milestone C — Complete travel services
| ID | Task | State |
| --- | --- | --- |
| VWATCH-001 | Subscribe to visa route changes | Planned |
| VWATCH-002 | Manage watched visa routes | Planned |
| VWATCH-003 | Visa change diff history with original sources | Planned |
| AIR-001 | Modern offline airport lookup | Planned |
| AIR-002 | Airport detail page | Planned |
| AIR-003 | Versioned offline airport updates | Planned |
| TRAVEL-001 | Curated useful travel information | Planned |
| TRAVEL-002 | Offline checklist templates | Planned |
| TRAVEL-003 | Favorite destinations and travel plans | Planned |
| BOOK-001 | Booking inquiry form | Planned |
| BOOK-002 | Secure booking inquiry API and unique tracking ID | Planned |
| BOOK-003 | Support agent request processing | Planned |
| BOOK-004 | Booking inquiry status in the app | Planned |
| PUSH-001 | Firebase Cloud Messaging configuration | Planned |
| PUSH-002 | Register and revoke device tokens | Planned |
| PUSH-003 | Price/visa/booking push delivery | Planned |
| PUSH-004 | Notification inbox and opt-in preferences | Planned |

## Milestone D — Quality and publishing
| ID | Task | State |
| --- | --- | --- |
| SEC-001 | HTTPS, authentication, rate limits and ACL | Planned |
| SEC-002 | Cache, timeouts, offline and retries | Planned |
| SEC-003 | Verify prices/visa/airport data provenance and freshness | Planned |
| SEC-004 | Privacy, minimization and data-deletion controls | Planned |
| QA-001 | ViewModel and domain unit tests | Planned |
| QA-002 | API/database integration tests | Planned |
| QA-003 | UI/end-to-end tests | Planned |
| QA-004 | Performance/battery and device compatibility | Planned |
| QA-005 | Privacy-conscious crash/quality telemetry | Planned |
| REL-001 | CI/CD, versioning, build artifacts | Planned |
| REL-002 | Release signing, Play App Signing and AAB | Planned |
| REL-003 | Store screenshots, privacy and Data Safety | Planned |
| REL-004 | Internal/closed testing and release/rollback | Planned |

## Delivery convention
1. Work on the first open task in dependency order; link its issue and PR.
2. Run all relevant tests, including Android debug APK and release AAB builds.
3. Fix failures before merging; record any operational blockers as comments.
4. Mark the completed task `Done` only after verification and update `Next`.
5. Do not promise deployment to a physical device or Google Play without
   device, signing, and developer-account access.
