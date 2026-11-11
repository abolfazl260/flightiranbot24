# Pars Air and Chabahar Airlines — source and safety audit
Review date: **11 November 2026**. Parent tracking issue: #172.

Two independent v1 carrier records, two guide datasets and reader/validator
coverage are added. The prior 15 airline records and all existing passenger
experience archives remain unchanged.

| Carrier | Stable ID | Verified designator | Published / draft | Fleet model families |
| --- | --- | --- | --- | --- |
| Pars Air | `pars-air` | ICAO **PRS**, telephony **PARS SKY**; no verified IATA code | **14 / 6** | **3** |
| Chabahar Airlines | `chabahar-air` | ICAO **IRU**, telephony **CHABAHAR**; no verified IATA code | **13 / 7** | **4** |

An airline page being published does not mean all sections are complete.
Drafts remain hidden when current airline-specific evidence is unavailable.
`verified_at=2026-11-11T00:00:00Z` is a review-day marker, not a
policy-effective date. No live route snapshots, fake ratings/reviews,
guessed IATA designators, fleet counts, seat configurations or invented
contact channels were added.

## Pars Air — identity and current traveler evidence

### Identity

- The FAA's aircraft-company designator list explicitly maps **PRS** to
  **PARS AIR** and telephony **PARS SKY**:
  https://www.faa.gov/air_traffic/publications/atpubs/cnt_html/chap3_section_3.html
- The Iranian AIM / Civil Aviation Authority operator list, effective
  **10 June 2026**, also lists **PARS AIR / PRS / PARS SKY**:
  https://oibk.ir/fa/iran/airlines
- The official/company domain used by industry profiles and employment
  notices is **https://parsair.ir/**; its page did not load in this
  browser review. That is not proof of a company shutdown or a
  site-security incident.
- A secondary travel directory (MySafar, 24 Khordad 1405) labels the
  company with IATA **PF**, while the FAA, Iranian AIM and Planespotters
  material reviewed here do not confirm that two-letter assignment.
  Rahig's UI displays `PR` as its own airline key. **Neither PF nor PR
  is inserted as an IATA code** until verified against an authoritative
  IATA source.
- The Pars Instagram handle `parsair.official` is referenced in
  airline-industry association forwards. We label it as an identified
  channel, not as a verified customer-service endpoint:
  https://t.me/s/airanews

### Baggage and ticket rules

- The AirC circular channel announced **17 Mehr 1405** an update to
  Pars Air's baggage allowance procedure and excess-baggage tariff:
  https://t.me/s/aircir
  A separate **7 Mehr 1405** Pars Air fare sheet was also announced.
  The linked attachments could not be extracted reliably in this review;
  therefore the guide does not invent the new kilograms, route-specific
  excess charges or a current fare table.
- Rahig's live airline page (reviewed 11 November 2026) reports that,
  in its **20 recent observed flights**, 20 kg was the common checked
  allowance. It also says allowance depends on fare class and the
  exact flight result/ticket:
  https://rahig.com/airlines/parsair
  This is a **small secondary sample**, not a universal carrier policy,
  and it does not replace the 17 Mehr circular or the ticket itself.
- FlightGate's secondary guide, published **18 Ordibehesht 1402** and
  last updated **2 Dey 1402**, stated 20 kg domestic / 25 kg
  international checked baggage, 10 kg infant baggage and 7 kg cabin
  baggage, and included old cancellation percentages and special-service
  examples:
  https://www.flightgate.ir/%D9%87%D9%88%D8%A7%D9%BE%DB%8C%D9%85%D8%A7%DB%8C%DB%8C-%D9%BE%D8%A7%D8%B1%D8%B3/
  These values are explicitly marked **historical** in the guide and
  are not represented as current after the October 2026 update.
- The same historical guide describes wheelchair requests at booking,
  pregnancy/infant conditions and pet-carriage limits. Those are not
  surfaced as current permissions. Pet acceptance remains draft;
  special-assistance guidance is explicitly dated and caveated.
- Rahig says cancellation depends on fare class and whether the ticket
  is system or charter; the charter organizer may apply different terms.
  The older 1402 cancellation percentages are not re-published as current.
  For agency tickets, the traveler should submit the request through the
  issuing seller and inspect the exact refund quote before confirmation.

### Routes, contacts and fleet

- Rahig reported **68 observed routes across 23 cities** during the
  previous six months, including Tehran–Shiraz (last observed 19 Aban
  1405), Tehran–Isfahan (16 Aban), Isfahan–Mashhad (13 Aban),
  Tehran–Mashhad (10 Aban) and Tehran–Ahvaz (2 Aban). These are
  historical observations in a ticket-search platform, **not a
  guaranteed timetable or live flight status**.
- MySafar's contact directory dated **24 Khordad 1405** lists
  **021-49965000** for Pars Air:
  https://www.mysafar.com/mag/travel-facts/contact-information-for-iranian-airlines/
  It is a secondary directory number; current reachability and hours
  were not tested and the official website did not load in this review.
