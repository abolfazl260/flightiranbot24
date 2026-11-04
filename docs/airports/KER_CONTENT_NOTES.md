# KER — editorial and data verification notes

**Reviewed:** 2026-11-04 UTC. **Airport:** Ayatollah Hashemi Rafsanjani International Airport, Kerman (`KER`, `OIKK`).

## Publication decision

- Published **13 sections**: baggage rules, flight-status lookup, airport location map, overview, terminals, city access, parking, facilities, passenger checklist, baggage claims, lost property, contacts and passenger complaints.
- `traveler-experiences` remains a draft: there are no consented, moderated and approved testimonials in this repository.
- `airport-videos` remains a draft: no verified, reusable airport-guide video, licensing or attribution has been provided.
- The KER catalog entry has `enabled: true` because verified sections are published. This prepares data availability but **does not itself enable Android or Telegram airport navigation**.
- Flight statuses, check-in times, parking tariffs, parking occupancy, airline destinations, and terminal assignments are **not stored as live facts**.
- The map points to the public airport coordinates, **not** an indoor floor plan or confirmed gate-level map.
- General battery and baggage safety advice is not an airline-specific allowance or a replacement for current aviation requirements.

## Sources and evidence assessment

| Topic | Source | Editorial judgement |
| --- | --- | --- |
| IATA / ICAO codes, coordinates, elevation | https://ourairports.com/airports/OIKK/ | Established reference data (OurAirports), not official operational AIP |
| Airport aeronautical reference | https://airportguide.com/airport/info/KER | Cross-check only; not an AIP/NOTAM substitute |
| Terminals and general access | https://www.flightgate.ir/%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%DA%A9%D8%B1%D9%85%D8%A7%D9%86/ | Travel directory information, last checked in editorial review; terminal names/positions require travel-day confirmation |
| Taxi and estimated city distance | https://www.mysafar.com/mag/travel-facts/kerman-airport/ | Secondary travel guide; route and fare remain variable |
| New passenger hall (Bahman 1399 / February 2021), parking development | https://www.tasnimnews.ir/fa/news/1399/11/20/2448839/%D8%A8%D8%A7%D9%86%D8%AF-%D8%AF%D9%88%D9%85-%D9%88-%D8%B3%D8%A7%D8%AE%D8%AA%D9%85%D8%A7%D9%86-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%DA%A9%D8%B1%D9%85%D8%A7%D9%86-%D8%A7%D9%81%D8%AA%D8%AA%D8%A7%D8%AD-%D8%B4%D8%AF | Historical opening announcement, not proof of today's parking capacity |
| Terminal facilities listed historically | https://gashttour.ir/2021/10/30/%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%A8%DB%8C%D9%86-%D8%A7%D9%84%D9%85%D9%84%D9%84%DB%8C-%DA%A9%D8%B1%D9%85%D8%A7%D9%86/ | Older secondary source; all amenities expressly subject to current verification |
| Airport contact switchboard | https://www.tasnimnews.ir/fa/news/1403/10/15/3231830/%D8%B4%D9%85%D8%A7%D8%B1%D9%87-%D8%AA%D9%85%D8%A7%D8%B3-%D8%AA%D9%85%D8%A7%D9%85-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D9%87%D8%A7%DB%8C-%DA%A9%D8%B4%D9%88%D8%B1 | Published number: 03432110113 |
| Flight status / 199 hotline | https://www.tasnimnews.ir/fa/news/1405/04/11/3631471/%DA%A9%D8%A7%D9%87%D8%B4-%D8%AF%DB%8C%D8%AF-%D8%AF%D8%B1-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%DA%A9%D8%B1%D9%85%D8%A7%D9%86-%D9%BE%D8%B1%D9%88%D8%A7%D8%B2-%D8%AA%D9%87%D8%B1%D8%A7%D9%86-%D8%AF%D8%B1-%D8%B4%DB%8C%D8%B1%D8%A7%D8%B2-%D8%A8%D9%87-%D8%B2%D9%85%DB%8C%D9%86-%D9%86%D8%B4%D8%B3%D8%AA | Quotes Kerman airport manager (1405/04/11) directing passengers to 199 |
| National FIDS | https://fids.airport.ir/ | Public national status portal; no claim of current availability or programmatic API |
| Dangerous goods / power banks | https://www.easa.europa.eu/en/light/topics/dangerous-goods-when-flying and https://www.iata.org/contentassets/90f8038b0eea42069554b2f4530f49ea/guidance-to-operators---power-banks.pdf | General safety sources; airline, local security and current ICAO rules prevail |
| Complaints | https://farasa.cao.ir/ and https://www.caa.gov.ir/ | Iran Civil Aviation Organization passenger-rights route; availability may vary |

## Quality caveats

1. The airport-specific official site `https://kerman.airport.ir/` is identified by independent directories but could not be fetched during this review; **no claim of its current accessibility** is made. No live flight board data is scraped.
2. Public reports vary in the street address wording (e.g. Boulevard Jomhouri versus Boulevard Imam Khomeini). The published content uses approximate access guidance and a coordinate map rather than an unverified precise postal address.
3. Terminal facilities were described in earlier reports; their daily opening hours and availability have not been directly revalidated with the airport operator. No precise taxi fares, parking rates or floor plans are claimed.
4. The status hotline and relevant website can be subject to network or operational interruptions; travelers should verify with their operating airline before making time-sensitive travel decisions.
5. This content is designed for passengers; aeronautical flight planning must use official current AIP/NOTAM documentation.

## Future maintenance

Edit `data/airports/details/KER.v1.json` directly. Re-verify published factual statements and links before changing them, then update the section-specific `reviewed_at`. Keep the two unverified media/review sections in draft until permission, quality and authenticity are confirmed. Run `python scripts/validate_airport_content.py` and `pytest tests/test_airport_content_catalog.py` before release.
