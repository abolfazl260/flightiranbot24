# Airport content catalog v1 (GitHub-managed, per-airport)

## Purpose and current release status

The canonical list of 28 airport identities is already at
`src/flightiran/modules/airport/data/airports.json`. **Do not move, replace,
or duplicate its authority.** The new `data/airports/` directory registers
optional *content pages*, keyed by IATA airport code. The Android airport
entry point currently displays "coming soon"; this content feature does not
enable that route, Telegram airport menus, live feeds, or user submissions.

All five requested Mehrabad (THR) sections are present as **empty drafts**.
No unsupported facts, reviews, photos, videos, map coordinates, or live
flight data have been fabricated.

## How it works

- `airport-index.v1.json` lists airports with content pages, a safe relative
  detail path, and `enabled` flag. It is not another airport identity list.
- `details/THR.v1.json` is one independent content document for Mehrabad.
  Every document has an ordered array of sections; sections may differ across
  airports. Draft and archived sections must not be displayed.
- A section has an arbitrary unique `id`, Persian `title_fa`, `icon`,
  `order`, `status`, `reviewed_at`, `source_urls`, and `blocks`.
- **No five-section limit:** add a sixth, tenth or entirely different section
  to one airport without adding it to others.
- Block types currently available: `text`, `bullets`, `link`, `image`,
  `video`, `map`, `flight_board`, and `experience`. New sections made of
  these primitives require only new JSON. A brand-new interactive block type
  needs a schema/client-renderer version update.
- Each airport document is fetched **only when requested** and can fall back
  to a bundled snapshot in the future UI. JSON is public; no credentials,
  private user data or unmoderated submissions may be stored here.

## Adding an airport or section

From the repository root:

```bash
python scripts/airport_content.py add-airport MHD
python scripts/airport_content.py add-section THR --id parking --title "پارکینگ" --icon car --order 60
python scripts/validate_airport_content.py
pytest tests/test_airport_content_catalog.py
```

Then edit `data/airports/details/THR.v1.json` via a GitHub pull request.
For example, a **sample structure only** for a sixth section:

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

To publish a real section, add verified content in `blocks`, link to its
source(s) in `source_urls`, set a genuine ISO 8601 `reviewed_at`, and change
`status` to `published`. Finally set the airport's `enabled` to `true`
in `airport-index.v1.json` (only when at least one section is published).
The validator rejects published factual content without attribution,
unapproved traveler experiences, invalid URLs, duplicate section IDs, unknown
airport codes and enabled empty pages. CI runs the checks on every PR.

### Five starter sections and their intended data

| Section ID | Data to register | Rules |
| --- | --- | --- |
| `baggage-rules` | Airline-specific baggage rules, applicable routes and official links via text/bullets/link blocks | Do **not** assert one blanket baggage allowance per airport; record airline, fare/route scope and last review |
| `flight-status` | Declarative `flight_board` block for a first-party integration once reliable, or an official `link` | Never manufacture departure times or call arbitrary remote APIs from a JSON block. Existing `IranFidsRepository` uses the project's first-party endpoint, with freshness checks |
| `traveler-experiences` | Individually moderated `experience` blocks | Obtain consent for publication, remove identifying data, set `approved: true` only after review; public GitHub is **not** a submission inbox |
| `airport-map` | Verified coordinates and a public HTTPS map link in a `map` block; optional image with rights | Verify terminal and map location, license and update date |
| `airport-videos` | `video` blocks: descriptive title, public HTTPS video URL and optionally a thumbnail/credit | Use legally hosted media, no autoplay/embedded script or private links |

### Example block shapes (documentation examples, not published content)

```json
{"type": "text", "text_fa": "متن تأییدشده با منبع"}
{"type": "bullets", "items_fa": ["مورد اول", "مورد دوم"]}
{"type": "link", "title_fa": "منبع رسمی", "url": "https://example.org/"}
{"type": "image", "url": "https://example.org/terminal.webp", "alt_fa": "نمای ترمینال"}
{"type": "video", "title_fa": "راهنمای ترمینال", "url": "https://example.org/video"}
{"type": "map", "title_fa": "ورودی ترمینال", "latitude": 0, "longitude": 0, "external_url": "https://maps.example.org/"}
{"type": "flight_board", "data_source": "iran_fids", "direction": "both"}
{"type": "experience", "id": "review-001", "text_fa": "تجربه تأییدشده", "rating": 5, "visit_date": "2026-10-01", "approved": true}
```

Examples intentionally use **placeholder** values and must not be published
as airport facts.

## Publishing, client handling and later upgrades

Canonical public raw URLs (after merge to main):

- `https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airports/airport-index.v1.json`
- `https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/airports/details/THR.v1.json`

The Android data layer now parses arbitrary section IDs and typed content blocks.
The actual airport UI remains deliberately disabled until a separate UI release.
Once a generic renderer is connected, supported block types can be updated
remotely without redeploying an APK. Unknown future block types should be ignored,
never interpreted as HTML or JavaScript. Hide unsupported/empty sections;
show source and review timestamps for factual content.

The GitHub raw endpoint has no publishing API, moderation inbox, transactional
database or real-time feed. Future **user-submitted reviews** require an
authenticated submission API, rate limiting, abuse review, privacy controls,
and a publish-to-catalog workflow. Live status requires a separately verified
first-party service with clear `fetched_at`, source time and unavailable/stale
states. Keep dynamic flight observations out of this static JSON.

For fast editing at larger scale, add an authenticated admin UI in a later
phase. It should save reviewed changes through a PR or validated publishing
pipeline, not expose the GitHub write token in the Android app.
