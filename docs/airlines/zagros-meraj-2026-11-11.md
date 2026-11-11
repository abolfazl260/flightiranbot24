# Zagros Airlines and Meraj Airlines: source audit (11 November 2026)

Parent issue: #172. Content-only carrier addition to the existing v1 airline
catalog. Every listed link is a source reference, **not** proof that a
booking/payment service, fare or flight operates in real time. No original
passenger feedback, moderation records, other airline guides or airport guides
were changed.

## Inventory and publication scope

| Carrier | Stable ID | IATA / ICAO | Published sections | Draft sections | Aircraft type snapshots |
| --- | --- | --- | ---: | ---: | ---: |
| Zagros Airlines | `zagros-air` | ZO / IZG | 14 | 6 | A319, A320, MD-82, MD-83 |
| Meraj Airlines | `meraj-air` | IJ / MRJ | 14 | 6 | A300-600, A319, A320, A321 |

Both guides have exactly 20 candidate sections; unverified **check-in,
seat selection, catering, lounge, pet acceptance, and onboard connectivity**
remain unpublished drafts. This is not a finding that these services do not
exist. All sections use the review-day marker `2026-11-11T00:00:00Z`;
it is *not* a stated policy-effective date or exact clock time.

Both public company websites failed to provide trustworthy, current
policy text in our web reader: Zagros returned HTTP 502; Meraj timed out.
**These results do not establish a site outage for other users.** No claim
of live booking, tariffs, payment, check-in availability, contact hours, or
fleet dispatch has been fabricated. We published practical, clearly
source-qualified guidance and left carrier-specific unverifiable amenities
as drafts.

## Zagros evidence and caveats

- **ICAO IZG**, name and callsign: dated public-air-operations record
  (Iran AIM / CAO Iran, effective 10 June 2026),
  https://oibk.ir/fa/iran/airlines/izg .
  This states aircraft-record counts are registry history, **not active
  fleet** counts. Official origin links are cited from its page.
- **IATA ZO and ICAO IZG:** 2026 fleet directory
  https://www.planespotters.net/airline/Zagros-Air ,
  and aircraft-level tracker
  https://www.flightradar24.com/data/aircraft/ep-zat ,
  plus https://www.flightradar24.com/data/airlines/zo-izg/fleet .
  Non-airline booking/help sites sometimes give Z4 or ZV; these conflicting
  reseller pages are not used for identity.
- Officially reported website **www.zagrosairlines.com** is identified by
  the US Federal Register filing published 15 September 2026,
  https://www.govinfo.gov/content/pkg/FR-2026-09-15/pdf/2026-18909.pdf ,
  and the aviation directory. The report's purpose is regulatory; it is
  **not evidence of carrier services, route availability or fare rules**.
- Historical *dated observations* illustrate Tehran–Kish / Shiraz and
  Tehran–Istanbul/Tashkent activities:
  https://www.flightradar24.com/data/aircraft/ep-zat and
  https://data.flightradar24.com/data/aircraft/ep-zax .
  An airport's operational notices provide an independent example:
  https://t.me/s/MEHRABAD_AIRPORT?before=28745 .
  These are not active timetable commitments. Airport links in the
  network section point only to existing airport IDs; there are no
  invented `route_snapshot` blocks.
- Fleet types derived from Planespotters/FR24. Their totals and
  in-service/parked classification differ from registry histories, so
  each of four family records uses `count:null`, `status:unknown`,
  `relationship:unknown` and `configuration_fa:null`.
- The company website did not expose an accessible present-day
  baggage allowance, check-in deadline, change/waiver penalty or customer
  hotline. Old 4746 numbers from employment/agent pages must not be
  presented as freshly verified support. Third-party per-fare tables are
  not adopted as universal official policies.

## Meraj evidence and caveats

