# IFN — Isfahan Shahid Beheshti Airport verification notes

Review date: 2026-11-04 UTC.
IATA: IFN; ICAO: OIFM; locality: Isfahan, Iran.

## Source hierarchy and provenance

- Airport operator website referenced in AIP and airport guides: https://isfahan.airport.ir/. The operator's website did **not** respond reliably to direct retrieval during this research; no live assertions were inferred from it.
- Iran Airports flight-information service: https://fids.airport.ir/. The board was not retrievable in this review, so no real-time arrival/departure status, flight timetable or gate is stored in GitHub.
- Airport identity, reference-point coordinates and elevation: https://ourairports.com/airports/OIFM/. Coordinates 32.755142, 51.883877 describe the airport reference point, **not** a terminal doorway or floor plan.
- Airline-authored passenger and service guide: https://blog.flysepehran.com/fa/airports/isfahan-airport/ (Flysepehran, published 1404/06/09). It describes the separate domestic/international terminals, transport, parking, facilities, CIP and lost property. Claims are attributed, not presented as guaranteed operational availability.
- Baggage safety and restrictions: https://www.iata.org/bags/index and https://www.iata.org/en/youandiata/travelers/batteries. Baggage allowances are airline/fare/route-specific. Batteries and restricted goods require airline/local-rule confirmation.
- Contact number cross-reference: https://www.flightgate.ir/%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%A7%D8%B5%D9%81%D9%87%D8%A7%D9%86/ (updated 1403/11/16); numbers were not telephone-verified.
- Aviation regulator online-service directory: https://www.caa.gov.ir/electronic-systems; passenger-rights portal https://farasa.cao.ir/. Both were access-restricted or unavailable in the browser session. Do not promise that a complaint was submitted.
- Aviation reference for chart/current AIP discovery: https://oibk.ir/fa/airports/oifm/charts (this is an aviation-reference aggregator linking to the official AIP, not a passenger terminal plan).

## Editorial decisions and limitations

- All **20 published** sections have documented HTTPS source URLs and a review timestamp; **2 drafts** are preserved empty.
- Traveler experiences require verified original submissions, consent to publication, anonymisation and approval. No review was fabricated or copied.
- Airport video requires verified attribution and reuse rights. No video/image was republished without such authorization.
- No terminal floor plan, confirmed accessible route map, guaranteed Wi-Fi, permanent bus schedule, fare, real-time parking occupancy or CIP price was verified. Directions are general and refer readers to service operators.
- A reported bus link via Kaveh terminal is described as a potentially changing service; no timetable is hardcoded. No direct metro/rail link to the airport terminal was independently verified.
- No flight_board block is enabled: the static official flight-information link is safer until first-party integration has been independently verified.
- Contact numbers are historical published references, not checked by calling the airport.
- Airport identity stays canonical in `src/flightiran/modules/airport/data/airports.json`. Only `data/airports/details/IFN.v1.json` and the existing content index are changed; no new storage, admin panel or Android block type.

## Verification

```bash
python scripts/validate_airport_content.py
pytest tests/test_airport_content_catalog.py
```