- Planespotters' **27 September 2026** snapshot lists CRJ-200 as the
  primary family and Boeing 737 variants in future/parked/historical
  records:
  https://www.planespotters.net/airline/Pars-Air
  Iranian AIM's registry data also lists one Boeing 737-400 registration.
  The datasets distinguish aircraft registration from active fleet size.
  The guide contains **CRJ-200, 737-400 and historic 737-300** model
  families, all with `count:null`, `status:unknown`,
  `relationship:unknown` and unknown configuration.

## Chabahar Airlines — verified pause notice and safe-link handling

### Identity

- Iranian AIM's operator list, effective **10 June 2026**, lists
  **CHABAHAR AIRLINE / ICAO IRU / callsign CHABAHAR**:
  https://oibk.ir/fa/iran/airlines
- Planespotters does not establish a reliable IATA two-letter code for
  Chabahar in the profile reviewed. No placeholder or guessed IATA
  designator is stored.
- The company's official Telegram channel `@chabaharairline`
  identifies itself as the official channel and lists the newer domain
  **https://chabaharairlines.ir/**:
  https://t.me/s/chabaharairline
  The .ir domain was not retrievable in this browser review; the
  Telegram channel was accessible and is the primary public link in
  the app.
- **Legacy-domain security warning:** the older `chabaharairlines.com`
  site currently renders unrelated/suspicious content rather than a
  trustworthy passenger website. The legacy domain is deliberately
  **not linked** anywhere in the airline index, user-facing guide,
  booking CTA or contact section. Do not use it for payment or identity
  documents.

### Operations and routes

- The official Telegram archive contains an explicit company statement
  that flights are **temporarily stopped** and gives no confirmed
  resumption date in that notice. No later explicit restart notice was
  found in the channel content reviewed for this change.
  The guide therefore does not advertise active inventory, a book-now
  button or an operational timetable. This is a **temporary-pause notice**,
  not a claim that the airline is permanently closed.
- Older channel posts refer to Tehran–Mashhad, Tehran–Shiraz,
  Tehran–Zahedan and Mashhad–Zahedan. They are recorded as historical
  route announcements only. Airport links navigate existing airport
  guides; no `route_snapshot` is published.
- Travelers with an already-issued ticket should contact the ticket
  seller and verify the current company notice before paying for an
  alternative or assuming automatic refund.

### Passenger rules and contact

- No current airline-specific baggage allowance, excess-baggage tariff,
  check-in window, seat-selection entitlement, refund penalty table,
  medical/assistance acceptance rule, pet-carriage rule, lounge or
  onboard connectivity policy could be safely verified from a
  trustworthy current passenger source.
- MySafar's contact directory dated **24 Khordad 1405** lists
  **021-44671959** for Chabahar:
  https://www.mysafar.com/mag/travel-facts/contact-information-for-iranian-airlines/
  This is a **secondary directory listing**, not proof the line is
  currently staffed. It is displayed with an explicit verification
  caveat and is not presented as an active 24/7 hotline.
- The app provides the official Telegram channel and the .ir domain
  identified there. The old .com domain is not linked.
- General IATA baggage, battery, travel-document and passenger-rights
  advice is identified as **general guidance**, never as Chabahar policy:
  https://www.iata.org/en/youandiata/travelers/baggage/ ;
  https://www.iata.org/en/youandiata/travelers/batteries/ ;
  https://www.iata.org/en/youandiata/travelers/passenger-rights/ ;
  https://www.iata.org/en/travel-centre/ .

### Fleet

- Iranian AIM's registry snapshot associates Chabahar's IRU operator
  with MD-82, MD-83 and Fokker 100 records; Planespotters also lists
  a historical Boeing 737-300 record:
  https://oibk.ir/fa/iran/airlines ;
  https://www.planespotters.net/airline/Chabahar-Airlines
- Registry rows may include retired, stored or historic aircraft.
  All four model cards therefore keep null counts, unknown status,
  unknown ownership/lease relationship and unknown cabin layout.

## Technical changes, CI and rollback

- Index grows from **15 to 17** carriers. New independent records:
  `pars-air` (PRS) and `chabahar-air` (IRU).
- Pars: **20 sections / 14 published / 6 drafts**.
  Chabahar: **20 sections / 13 published / 7 drafts**.
- Python tests verify IDs, source-scoped policy sections, code identity,
  hidden drafts, fleet unknowns, no synthetic reviews, no active route
  snapshots and the Chabahar legacy-domain link ban.
- Android bundled-asset tests and Cloudflare Mini App tests verify both
  independent detail parsers, Persian search aliases, publication gates
  and Chabahar's pause notice.
- No schema, UI component, API, database, moderation or release workflow
  changes. The APK/AAB workflow remains **manual dispatch on main only**.
  Existing installed Android offline content changes only after the
  next manually requested build.
- CI must pass airline-content validation, Python, Cloudflare and Android
  unit/lint/androidTest compilation before merge. Revert only this PR to
  roll back these two guide records without changing prior airlines.
