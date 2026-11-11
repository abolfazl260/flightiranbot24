# Mahan Air and Iran Aseman source audit — 11 November 2026

Issue: #172. This content-only follow-up adds two **independent** carrier records
to the existing airline index and v1 detail contract. It does not rewrite or
re-verify Iran Air, Emirates, airports, visas, passenger experiences, ratings or
other carrier content. The published status means **source-scoped guidance is
available**, not that all travel policies are current and complete.

## Published scope and limitations

| Airline | IATA / ICAO | Published / draft | Fleet snapshots | Important unknowns |
| --- | --- | --- | --- | --- |
| Mahan Air (`mahan-air`) | W5 / IRM | 19 / 1 | 6 aircraft families | Current baggage tariff and refund penalties; active aircraft counts and ownership; inflight connectivity |
| Iran Aseman (`iran-aseman`) | EP / IRC | 14 / 4 | 5 aircraft families | Current baggage tariff, check-in conditions, cabin seat selection, catering, CIP, inflight connectivity and active fleet |

Both source reviews use `2026-11-11T00:00:00Z` as a **review-date
marker**, not an exact fetch time. All `effective_from/to` are null unless
supported by a concrete source. Unknown values are not converted into
invented zeros, free entitlements, active flight status, precise departure
times or safety assessments. Historical notices are described as historical.

## Mahan Air — primary sources and boundaries

- IATA code search: https://www.iata.org/en/publications/directories/code-search/?airline.search=W5
  verifies `W5`. ICAO `IRM` is corroborated by operator references at
  https://www.flightradar24.com/data/airlines/w5-irm/fleet .
- The first-party Telegram account https://t.me/s/mahanairchannel explicitly
  describes itself as official and currently points passengers to
  **https://www.mahanair.co.ir/**. The website was reachable as a shell/logo
  but did not expose independently reviewable live booking, baggage or fare
  rules in the browser. The previous `mahan.aero` URL appears in older
  official posts and must not be silently substituted for the current
  announcement.
- The company's historical Q&A at
  https://t.me/s/mahanairchannel?before=870 documents online check-in,
  some exclusions, baggage handoff at the airport and seat selection.
  These older cutoffs and airport limitations are **not presented as live
  2026 deadlines or universal online availability**.
- The official live-animal page is advertised by the first-party channel:
  https://www.mahanair.co.ir/fa/live-animals . The announcement mentions
  AVIH coordination, routing, cage documentation and special acceptance.
  Requirements and availability must still be rechecked for the specific
  itinerary. No cabin pet acceptance is inferred.
- Historical cabin reference:
  https://t.me/s/mahanairchannel?before=2406 (A310 business class).
  Catering message: https://t.me/s/mahanairchannel/3257 .
  Historical loyalty benefits: https://t.me/s/mahanairchannel?before=1442
  and https://t.me/s/mahanairchannel/775 . None is a guarantee of a
  specific onboard configuration, menu, lounge benefit or price today.
- Fleet type corroboration:
  https://www.flightradar24.com/data/airlines/w5-irm/fleet
  and https://www.planespotters.net/airline/Mahan-Airlines .
  These independent sources cannot validate `active`, `owned`,
  `leased` or a common count for this snapshot, so all count and
  configuration fields remain null and operating/ownership statuses
  `unknown`.
- Current-date advertisements in the official channel mention particular
  Tehran/Bandar Abbas, Mashhad and Kerman services and upcoming seasonal
  additions. They are **not** imported into undated recurring route
  snapshots or treated as guaranteed flights for a user's travel date.

## Iran Aseman — primary sources and boundaries

- IATA member record: https://www.iata.org/en/about/members/airline-list/iran-aseman-airlines/158/
  explicitly confirms the legal name, country, **EP**, **IRC**, account
  code **815**, and declared website **www.iaa.ir**.
- The first-party channel https://t.me/s/asemanairlines states
  its official status, repeats www.iaa.ir, and announces date-specific
  routes such as Tehran–Shiraz, Shiraz–Bandar Abbas and Shiraz–Abadan.
  These announcements are neither a live flight monitor nor a global
  network/schedule guarantee.
- Its published updates describe Fokker 100 on certain Tehran–Shiraz
  flights and plans to return some A320, Boeing 737 and A340 aircraft to
  service. Maintenance/recovery plans are not proof of completed work or
  currently active aircraft.
- Third-party fleet history:
  https://www.planespotters.net/airline/Iran-Aseman-Airlines .
  It also documents ATR 72 models in historical records. Counts from
  different sources and the distinction between historical, stored and
  active equipment are not comparable; all five model-family snapshots
  therefore use null counts and unknown operational relationships.
- Live carrier `https://www.iaa.ir/` pages repeatedly timed out in the
  browser during source review. **Do not interpret this as global outage**.
  Consequently, current numeric baggage policies, change/refund penalties,
  active web check-in, seat map, menu, lounge access and inflight connectivity
  are not asserted. Sections that would otherwise advertise unverified
  carrier-specific amenities remain draft.

## Common public safety / passenger references

- IATA travel baggage: https://www.iata.org/en/youandiata/travelers/baggage/
  — general passenger considerations; not a substitute for carrier fare
  conditions or legally applicable claims deadlines.
- IATA lithium battery guide:
  https://www.iata.org/en/youandiata/travelers/batteries/
- ICAO international power bank notice (2026):
  https://www.icao.int/news/new-power-bank-restrictions-will-safeguard-international-aviation?pubDate=20260427

Both guides label these as **general**, not official Mahan/Aseman-specific
policy. Checked/cabin/extra baggage and consumer refunds must be matched to
the ticket's operator, seller, fare, route, travel date and applicable law.

## Contract, privacy, testing and rollback

- Two new `details/<stable-id>.v1.json` files and two independent index
  entries. Public JSON paths and stable IDs are unique. Existing index rows
  are preserved unchanged; each new carrier's source/date flags are separate.
- Android/Mini App use existing section block types; no new reader, database,
  schema version or UI workflow. `airport_link` references only known IATA
  airports, never duplicates airport records. No `route_snapshot` claims
  an active timetable.
- No public passenger experiences or star ratings are generated. Shared
  moderated live experiences remain controlled by existing APIs.
  `published_reviews` and `experience_links` stay empty.
- Assertions check independent published/draft counts, source URLs,
  correct identity codes, published policy scopes, draft suppression, fleet
  count/status unknownness, zero fabricated reviews and no routes.
- Validate `python scripts/validate_airline_content.py`,
  `pytest tests/test_airline_content_catalog.py` and the existing Android
  / Cloudflare CI. Screen and TalkBack/offline checks require separate
  device validation. JSON edits do **not** trigger Android APK packaging.
- Roll back by reverting this PR (two details, index, tests, catalog doc,
  this audit); do not delete another carrier's data or alter immutable
  passenger archive material. Keep #172 open until current tariffs and
  other carrier-specific service rules are independently verified.
