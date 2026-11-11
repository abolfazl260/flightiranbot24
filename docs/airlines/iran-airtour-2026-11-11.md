# Iran Airtour airline guide — source and acceptance audit (2026-11-11)

Related parent #172. Scope: independent airline guide `iran-airtour`, no changes to existing
four carriers, flight prices, visas, airport data, original reviews, moderation or release workflows.

## Outcome

- Verified IATA identity: **B9** designator, **IRB** ICAO, accounting code **491**, Iran.
- **19** content sections: **13 published** source-scoped traveler guidance and **6 draft**:
  `checkin`, `seat-selection`, `cabin`, `catering`, `lounges` and
  `onboard-connectivity`.
- Six model snapshots: **Airbus A300-600, A310, A320; MD-82, MD-83 and MD-87**.
  Their counts, active/stored status, owned/leased relationship and seating configuration are
  **unknown** in this catalog. Never infer safety/airworthiness from model or age.
- No fabricated traveler experiences/ratings; static review arrays remain empty. Existing live
  moderated shared experiences and ratings remain controlled by existing project services.
- No unsourced numeric baggage rule, universal refund penalty, check-in cutoff, active route
  inventory, scheduled departure time, or rights-cleared photos/logos added.

## Source-by-source evidence

| Topic | Sources inspected | Publication decision |
| --- | --- | --- |
| Identity | https://www.iata.org/en/about/members/airline-list/iran-airtour-airline/498/ | IATA officially lists legal name, B9/IRB, country Iran and code 491. |
| Official website discrepancy | https://www.iata.org/en/about/members/airline-list/iran-airtour-airline/498/ ; https://ir.linkedin.com/company/airtourofficial | IATA currently lists `www.iat.aero`; company-operated LinkedIn states `www.iranairtour.ir` for booking/support. Use the latter as index website, label discrepancy in the access guide. Neither site produced usable live booking terms in our web reader. Do not infer global outage. |
| Fleet families and historical equipment | https://www.flightradar24.com/data/airlines/b9-irb/fleet ; https://www.planespotters.net/airline/Iran-Air-Tours | Both list six overlapping current/historical model families. FR24 and Planespotters display an apparent fleet size around 19, but this is not a verified count of operationally available or owned jets for the travel day. Leave counts null and status/relationship unknown. |
| Legal operator code, not flight status | https://oibk.ir/fa/iran/airlines/irb | Aggregates Iranian aviation source registration / 2026 designator information. Registration rows do not equal active fleet counts. |
| Routes and flight announcements | https://ir.linkedin.com/company/airtourofficial | The carrier's social page announced Tehran–Tashkent beginning **5 November 2026**, and other Tehran–Islamabad, Tehran–Kuala Lumpur and Tehran–Yerevan services. Announcements are not a current timetable or guaranteed date. Origin Tehran is not automatically expanded into IKA or THR; publish only airport guide links, not route snapshots. |
| Baggage and incident reporting | https://www.iata.org/en/youandiata/travelers/baggage/ | General IATA guidance confirms fare/route variability and prompt report at arrival. Does not establish Iran Airtour's checked or cabin allotment, fee or applicable deadlines. |
| Tickets, refunds and passenger assistance | https://www.iata.org/en/youandiata/travelers/passenger-rights/ | General jurisdiction-sensitive guidance only. No airline-specific refund table; no harmonized disability assistance policy. |
| Lithium batteries and power banks | https://www.iata.org/en/youandiata/travelers/batteries/ ; https://www.icao.int/news/new-power-bank-restrictions-will-safeguard-international-aviation?pubDate=20260427 | General transport safety baseline, **not** carrier-specific permission for unusual devices. |
| Visa/passport/health for international routes | https://www.iata.org/en/travel-centre | Individual nationality, destination, transit conditions and departure date determine travel document requirements. No universal waiver implied. |

### Rejected information and risk controls

- Pages from `iranairtourvirtual` are for a **flight-simulation virtual airline**, not Iran
  Airtour Airlines. No flight, aircraft or official contact claims were taken from them.
- Third-party ticket vendors and outdated directory numbers are not evidence of current rules,
  fees, support hours or check-in times.
- The exact identity `iran-airtour` is separate from `iran-air` (Iran Air / Homa);
  IATA codes B9/IRB and IR/IRA must never be cross-wired.
- A promotional page's claimed safety certification is not an independently verified safety
  ranking and is not displayed as a certification claim in this guide.
- Historical and independently tracked fleet records cannot prove aircraft active on a specific
  departure date. Model names must retain null counts and unknown status and ownership.
- Official website/payment availability is **not** confirmed by an IATA link, social profile,
  redirect or successful HTML shell. No authenticated login, transaction or passenger-data
  collection was attempted.

## Contract and QA

The update adds `data/airlines/details/iran-airtour.v1.json`, one index entry and tests
for the existing JSON contract. Android and Mini App readers already support text, bullets,
links, fleet cards and airport guide navigation; no new renderer, API, database or UI
version needed. Published sections require reviewed HTTPS sources; draft sections are
suppressed by existing Android/Mini App controls.

Validate `python scripts/validate_airline_content.py`,
`python -m pytest tests/test_airline_content_catalog.py`,
`node --test cloudflare/test/guide_catalog.test.mjs`, plus repository CI with
Android unit tests/lint/instrumentation compilation. Physical-device Persian RTL,
offline fallback and TalkBack acceptance remain separate manual tests.

A content-only PR is reversible without changing any original reports, consent flags,
other carrier or airport records. Android fallback packed into a previous APK remains
the older snapshot until a later **manual** build; automatic APK packaging must remain
disabled. Continue source review before new route or policy claims, and leave #172 open
for current carrier-specific policy, licensed assets and remaining integration.