- **ICAO MRJ** confirmed by CAPA aviation profile
  https://centreforaviation.com/data/profiles/airlines/meraj-air-mrj ,
  MIDRMA registration/approval records
  https://midrma.com/en/rvsm/approvalList/ir ,
  and industry fleet directory
  https://www.planespotters.net/airline/Meraj-Airlines .
- **IATA IJ** shown by Planespotters and independent airline directories,
  but CAPA's current profile explicitly lists **IATA: n/a**.
  Our index follows the published Planespotters code IJ and labels
  this discrepancy in the guide; it does not imply CAPA confirms IJ.
  Recheck the operating-carrier identifier for a specific booking.
- CAPA identifies **https://meraj.aero/** as a carrier website; the
  Planespotters profile also lists this domain. The site timed out in
  this review. We make no assertion that `apps.meraj.aero` reservation or
  ticket-status endpoints are safe/reachable without separate verification.
- https://t.me/s/Merajairlinesinfo/828 is an archived airline-branded
  Telegram channel with references to the company domain and a Bale
  announcement. **We did not independently verify channel administration
  or dates of every post.** An archived Rasht–Istanbul announcement
  mentions **25 kg economy / 30 kg business** specifically for that
  route; it is included only as a **historical route-specific example**,
  *never* a universal or currently effective baggage entitlement.
  An archived **021-61954** contact cannot be guaranteed current.
- Fleet families A300-600, A319, A320, A321 are corroborated by
  Planespotters and MIDRMA. The fleet aggregator lists historical,
  parked and active aircraft. MIDRMA RVSM coverage/approval data is
  **not** real-time operating status or passenger safety ranking.
  Counts, status, ownership and seat configurations remain null/unknown.
- No current airline-specific cancellation penalties, online check-in
  or cutoff, accessible seating, pet cabin acceptance, catering menu,
  lounge eligibility or Wi-Fi terms were corroborated. Those policies
  are either draft or explicitly general advice.

## Public traveler guidance, distinct from carrier policy

- General baggage and missing-baggage reporting:
  https://www.iata.org/en/youandiata/travelers/baggage/
- Passenger rights, which depend on jurisdiction and ticket conditions:
  https://www.iata.org/en/youandiata/travelers/passenger-rights/
- General lithium battery and power bank guidance:
  https://www.iata.org/en/youandiata/travelers/batteries/
- International passport/visa/transit requirements:
  https://www.iata.org/en/travel-centre
- Airline refund complaint process as described by Iran CAO:
  https://t.me/s/caa_ir?before=765 and https://www.caa.gov.ir/

Carrier-specific allowances, costs, eligibility, cancellation timelines,
legal remedies and safety claims were not extrapolated from general rules.

## Contract, tests, privacy, release and rollback

- Index now has **nine** independently addressable carrier IDs. New
  `details/zagros-air.v1.json` and `details/meraj-air.v1.json`
  use existing JSON v1 schema, supported Android/Mini App text/bullets/link,
  airport-guide and fleet block types. No app API, database, loader,
  schema or release workflow changes.
- All published sections require at least one HTTPS source, a review
  marker and nonempty content; draft blocks remain empty and hidden by
  existing readers. Carrier-specific policies preserve separate
  `operating_carrier` and `seller:unknown` scope.
- Each guide has zero synthetic reviews, ratings, claims of historical
  passengers, profile images, logos or copyrighted media. Consent-gated
  live experience workflows are unaffected.
- Python catalog/scope/unknown-fleet snapshots, Android bundled-reader
  draft filters/search and Cloudflare Mini App parsing/search must pass
  with existing test and lint CI.
- Deployed live JSON propagation is not a guarantee of CDN/cache freshness.
  Installed Android bundled offline guides update on a later **manually
  dispatched build on main**; merges do not automatically package APKs.
  Persian RTL, real-device accessibility and offline fallback need
  separate end-to-end review.
- Rollback: revert this PR alone; preserve all seven previous carrier
  records and other Project data. Keep #172 open for verified present-day
  company policies, licensed media and unresolved details.
