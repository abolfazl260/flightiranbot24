# Taban Airlines and Karun Airlines — source audit
Review day: **11 November 2026**. Parent tracking issue: #172.

The v1 carrier catalog receives two separate guide files, independent
identities and reader/validator tests. The preceding 13 carriers and
historical passenger feedback/consent records are unchanged.

| Carrier | Stable ID | IATA / ICAO | Sections published / draft | Fleet families |
| --- | --- | --- | --- | --- |
| Taban Airlines | `taban-air` | **HH / TBN** | **15 / 6** (21 total) | **5** |
| Karun Airlines | `karun-air` | **NV / KRU** | **14 / 6** (20 total) | **4** |

**Publication is partial coverage**, not completeness. The six drafts
per carrier suppress unverified check-in cutoff/online availability,
seat-selection booking, onboard catering, lounge/CIP, pet carriage
and inflight connectivity. An absent visible card does **not** mean
the service is unavailable.

`verified_at=2026-11-11T00:00:00Z` is a review-day marker, **not**
the exact review time or an assertion of a policy-effective date.
No passenger ratings, reviews, licensed logos/photos, live timetables,
numeric fleet counts, seat layouts or universal fee tables invented.

## Taban: primary sources

- The official airline website **https://taban.aero/** was accessed
  directly and displays online purchase search, live-status/booking
  lookup entry points, company contacts, fleet, routes, complaint forms,
  and dated 1405 commercial and operational notices. Availability
  of payment, reservation APIs and current flight inventory was **not**
  tested. An airport independently links to this exact company domain:
  https://gzpairport.com/en-EN/flights/arrival-flights/detail/7235/16.10.2026%2C03_30/HH_1003076 .
- Official commercial bulletins are accessible at
  https://taban.aero/knowledge.asp?lang=fa&pid=36&title=%D8%A8%D8%AE%D8%B4%D9%86%D8%A7%D9%85%D9%87_%D9%87%D8%A7 .
  They list a **5 Aban 1405** domestic fare notice, a **6 Mehr 1405**
  international excess-baggage/wheelchair charges notice, and an
  earlier **23 Azar 1404** cabin baggage notice. Actual tables are
  **image/PDF attachments**, not verified machine-readable passenger
  tariff text. We link to the dated notices **without extracting or
  inventing the kilograms/charges**, and require route- and
  fare-specific reconfirmation.
- Excess baggage and wheelchair:
  https://taban.aero/knowledge.asp?lang=fa&pid=36&tid=9273&title=%D9%86%D8%B1%D8%AE_%D8%A7%D8%B6%D8%A7%D9%81%D9%87_%D8%A8%D8%A7%D8%B1_%D9%88_%D9%87%D8%B2%DB%8C%D9%86%D9%87_%D8%AE%D8%AF%D9%85%D8%A7%D8%AA_%D9%88%DB%8C%D9%84%DA%86%D8%B1_%D8%AF%D8%B1_%D9%BE%D8%B1%D9%88%D8%A7%D8%B2%D9%87%D8%A7%DB%8C_%D8%A8%DB%8C%D9%86_%D8%A7%D9%84%D9%85%D9%84%D9%84%DB%8C
  is dated **6 Mehr 1405**, but route amounts are in images;
  no flat charge is asserted.
- **Power banks (substantive and date-scoped first-party safety rule):**
  the **4 Mordad 1405** official aviation-notice transcription
  https://taban.aero/knowledge.asp?lang=fa&pid=32&tid=9247&title=title
  forbids *charging a power bank onboard*, limits personally carried
  power banks to **two** per passenger, and discourages using a power
  bank to recharge other electronics in flight.
  General lithium safety guidance from
  https://www.iata.org/en/youandiata/travelers/batteries/
  remains separate. Reconfirm any later updates at travel time.
- Official **contact and lost baggage**: home page explicitly lists
  **021-4854** (call center), **021-40441214** (support),
  sales **021-4854 extensions 101/102**, `info@taban.aero`,
  and baggage `commercial@taban.aero`. Call availability/hours
  were not directly verified. Complaints, feedback and message
  submission are publicly linked; no successful submission tested.
- **Ticket corrections and refund rules:** official bulletin pages
  https://taban.aero/knowledge.asp?lang=fa&pid=36&tid=9196&title=_%D9%85%D9%82%D8%B1%D8%B1%D8%A7%D8%AA_%D8%AC%D8%AF%DB%8C%D8%AF_crcn_%D9%87%D9%88%D8%A7%D9%BE%DB%8C%D9%85%D8%A7%DB%8C%DB%8C_%D8%AA%D8%A7%D8%A8%D8%A7%D9%86
  and
  https://taban.aero/knowledge.asp?lang=fa&pid=36&tid=9211&title=%D8%A7%D8%B5%D9%84%D8%A7%D8%AD_%D9%85%D8%B4%D8%AE%D8%B5%D8%A7%D8%AA_%D9%85%D8%B3%D8%A7%D9%81%D8%B1_%D8%AF%D8%B1_%D9%BE%D8%B1%D9%88%D8%A7%D8%B2%D9%87%D8%A7%DB%8C_%D8%AF%D8%A7%D8%AE%D9%84%DB%8C_%D9%88_%D8%AE%D8%A7%D8%B1%D8%AC%DB%8C
  show 1404 circulars with image attachment restrictions;
  **no current penalty percentages or blanket refund rights**.
