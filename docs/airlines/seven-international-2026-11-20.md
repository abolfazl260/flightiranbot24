# Seven international airlines — source review (2026-11-20)

Seven source-bound airline guides have been added to the existing GitHub JSON catalog. IATA confirms legal identity and IATA/ICAO codes. Airline-owned baggage, check-in and service pages support 13 published passenger-facing sections per guide; 9 sections without sufficient current detail remain unpublished drafts.

| Airline | IATA | ICAO | IATA source | Baggage source | New archive links |
| --- | --- | --- | --- | --- | --- |
| Turkish Airlines | TK | THY | https://www.iata.org/en/about/members/airline-list/turkish-airlines/196/ | https://www.turkishairlines.com/en-tr/any-questions/checked-baggage/ | 14 |
| Lufthansa | LH | DLH | https://www.iata.org/en/about/members/airline-list/lufthansa/115/ | https://www.lufthansa.com/az/en/digital-self-services | 17 |
| Qatar Airways | QR | QTR | https://www.iata.org/en/about/members/airline-list/qatar-airways/277/ | https://www.qatarairways.com/en-ie/help.html | 6 |
| Air Canada | AC | ACA | https://www.iata.org/en/about/members/airline-list/air-canada/21/ | https://www.aircanada.com/ca/en/aco/home/plan/baggage/checked.html | 7 |
| Austrian Airlines | OS | AUA | https://www.iata.org/en/about/members/airline-list/austrian/60/ | https://www.austrian.com/au/en/free-baggage | 4 |
| Pegasus Airlines | PC | PGT | https://www.iata.org/en/about/members/airline-list/pegasus-airlines/378/ | https://www.flypgs.com/en/travel-services/flight-services/additional-baggage | 1 |
| LOT Polish Airlines | LO | LOT | https://www.iata.org/en/about/members/airline-list/lot-polish-airlines/116/ | https://www.lot.com/pl/en/help-center/baggage/baggage-allowance-according-to-travel-class | 2 |

## Experiences and publication

The immutable 51-report original archive is unchanged. 36 reports can be associated with one or more of these foreign airlines, producing 51 new links and 75 total airline associations. All source names and surnames remain preserved verbatim. `operating` indicates an expressly described flight, while `mentioned` covers a cancelled, contemplated, compared or booked trip not clearly completed.

Every archive link has `moderation_status=pending`, `privacy_reviewed=false` and `consent_status=unknown`. An original report and author name are not republished until express permission and privacy review are recorded. No ratings are derived from the prose.

## Rollout

Android reads the remote JSON from the main branch, with an offline bundled fallback only after the next manual APK build. After deploying the server code, backfill the new archive target associations idempotently using `docker compose exec -T bot python scripts/manage_experiences.py import`. This work does not create new Telegram commands or mini-app screens. No flight schedule, fleet counts, ticket penalties or live availability is inferred.

## Remaining verification

Fill remaining drafts from carrier-specific official evidence with observation dates. Recheck baggage entitlements and transit requirements for each ticket; no universal weight allowance or transit-visa waiver has been asserted.
