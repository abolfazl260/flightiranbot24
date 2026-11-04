# Remaining 20 airport passenger guides — provenance and limits

**Reviewed (UTC):** 2026-11-04T11:05:45.686Z. **Target:** all 20 previously disabled airports from the existing 29-airport identity catalog.

## Editorial policy

- No additional identity, admin, database or API is introduced. 19 previously disabled airport detail JSON files are populated in this PR; IFN was independently published on main during work and is preserved unchanged. The complete set of 29 is indexed.
- Published facts and passenger guidance are attributed by per-section HTTPS `source_urls` and `reviewed_at`. Routes, terminal allocations, fees, parking capacity, flight status, visa eligibility and service hours are not fixed as live claims.
- Official airport/operator links are preferred. Some Iranian airport official services and the Minsk airport website were unavailable for independent live retrieval; the content explicitly discloses these limitations.
- Maps based on OurAirports/OIBK are approximate geographic references, not official terminal plans; the Delhi terminal-map link is the airport's official interactive guide.
- Traveler experiences and passenger-guide videos remain unpublished drafts throughout this batch. Existing approved videos elsewhere in the repository are unaffected.
- An absent or uncertain section remains an empty draft, not an unsubstantiated published claim.

## Concurrent main changes

- IFN: existing main guide retained rather than overwritten by this batch.

## Sources and coverage by airport

| IATA | ICAO | Main source(s) | Limitations | Published | Drafts |
|---|---|---|---|---:|---:|
| AMS | EHAM | [source](https://www.schiphol.nl/en/) · [source](https://www.schiphol.nl/en/from-to-schiphol/by-public-transport/train/) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| ATH | LGAV | [source](https://www.aia.gr/en/) · [source](https://www.aia.gr/en/traveller/transportation-airport/public-transportation-airport) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| AUH | OMAA | [source](https://www.zayedinternationalairport.ae/) · [source](https://www.zayedinternationalairport.ae/en/plan-and-prepare/at-the-airport/terminal-guides) | Prices, assignments and timetables change; official latest notices supersede. | 16 | 3 |
| AWZ | OIAW | [source](https://oibk.ir/fa/airports/oiaw) | Operational facilities, ground transport or parking may be undetermined; FIDS was inaccessible. | 9 | 10 |
| BKK | VTBS | [source](https://suvarnabhumi.airportthai.co.th/?lang=en) · [source](https://suvarnabhumi.airportthai.co.th/service/way-to-airport/detail/Transportation_BKK) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| CDG | LFPG | [source](https://www.parisaeroport.fr/en/) · [source](https://www.transilien.com/en/page-lignes/ligne-b) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| DEL | VIDP | [source](https://www.newdelhiairport.in/) · [source](https://www.newdelhiairport.in/terminals) | Prices, assignments and timetables change; official latest notices supersede. | 16 | 3 |
| DOH | OTHH | [source](https://dohahamadairport.com/) · [source](https://aim.gov.qa/eaip/2026-01-22-AIRAC/html/eAIP/AD-2.OTHH-en-GB.html) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| DXB | OMDB | [source](https://dubaiairports.ae/) · [source](https://www.dubai.ae/arriving-to-dubai) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| FRA | EDDF | [source](https://www.frankfurt-airport.com/en.html) · [source](https://www.frankfurt-airport.com/en/transport-and-parking/to-from-the-airport/travel-by-train.html) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| IFN | OIFM | [source](https://oibk.ir/fa/airports/oifm) · [source](https://blog.flysepehran.com/fa/airports/isfahan-airport/) | Operational facilities, ground transport or parking may be undetermined; FIDS was inaccessible. | 20 | 2 |
| KIH | OIBK | [source](https://blog.flysepehran.com/fa/airports/kish-airport/) · [source](https://blog.flysepehran.com/fa/airports/kish-airport/) | Operational facilities, ground transport or parking may be undetermined; FIDS was inaccessible. | 13 | 6 |
| KUL | WMKK | [source](https://www.malaysiaairports.com.my/) · [source](https://www.mot.gov.my/en/aviation/infrastructure/list-of-airports/KLIA) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| LHR | EGLL | [source](https://www.heathrow.com/) · [source](https://tfl.gov.uk/modes/elizabeth-line/getting-to-and-from-heathrow-on-the-elizabeth-line) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| MAD | LEMD | [source](https://www.aena.es/en/adolfo-suarez-madrid-barajas.html) · [source](https://gestionesytramites.madrid.org/en/plan-your-trip-to-madrid/plan-your-trip/itineraries/adolfo-suarez-madrid-barajas-airport) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| MSQ | UMMS | [source](https://airport.by/) · [source](https://www.iata.org/en/services/certification/training-development/cbta-center/cbta-certified-companies/republican-unitary-enterprise-minsk-national-airport/452845/) | Official site inaccessible, bus information secondary. | 15 | 4 |
| MUC | EDDM | [source](https://www.munich-airport.com/) · [source](https://www.munich-airport.com/public-transport-260822) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| OMH | OITR | [source](https://oibk.ir/fa/airports/oitr) | Operational facilities, ground transport or parking may be undetermined; FIDS was inaccessible. | 9 | 10 |
| PEK | ZBAA | [source](https://www.bcia.com.cn/) · [source](https://www.bcia.com.cn/dtjcx.html) | Prices, assignments and timetables change; official latest notices supersede. | 15 | 4 |
| ZAH | OIZH | [source](https://oibk.ir/fa/airports/oizh) | Operational facilities, ground transport or parking may be undetermined; FIDS was inaccessible. | 9 | 10 |


## November 2026 operational correction — FRA

The airport operator confirms **Terminal 3 is operational** and that **all airlines formerly operating from Terminal 2 have moved to Terminal 3**. Terminal 3 serves gates G, H and J; passengers must verify their operating airline and current terminal before departure. The guide's `terminals`, `ground-transport` and `connections` sections cite the operator's current terminal page: https://www.frankfurt-airport.com/en/flights-and-transfer/terminal-3.html. This corrects obsolete wording that presented Terminal 2 as an active alternative.

## Recheck triggers

Re-verify each airport on airline/terminal changes, service disruptions, new transport/parking tariffs, government entry requirement changes, and airport notices. Do not advance `reviewed_at` without a real review.

## Validation

```bash
python scripts/validate_airport_content.py
pytest tests/test_airport_content_catalog.py tests/test_airport_remaining_guides.py
```
