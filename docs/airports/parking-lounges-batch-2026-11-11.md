# International airport parking, lounge and transfer guides
Review date: **11 November 2026**. Batch branch:
`content/airport-parking-lounges-europe-asia-20261111`.

This batch publishes **10 previously empty sections** across six airport
records. Each of the six airports now has **17 published sections**; only
`traveler-experiences` and `airport-videos` remain drafts. No user reviews,
ratings or video assets were fabricated.

## Summary

| Airport | Newly published sections | Remaining drafts |
| --- | --- | --- |
| Amsterdam Schiphol (AMS) | parking, lounges | traveler experiences, airport videos |
| Athens (ATH) | lounges, connections | traveler experiences, airport videos |
| Zayed International, Abu Dhabi (AUH) | parking | traveler experiences, airport videos |
| Suvarnabhumi, Bangkok (BKK) | parking, lounges | traveler experiences, airport videos |
| Paris Charles de Gaulle (CDG) | parking, lounges | traveler experiences, airport videos |
| Indira Gandhi, Delhi (DEL) | parking | traveler experiences, airport videos |

## Sources and content

### Amsterdam Schiphol (AMS)

- Official parking catalogue: https://www.schiphol.nl/en/parking/
- Official lounge and airline-lounge guide:
  https://www.schiphol.nl/en/page/airline-lounges/
- Official description of Lounge 1–4:
  https://www.schiphol.nl/en/at-schiphol/schiphol-s-lounges-and-piers/

The parking guide distinguishes P1 short-stay (2–6 minute walk), P3 long-stay
(sheltered/unsheltered, 24/7 free shuttle approximately every 10 minutes),
P6 valet and P12. P12 and valet require reservation; current rates and
availability are left to the live official booking page.

The lounge guide distinguishes the post-security commercial areas named
Lounge 1–4 from airline and Privium lounges. It names Privium, KLM Crown and
Aspire locations without promising access to every ticket holder. Airline,
membership and flight eligibility remain controlling.

### Athens International Airport (ATH)

- Official business-lounge directory and hours:
  https://www.aia.gr/en/traveller/services-facilities-airport/business-lounges-airport
- Official transfer/connecting-flight guide:
  https://www.aia.gr/en/traveller/connecting-flights

The lounge guide covers the official directory for non-Schengen Area A,
Schengen Area B and the satellite terminal. Hours are transcribed as
published by AIA but may vary with operating schedules; eligibility and
price must be confirmed with the airline or lounge operator.

The connection guide preserves the airport's actual transfer instructions:
A1–A27 and B1–B31 are in the main terminal; C15–C40 are in the satellite
terminal. Transfer desks, CUSS/web check-in, baggage reclaim and customs
steps are described. AIA explicitly limits its minimum connecting times
to through-booked itineraries with baggage checked through to the final
destination. Self-made connections and baggage re-check require extra time.

### Zayed International Airport, Abu Dhabi (AUH)

- Official parking and pre-booking:
  https://www.zayedinternationalairport.ae/parking-and-transport/parking/pre-book-parking
- Official valet parking:
  https://www.zayedinternationalairport.ae/parking-and-transport/parking/valet-parking

The official airport lists approximately 3,380 parking spaces, 24-hour
operation and a 2–5 minute walk to the terminal. Long-stay parking requires
pre-booking; short-stay pre-booking is advised but not mandatory. The guide
also covers designated pick-up/drop-off and accessible parking, and keeps
valet as a separate product. Rates are not duplicated in static content;
the official booking page remains authoritative for current prices.

### Suvarnabhumi Airport, Bangkok (BKK)

- Official parking rates:
  https://suvarnabhumi.airportthai.co.th/service/transportation/detail/58
- Official parking-zone directory:
  https://suvarnabhumi.airportthai.co.th/service/airport-guide/detail/All_parking_zones_at_Suvarnabhumi_Airport
- Official lounge directory:
  https://suvarnabhumi.airportthai.co.th/service/facility/detail/230

The parking guide distinguishes public multi-storey/open zones 2–7 from
long-term Zone A and the Public Transportation Center Zone D. It notes the
official 15-minute free period and explains that fees depend on duration
and vehicle type, without hard-coding rates that can change.

The lounge guide names Miracle and The Coral as well as major airline
lounges and describes their concourse-based locations. Some international
lounges are listed as 24-hour while domestic operations are listed with
daytime hours; travellers must verify the exact lounge, gate area and
eligibility on the official directory before proceeding airside.

### Paris Charles de Gaulle (CDG)

- Official Paris Extime parking booking:
  https://www.extime.com/en/paris/car-parks
- Official Extime lounge directory:
  https://www.extime.com/en/paris/services/extime-lounge

The parking guide links to the official operator's terminal-aware booking
flow and tells travellers to select CDG and the correct terminal. It does
not copy changing tariffs into static airport content.

The lounge guide identifies Extime Lounge at Terminal 1 and Terminals 2B/2D,
with buffet, Wi-Fi and shower options. The published hours are the operator's
current listing and may change seasonally; access is only for eligible
flights in the relevant terminals.

### Indira Gandhi International Airport, Delhi (DEL)

- Official airport parking page:
  https://www.newdelhiairport.in/parking
- Official airport lounge page:
  https://www.newdelhiairport.in/encalm-lounge

The airport's official site lists visitor parking at T1, T2 and T3, with
24-hour operation and tariffs varying by terminal, vehicle type and stay
duration. Static content does not repeat the rate table; the live official
page is the source for current charges and Park & Fly conditions.

The airport's official lounge guide lists domestic lounges across T1/T2/T3,
an international lounge at T3 and transit lounges at T3 arrivals, including
nap and shower facilities. It explains that walk-in, eligible bank-card
and membership access options differ by lounge and provider. Prices are
not duplicated in the static airport file.

## Publication rules

- Prices, availability, opening hours and parking inventory can change;
  the guide points users to official live pages rather than treating the
  snapshot as a guaranteed quote.
- Lounge-area names are not confused with airline or paid lounge products.
- Transfer minimum times are not generalized beyond the airport's stated
  eligibility conditions.
- No terminal-specific parking or lounge access is promised without
  checking the flight's terminal and the operator's current terms.
- User experiences remain drafts until real, consented and approved
  passenger submissions exist. No fabricated ratings or quotes were added.
- Airport video sections remain drafts until an airport-specific,
  rights-safe and relevant video source is verified.

## QA

- JSON schema/source/date validation and the Python test suite are required.
- New tests verify the 10 sections are published with source URLs and
  review timestamps, while user experiences and airport videos remain
  unfilled rather than fabricated.
- No airport identity, schema, UI, API, database, Android release workflow
  or existing passenger-review data is changed.
