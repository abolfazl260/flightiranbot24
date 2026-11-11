# Caspian Airlines and Sepehran Airlines — provenance and publication audit
Review date: **11 November 2026**. Parent tracking issue: #172.

This change adds two independent v1 airline guide details, two index identities,
related parser tests and coverage documentation. The previous eleven carrier
details, airport guides and historic/modeled passenger feedback remain unchanged.
An airline guide being "published" means only the **reviewed parts are visible**;
it is not certification of all fare rules or present-day operations.

## Coverage and identity

| Carrier | Stable ID | Verified codes | Visible / draft sections | Fleet families |
| --- | --- | --- | ---: | ---: |
| Caspian Airlines | `caspian-air` | ICAO **CPN**; **no verified IATA code** | **14 / 6** | 7 (5 listed passenger-jet models and 2 historical Boeing 747 variants) |
| Sepehran Airlines | `sepehran-air` | IATA **IS**, ICAO **SHI** | **19 / 2** | 5 (737-300/-400/-500 and historical Dornier 328/328JET) |

The index contains **13** independent carriers with no made-up reviews,
passenger names, airline rating data, active timetable, payments, airline
logos or other rights-restricted content.

All review dates use `verified_at:2026-11-11T00:00:00Z` as a **day-only
review marker**. That timestamp is **not** an actual time-of-day visit
or a policy-effective date. We do not silently treat older company posts as
new 2026 policies. Fleet count, active/parked status, ownership and seat
configuration are consistently `null`/`unknown`.

## Caspian: identity, baggage and current unknowns

- Identity: the Iran AIM/CAO 2026 ICAO operator notification was effective
  **10 June 2026**. Its CPN record and callsign CASPIAN are summarized at
  https://oibk.ir/fa/iran/airlines/cpn with the primary AIP document linked
  from that page. Both
  https://centreforaviation.com/data/profiles/airlines/caspian-airlines-cpn
  and https://www.planespotters.net/airline/Caspian-Airlines
  list **IATA n/a/blank**. No assumed two-letter airline code is included
  in the index or the traveler FAQ.
- The company's self-described official social channel is
  https://t.me/CaspianAirlinesChannel . An independently accessible
  forwarded carrier announcement published by the Iran Airlines
  Association at https://t.me/s/airanews names Caspian and states:
  **20 kg** economy domestic checked baggage; up to **30 kg**
  international and business; maximum **32 kg** per checked piece;
  **10 kg** cabin luggage. **The forwarded item did not establish a
  current airline policy-effective date**, per-fare variations, detailed
  cabin size or current surcharge. Numbers are explicitly presented as
  a quoted, dated-review source with itinerary confirmation, not
  universal present-day entitlement.
- The carrier's website `https://caspianairlines.com/` is listed in
  the aviation directory; its contents were **not retrievable** from our
  browser. That is not evidence of global outage, nor proof that booking
  or payment currently works. The social channel was independently
  located by its name/profile; channel administration was not audited.
- There is no reliably recovered present-day official check-in deadline,
  online seat selection, catering, lounge, pet policy, medical admission
  rule, telephone support hours or refund penalty table. Six such
  amenities remain unpublished draft. Published practical baggage,
  lost baggage, passenger assistance, refunds and passport guidance
  distinguish *general IATA advice* from actual Caspian entitlements.
- Fleet: https://www.planespotters.net/airline/Caspian-Airlines
  lists 737-300, 737-400, 737-500, MD-82 and MD-83.
  Iran's registry/ICAO directory at
  https://oibk.ir/fa/iran/airlines/cpn also includes historical
  **Boeing 747-100 and 747-200** registrations. This is not evidence
  of present-day passenger Boeing 747 service. These **seven** type
  snapshots have `count:null`, `status:unknown`,
  `relationship:unknown`; no tracker-based "in service" total is
  republished as a verified operator count.

## Sepehran: original carrier-published evidence

- Identity: https://www.planespotters.net/airline/Sepehran-Airlines
  lists **IS/SHI** and the company website `flysepehran.ir`.
  The company-authored Persian blog at
  https://blog.flysepehran.com/fa/ links customers to
  **https://flysepehran.com/** for direct purchase, seat selection,
  cancellation and special requests. We use the latter as the index
  website and record the alternate industry-listed domain;
  live payment availability was not verified.
  The Iranian ICAO operator list
  https://oibk.ir/fa/iran/airlines confirms SHI and callsign SHIRAZI.
