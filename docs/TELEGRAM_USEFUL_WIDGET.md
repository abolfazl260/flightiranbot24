# Interactive travel resources (#206)

The existing Telegram `menu:useful`, `/start useful` and new `/useful` command
open an HTML widget in private Telegram chats. `/useful_legacy` always opens the
existing inline menu; choosing it (or **منوی ساده** inside the widget) keeps
subsequent menu navigation in the simple interface. `/useful` explicitly opts
back into the widget. Unsupported clients see the fallback command in the
widget caption. Groups, Bale and `sendWidget` failures use the existing menu.
Existing `useful:<category>` callback links remain compatible.

## Content and navigation

`UsefulContentCatalog` is the only content source. No IDs, URLs, titles or
active resources in the catalog are changed. The home page shows all six
categories, their source counts and an all-resources view. `flight-rules` and
`travel-sites` remain accessible from their existing parent categories; Back
retains the parent through which the user entered. Country and subject
suggestions filter existing titles/descriptions/category labels. Country names
are derived from the catalog's country-resource titles, rather than maintained
in another list. Inactive links are excluded. Unrecognized future categories
remain reachable through All resources.

Widgets support buttons, not keyboard text inputs, and have no internal scroll.
Consequently **جست‌وجو با فیلتر** offers tappable subject/country suggestions.
Lists have at most four rows per page; home uses a two-column category grid.
Long title previews have an ellipsis; detail pages retain every character of
the full title and description. Descriptions and checked-on dates are shown
only when the actual catalog supplies them. No date, verification or official
source status is inferred. The same Telegram message receives navigation and
refresh updates. Opening a source explicitly sends a regular inline HTTP(S)
URL button; the user presses that button to leave the bot. Previews are disabled.

**تازه‌سازی اطلاعات** resolves the current deployed server catalog again. It
does not scrape external websites or claim their contents have changed. Changes
to the Python catalog still use the existing Git deployment/restart workflow.
Errors retain the last valid state; failed widget edits provide the explicit
simple-menu command in a normal chat message.

## Security and limits

The shared widget dispatcher accepts `uf:` requests only from the owner in a
private Telegram chat, for an integer message ID, a matching server session
nonce/revision, an allowlisted action and data-query type. Shared widget IDs,
Bale requests, stale revisions and unknown sessions are rejected. Session locks
prevent duplicate concurrent actions. All actions fit the 64-byte request limit;
UTF-8 HTML, zlib level-9 output and every state field are checked against the
32,768/4,096/1,024-byte limits. JSON text is rendered with `textContent`, never
HTML; no external code, fonts or assets are loaded. Source URLs are resolved
from the active catalog at the moment of the explicit open action; arbitrary
client URLs and credentials in URLs are rejected. Logs record only exception
classes, not Telegram transport URLs or credentials.

Only the latest 20 widget sessions per user are retained in process memory,
using the existing Telegram context. After a restart or session eviction,
reopen with `/useful`; old requests are safely rejected. No new database,
poller, token, service, migration, Android or Mini App change is needed.

## Validation and deployment

```sh
ruff check src tests migrations
pytest tests/test_telegram_useful_widget.py tests/test_useful_content.py
pytest
```

The Python tests exercise actual handlers and dispatcher, all 21 catalog
resources, eight categories/subcategories, full Unicode detail round trips,
payload limits, catalog replacement/failure, owner checks, replay/concurrency,
removed sources and the old command/menu paths for private chat, groups and
Bale. A dependency-free Node VM DOM smoke executes the actual generated widget
JavaScript and state to check navigation, explicit opens, retained errors and
text safety. This is a DOM contract test, not a Telegram rendering test.

Deploy/restart only the existing Telegram service; its command-menu sync adds
`/useful`. No environment variables or database schema changes are required.
Automated tests do not send messages to a live bot. A local Chromium visual
attempt was blocked by the executor's socket restrictions, and the managed
browser disallowed local file navigation; no real Telegram/device visual test
was performed. Before announcing the feature to users, verify on current mobile
and desktop Telegram clients supporting Bot API 10.4 widgets:

- Open `/useful`, `/start useful` and the travel-information menu; check all
  six categories and 21 sources, RTL and light/dark themes at phone widths.
- Follow both subcategories and Back; filter by Canada and an empty subject;
  page long details without clipping beyond the widget's 600px height limit.
- Refresh after a server catalog update; force an error and confirm valid data
  remains. After a restart, use `/useful` to open a new session.
- Explicitly open both `https://t.me/...` and external HTTP(S) source buttons.
- Test `/useful_legacy` on an unsupported client, group and Bale, then navigate
  back to the simple menu without reopening unsupported media.

Rollback by reverting the PR and restarting Telegram. Catalog data are
unchanged; old inline buttons continue working. Previously sent widget messages
may remain but their requests will no longer be dispatched.

Official widget profile and API: https://core.telegram.org/bots/widgets
