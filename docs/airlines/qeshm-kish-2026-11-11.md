# Source audit: Qeshm Air and Kish Air — 11 November 2026

Parent: #172. Independent source-gated v1 JSON guides for `qeshm-air` and
`kish-air`. Neither overwrites the existing five carriers or the immutable
experience archive. `published` means a section has reviewed source-backed
guidance, **not** that every fare, schedule or service is currently valid.

## Coverage

| Carrier | Codes | Published / draft | Fleet models | Main gaps |
| --- | --- | --- | --- | --- |
| Qeshm Air | QB / QSM | 17 / 2 | 4 | Current dated fare/fee table; current aircraft status/count; catering and onboard connectivity |
| Kish Air | Y9 / KIS | 15 / 5 | 4 | Current airline-specific baggage/refund tables, online check-in, selection, lounge, pets, connectivity and fleet counts |

All source review timestamps `2026-11-11T00:00:00Z` denote a **review
day**, not an exact visit time or policy-effective date. No specific
`effective_from`/expiry is asserted. Sections with undisclosed amenities
remain draft; unknown values are null/unknown, never invented zeros, rates,
rankings or active aircraft.

## Qeshm Air — authoritative pages read

- The carrier's public site is **https://www.qeshm-air.com/web2/**. It has
  visibly working textual pages for purchase, flight-status lookup,
  ticket-status lookup, baggage, refunds, traveler support, and fleet.
  The online purchase entry **https://apps.qeshm-air.com/ibe** is also
  advertised repeatedly by the company's own
  **https://t.me/s/qeshmair**. The booking endpoint was not retrieved
  successfully in this environment; **no payment or live inventory was tested**.
- Cabin allowance:
  https://www.qeshm-air.com/web2/knowledge.asp?cid=5106&ctype=guide&lang=&title=%D8%A8%D8%A7%D8%B1_%D9%87%D9%85%D8%B1%D8%A7%D9%87_%D9%85%D8%B3%D8%A7%D9%81%D8%B1_(%DA%A9%D8%A7%D8%A8%DB%8C%D9%86)
  documents one piece, 5 kg for economy/domestic and 7 kg for
  business/international, with **55×40×20 cm** measurements. Page
  contains no explicit effective date. Present this as the source's
  reviewed published guidance requiring itinerary-specific confirmation.
- Baggage FAQ:
  https://www.qeshm-air.com/web2/knowledge.asp?ctype=faq&lang=&pid=21&title=%D8%A8%D8%A7%D8%B1_%D9%85%D8%B3%D8%A7%D9%81%D8%B1
  reports a **Dubai-only example** (30 kg economy / 40 kg business);
  never make it universal checked luggage for all flights. Checked
  allowance otherwise comes from the **ticket** and extra charge from
  current carrier process. Other-size/infant rules are not generalized.
- General FAQ:
  https://www.qeshm-air.com/web2/knowledge.asp?ctype=faq&lang=fa&pid=15&title=%D8%B3%D9%88%D8%A7%D9%84%D8%A7%D8%AA_%D8%B9%D9%85%D9%88%D9%85%DB%8C_%D9%85%D8%B3%D8%A7%D9%81%D8%B1%D8%A7%D9%86
  advises airport arrival **2h domestic / 3h international** and cites
  check-in counter cutoffs **30m domestic / 45m international**, gate
  **15m**. All may be stale; require same-day confirmation.
  Also covers document checks, pet handling, reporting lost/damaged bags
  *before leaving baggage claim*, contact information, fare classes and
  airport terminal references. We deliberately do not publish its
  undated medical acceptance thresholds, blanket immigration claims,
  compensation amounts, liability disclaimers or universal refund deadlines.
- Official refund instructions:
  https://www.qeshm-air.com/web2/knowledge.asp?cid=5788&ctype=help&lang=&pid=22&title=%D8%B1%D9%88%D8%B4_%D8%A7%D8%B3%D8%AA%D8%B1%D8%AF%D8%A7%D8%AF_%D8%A8%D9%84%DB%8C%D8%B7:
  differentiate guest purchase (buyer phone + ticket) from same-account
  purchase. Current penalty diagrams are images without a reliable textual
  per-fare effective date; **no penalty percentage inferred**.
- Official contact:
  https://www.qeshm-air.com/web2/knowledge.asp?id=8013&lang=fa&pid=0&tid=0&title=%D8%AA%D9%85%D8%A7%D8%B3_%D8%A8%D8%A7_%D9%85%D8%A7
  lists **021-47999**, **info.qeshm@qeshm-air.com**, and
  Tehran Riahi Street office. Office hours are not asserted as 24/7
  hotline availability.