- Fleet: the official page
  https://taban.aero/knowledge.asp?ctype=fleet&lang=fa&title=%D9%85%D8%B9%D8%B1%D9%81%DB%8C_%D9%86%D8%A7%D9%88%DA%AF%D8%A7%D9%86
  lists MD-88, Boeing 737-400 and A310 with undated counts,
  while https://www.planespotters.net/airline/Taban-Airlines
  separately shows historic A319 and Boeing 737-300 records.
  The 2026 Iran AIM officially notified aircraft-operator ICAO code
  is **TBN**; `TBM` appears only as a *historical registry code*,
  not a second current ICAO identity:
  https://oibk.ir/fa/iran/airlines .
  Five model snapshots retain `count:null`,
  `status:unknown`, `relationship:unknown`, and
  `configuration_fa:null`.
- Route announcements at https://taban.aero/ include sample month
  counts/paths such as Mashhad–Tehran and Tehran–Istanbul; those
  numbers **are not an independently checked future live schedule**.
  The flight detail at the independent Gazipasa Airport is a
  dated October 2026 movement, not a future guarantee.

## Karun: evidence and crucial limitations

- **Official Iran AIM operator code KRU** and callsign KARUN:
  https://oibk.ir/fa/iran/airlines/kru , published from the official
  10 June 2026 ICAO designators notified by Iran.
- Airline industry sources
  https://centreforaviation.com/data/profiles/airlines/karun-airlines-nv
  and https://www.planespotters.net/airline/Karun-Airlines
  show **IATA NV / ICAO KRU**, commercial name Karun Airlines and
  predecessor **Iranian Naft Airlines**. They describe Ahvaz and
  Tehran hubs and a mix of charter/scheduled operations historically;
  we make **no currently-bookable route or carrier safety claim**.
- `https://karunair.ir/` is the company domain listed by
  Planespotters. It returned **403 Forbidden** in the public web
  reader, and `https://www.karunair.ir/` was also inaccessible.
  These are access failures in this environment, **not proof** that
  booking/payment or its site is down globally.
  Consequently **no present-day first-party baggage number,
  refund penalty percentage, check-in/online seat entitlement,
  lounge, pet-cabin policy, hotline number or medical acceptance
  guarantee** was published.
- Four model families:
  Boeing 737-300, Boeing 737-500, Fokker 50 and Fokker 100 are
  documented in Planespotters' September 2026 snapshot. The ICAO
  operator's linked aircraft-registration count and the independent
  fleet's active/parked/total classifications are **not
  interchangeable**. Each model count, operating status, ownership
  and configuration is unknown in this guide.
- General IATA baggage, battery, rights and travel sources
  may guide questions for the airline, **not establish a Karun
  allowance**:
  https://www.iata.org/en/youandiata/travelers/baggage/ ;
  https://www.iata.org/en/youandiata/travelers/batteries/ ;
  https://www.iata.org/en/youandiata/travelers/passenger-rights/ ;
  https://www.iata.org/en/travel-centre .

## Validation, rollout, security and rollback

- Added 2 identities and per-carrier JSON detail datasets. Now
  **15** independent published index records. Date/source gates
  and `operating_carrier` scoping remain unchanged. Historical
  passenger reviews/consent and all other carriers/airports are untouched.
- Six suppressed drafts for both; Taban's 15th published section is
  independent official survey/complaints guidance. No unapproved
  image, fake source attribution, credentials or ad/affiliate links.
- Python tests assert 15 IDs, publication snapshots, HH/TBN and NV/KRU,
  historical-code distinction, exact draft suppression, safe links
  and null aircraft fields. Android bundled assets and Cloudflare
  Mini App tests verify independent parsing and search aliases.
- Require airline validator and CI (Python, Cloudflare, Android
  unit/lint/androidTest Kotlin compile) to pass before merge.
- **No** Android build workflow, signing, release trigger, schema,
  database, new UI block, API or consent workflow change. Manual
  APK build remains the only way to update already-installed
  bundled offline data. App release/accessibility, real-device RTL
  and deployed CDN cache still require separate testing.
- Revert only this PR to roll back both guides without altering
  previous carrier records. Leave #172 open for current Karun
  primary-source fare checks and further airlines.
