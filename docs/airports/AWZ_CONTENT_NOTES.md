# AWZ — Ahvaz airport editorial source review

**Reviewed:** 2026-11-04 (UTC). **IATA:** AWZ. **ICAO:** OIAW. **Location:** Ahvaz, Khuzestan, Iran.

## Publication decision

- Published **17** passenger-oriented sections and retained **2** empty drafts: `traveler-experiences` (no approved, consented submission) and `airport-videos` (no licensed, verified public video for use in the airport guide).
- Existing AWZ identity is unchanged. Enabled its current v1 index entry only after populating the detail document. No administration system, new schema, new backend or unreviewed media.
- All factual published sections include a direct HTTPS source, date and user-facing caveats; no live flight values, gate/flight timetables, fixed fares or guaranteed facility opening hours.
- The location map is a **reference point**, not an official terminal floor plan.

## Provenance and evidence quality

| Claim / content | Link | Evidence assessment |
| --- | --- | --- |
| Codes AWZ / OIAW; named airport; latitude 31.3364, longitude 48.763789 | https://ourairports.com/airports/OIAW/ | OurAirports community-maintained data updated 2026-01-20; not an operational AIP |
| Terminals, passenger facilities, parking categories, roads, historical CIP description and 199 hotline | https://blog.flysepehran.com/fa/airports/ahvaz-international-airport/ | Airline-published guide dated 1402/07/22 and subsequently edited; descriptions may be outdated; do not extrapolate current availability |
| Independent airline language cross-check | https://blog.flysepehran.com/en/airports/ahvaz-international-airport/ | Same publisher, not an independent operator confirmation |
| Central airport switchboard 06134434601 | https://www.tasnimnews.ir/fa/news/1403/10/15/3231830/%D8%B4%D9%85%D8%A7%D8%B1%D9%87-%D8%AA%D9%85%D8%A7%D8%B3-%D8%AA%D9%85%D8%A7%D9%85-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D9%87%D8%A7%DB%8C-%DA%A9%D8%B4%D9%88%D8%B1 | News listing dated 1403/10/15; phone may have changed |
| Official airport homepage | https://ahwaz.airport.ir/ | Identified as official by the airline. **Direct access timed out** on 2026-11-04; current site content was not independently read |
| National flight information display | https://fids.airport.ir/ | Official domain; direct access timed out on 2026-11-04; no claim of currently reachable live board or public API |
| Airline- and route-specific baggage allowance, problems with baggage | https://www.iata.org/en/youandiata/travelers/baggage/ | IATA passenger guidance (general, not AWZ-specific) |
| Lithium battery safety | https://www.iata.org/en/youandiata/travelers/batteries | IATA passenger guidance |
| Two-power-bank maximum and no recharging power banks in flight effective 2026-03-27 | https://www.icao.int/news/new-power-bank-restrictions-will-safeguard-international-aviation?pubDate=20260427 | ICAO 2026 notice; individual airline or regulator restrictions may be more stringent |
| Wheelchair and assistive-mobility planning | https://www.iata.org/en/programs/passenger/accessibility/ | IATA guidance; does not verify actual AWZ equipment inventory |
| New CIP lounge, three-storey parking, airport hotel and garden-restaurant under construction | https://t.me/s/airportnews?after=45583 | IAC public-relations announcement relayed through airportnews channel; **not evidence of opening/completion** |
| Civil aviation complaint route | https://www.caa.gov.ir/ and https://farasa.cao.ir/ | Government portals named in repository's earlier airport notes; real-time service availability not certified |

## Important discrepancies and limitations

1. **CIP:** The older Sepehran airline article describes existing CIP reservations, while the airport company has more recently announced construction of a **new** CIP lounge. They could refer to different facilities or periods. The content intentionally does not confirm today's CIP availability, rate or booking phone.
2. **Parking:** Sepehran mentions daily and round-the-clock parking and provides old capacities. The company separately discusses an upcoming multi-storey car park. Neither those capacities nor future opening dates are published as current facts.
3. **Road/access:** Sepehran and other secondary directories use varying boulevard names. This guide offers a coordinate reference and general access routes, not a precise entrance map.
4. **Terminal operations:** The airline source describes domestic and international terminal areas, not immutable airline-to-gate assignments. No official indoor terminal map has been found.
5. **Public transport:** No official source validated a dedicated metro, railway or fixed bus service directly to the terminal, so the guide makes no claims of one. Taxi and private vehicle are described with availability caveats.
6. **Special assistance:** General IATA guidance informs passenger preparation; specific AWZ wheelchair inventory or accessibility fixtures remain unverified.
7. **User-generated content & media:** No real traveler accounts with consent or correctly licensed, independently verified airport guide videos were found; both remain drafts. No scraped review text has been copied.
8. **Live flight operations:** Check flight status directly with the operating airline and airport. FIDS and the airport website could not be reached during review; no live status was inserted.
9. **Operational updates:** These static documents are passenger orientation, not real-time operating instructions or aeronautical AIP/NOTAM advice.

## Maintenance / tests

- Edit only `data/airports/details/AWZ.v1.json` and its index entry for future AWZ publication changes.
- Re-check airport-specific claims and working links before updating each section's `reviewed_at`.
- Run `python scripts/validate_airport_content.py` and `pytest tests/test_airport_content_catalog.py tests/test_airport.py`; check Android test/build GitHub Actions before merge.
