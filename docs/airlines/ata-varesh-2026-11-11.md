# ATA Airlines and Varesh Airlines — source audit, 11 November 2026

Parent: #172. Two independent v1 guides and index records added to the
seven+two existing airline catalog; previous nine airline details, airport
guides and moderated passenger feedback were **not modified**.

| Carrier | Stable ID | Codes | Published / draft | Fleet model families |
| --- | --- | --- | --- | --- |
| ATA Airlines | `ata-air` | IATA **I3**, ICAO **TBZ** | **16 / 4** | A320, 737-300, 737-500, MD-82, MD-83, MD-87, historical ERJ-145 |
| Varesh Airlines | `varesh-air` | **ICAO VRH**; IATA unverified/unlisted | **18 / 2** | 737-300, 737-500, historical A320-200 |

**Important:** ATA's ICAO designator `TBZ` also happens to be the IATA
airport code for Tabriz. The contexts are separate: codes are always
tagged with the system in our index. CAPA, Planespotters and
Flightradar24 currently show **no IATA designator for Varesh**. No
fictional `VR` or other placeholder is published.

All `verified_at:2026-11-11T00:00:00Z` marks review day, **not**
a stated policy-effective date. Unverified onboard amenities are
not represented as definitively unavailable. No synthetic reviews,
ratings, live timetables, operational fleet sizes, aircraft ownership,
availability guarantees or copyrighted images were added.

## ATA — primary-source passenger information

- **Official website, booking, refunds and ticket validation**
  https://ataair.ir/ lists the carrier's `app.ataair.ir` engine,
  refund and verification functions and public forms.
- **Carrier rules, updated 10 Aban 1404 on the page:**
  https://ataair.ir/قوانین-و-مقررات-آتا/
  This is *not* a newly effective 1405 policy.
  The displayed economy/main seat allowance is **20 kg domestic /
  25 kg international**, **10 kg infant**, with a stated
  **15 kg Embraer exception**. Cabin baggage is stated as
  **6 kg** and **35×55×25 cm**, max combined dimension **115 cm**.
  These are **dated carrier guidance** and must be reconfirmed
  against the itinerary, fare, operating aircraft and any newer
  contract. No all-route excess-baggage fee is inferred.
- The same carrier page covers checked bag incident reporting,
  ID/passport matching, unaccompanied children (ages 6–12 under
  published procedure), pre-declared medical and pregnancy
  assistance, and domestic pet/bird transport with species,
  cage, vaccine documentation and aircraft-specific restrictions.
  These statements are **not** medical advice, a legal guarantee,
  admission permission or proof of currently offered Embraer service.
- **FAQ from Bahman 1402:**
  https://ataair.ir/سوالات-متداول/
  describes airport check-in and a route-and-delay-specific refund
  workflow requiring station approval. Historical examples cannot
  establish live online check-in availability or unconditional refunds.
- **Baggage information:** https://ataair.ir/اطلاعات-بار/
  distinguishes prohibited items, conditional items and cabin items.
  International lithium guidance is separately linked.
- **Carrier contact:** https://ataair.ir/تماس-با-ما/
  shows `0214855` (Tehran), reservation extensions 2131/2133, and
  `04132613330` (Tabriz). Hours and successful phone connection
  are not independently verified; numbers are represented as
  company-page contacts only.
- **Historical official fleet description:**
  https://ataair.ir/ناوگان-هوایی/
  includes an undated/current-worded claim of 16 aircraft on
  a page last edited in 1401. **This is not a verified live 2026
  in-service fleet number.** Planespotters (as of 27 Sep 2026)
  https://www.planespotters.net/airline/ATA-Airlines-Iran
  distinguishes 23 in fleet with parked/active records and
  other historic models. The guide records **seven model families**
  with `count:null`, `status:"unknown"`,
  `relationship:"unknown"`, `configuration_fa:null`.
  No safety ranking inferred from model age or registration.
- **Code cross-check:** Planespotters shows I3/TBZ and Iran
  2026 official operating-agency registry records ICAO TBZ:
  https://oibk.ir/iran/airlines .
- Historic schedules in the company's public channel
  https://t.me/s/ataair_ir include Tehran/Tabriz/Mashhad routes.
  They are **not current recurring schedules**. Our network
  section links preexisting airport guides only.

## Varesh — primary-source passenger information

