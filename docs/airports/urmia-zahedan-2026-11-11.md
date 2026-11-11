# Urmia (OMH) and Zahedan (ZAH) airport content completion
Review date: **11 November 2026**. Branch: `content/airport-drafts-urmia-zahedan-20261111`.

This batch publishes 18 sections in each airport record. The only remaining
unpublished section in each record is `traveler-experiences`: no approved
passenger-submitted reviews are present in the repository, and no fabricated
names, visit dates, ratings or quotes were created.

## Result

| Airport | Before | Published now | Remaining unpublished |
| --- | ---: | ---: | --- |
| Urmia (OMH / OITR) | 9 published / 10 draft | 9 new sections | traveler experiences |
| Zahedan (ZAH / OIZH) | 9 published / 10 draft | 9 new sections | traveler experiences |

Newly published sections in both records:
- airport video
- terminals
- ground transport
- passenger-car parking information
- facilities
- accessibility
- lounges / CIP
- connections
- international travel

The content distinguishes **not documented in the reviewed official source**
from **not available at the airport**. Missing details are not represented as
negative facts. No parking tariff, bus timetable, gate number, lounge product,
wheelchair service guarantee, minimum connection time or live flight schedule
was invented.

## Urmia — OMH / OITR

Primary source: Iran AIM official AIP PDF
https://ais.airport.ir/documents/452631/186846229/OITR.pdf

The AIP pages are not all on the same effective date:
- AD 2.2 / AD 2.3: WEF **19 February 2026**.
- AD 2.4 / AD 2.5 passenger facilities: page marked WEF **17 April 2025**.

Evidence used:
- AD 2.1 identifies OITR as **Uromiyeh / Secondary International Aerodrome**.
- AD 2.2 places the airport **7 NM north of Uromiyeh** and identifies Iran Airports & Air Navigation Company as operator. It lists the airport website as https://uromieh.airport.ir.
- AD 2.3 lists customs and immigration as **O/R** (on request / by arrangement); this is not a promise that border services are continuously staffed for every passenger flight.
- AD 2.5 lists **taxis and buses**, first aid at the aerodrome, hospital in the city, a bank at the aerodrome, and hotels, restaurants and tourist office in the city.
- The AIP does not publish passenger-terminal numbering, a passenger floor plan, car-park capacity/tariffs, lounge/CIP details, PRM/wheelchair procedures, bus routes/timetables, or passenger connection minimum times.
- The official Iran AIM/OIBK airport and chart pages were used as supporting references:
  https://oibk.ir/fa/airports/oitr
  https://oibk.ir/fa/airports/oitr/charts
- Official airport-company public-relations video, posted by the airport-company news channel, documents a visit to the operational sections of Shahid Bakeri Urmia Airport:
  https://t.me/airportnews/42349
  The video is described as a 1:42 visit report, not a terminal map.

## Zahedan — ZAH / OIZH

Primary source: Iran AIM official AIP PDF
https://ais.airport.ir/documents/452631/186846253/OIZH.pdf

The PDF contains pages with different effective dates:
- AD 2.2 / AD 2.3 / passenger facilities AD 2.5 are marked WEF **5 September 2024**.
- AD 2.20 local traffic regulations is marked WEF **1 October 2026**.
The passenger-service table is therefore explicitly treated as the latest accessible AIP passenger-facility evidence found in this review, **not as a freshly revised 2026 passenger-service bulletin**.

Evidence used:
- AD 2.1 identifies **OIZH — Zahedan / International**.
- AD 2.2 places the airport **3 NM south-east of Zahedan** and lists Iran Airports & Air Navigation Company as operator.
- AD 2.3 lists customs and immigration as **O/R**; this must be coordinated for the relevant operation and does not guarantee service availability for every flight.
- AD 2.5 lists **taxis**, first aid, ambulance and a doctor at the aerodrome, a hospital in the city, a bank at the aerodrome, and hotels, restaurants and tourist office in the city.
- The AIP does not publish passenger-car parking capacity/tariffs, bus routes/timetables, passenger lounge/CIP details, wheelchair/PRM arrangements, or minimum passenger connection times.
- A report attributed to the Ministry of Roads and Urban Development describes domestic and international passenger terminals at Zahedan. The available copy is a secondary republication, so the guide does not infer gate numbering, terminal dimensions or current floor plans from it:
  https://gostareshsakhteman.com/city-housing-construction/134427/
- The airport public-relations channel published a 3:25 video about the terminal renovation, describing facade, paving, stairs, lighting, partitions, baggage conveyor and HVAC work:
  https://t.me/zahedanairport/10175
- The official Iran AIM/OIBK pages were used for airport identity and the current AIP chart index:
  https://oibk.ir/fa/airports/oizh
  https://oibk.ir/fa/airports/oizh/charts

## Publication and safety rules

- Parking pages explicitly distinguish passenger-car parking from the aircraft apron / APDC charts.
- Ground transport only lists transport modes actually stated in AIP; no unsupported bus service is advertised for Zahedan.
- International designation is not presented as proof of scheduled international service on a given date.
- O/R customs/immigration is explained as requiring coordination; it is not presented as 24/7 passenger processing.
- Lounge/CIP and accessibility sections say that current details were not confirmed in the reviewed AIP; they do not claim those services do not exist.
- The video blocks link to individual public Telegram posts, not generic search pages.
- Traveler-experience sections remain drafts until real passenger submissions with a visit date and rating are received and approved. No synthetic experience block is included.

## QA

- Airport JSON schema and HTTPS/source/date validator are run in CI.
- Python tests assert 18 published sections for each airport, one remaining traveler-experience draft, the official video URLs, and the absence of fabricated experience blocks.
- No airport identity, existing published section, experience record, schema, reader UI, API, database or release workflow is changed.
