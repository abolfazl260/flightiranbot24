# Airline guides v1 — #172

## Audited baseline and scope

Based on `main` at `edb62f37567424005f2681e75b8a611fd1eb23fe`. Airports use an
independent per-IATA index/detail JSON contract, bounded OkHttp reads and a bundled
fallback. The identity catalog is separate from its guide content. The launcher
has native Services destinations. Airline identities must not reuse airport IATA
keys or the airport `experience` block (which requires a numeric rating).

This is the first implementation PR: native Persian/RTL directory, searchable
identity, section pages, fleet cards, public JSON/schema/validator, and offline
fallback. Content changes using existing block types need no new APK after this
reader is released. No new database, account, submission form or admin panel.

The Android release and screenshot workflows were audited: both already require
manual dispatch on `main`. They are unchanged. Content CI validates JSON only;
it does not package/sign/release APK or AAB files.

## Coverage, not a completeness percentage

| Stable ID | Index/detail state | Published sections | Draft sections | Sources/limitations |
| --- | --- | ---: | ---: | --- |
| `iran-air` | published | 3 | 4 | Rechecked IATA identity, announced .ir domain migration and contact; detailed operational policy review continues. See docs/airlines/iran-air-2026-11-10.md. |
| `emirates` | published | 18 | 0 | Specialist policies, seat selection and FAQ; dated 31 March 2026 model/owned/leased inventory. Active status and configurations unknown. See dated Emirates source audit. |

Current Emirates coverage supersedes the initial counts below; see `docs/airlines/emirates-2026-11-10.md`.

Both are labelled **راهنما در حال تکمیل**, including when basic identity is
available. `published` means a reviewed portion is available, never a complete
carrier guide. No entire airline is currently draft/archived. There are **zero**
passenger experiences, numeric ratings, licensed photos or logos in this initial
public dataset. Missing services are not described as unavailable.

## File contract and maintenance

- `data/airlines/airline-index.v1.json`: stable IDs, names, aliases/former names,
  country, official website, dated code assignments and exact detail paths.
- `data/airlines/details/<stable-id>.v1.json`: independent publication metadata,
  sections and separately gated published ratings / experience associations.
- `airline-index.schema.json` and `airline-detail.schema.json`: strict v1 schema.
- `scripts/validate_airline_content.py`: cross-file identities, paths, publication,
  source HTTPS, dates, policy scope, fleet metadata and review guardrails.

Add a carrier by choosing a stable lowercase ID, creating its **own** detail file
and index entry, initially `draft`. Renaming a brand changes display fields or
aliases, never its ID. IATA/ICAO assignments are optional arrays with validity
periods; codes are not IDs. Historical reuse must have non-overlapping periods;
controlled concurrent duplicates require `shared: true` on both assignments.
IATA permits alphanumeric two-character codes; ICAO is three uppercase letters.

Each airline, section and fleet snapshot has `metadata`: `draft/published/archived`,
`source_urls`, `verified_at`, `effective_from/to`, confidence and explicit `stale`.
Never advance verification dates without checking the sources. Unknowns are null
(or `unknown` for enumerated states), never fabricated zeros or free prices.
A published item needs sources and a non-future verification date. Stale,
not-yet-effective, expired, draft and archived items are hidden by Android.

Sections have stable ID, Persian title, icon, order and typed blocks. Existing
`text`, `bullets`, `link` payloads match airport content; Android reuses its typed
text/link/bullet models. Fleet and airport links have dedicated types. Unknown
future block types are skipped without blank section cards. New renderers need
an Android update and schema/parser tests before publishing those blocks.

A policy must carry explicit scope, including unknown route/fare/cabin fields,
operating carrier, seller and journey type. The Persian scope note is always
shown. Initial policies link to official applicable rules instead of asserting
universal numeric allowances, fees, check-in cutoffs or compensation. Preserve
marketing/operating carrier distinction; a codeshare does not imply ownership.

Fleet snapshots carry their own verification/source, observation date, count,
status and ownership/operation relationship. A count/configuration without its
own published source is rejected. No safety or airworthiness inference is made.
Media blocks require verified usage rights, license, source and attribution;
otherwise keep the section draft. The initial reader opens licensed media at
its source; it does not download arbitrary images or execute embedded HTML.

`airport_link` references the existing airport index by IATA and opens its native
page. It is a navigation reference, not a claim of a current airline route. No
route schedules were added. Sourced network sections can reuse these links;
structured route inventories and bidirectional airport sections are later work.

