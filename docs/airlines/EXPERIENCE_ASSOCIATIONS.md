# Airline experience associations from GitHub issue #168

The 51 original reports remain immutable in `data/experiences/archive/github-168.v1.json`.
All original author labels (`author_original`), dates, message headers, punctuation, and
verbatim text are retained. Never invent a surname for aliases or `Deleted Account`.
The mapping lives separately in `data/experiences/archive/index.v1.json`.

## Scope

- 22 of the 51 reports explicitly identify one of the 20 supported airline guides.
- Those 22 reports create 24 carrier associations across 10 airline guides.
- A cancelled Varesh booking is a `mentioned` association, not a completed flight.
- Other airlines cited in the archive are **not** silently treated as supported airlines.
- Neither airline association nor existing GitHub visibility establishes the author's
  consent to republish their experience or full name.

## Safe publication workflow

1. Deploy updated code and import the archive using `python scripts/manage_experiences.py import`;
   existing imports are backfilled idempotently with source-name attribution and airline targets.
2. Verify the named author's permission to republish **their original display name**
   and a reviewed public version of their report. Store an auditable permission reference.
   Conduct a privacy review; review contact details, other people's identities and sensitive
   travel information before producing public text.
3. Approve that **specific** archive record with the existing server-only moderation CLI:
   `python scripts/manage_experiences.py moderate --id <DB_ID> --state approved --operator <OPERATOR> --reason <REASON> --permission-evidence <REFERENCE> --public-text-file <REVIEWED_FILE>`.
   The original author name is applied automatically; explicit name overrides are rejected.
4. The existing Android airline page reads approved reviews from
   `/api/v1/experiences?target=airline:<AIRLINE_ID>`. Before approval no archive text
   or identifiable name is included in that API. No fabricated star ratings are created.

**Important:** approval is not automatic. Pending mappings are non-public. The archived
originals and independent airline guide sections remain unchanged.