- The company site **https://vareshair.ir/** was reachable, with
  direct passenger pages for booking, luggage, wheelchair, pets,
  medical, unaccompanied children, loyalty and catering.
  Aviation directories identify the additional declared domain
  `vareshairline.com`, but that domain could not be opened in our
  environment. This does not establish a platform-wide outage or
  invalidate the accessible `.ir` carrier website.
- **Baggage:** https://vareshair.ir/html/item/559
  displays **20 kg domestic economy**, **20–30 kg international
  economy** (a *range*, not one entitlement), **40 kg premium
  economy**, **5 kg hand baggage** and maximum
  **22×40×55 cm** cabin size. The page has no independently
  verified policy-effective date. A ticket's fare and confirmed
  itinerary-specific allowance must be checked; no fixed
  all-route extra charge is invented.
- **Wheelchair:** https://vareshair.ir/html/item/647
  lists requesting at the airport, up to 2h prior for domestic /
  3h prior for international, capacity limitation, domestic
  free service, international route-based charges and hotline
  `02149743` extension **141**. These figures are not a
  guarantee of acceptance or a statement of a 2026 effective
  date. Specific device/battery and medical requirements must
  be separately confirmed.
- **Pets:** https://vareshair.ir/html/item/562
  requires prior airline coordination, a secure ventilated cage,
  veterinary certificate, vaccines and destination permits.
  Species, cabin vs hold, size and availability vary; the
  published page does not guarantee all cats/dogs are accepted
  in cabin or for free.
- **Booking:** https://vareshair.ir/html/item/558
  describes ticket issuance and provides **02149743**, sales
  extensions **366/367**. The site links an online check-in
  entry, but a completed live check-in transaction was not
  tested; no universal cutoff or route eligibility asserted.
- **Loyalty:** https://vareshair.ir/club
  documents points/tier-specific luggage and fare/date-change
  benefits and restrictions. We do **not** present elite perks
  as automatic rights for every ticket.
- **Catering:** https://vareshair.ir/html/item/1000
  describes the operator's Vareng catering company; not an
  itinerary-specific meal/menu guarantee.
- **Fleet:** https://www.planespotters.net/airline/Varesh-Airlines
  classifies Boeing 737-300/737-500 and historical A320-200,
  whereas https://data.flightradar24.com/data/airlines/vrh
  groups aircraft differently and the Iranian registry
  https://oibk.ir/fa/iran/airlines includes only registered
  aircraft associated with the carrier. Four different
  methodologies should not be conflated into an operating
  fleet count, so three family snapshots have null counts and
  unknown status/ownership.
- **Identity:** Iran's 2026 operating-agency registry
  https://oibk.ir/fa/iran/airlines confirms **VRH**;
  https://centreforaviation.com/data/profiles/airlines/varesh-airlines-vrh
  and Planespotters say **IATA: n/a/blank**.
  We only publish an ICAO code, never guess the IATA code.
- **Network:** published carrier destination examples and
  independent dated flights illustrate locations but are not
  imported as `route_snapshot` without current timetable
  confidence.

## General references, not carrier-specific policies

- https://www.iata.org/en/youandiata/travelers/batteries/
- https://www.iata.org/en/youandiata/travelers/passenger-rights/
- https://www.iata.org/en/travel-centre

These general standards do not supersede an operating carrier's
specific baggage, reimbursement, battery, medical or border policy.

## Technical compatibility, tests and rollback

Two separate version-1 details and two index identities use the
existing Android and Mini App parsers and supported blocks. Each
published section has HTTPS source URLs and scoped review date;
drafts have empty bodies; every policy section is scoped to its
own operating carrier with `seller:unknown`. All nine earlier
entries remain byte-for-byte unchanged. No APIs, schema version,
database, live feedback consent logic or moderation were changed.

Tests must assert 11 registered identities; ATA 16/4 and Varesh
18/2 publication states; ATA 7/Varesh 3 null-count fleet family
snapshots; no active timetable/route claims; no invented ratings;
search aliases and no fabricated Varesh IATA designator. Run
existing Python, Android (unit/lint/androidTest compile), Cloudflare
and content validator workflow suites. Real-device RTL,
accessibility, offline and actual remote cache deployment require
separate checks.

Android APK/AAB workflows remain **manual dispatch on `main`**;
merging content does not sign or publish an app. Revert this PR
alone to roll back both guides without touching original archives.
Keep issue #172 open for further carrier coverage and verified
current fare rules.