- Checked and cabin baggage:
  https://blog.flysepehran.com/fa/airline/where-is-my-baggage/
  is dated **25 Tir 1404** and says up to **20 kg domestic**,
  **25–30 kg international**, **6 kg cabin**, cabin dimensions
  **20×40×55 cm**, and up to **two international checked pieces**.
  https://blog.flysepehran.com/fa/ticket/ also says the actual
  allowance is printed on the itinerary and can vary.
  These are **historical, carrier-authored guidance**, not a
  guarantee that all 2026 routes or fares share the same allowance.
  https://blog.flysepehran.com/fa/magazine/online-services/
  documents adding excess baggage online in the 1402-era article;
  current fees and transaction success were not tested.
- Ticket/refund and seating:
  https://blog.flysepehran.com/fa/ticket/
  describes the self-service "پیگیری و استرداد" route and fare-specific
  cancellation deductions, plus online seat choice for direct and
  agency-issued tickets. Critically, the **same page contains a
  3-hour and a 4-hour pre-departure seat selection cutoff** in different
  sections. It must be treated as an unresolved conflict: **neither
  cutoff is published as the current binding rule**. Guide asks
  travelers to check the actual booking.
- Mobility and catering: the same ticket guide describes online
  wheelchair requests and historically free domestic service.
  https://blog.flysepehran.com/fa/airline/airline-meals/
  published **19 Shahrivar 1402** describes meal examples and says
  online meal selection is **"coming soon"**. This cannot be
  upgraded to confirmed availability today; readers receive a
  careful informational section, not a working selection CTA.
- Pets:
  https://blog.flysepehran.com/fa/services/pet-transportation/
  dated **18 Ordibehesht 1403**, describes pet transport in **some
  international routes only**, selected dogs/cats/ornamental birds,
  required health/cage/destination documents, and no cabin transport
  in that published policy. Prior approval is essential. The
  page prints **+98 21 49116**, but current hotline hours/reachability
  and 2026 policy effectiveness were not confirmed. Pet carriage
  availability for today's flight must not be inferred.
- Loyalty:
  https://blog.flysepehran.com/fa/flight/mhd-to-njf/ and the ticket
  guide describe **RedMiles**, tier-specific date-change/refund,
  checked baggage and award services. No all-user free changes or
  unconditional no-show refund is claimed.
- Fleet: Planespotters' **14 October 2026** snapshot includes
  737-300 and 737-500 and historical 737-400, Dornier Do-328 and
  Dornier 328JET. A historic type does **not** imply current service.
  All five model family counts, operating states, ownership
  relationships and seat maps remain null or unknown.

## General standards and exclusions

- https://www.iata.org/en/youandiata/travelers/baggage/
- https://www.iata.org/en/youandiata/travelers/passenger-rights/
- https://www.iata.org/en/youandiata/travelers/batteries/
- https://www.iata.org/en/travel-centre

These are **not carrier-specific** fares, legal remedies, accessibility
guarantees or battery exemptions. Neither carrier guide asserts
live routes or adds `route_snapshot`; airport links are navigational
only. All `published_reviews` and `experience_links` remain
empty, with existing consent-gated reviews untouched.

## Technical contract, tests, rollout and rollback

- JSON v1 source metadata and carrier policy scope match existing
  validation/parser contracts. No schema changes, new Android UI
  blocks, database, accounts, moderation changes, or new service.
- Tests: Python 13-carrier catalog and independent snapshots, missing
  IATA code in Caspian, mandatory IS/SHI in Sepehran, exactly 14/6 and
  19/2 publication gates, seven/five unknown-count fleet cards,
  authoritative source links and 3h/4h contradiction note.
  Android bundled assets, Persian normalized search and Cloudflare
  Mini App parse the same JSON; draft sections must remain hidden.
- CI must pass Python, Cloudflare, airline content validator and Android
  unit/lint/androidTest Kotlin compilation before merge.
- Offline content in an already-installed Android APK updates only
  after a **manually dispatched build on main**. This PR does not
  trigger or change the release/build workflows. CDN caching,
  device-level RTL, TalkBack and actual end-to-end booking services
  are separately unverified.
- Rollback by reverting only this content PR, keeping the existing
  eleven carrier guides and all original user data. Leave #172 open
  for any missing current fare or policy verification and licensed media.
