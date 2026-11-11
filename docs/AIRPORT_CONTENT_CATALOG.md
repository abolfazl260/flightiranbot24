# Airport content catalog v1 — edit JSON in GitHub

## Purpose

**GitHub is the content management interface. There is no airport admin panel.**
The canonical airport identity list remains
`src/flightiran/modules/airport/data/airports.json` (29 airports).
This new `data/airports/` directory contains independent *content*
documents, keyed by IATA code, without duplicating airport identity data.

All **29 existing airports** have independent JSON content files in `details/`.
The **Imam Khomeini (IKA)** page has **14 source-backed published sections** and **two empty drafts**. The **Mashhad (MHD)** page has **17 source-backed published sections** and **two empty drafts** (traveler experiences and airport videos). The **Kerman (KER)** page has **13 source-backed published sections** and **two unpublished drafts**; see `docs/airports/KER_CONTENT_NOTES.md`. The **Urmia (OMH)** and **Zahedan (ZAH)** pages now each have **18 source-backed published sections**; only the user-generated traveler-experience section remains unpublished because no approved passenger submissions are present. Their terminal, transport, parking, facilities, accessibility, lounge, connection and international-travel sections were reviewed against AIP and airport public-relations sources; video sections link to official airport-channel posts. See [Urmia and Zahedan source audit](airports/urmia-zahedan-2026-11-11.md). The **Amsterdam (AMS), Athens (ATH), Abu Dhabi (AUH), Bangkok (BKK), Paris-CDG (CDG), and Delhi (DEL)** pages now also have their previously empty parking, lounge, and Athens connection sections completed from airport/operator sources. Each has **17 published sections** and only the two user-generated/media sections (traveler experiences and airport videos) remain unpublished. See [international airport services audit](airports/parking-lounges-batch-2026-11-11.md). The **Doha (DOH), Dubai (DXB), Frankfurt (FRA), Kuala Lumpur (KUL), London Heathrow (LHR), and Madrid (MAD)** records now also have their parking and lounge sections published from official airport/operator sources. Each has **17 published sections**; only traveler experiences and airport videos remain unpublished. See [global airport parking and lounge audit](airports/parking-lounges-global-2026-11-11.md). Other airport pages are published independently; consult `airport-index.v1.json` for the current enabled set rather than assuming a fixed allowlist. The IKA location-map entry links to the location supplied on the official website. The MHD map uses a referenced airport point, not a terminal floor plan. No unverified terminal plans, passenger reviews, videos or live flight values are published. Android and the Mini App have published airport readers. Telegram private chats
now expose the same reviewed sections through a paginated HTML widget; see
[Telegram airport widget](TELEGRAM_AIRPORT_WIDGET.md).

## Repository layout

```text
src/flightiran/modules/airport/data/airports.json  # Canonical identity list
data/airports/
  airport-index.v1.json                           # Each code and its file path
  airport-index.schema.json                       # Index JSON schema
  airport-detail.schema.json                      # Per-airport JSON schema
  details/
    THR.v1.json                                   # Mehrabad
    IKA.v1.json                                   # Imam Khomeini
    MHD.v1.json                                   # Mashhad
    ...                                           # One file for each of 29 airports
```

There is no predefined fixed feature menu. Each document contains its own
ordered `sections` array with arbitrary IDs and titles. Content for THR
never leaks into MHD. Adding a sixth or tenth section to THR does not affect
the other airports. For new *block kinds*, a new schema/app renderer version
may still be necessary; adding sections made of existing blocks requires
only updating JSON.

## Edit an airport directly in GitHub

