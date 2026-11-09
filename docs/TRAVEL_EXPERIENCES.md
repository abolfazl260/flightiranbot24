# Shared travel experiences and genuine ratings

SQLite is the publication authority. `SQLiteExperienceService` replaces the old
in-memory adapter in production interfaces; the legacy adapter remains only for
compatibility. The additive Alembic `0013_travel_experiences` migration creates
content, many-to-many context, helpful-vote, abuse-report and audit tables.

## Exact archive and publication permission

`data/experiences/archive/github-168.v1.json` preserves issue #168, all source
comments, nine exact fenced text blocks and all **51** messages (23 + 28). Each
record retains its stable comment/order identity, original header/author/date,
raw message, source offset and SHA256. Round-trip tests join each message back
to its exact source block. No Unicode normalization, markdown escape removal,
name rewriting, inferred trip date, guessed airport or fabricated rating occurs.
The separate `index.v1.json` provides optional airport/airline/country/route/flight
annotations; empty mappings are intentional until evidence is reviewed.

The original material was supplied in GitHub issue comments and remains a
versioned source archive. It is **not** a public application feed, Mini App asset,
APK asset or approved review. Import always creates withheld/pending records with
null ratings and no publication consent. Public/redacted text is a separate view;
original records are never overwritten by moderation. Archive publication requires
an operator to record actual permission evidence, a reviewed public text and an
explicit public display name. Source availability on GitHub is not treated as
permission for public application publication. Do not turn this archive into an
asset route or automatically approve it.

## User workflow and moderation

Mini App users submit through server-validated Telegram initData. New text is
20..1500 characters, with an optional real integer overall satisfaction score
(1..5), relevant optional criteria, an optional stated travel date and an explicit
publication-consent checkbox. A display name is chosen separately; Telegram user
IDs and private names are never copied into the public response. No new media or
passport-document storage is introduced. Android uses a clear Telegram handoff;
it cannot submit a forged native identity.

Creation and edits go to pending. Editing removes previous helpful endorsements
and the old public view. Deletion/withdrawal immediately removes visibility at the
SQLite API. Reapproval needs current owner consent. Duplicate actor/context/text
submissions are rejected, submissions are capped to five/hour, owner edits to ten/minute, interactions to sixty/minute, and the signed
Worker job queue additionally limits requests. Explicit helpful on/off votes are
unique per actor/review; self-votes are rejected. Reports are deduplicated per
actor/review and remain private until reviewed. The existing authenticated job
bridge transports only allowlisted review operations; mutations are never replayed
automatically after an uncertain completion.

Run server-local moderation (no public moderation endpoint or client admin token):

```sh
alembic upgrade head
python scripts/manage_experiences.py import
python scripts/manage_experiences.py queue --kind user
python scripts/manage_experiences.py show --id 52
python scripts/manage_experiences.py reports
python scripts/manage_experiences.py moderate --id 52 --state approved \
  --operator reviewer-name --reason 'Reviewed text and explicit owner consent'
python scripts/manage_experiences.py resolve-report --id 1 \
  --operator reviewer-name --reason 'Reviewed and resolved'
```

For an archive item, `moderate` additionally requires `--permission-evidence`,
`--public-text-file` and `--public-name`. Add multiple `--target airport:IKA`,
`--target airline:iran-air`, `--target country:IR` etc only when supported by source
evidence. Unknown entities may remain unassigned. Rejection/deletion and all
moderation actions record operator, reason, timestamp and content hash privately.

## Public contract, statistics and interfaces

`GET /api/v1/experiences?target=airport:IKA&q=...&sort=newest&offset=0` and
`GET /api/v1/experiences/{id}` return only approved, consented public views.
Pages contain up to ten records. Supported contexts include airport IATA, stable
airline guide IDs, ISO country, IATA route and flight context. Sort by newest,
helpful or overall satisfaction; rating comparisons require **five actual numeric
approved ratings**. A smaller sample can show its calculated mean with a clear
low-sample warning. Zero numeric votes means average=null. Archive text never
creates a vote. Half-up mean rounding to two decimals is shared with the Worker.
The mean measures personal satisfaction, never aviation safety or legal accuracy.

Native Android guide panels and the public archive display the same contract with
search/sort/paging, full-text expansion, real dates and low-sample/empty/error
states. Mini App adds authenticated submission, optional criteria, own status,
edit/withdrawal, helpful votes and reports. `/experiences` and `start=experiences`
read the same source in the bot and open a signed Mini App handoff. Contextual
`start=xp_airport_IKA` / `start=xp_airline_iran-air` preserve the selected context.
Published bot text is paginated/escaped and unavailable records cannot be reopened.
Legacy unconsented airport blocks/static airline rating counts are not combined
with this publication feed; their original datasets remain intact.

## D1 projection, privacy and rollout

The existing publisher imports changed **public views only** and a small manifest
into additive D1 migration `0006_public_experiences.sql`. Original archive, actor
IDs, moderation notes, consent evidence and reports never enter D1 public tables.
Conditional writes, generated-time guards and SHA checkpoints skip unchanged rows
and prevent old publishers resurrecting removed views. A manifest commit removes
withdrawn IDs and renews a six-minute publication lease; public reads fail closed
when synchronization expires. No stale/offline review copy is silently substituted.
The initial published set is empty until real content is reviewed and permitted.

Confirmed edits/deletions of a previously published view through the bridge invalidate the public projection
before the completion is returned to the Mini App. A generation captured before
that mutation cannot renew it. The next publisher pass restores a current view.
This may briefly make public experiences unavailable (normally at most the existing
five-minute publisher interval). Operator/CLI changes require an immediate
`flightiran-cloudflare-publish --once` after moderation; otherwise normal propagation
is bounded by the six-minute lease. Already-read messages/screens cannot be recalled.
Public APIs send no-store and clients do not persist offline review text.

Deploy: back up normally, apply Alembic 0013 and D1 0006; deploy the Worker/assets,
server/bridge/publisher and updated bot; run the archive import and publisher once.
Include the archive and moderation script in the existing bot image; no new service,
secret, domain, R2 bucket or authentication mechanism is required. Android APK
publication remains a separate user-requested release. A 1,000-public-record cap
fails explicitly rather than truncating a publication snapshot; raise it with a
paged publisher before exceeding it. With unchanged content, each publisher pass
writes only its manifest/lease plus changed records; plan D1 reads against the
actual public row count and polling interval.

Rollback binaries/Worker together and leave additive SQLite/D1 tables intact.
The Alembic downgrade deliberately preserves user content and archive rows.
Do not delete or rewrite source #168, #15, #172 or #113 to close this integration.

Validation: Python persistence/identity/moderation/archive tests, real SQLite D1
projection SQL tests in Node, shared public JSON fixture in Python/Node/Kotlin,
Android compilation/unit tests and Mini App DOM interactions. Live-client/manual
release validation is separate from these mocked-transport tests.
