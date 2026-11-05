# Telegram Mini App: shared travel guides

The Mini App now exposes native Persian/RTL **airports** and **airlines** from
its home screen. It reads the same versioned `data/airports/` and `data/airlines/`
index/detail JSON as Android. Airport names come from the existing canonical
identity catalog, not a second inventory. Content changes on main require no
web UI rebuild when they use supported blocks.

The reader supports Persian/Arabic letter normalization, Latin/code/alias search,
Iranian/foreign filtering, section navigation, review dates and official sources,
text/bullets/links/maps/media source links, fleet snapshots, airport cross-links,
and the existing flight-board screen. Telegram BackButton and visible Back
controls move section → entity → directory → home. Search, filters and per-page
scroll positions are retained within the guide. Airline official links can be
shared using Telegram's share URL.

Published airline/section/fleet state, source verification, effective dates and
staleness are checked before rendering. Draft/archived/stale data and unknown
block types are hidden. Empty sections do not create cards. Fleet counts and
configuration remain unknown unless present in a verified snapshot. No schedule,
phone, allowance or rating data has been invented or copied into JavaScript.

Textual passenger reports remain unavailable pending #168 archive/consent work.
The legacy airport experience block is not rendered because it lacks the explicit
consent/privacy gates required for this new web reader. Explicit approved airline
numeric votes have criterion-specific counts and a null average, matching the
current Android sample policy. There is no online submission or new backend.

All GitHub reads are bounded, abort after ten seconds, omit credentials and
referrers, and use exact catalog paths. Telegram initData is never sent to GitHub.
Remote text is rendered with text nodes; arbitrary HTML/iframes are not executed.
Existing CSP allows the public source. Both new ES modules are allowlisted in
the Cloudflare Mini App asset router and included by the existing Python wheel
`*.mjs` package-data pattern. No authentication or user-scoped API changes.

During a network failure a previously parsed guide in the **same session** may
be reused with a clear notice and its review dates. Effective dates are checked
again when cached details are reopened. There is no persistent offline bundle;
a first visit without connectivity displays an error and retry. A successful
withdrawal response replaces the cached guide. Refresh explicitly rechecks the
index and selected detail, while ordinary Back navigation avoids network reads.

## Validation

```sh
node --test cloudflare/test/*.test.mjs
python -m pytest
python -m ruff check src tests migrations
node --check src/flightiran/webapp/static/mini.js
```

`node scripts/test_mini_guides.cjs` is an optional Playwright browser smoke test
(requires installed Playwright + Chromium; `CHROMIUM_EXECUTABLE` can select an
existing executable). It serves the real Mini App shell locally, mocks Telegram
and all APIs/catalog requests, and tests airline search/fleet/back/offline and
airport details at phone width. It checks for page errors and credential leakage;
it sends no live Telegram messages or authenticated service requests.

Deploy through the existing FastAPI/static or Cloudflare Worker asset workflow.
No Android build/signing/release workflow is changed or triggered. This PR changes
source only; it does not deploy the live Mini App or complete the later #172 phases.
