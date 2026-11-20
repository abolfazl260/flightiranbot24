# Seven international airlines: dated, source-backed routes and Pegasus services

Reviewed **2026-11-20 (UTC date only)**. This update adds **14 route snapshots**, two per carrier, to the Android/Mini App shared JSON guides. Each route has a specific official airline source, a separately dated observation, and `status: listed`. This is **not** proof of live availability or operation on any particular day. Flight number, schedule, fare, stop pattern, terminal and true operating carrier must be checked on the airline's booking/status tools.

| Carrier | Endpoints | Official passenger route source |
| --- | --- | --- |
| Turkish Airlines | IST–LHR | https://www.turkishairlines.com/en/book-flights-from-istanbul-to-united-kingdom |
| Turkish Airlines | IST–CDG | https://www.turkishairlines.com/en/flights-from-istanbul-to-paris |
| Lufthansa | FRA–LHR | https://www.lufthansa.com/lhg/gb/en/o-d/cy-cy/frankfurt-london |
| Lufthansa | MUC–LHR | https://www.lufthansa.com/lhg/de/en/o-d/cy-cy/munich-london |
| Qatar Airways | DOH–LHR | https://www.qatarairways.com/en-qa/destinations/flights-to-london/from-doha.html |
| Qatar Airways | DOH–CDG | https://www.qatarairways.com/en/destinations/flights-to-paris/from-doha.html |
| Air Canada | YYZ–YVR | https://www.aircanada.com/en-ca/flights-from-toronto-to-vancouver |
| Air Canada | YYZ–YUL | https://www.aircanada.com/en-ca/flights-from-toronto-to-montreal |
| Austrian Airlines | VIE–LHR | https://www.austrian.com/lhg/at/en/o-d/cy-cy/vienna-london |
| Austrian Airlines | VIE–FRA | https://www.austrian.com/lhg/at/en/o-d/cy-cy/vienna-frankfurt |
| Pegasus Airlines | SAW–AYT | https://www.flypgs.com/en/cities/flights-from-istanbul-to-antalya |
| Pegasus Airlines | SAW–ADB | https://www.flypgs.com/sehirler/istanbul-izmir-ucak-bileti |
| LOT Polish Airlines | WAW–CDG | https://www.lot.com/pl/en/flights/flights-to-europe/flights-to-france/flights-to-paris/flights-from-warsaw-to-paris |
| LOT Polish Airlines | WAW–LHR | https://www.lot.com/pl/en/flights/flights-to-europe/flights-to-great-britain/flights-to-london/flights-from-warsaw-to-london |

**Source interpretation:** An official route-search result may contain partner-operated or connecting choices. `operating_carrier: null` and/or `service_type: unknown` record that limitation, not an unverified promise. Lufthansa and Austrian timetable views show codeshare/partner operators on some flights; do not infer the operating carrier from the LH/OS flight number alone. Pegasus's two own direct route descriptions and LOT's direct Warsaw–Paris route explicitly support their more specific flags. No flight times, prices, live dates or historical route frequency are frozen.

## Referenced airports are not full airport guides

The `data/airports/airport-index.v1.json` catalog has 34 independent airport guides and is unchanged. Eight other valid route endpoints (ADB, AYT, SAW, VIE, WAW, YUL, YVR, YYZ) are recorded in `data/airlines/route-airports.v1.json` with independent official airport/operator URLs and JSON schema validation. The Python validator accepts only these reviewed extras plus the real airport-guide index, rejecting any unknown 3-letter code. An `airport_link` is provided **only** for actual airport guide pages: an airport code's presence in the route registry never manufactures a guide or navigable link.

## Pegasus cabin bundles and paid lounge

- `cabin`: https://www.flypgs.com/en/travel-services/flight-services/flight-packages and https://www.flypgs.com/en/travel-services/flight-services/seat-selection. Light, Saver, Saver Plus and Comfort Flex are **fare/service packages**, not separate cabin classes. Cabin-bag inclusion, seats, snacks and flexibility depend on the fare and flight.
- `lounges`: https://www.flypgs.com/en/travel-services/other-travel-services/isg-lounge. Pegasus describes **discounted paid access** for qualifying passengers at Istanbul Sabiha Gokcen's Plaza Premium Lounge and other partner products. A boarding pass does not entitle everyone to free or unconditional access. Avoid frozen price or hour claims.

All **22/22 sections in each of the seven new international guides** now have official-source publication metadata. The guide count remains **27**. The 51 immutable traveler source reports, original names, timestamps, moderation/consent flags, and previously mapped 75 airline associations are not altered; `published_reviews` remains empty for those seven carriers. Android manual build policy and the offline fallback release schedule remain untouched.

## Validation and expiry behavior

`scripts/validate_airline_content.py` checks registry integrity, source URLs and all route endpoints without allowing arbitrary IATA-like codes. Python tests inject an unregistered `ZZZ` route endpoint and a duplicate registry code and demand rejection. Android and Mini App tests assert two listed routes per carrier, no synthetic review scores, and Pegasus's sourced package/lounges content. Metadata dates show *when a source was reviewed*, not an expiry or live timetable; the clients' existing thirty-day review-overdue warning still applies.
