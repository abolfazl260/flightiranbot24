# MHD — research and verification notes

**Reviewed:** 2026-11-04 UTC. **Airport:** Shahid Hashemi Nejad International Airport, Mashhad (`MHD`, `OIMM`).

## Publication state
- Published: 17 passenger-facing sections in `data/airports/details/MHD.v1.json`: baggage, flight status, airport map, overview, terminals, metro, taxis, buses, parking, passenger checklist, facilities, baggage claims, lost property, accessibility, CIP, contacts and complaints.
- Draft: `traveler-experiences` and `airport-videos`. No consented moderated user testimonials or rights-cleared videos were available. Do not substitute invented testimonials or arbitrary video clips.
- Set `MHD.enabled = true` in the existing index. This exposes content to a compatible reader, **not** a new Android or Telegram page; airport navigation is still separately controlled.
- All publication timestamps are per section; static catalog content is not a flight tracker.

## Sources and editorial decisions
| Topic | Reference | Decision |
| --- | --- | --- |
| IATA/ICAO and location | https://centreforaviation.com/data/profiles/airports/mashhad-airport-mhd, https://oibk.ir/fa/airports/oimm | MHD / OIMM; map marker is approximate airport reference point, not terminal door |
| Aviation charts | https://oibk.ir/fa/airports/oimm/charts | Aviation charts are **not** terminal passenger floor plans |
| Actual flight status | https://fids.airport.ir/?public_airport_id=102, https://t.me/s/mashhadairport?after=4805, https://www.tasnimnews.ir/fa/news/1405/07/12/3713603/%D9%BE%D8%B1%D9%88%D8%A7%D8%B2-%D9%85%D8%B4%D9%87%D8%AF-%D9%86%D8%AC%D9%81-%D8%A8%D8%B1%D9%82%D8%B1%D8%A7%D8%B1-%D8%B4%D8%AF | Link to FIDS for airport ID 102 and provide 199 plus 051-33400019–23; no archived live observations |
| Terminals | https://blog.flysepehran.com/fa/airports/mashhad-airport/, https://www.varancip.com/%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%B4%D9%87%DB%8C%D8%AF-%D9%87%D8%A7%D8%B4%D9%85%DB%8C-%D9%86%DA%98%D8%A7%D8%AF-%D9%85%D8%B4%D9%87%D8%AF/, https://bhfars.ir/%D8%B1%D8%A7%D9%87%D9%86%D9%85%D8%A7%DB%8C-%D8%AC%D8%A7%D9%85%D8%B9-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%B4%D9%87%DB%8C%D8%AF-%D9%87%D8%A7%D8%B4%D9%85%DB%8C-%D9%86%DA%98%D8%A7%D8%AF-%D9%85/ | Persian sources agree: T1 domestic, T2 international departures, T3 international arrivals; **some English aggregator guides reverse T2/T3**, so advise checking the booked flight with airline/FIDS |
| Metro | https://t.me/s/transportmashhad?q=%23%D9%85%D8%AA%D8%B1%D9%88%D8%B4%D9%87%D8%B1, https://reylo.ir/station/mashhad-airport/, https://metro.mashhad.ir/ | Line 1 terminates at Airport station; do not hard-code service hours, prices or uninterrupted operations |
| Taxi, buses, parking | https://blog.flysepehran.com/fa/airports/mashhad-airport/, https://gashttour.ir/2021/10/23/%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%A8%DB%8C%D9%86%E2%80%8C%D8%A7%D9%84%D9%85%D9%84%D9%84%DB%8C-%D8%B4%D9%87%DB%8C%D8%AF-%D9%87%D8%A7%D8%B4%D9%85%DB%8C%E2%80%8C%D9%86%DA%98%D8%A7%D8%AF/ | General availability is documented but individual bus numbers, parking capacities and current fares are not independently verified for publication |
| Services and lost items | https://blog.flysepehran.com/fa/airports/mashhad-airport/, https://bhfars.ir/%D8%B1%D8%A7%D9%87%D9%86%D9%85%D8%A7%DB%8C-%D8%AC%D8%A7%D9%85%D8%B9-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%B4%D9%87%DB%8C%D8%AF-%D9%87%D8%A7%D8%B4%D9%85%DB%8C-%D9%86%DA%98%D8%A7%D8%AF-%D9%85/ | General facilities and claim-routing guidance only; no unverified office extensions or opening hours |
| Accessible travel | https://oibk.ir/fa/iran/regulations, https://bhfars.ir/%D8%B1%D8%A7%D9%87%D9%86%D9%85%D8%A7%DB%8C-%D8%AC%D8%A7%D9%85%D8%B9-%D9%81%D8%B1%D9%88%D8%AF%DA%AF%D8%A7%D9%87-%D8%B4%D9%87%DB%8C%D8%AF-%D9%87%D8%A7%D8%B4%D9%85%DB%8C-%D9%86%DA%98%D8%A7%D8%AF-%D9%85/ | Request assistance from the operating airline; do not equate normal accessibility with paid CIP |
| Commercial CIP | https://www.cipmhd.com/ | Link is a commercial service provider mentioning MHD; does not imply endorsement, exclusivity or mandatory purchase |
| Passenger complaints | https://gostareshsakhteman.com/city-housing-construction/20013/, https://www.caa.gov.ir/, https://farasa.cao.ir/ | Escalation to civil aviation passenger-rights portal after airline/seller follow-up |

## Reliability limitations
The official Mashhad airport homepage (`https://mashhad.airport.ir/`) and central FIDS service can be slow or unavailable to automated clients; their official/publicized links were corroborated from airport communications and third-party references. Do not interpret absence of an accessible web response as a flight cancellation or a permanent closure.

Airport terminal use, airline routes, operational restrictions, parking prices and transport services may change at short notice. Keep sources with each section and recheck claims before changing `reviewed_at`. The catalog deliberately excludes fixed baggage weights, live schedules, precise parking fees, unverifiable terminal floor-plan images and fabricated customer experiences.

## Validate
```bash
python scripts/validate_airport_content.py
pytest tests/test_airport_content_catalog.py
```