1. Open [airport details](https://github.com/abolfazl260/flightiranbot24/tree/main/data/airports/details) (use this feature branch before PR merge).
2. Open `THR.v1.json` or the intended airport by IATA code; use GitHub's
   **Edit this file** (pencil) action.
3. Under `sections`, update only the chosen airport's fields and `blocks`.
   Existing sections are drafts until verified. Add any new section using
   the documented shape below.
4. For factual published content, add official `source_urls`, set the actual
   ISO 8601 `reviewed_at`, and use `status: "published"` only after review.
5. Commit through a pull request; CI validates JSON schema and source/date
   requirements. Set `enabled: true` for that IATA in
   `data/airports/airport-index.v1.json` only after at least one section
   is published. Its own `enabled` flag controls visibility.

A section you have not completed may remain a draft indefinitely. Draft and
archived sections must not be displayed to users. No administrator portal,
login, tokens or upload service are required to prepare content.

### Sample sixth section

Place this in `sections` for just one airport (for example THR):

```json
{
  "id": "parking",
  "title_fa": "پارکینگ",
  "icon": "car",
  "order": 60,
  "status": "draft",
  "reviewed_at": null,
  "source_urls": [],
  "blocks": []
}
```

### Sample published text section — **schema example, not airport facts**

```json
{
  "id": "passenger-guide",
  "title_fa": "راهنمای مسافر",
  "icon": "book-open",
  "order": 70,
  "status": "published",
  "reviewed_at": "2026-11-03T12:00:00Z",
  "source_urls": ["https://example.org/official-passenger-guide"],
  "blocks": [
    {"type": "text", "text_fa": "متن بررسی‌شده مخصوص همین فرودگاه."},
    {"type": "link", "title_fa": "اطلاعات رسمی", "url": "https://example.org/official-passenger-guide"}
  ]
}
```

This example contains hypothetical text and URLs and must **never** be
copied verbatim into production as real information.

## Five initial sections (editable independently)

| Section ID | Title | What belongs in the section |
| --- | --- | --- |
| `baggage-rules` | بار مجاز و قوانین حمل بار | Verified airline/route/fare-specific rules and direct official links. A blanket allowance per airport would be misleading. |
| `flight-status` | وضعیت پروازها | Static official link or `flight_board` descriptor of the existing first-party `iran_fids` source once verified. Never place live observations in GitHub. |
| `traveler-experiences` | تجربه کاربران | Only privacy-reviewed, consented, explicitly approved, anonymized experiences. Do not commit raw submissions or identity details. |
| `airport-map` | نقشه فرودگاه | Verified terminal map links/coordinates and attributed screenshots where licensed. |
| `airport-videos` | ویدیو فرودگاه | Verified HTTPS video links, description, thumbnails and attribution with reuse rights. |

These five are **starter section definitions**, not a hardcoded app menu. Each airport may
have a different subset, title, number of sections, order, or set of blocks.

### Supported content block shapes

```json
{"type": "text", "text_fa": "متن فارسی بررسی‌شده"}
{"type": "bullets", "items_fa": ["مورد یک", "مورد دو"]}
{"type": "link", "title_fa": "اطلاعات بیشتر", "url": "https://example.org/"}
{"type": "image", "url": "https://example.org/image.webp", "alt_fa": "توضیح تصویر"}
{"type": "video", "title_fa": "راهنمای سالن", "url": "https://example.org/video"}
{"type": "map", "title_fa": "مکان", "latitude": 0, "longitude": 0, "external_url": "https://example.org/map"}
{"type": "flight_board", "data_source": "iran_fids", "direction": "both"}
{"type": "experience", "id": "review-001", "text_fa": "تجربه تأییدشده", "rating": 5, "visit_date": "2026-10-01", "approved": true}
```

Block values above are **examples only**. No content should be published
without checking sources, authenticity and media rights. The schema prevents
arbitrary HTML/script blocks from being interpreted by the Android reader.

## Add more sections or airports

To add a section, directly append a new JSON object in a single airport file.
Optionally, maintainers can use the small local CLI that merely creates draft
JSON; it is **not an admin panel**:

```bash
python scripts/airport_content.py add-section THR --id parking --title "پارکینگ" --icon car --order 60
```

For a brand-new airport code, first register its identity in the canonical
`airports.json`; then:

```bash
python scripts/airport_content.py add-airport XYZ
```

If the code already exists in `data/airports/airport-index.v1.json` (all
current 29 do), do not call `add-airport`; edit its file directly.

## Validation and deployment

Run locally from the repository root:

```bash
python scripts/validate_airport_content.py
pytest tests/test_airport_content_catalog.py
```

The main CI workflow runs the Python tests on pull requests. It rejects
duplicate section IDs, unknown airports, mismatching data files, incomplete
published sections, missing factual sources and unapproved experiences.

After merging into main, production raw URLs have the form:

- `https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airports/airport-index.v1.json`
- `https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airports/details/THR.v1.json`

The Android content reader can fetch these independently when a supported
airport page is opened. The Android and Mini App readers are active. The Telegram private airport
widget reads the same versioned content copied into the bot Docker image.
This does not add a management screen or publish fake live flight data.

Versioned JSON changes should preserve compatibility for mobile clients;
new block *types* need a compatible client release. Data-backed changes to
existing supported block types do not require an APK rebuild.

## Tabriz (TBZ) source review

The TBZ page has 13 reviewed published passenger-guidance sections and two drafts
(unapproved traveler experiences and unverified passenger-guide videos).
The airport location map uses an approximate reference coordinate, not an indoor
floor plan. Current flight status, bus timetables, fares and terminal assignments
are **not** hardcoded. See [Tabriz verification notes](airports/TBZ_CONTENT_NOTES.md)
for official links and source limitations.

## GSM — Qeshm Airport

GSM (ICAO OIKQ) has an independently enabled passenger guide with 11 documented sections and two empty drafts. See [GSM editorial and provenance notes](airports/GSM_CONTENT_NOTES.md). Flight statuses and schedules are not stored as live values in GitHub.
