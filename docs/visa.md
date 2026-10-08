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