- Mobility equipment:
  https://www.qeshm-air.com/web2/knowledge.asp?cid=5780&ctype=guide&lang=&title=%D8%B5%D9%86%D8%AF%D9%84%DB%8C_%DA%86%D8%B1%D8%AE%D8%AF%D8%A7%D8%B1_%D9%88_%DB%8C%D8%A7_%D8%B3%D8%A7%DB%8C%D8%B1_%D9%88%D8%B3%D8%A7%DB%8C%D9%84_%DA%A9%D9%85%DA%A9_%D8%AD%D8%B1%DA%A9%D8%AA%DB%8C_%D8%A8%D8%A7%D8%AA%D8%B1%DB%8C_%D8%AF%D8%A7%D8%B1
  distinguishes battery types and removal; no guarantee of specific
  medical eligibility. The general travel page covers exit-row seating.
- Official undated model page:
  https://www.qeshm-air.com/web2/knowledge.asp?ctype=fleet&lang=fa&title=%D9%85%D8%B9%D8%B1%D9%81%DB%8C_%D9%86%D8%A7%D9%88%DA%AF%D8%A7%D9%86
  names **A300-600, A320, Avro RJ100, Fokker 100** with raw page
  counts, but not a dated active/owned/leased inventory.
  Independent sources
  https://www.flightradar24.com/data/airlines/qb-qsm/fleet and
  https://www.planespotters.net/airline/Qeshm-Air differ on the
  count of current aircraft and types of operational states.
  The four snapshots therefore retain null count/configuration and
  status/relationship `unknown`. Codes QB/QSM confirmed in
  https://centreforaviation.com/data/profiles/airlines/qeshm-air-qb .
- Network sources are official dated posts and the public route widgets.
  The airport links navigate the existing airport catalog and **do not**
  assert a live `route_snapshot`, timetable or departure.

## Kish Air — sources and limits

- The company's self-described **official** Telegram channel
  https://t.me/s/KishAir repeatedly advertises **kishairlines.ir**
  as its booking website and posts original 1405 service announcements.
  During our review both `https://kishairlines.ir/` and
  `https://www.kishairlines.ir/` were inaccessible from the public
  browser tool. That does **not** prove global downtime.
- The announcements discuss launching a **Kish–Gorgan** route,
  **Rasht–Bandar Abbas** service, fleet maintenance/return of some
  Airbus/Fokker equipment and improving onboard catering.
  The copy does not claim any perpetual schedule, operational
  readiness for other aircraft, standard free meal or lounge access.
- Aviation directory and history
  https://www.planespotters.net/airline/Kish-Air
  and https://www.flightradar24.com/data/airlines/kis/fleet
  confirm **Y9 / KIS**, and model families **A321, Fokker 100,
  MD-82 and MD-83**. PlaneFinder
  https://planefinder.net/data/airline/KIS/fleet
  contains additional historic/registration classifications, and
  the totals do not match the other sources. We therefore publish **no
  operational count, ownership, or seat configuration**, and make no
  safety ranking.
- No official up-to-date, independently retrievable Kish Air fare
  or baggage rules, check-in cutoff, cabin pet policy, lounge admission,
  online seat selection or inflight connectivity were verified. These
  amenities either remain draft or appear only as **explicitly general,
  non-carrier-specific passenger guidance** with relevant IATA links.

## General safety and passenger standards

- Checked baggage overview:
  https://www.iata.org/en/youandiata/travelers/baggage/
- Lithium batteries / power banks:
  https://www.iata.org/en/youandiata/travelers/batteries/
- Passenger rights / legal jurisdiction:
  https://www.iata.org/en/youandiata/travelers/passenger-rights/
- Travel documents:
  https://www.iata.org/en/travel-centre

These are **not** airline-specific fare entitlements or permission to
bring every device onboard. Confirm with the operating carrier, departure
airport and destination authority.

## Schema, tests, rollback and publication

- New `qeshm-air` and `kish-air` index identities and separate v1 details
  use the existing Persian/RTL Android and Mini App block types.
- Publication gates, policy scope, review day, HTTPS sources, null/unknown
  fleet values, airport-link integrity and no fabricated reviews are
  asserted in Python + Android + Cloudflare reader tests.
- `published_reviews` and `experience_links` are empty. Immutable
  historical passenger experiences and moderated live ratings are
  unchanged; no generated stars or borrowed copyrighted media.
- No API, schema version, database or Android app release workflow
  modifications. Validate JSON, all unit tests, Android lint/unit tests
  and Android instrumentation-test compilation through PR CI.
- Offline bundles only receive new JSON at the next **manual**
  Android build. Direct deployed remote availability, real-device RTL,
  accessibility and TalkBack still require manual checks.
- Revert only this PR if source quality or rendering regresses; retain
  all existing carrier, airport, travel and experience records. Keep #172
  open for policy tariff verification and licensed media integration.
