# Android full travel app — sequential delivery board

This board tracks the **64 tasks** planned for Android 1.0. An entry marked
`Done` requires a reviewed PR merged into `main` plus passing applicable
CI; `Next` is not implemented. **Completed: 1/64**. The active task is AND-002. Next planned: AND-003.

Do not mark Telegram-only screens as native features. Backend APIs, authentication,
push notifications and reservation workflows need their own implementation
and independent acceptance tests.

## Milestone A — Android Foundation
| ID | Task | State | GitHub |
| --- | --- | --- | --- |
| AND-001 | Kotlin and Jetpack Compose alongside existing Java / gradual launcher migration | Done | #48, PR #50 |
| AND-002 | MVVM, Domain/Repository layers and dependency injection | In progress | #49 |
| AND-003 | Retrofit/OkHttp, Coroutines, DataStore and Room | Next | — |
| AND-004 | Development/Staging/Production Android build environments | Planned | — |
| API-001 | Versioned REST API and OpenAPI schemas | Planned | — |
| API-002 | Ticket price, 21-day average and history endpoints | Planned | — |
| API-003 | User-owned price and visa alert management API | Planned | — |
| API-004 | Visa rules, provenance and airport search API | Planned | — |
| API-005 | Profile, devices, settings and booking requests API | Planned | — |
| AUTH-001 | Standalone identity provider and guest mode | Planned | — |
| AUTH-002 | Token/session rotation and secure revocation | Planned | — |
| AUTH-003 | Optional Telegram account linking with one-time proof | Planned | — |
| AUTH-004 | Profile, logout, device management and account deletion | Planned | — |
| UI-001 | Advertio visual identity and design tokens | Planned | — |
| UI-002 | Components (cards, inputs, tables, bottom navigation) | Planned | — |
| UI-003 | Persian, English, Arabic, RTL/LTR | Planned | — |
| UI-004 | Light/dark themes, typography, accessibility and loading/error states | Planned | — |

## Milestone B — Core travel features
| ID | Task | State |
| --- | --- | --- |
| HOME-001 | Dashboard, recents and quick actions | Planned |
| HOME-002 | Bottom navigation and deep links | Planned |
| HOME-003 | Connection status and freshness indicators | Planned |
| TICKET-001 | Origin and destination picker | Planned |
| TICKET-002 | Current fare list in tomans | Planned |
| TICKET-003 | 21-day average, price and percent changes | Planned |
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
