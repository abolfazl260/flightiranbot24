# KIH — Kish International Airport: verification notes

**Reviewed:** 2026-11-04 UTC. **IATA:** KIH. **ICAO:** OIBK.

## Editorial rules
- Airport identity already exists in the 29-airport canonical catalog. The existing `KIH.v1.json` draft is to be updated, not duplicated.
- Publish only sourced guidance. Never put live flight statuses, promised fares, guaranteed check-in/terminal assignments or timetable values in the JSON.
- New passenger terminal opened in 1402; pre-opening terminal/parking descriptions are historical. Current allocation must be confirmed with the airline.
- Airport coordinates are a community-derived geographical reference; they are not an indoor passenger map.
- Videos require usage permission, and traveler experiences require demonstrable consent and moderation. Both remain draft.
- Accessibility layout, parking prices, exact operating hours and current direct airport-phone reachability are not independently verified.
- The operator’s public company phone is not represented as a flight-information hotline.

## Sources
- Operator and current news: https://kishports.com/
- Official operator contact: https://kishports.com/?page_id=832
- Operator announcement (11 Aban 1405): https://kishports.com/?p=8612
- Airline guide (published 1402/04/05, potentially outdated): https://blog.flysepehran.com/fa/airports/kish-airport/
- Airline historical terminal migration: https://t.me/s/KishAir?before=1163
- Community aviation reference for KIH/OIBK and airport reference point: https://oibk.ir/fa/airports/oibk
- ICAO 2026 power-bank safety information: https://www.icao.int/news/new-power-bank-restrictions-will-safeguard-international-aviation?pubDate=20260427
- Airport site: https://kishairport.ir/ (reachable landing page; live board content not independently readable)

## Checks
`python scripts/validate_airport_content.py` and `pytest tests/test_airport_content_catalog.py`.
