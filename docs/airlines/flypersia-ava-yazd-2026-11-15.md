# FlyPersia, Ava Airlines, Yazd Airways — evidence review 2026-11-15

Adds independent airline v1 guides, without altering existing carriers, schema, reader, ratings, airport data, or manually triggered Android release.

| Airline | ICAO | IATA | published | draft |
| --- | --- | --- | ---: | ---: |
| FlyPersia | FPI | FP (secondary only) | 14 | 8 |
| Ava | AXV | not verified | 20 | 2 |
| Yazd | DZD | not verified | 14 | 8 |

## Reviewed evidence
**FlyPersia**: [OIBK Iranian operator list](https://oibk.ir/fa/iran/airlines) establishes FPI; [Planespotters](https://www.planespotters.net/airline/FlyPersia) shows FP and Boeing 737/757 family records (757 historical); [Rahig](https://rahig.com/airlines/flypersia) provides 33 sample fares, 20 kg *observed* baggage and 23 *observed* routes. None is a universal current operating policy. [Company-listed domain](https://www.flypersia.aero/) could not be read. Phone, online check-in, seat choice, pets, catering, lounge, connectivity and current tariff remain unverified.

**Ava**: [Official site](https://avaair.ir/), [general terms](https://avaair.ir/rules/rules-general-terms-and-conditions/), [refund policy](https://avaair.ir/rules/rules-cancellation-and-refund-policy/), [maternity scheme](https://avaair.ir/pregnant-women/), [limited pet route](https://avaair.ir/pet-transport/) and [contact page](https://avaair.ir/contact-us/) substantiate passenger information; [FAA](https://www.faa.gov/air_traffic/publications/atpubs/cnt_html/chap3_section_3.html) confirms AXV. The pet-service announcement is restricted to IKA–IST and the site's own refund descriptions differ: no universal refund outcome is promised. [Planespotters](https://www.planespotters.net/airline/AVA-Airlines) is only a secondary aircraft family reference, not proof of active fleet counts.

**Yazd Airways**: [OIBK](https://oibk.ir/fa/iran/airlines/dzd) substantiates DZD; [company public-relations feed](https://t.me/s/yazdairways) gives dated announcements, contact and company-referenced [domain](https://www.yazdairways.com/), with references to Airbus A310, RJ85 and BAe 146. The company website timed out here. No specific current baggage, refund, check-in, seat, pet or lounge tariff is asserted, and announced routes are not guaranteed future services.

IATA's [baggage](https://www.iata.org/en/youandiata/travelers/baggage/), [passenger rights](https://www.iata.org/en/youandiata/travelers/passenger-rights/) and [battery](https://www.iata.org/en/programs/cargo/dangerous-goods/lithium-batteries/) guidance is generic and never presented as proof of each airline's tariff. Fleet quantities and status are unknown; no synthetic reviews, star ratings, logo, live timetable or booking guarantee added.

## Release checks
Validate with `python scripts/validate_airline_content.py`, `pytest tests/test_airline_content_catalog.py`, `node --test cloudflare/test/guide_catalog.test.mjs` and Android tests. Deterministic test clocks advance to 2026-11-15. New data is immediately addressable from the public Android JSON endpoint; installed Android applications require the airline-guide-capable version and Mini App access depends on its deployed runtime.
