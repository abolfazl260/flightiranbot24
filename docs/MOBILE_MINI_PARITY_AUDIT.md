# Android / Telegram Mini App feature audit

Baseline: Android `main` at `004aa1b66091119d49e36dd3410e2d3b15230e73`.
The Mini App comparison includes the initial airport/airline work in PR #183;
this follow-up extends that same PR rather than dropping the pending changes.

## Active native home destinations

| Native destination | Previous Mini App state | Result in this PR |
| --- | --- | --- |
| Ticket prices | Present: origin/destination, prices, changes, support | Preserved |
| Iran flights | Screen existed but lacked a direct Home entry and official-site fallback | Home entry + explicit official FIDS link, existing feed kept |
| Airport guides | Disabled on main; first part of #183 adds native web reader | Search/filter/source sections + popular/alphabetic ordering matching Android |
| Airline guides | Absent on main; first part of #183 adds shared reader | Preserved: search, fleet, official links, publication gates, counts-only ratings |
| Bot shortcut | Backend link existed but no direct Home entry | Home entry |
| Visa guide | Live API list/detail/watch existed; native snapshot and passport search absent | Searchable passport selector, same six popular destinations, optional Android snapshot, source dates/scope/attribution |
| Travel websites | Search/categories/images present; errors discarded a usable session catalog | Keep previous session catalog on refresh failure with receipt time and warning |
| Checklist | Same 12 items, local progress and confirmed reset | Preserved; accessible from privacy/data management |
| Support | Present | Preserved; also reachable from privacy/deletion instructions |
| Privacy | Absent | Seven platform-specific sections, local data management and support/deletion request link |

Tests map all ten active `LocalHomeRepository` destinations to reachable Mini App
entries. Popular visa destinations are checked against native `VisaCountries`.
Privacy information is also readable before Telegram sign-in; account screens
remain behind the existing bootstrap/authentication flow.

## Visa snapshot parity

The web reader uses the **unchanged** native `android/app/src/main/assets/visa/`
manifest and twenty compact shards from public GitHub. It validates coverage,
unique passport/destination identities, seven-field tuples, version/license,
source dates, unknown values and source URLs. It preserves the supplied notes,
verification dates and destination-file modification dates. The dataset's
CC-BY-4.0 attribution and modification date are displayed explicitly. A snapshot
is not relabelled as live data or silently substituted for a successful API read.

The user chooses “نسخهٔ همراه اندروید” or the existing online API. Snapshot-only
passport changes do not mutate server preferences. Alert creation still uses the
existing signed API and can reject unsupported passports; no unauthenticated
alert endpoint was added. Outdated visa-detail requests cannot overwrite a newer
or closed dialog.

Public snapshot downloads omit credentials/referrers and use bounded exact paths,
with four shard requests at a time. A validated full snapshot may be stored in
its own Cache Storage namespace (`flightiran-public-visa-v1`), without account IDs,
Telegram initData or user preferences. Later offline reads revalidate the cached
snapshot. Storage denial does not prevent online use. Clearing that cache waits
for pending downloads and prevents a cleared request from repopulating storage.
It does not clear another user's checklist, browser caches or server alerts.

## Platform differences retained explicitly

- Android installs a frozen visa bundle; the web needs connectivity for its first
  successful download and a loaded Mini App shell. Cache Storage availability,
  eviction and Telegram WebView behavior vary. This is not a PWA/install-shell
  or guaranteed first-visit offline feature.
- Airport/airline offline fallback remains a dated same-session copy in web, as
  documented in `MINI_APP_TRAVEL_GUIDES.md`. Android can use its APK-bundled copy.
- Native Android permission/settings screens cannot be controlled by a Telegram
  website. The web privacy page explains its own storage/account behavior and
  offers actual checklist/public-cache actions, not a nonfunctional OS button.
- Android renders FIDS in a WebView; Mini App keeps its approved feed UI and opens
  the official site externally instead of embedding an unapproved iframe.
- Telegram and Android checklists remain separate device-local data. No account
  sync, server deletion promise, online ratings, invented reviews or later #168
  experience integration is introduced.
- City artwork and other native visual styling are presentation differences;
  the web retains its existing design. No Android build/release workflow changes.

## Validation

- Full Python suite: 413 passed; Ruff passed.
- Node/Cloudflare suite: 44 passed. Includes native snapshot integrity, offline
  cache/reload/deletion, clear-during-download, country search and module routing.
- Headless Chromium phone-width smoke covers both guide readers plus privacy,
  local cache deletion, official FIDS navigation, passport search, full native visa
  snapshot, popular destination detail and pre-login privacy/auth boundaries.
- Browser tests mock Telegram and APIs; no live Telegram message, backend user
  mutation, production deployment or Android release was performed.

## Recorded fare ranking (#198)
Android and Mini App now expose cheapest / verified historical reductions tabs.
Origin and destination filters apply before ranking. Reduction eligibility requires
positive finite historical mean, at least three samples and a current price below
that mean; the displayed percentage is recomputed, never trusted from change_percent.
Cards retain booking/support and Mini App price alerts. Recorded timestamps and
stale labels remain visible; no inventory or booking guarantee is implied.

## Shared ranking contract (#199)
All three clients are covered by the same versioned JSON fixture, including
invalid means, insufficient samples, price increases, ties and half-up decimals.
See `TICKET_RANKING.md` for precision, filtering, source-cohort and freshness rules.
The public API adds an exact mean alongside its compatible rounded field. Telegram
reads the stored cohort; Android and Mini App keep stale last-good rates on failed
refresh rather than presenting them as current. Result counts vary by interface,
while the order of common routes is identical.

## Recorded route charts (#200)
Android and Mini App now render the same 21 UTC calendar-day daily minima as
Telegram `/chart`. The native Canvas and web SVG keep real date gaps; explicit
empty/single/flat-series states and accessible daily values accompany the graph.
A public, bounded history API is served directly from SQLite or via the existing
server-to-D1 publisher. See `TICKET_HISTORY.md` for rollout and rollback.

## Shared experiences and satisfaction (#202)
Android airport/airline guide panels, Mini App and `/experiences` now read the same
approved/consented public contract. Native writes use an explicit Telegram handoff;
Mini App supplies signed identity for submission, status, edit/delete, reports and
helpful votes. Ratings are actual approved integers; archives have no inferred
stars. All 51 source reports are preserved separately and withheld by default.
See `TRAVEL_EXPERIENCES.md` for moderation, permission, propagation and rollback.
