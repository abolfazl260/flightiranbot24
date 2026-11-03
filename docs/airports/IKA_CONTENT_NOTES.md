# IKA — editorial and data verification notes

**Reviewed:** 2026-11-03 UTC. **Airport:** Imam Khomeini International Airport (`IKA`, `OIIE`).

## Publication state

- Published: 14 reviewed sections, including baggage rules, official flight-status lookup, airport location map, terminals, metro, taxi, parking, passenger guidance, facilities, damaged/lost baggage, lost property, CIP, contacts and complaints.
- Draft: `traveler-experiences` (no consented moderated testimony supplied), and `airport-videos` (no verified reusable passenger guide video supplied).
- Enabled in `data/airports/airport-index.v1.json`; this does **not** expose an airport UI because Android airport navigation remains disabled.
- The location map is a **link to the official website's selected Google Maps place**, not a terminal floor plan or gate-level map.
- Live flight status is **not stored or claimed**; the linked airport board should be consulted directly. The existing first-party FIDS path is not assumed functional for IKA.
- The airport publishes **no generalized universal baggage allowance**. Checked baggage weight/number and cabin-baggage limitations need independent confirmation with the operating airline and fare class.
- Metro operating times and parking/taxi fees are not hard-coded; they change and must be checked before travel.
- Source references and the UTC review timestamp are stored in **each published section**, so sections can be rechecked independently.

## Primary official references

All below are pages linked from the official **[IKAC passenger site](https://www.ikac.ir/)**.

| Category | Official reference |
| --- | --- |
| Terminals | https://www.ikac.ir/fa-IR/airport.ikac/5206/ |
| Airport flight-status page | https://www.ikac.ir/fa-IR/airport.ikac/5257/ |
| Baggage guidance | https://www.ikac.ir/fa-IR/airport.ikac/5076/page/%D9%85%D9%82%D8%B1%D8%B1%D8%A7%D8%AA-%DA%86%D9%85%D8%AF%D8%A7%D9%86 |
| Baggage claims | https://www.ikac.ir/fa-IR/airport.ikac/5077/page/%D8%A7%D9%85%D9%88%D8%B1-%D8%AC%D8%A7%D9%85%D9%87-%D8%AF%D8%A7%D9%86 |
| Metro | https://www.ikac.ir/fa-IR/airport.ikac/5082/page/%D9%85%D8%AA%D8%B1%D9%88 |
| Airport taxi | https://www.ikac.ir/fa-IR/airport.ikac/5083/page/%D8%AA%D8%A7%DA%A9%D8%B3%DB%8C |
| Parking | https://www.ikac.ir/fa-IR/airport.ikac/5085/page/%D9%BE%D8%A7%D8%B1%DA%A9%DB%8C%D9%86%DA%AF-%D9%87%D8%A7 |
| CIP | https://www.ikac.ir/fa-IR/airport.ikac/5052/page/%D8%AE%D8%AF%D9%85%D8%A7%D8%AA-CIP |
| Lost property | https://www.ikac.ir/fa-IR/airport.ikac/5254/page/%D8%AA%D8%AD%D9%88%DB%8C%D9%84-%D8%A7%D8%B4%DB%8C%D8%A7%D8%A1-%D8%AC%D8%A7%D9%85%D8%A7%D9%86%D8%AF%D9%87 |

## Maintenance

Update `data/airports/details/IKA.v1.json` directly in GitHub.
For each changed published section, recheck every operational claim against
an official current source, update `reviewed_at` to the actual check time and
retain the source in `source_urls`. If a claim can no longer be supported,
correct it or revert the section to `draft`. Never invent testimonials or
copy media assets without reuse rights. Details may change during operational
disruptions, airline changes and terminal reassignments.