Validate every PR:

```sh
python scripts/validate_airline_content.py
pytest tests/test_airline_content_catalog.py
python scripts/check_android_ui_contract.py
gradle -p android :app:testDebugUnitTest :app:lintDebug :app:compileDebugAndroidTestKotlin
```

Review the sources and independent publication flags, then merge the content PR.
To withdraw a section, mark it draft/archived or stale. To withdraw a carrier,
change the index and detail publication status. Revert the relevant commit to
roll back. Never delete another airline's file to update this airline. Preserve
all existing airport, visa, price and experience data.

## Privacy, experiences and ratings

#168 is still open and its immutable archive is **not present on this baseline**.
Its current description now references **51 reports (23 + 28)**, not just the 23
mentioned by the older #172 text. This PR does not copy, summarize, rename,
reorder, deduplicate or modify any original experience. `experience_links` are
sidecar mappings by immutable experience ID to one/many airline IDs, relationship
(operating/marketing/mentioned/unknown), public source URL and publication gates.
They contain no author, timestamp, original body, travel identifiers or inferred
stars. Pending associations may be prepared but the validator rejects approved
associations until the immutable archive, consent and privacy integration exists.
The UI explicitly explains the unavailable integration; no reviews are fabricated.

Textual experiences and numeric votes are separate products. A public
`publishedReview` requires granted consent, approved moderation, verified origin,
privacy review, no conflict of interest, a unique review ID, airline ID, publication
time and explicit integer votes 1–5. Each criterion has a separate denominator.
The conceptual `reviewSubmission` definition is separate and cannot enter the
public review array. Never commit private pending submissions or consent evidence
to a public repository. Public ID is opaque; it must not encode a passenger name,
PNR, phone, ticket number or exact travel identity.

**Sample policy: unset pending product approval.** Display valid counts only.
`AirlinePage.average` is null, even if historical numeric votes later arrive.
There is no rating sort, ranking, medal, “best airline” label or extracted score
from text. Proposed future method: arithmetic mean per criterion over its own
explicit votes, fixed one-decimal half-up rounding; overall uses only explicit
`overall` votes, not a mixture of unequal criterion samples. Activation requires
an approved minimum sample, common time window and comparability policy, plus
schema/UI/calculation tests in a separate PR. No threshold is invented here.

Before a historical vote is approved, maintainers verify origin and permission,
check duplicate traveler/flight submissions and promotional conflicts using
**private** evidence, and assign a unique publication ID. The current validator
rejects duplicate publication IDs, out-of-range/fractional values and unapproved
records; it cannot independently detect two real-world submissions with different
IDs. Online voting requires a separately approved identity/deduplication/rate-limit
and moderation design. No online voting endpoint exists in this PR.

The app offers a correction/report link to existing project support. Maintainers
withdraw a problematic published record through PR, recalculate counts, and retain
any required consent/audit trail privately. Preserve the immutable #168 original;
public access changes must not destructively rewrite it.

## Reader behavior and manual verification

Loading, empty, unpublished/unavailable, transport/parser error and bundled-copy
states have Persian messages. A successful archive response is never treated as a
network failure. The copy bundled at APK build time is a fallback, not a durable
cache of later downloads; it may contain an older reviewed snapshot if the network
is unavailable. Each page/section displays its review date and an explicit notice.
Remote withdrawal cannot retroactively erase an already installed offline copy.
Do not bundle private or consent-revocable content; the initial fallback contains
only public official facts and links. There are no cookies or passenger data.

Directory filters, selected airline/section, back navigation and per-screen scroll
state survive rotation using saveable state. Shared TravelTheme enforces RTL;
Material controls provide touch semantics; headings and variable-height cards
support TalkBack and large text. No fixed-height text or color-only status.

Manual/emulator checklist (requires Android tooling, not JSON CI):

1. Services → ایرلاین‌ها; search Persian/Arabic ی/ک, aliases, Latin names and codes.
2. Iranian/foreign filters; open Emirates baggage/refund/check-in links, verify
   direct-vs-agent wording and lack of universal allowance/price claims.
3. Open fleet; check model cards, dated observations and unknown counts/status.
4. Back section → overview → directory; rotate and check query/scroll retention.
5. Disconnect network; verify bundled-copy notice and review dates, retry online.
6. Inject draft/stale/unknown blocks; ensure no draft card, blank card or crash.
7. TalkBack, 1.6×/2× fonts, landscape, external-link failures and airport return.
8. Experience area: no original reports leaked, no synthetic averages or stars.

