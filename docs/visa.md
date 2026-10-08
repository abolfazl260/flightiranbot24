# Flight Iran Bot 24 — Visa and entry requirements

## Source and license

The data is retrieved directly from **https://travelrequirements.info/data/index.json**.
Destination JSONs listed in the manifest are downloaded and validated before any changes
are committed to SQLite. Original provider metadata, citations and verification dates are
preserved under `visa_destination_data.raw_data`.

The upstream publication, **TravelRequirements.info — Entry Requirements Dataset,
AXG Sp. z o.o.**, is licensed **CC BY 4.0**:
https://creativecommons.org/licenses/by/4.0/ .
The bot formats and translates user-interface labels, but must never present general
nationality-only data as a legally binding entry decision.

## Deployment

```sh
docker compose up --build -d
```

A one-shot `migrate` service runs before `bot` and `web`.
It upgrades existing versioned SQLite databases, creates new databases, and checks
legacy databases that were created using SQLAlchemy metadata rather than Alembic.
The named `flightiran-data` volume is preserved. **Back it up before upgrading**.

For installations managed by systemd without Docker:

```sh
# Use the same DATABASE_URL and environment as the bot.
python -m flightiran.db.migrate
systemctl restart flightiran
systemctl restart flightiran-web
```

The new migration creates `visa_rule_index` and leaves the raw destination JSON table
introduced in 0005 intact.

## Refresh strategy

- Run `/visa_sync` in the admin's private Telegram chat to import the dataset immediately.
- The bot also runs a check at startup, then every 6 hours (configurable with
  `VISA_SYNC_INTERVAL_HOURS`).
- Unchanged country files are skipped by manifest `lastUpdated`, with periodic
  unconditional file rechecks every seven days.
- Both the detailed country JSON and the flattened passport/destination index are written
  inside one transaction. A failed download or invalid document preserves the last
  committed version.
- The admin receives a notification when provider JSON content changes, including
  direct download links. This can include editorial/source-verification changes; a
  notification does **not** necessarily prove that the immigration law changed.
- In-progress sync requests are serialized inside the bot process. Only the bot process
  runs the scheduler, not the web service.

Initial import downloads the full coverage and populates ~39,601 indexed passport routes.
The UI may show "Data not imported yet" until this has completed.

## Date provenance and source-link policy

Visa outputs distinguish **three separate upstream dates**, taken from the original
destination JSON, rather than from the bot's SQLite update or server clock:

| User-visible field | Exact upstream field | Meaning |
| --- | --- | --- |
| Source last verified | Passport-specific `visaPolicy.byPassport[passport].source.lastVerified`, or `visaPolicy.defaultSource.lastVerified` | The publisher's most recent documented check of the cited legal source |
| Last source-recorded change | The same cited source's `lastChanged` | A source-content change reported by the dataset; **not** automatically a new law or effective date |
| Destination dataset last updated | `meta.lastUpdated` | Date that the publisher updated the destination data file |
| Destination last fully reviewed | `meta.lastFullReview` | Most recent comprehensive review claimed for that destination |

Some passport rows cite only the **shared destination policy**, rather than a
passport-specific source. The UI explicitly labels this lower-granularity citation.
If the original field is absent or an invalid calendar date, the bot displays
"Not stated by source" and never replaces it with `VisaDestinationData.last_fetched_at`,
`VisaDatasetState.last_checked_at`, or Telegram message time.

**Last verified is not a legal expiry date or a guarantee the rule is still valid.**
The source tab expressly explains that no binding effective-until date has been
established. It also warns when a verification is older than 30 days or the source
is marked unverified/unavailable.

Links in Telegram text are HTML anchors (`<a href="https://...">...</a>`) with
HTTPS-only validation and safe HTML escaping. The main card, detail tabs,
native `sendRichMessage` report, and the administrator's formatted
`/visa_sync` result link to the relevant official rule, original destination
JSON and upstream dataset/CC BY 4.0 attribution. A source URL is not replaced
with the dataset URL; the user can open both independently.

The admin sync report distinguishes the **local check timestamp** from the
**newest published destination lastUpdated in the manifest**. This newest date
does not mean every destination or passport rule was reverified on that date.

## Telegram commands

- `/visa` — open the interactive passport and destination picker.
- `/visa AF TR` — Afghan passport / Turkey, source-backed details.
- `/visa AF TR IR` — same journey with declared Iranian residence. Residence
  is **displayed but not automatically used as an eligibility exception**.
- `/visa IR` — select Iranian passport and browse destinations.
- `/visa_list IR` — show destinations by entry status, with counts and pagination.
- `/cancel` — cancel an ongoing free-text country search.
- `/visa_sync` — admin-only forced check, results and source download URLs.

All pickers support paging through the passport/destination list, searching country
names in Persian/Arabic/English, and entering the two-letter country code.

## Rich output and fallbacks

The "Full rich-text report" button uses the same native Telegram
`sendRichMessage` API transport as the existing ticket tables.
It presents a rich table and source-backed sections. In clients where this endpoint
is unsupported or a request fails, the bot sends individual HTML-formatted sections
with safe escaping and source links. The user can also open these tabs individually:

- Visa types, application links, fee, validity, entries, processing and document specifications.
- Passport validity, travel insurance, proof of funds, onward ticket, health and customs rules.
- Transit/entry modes and additional levies when present.
- Destination facts including currency, timezone, payments, plugs, safety and emergency contacts.
- Travel tips, FAQ, source provenance, verification dates and upstream JSON.

Documentation is shown in the bot's configured language where localized labels exist.
Long official-source descriptions are preserved in their original language to prevent
translation from changing legal meaning. The original JSON is linked for full verification.

## Important limitation

The upstream matrix is primarily based on **passport citizenship × destination**.
It generally does not evaluate residence in a third country, travel purpose, transit
itinerary, passport class, supporting visas or exact travel dates. Missing or
`required: false` fields with vague supporting sources must **not** be shown as a
confirmed exemption. The UI presents the original source text and explicit caveats.

Users must confirm their itinerary with the destination's immigration authority and
their airline. This feature does not issue visas or determine boarding eligibility.

## Quality assurance

```sh
ruff check src tests migrations
pytest
```

Tests cover normalization, row-vs-policy citations, safe HTML, localized country search,
pagination callback limits, direct commands, SQL query paths and fresh/legacy database
migration. Check a real `/visa_sync` after the new release to confirm provider reachability
and compare important journeys against official references.