Remaining phases: richer source-reviewed Iranian operational guides; detailed
scoped allowances and fleet counts; route inventory and airport backlinks; #168
immutable/permission-aware reader; approved rating means and comparison; licensed
inline media. Live data and online submissions require separate approval per #172.

## Current integration after #202 and the #172 ratings follow-up

The initial-baseline limitations above are historical. The immutable 51-report
archive and persistent, consent/moderation-aware publication service now exist
(see `TRAVEL_EXPERIENCES.md`). Android's airline overview opens the shared live
`airline:<stable-id>` experience panel, and native submissions explicitly hand
off to Telegram. The old static `published_reviews` fields are not combined with
the live API or used to double-count votes. Archive originals remain withheld
until individual permission/privacy review; no source content is changed here.

The live submission contract now covers all eight requested dimensions: explicit
overall satisfaction (`rating`), crew, seat, cleanliness, catering, check-in and
boarding (`checkin`), baggage handling (`baggage`) and value for money (`value`).
The existing optional delay-response criterion is retained for compatibility.
Airline-only criteria are rejected for an airport-only context. Each optional
criterion may be omitted independently; omission is never a zero vote. Criteria
remain optional when editing, and changing form contexts retains the draft votes
for criteria that still apply.

Both first-party SQLite and Cloudflare D1 return additive `stats.criteria` entries
with a separate count, arithmetic average (two-decimal half-up), and low-sample
flag. A criterion without votes has no summary entry, meaning unknown, not zero.
The cohort is all approved, consented records matching the selected context and
text filter, before pagination. Multi-context associations do not duplicate a
review. Overall satisfaction still uses explicit overall votes only; criteria
never create a weighted or inferred overall score. The reader displays the
method and each denominator, and marks samples below five. These are passenger
satisfaction measures, not safety scores or official airline rankings. No
cross-airline leaderboard/comparison is introduced: a common time window and
comparable populations still require a separate product decision.

The shared Python/Node/Kotlin JSON fixture now includes criterion statistics.
Database tests cover missing overall votes, different criterion denominators,
rounding, context isolation and pending-review exclusion. D1 tests exercise the
actual SQL aggregation over the filtered cohort, including a page with no rows.
Android validates received summary counts/means/low-sample flags and gracefully
supports an older server without `stats.criteria`. Existing clients ignore the
additive fields. No new table, migration, token, or signed release trigger.

Deploy the Python service and existing Worker to enable the additive API; release
Android manually using the existing workflow to show the native summaries.
Content-only guide edits still require no APK rebuild. Revert the follow-up PR
for rollback: the new integer votes remain valid JSON and must not be erased.
A previous backend rejects submissions using the three new criterion names;
pause those submissions during rollback until server/client contracts match.

Remaining #172 work is not represented as complete: richer verified Iranian
operational content, detailed dated fleet counts, structured sourced routes,
licensed inline media, comparable airline rankings and real-device TalkBack/RTL
acceptance. Unknown information remains unpublished; no archive permission,
source verification, aircraft count, media license or user rating is fabricated.

## Reviewed content on 2026-11-10

Emirates now has 10 published sections and no draft sections: cabin and catering
were published after official-source review, special assistance was added, flight
status provenance corrected, and fleet family references rechecked without adding
counts. Iran Air remains 1 published / 4 draft sections. See
[the source review](airlines/emirates-2026-11-10.md) for URLs, scope and limitations.
No carrier is represented as complete; no other content's review date is advanced.

### Dated route block and source review age (Emirates follow-up)

`route_snapshot` extends v1 additively; old readers skip it and still display
network text and airport links. See the dated Emirates audit for exact field
semantics and sources. It records a directed source-page relationship, not a
live schedule. Both native and Mini App readers support it; publication does not
install a new reader on existing Android devices. Published route endpoints must
exist in the airport index and operating carrier IDs, when known, in the airline
index. Unknown operator/connection stays null/unknown; metadata preserves unknown
effective dates. No duplicated airport details or reverse-direction route inferred.

An editorial warning appears after 30 days since source review, independently of
legal effective periods. Mark explicitly invalid data stale to hide it. Review
network and policy sources monthly and before travel; retain the historical fleet
observation date rather than silently replacing it with the source review date.
