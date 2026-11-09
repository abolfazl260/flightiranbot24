# Private Telegram visa widget

`/visa` without arguments and the main Visa menu open the new private-chat widget.
`https://t.me/Flightiranbot?start=visa_widget` is an explicit entry point. Existing
`/start visa`, `visa_IR_TR`, `/visa IR TR`, text search and `visa:*` callbacks retain
their existing flows. The widget's Text search button opens that existing flow.
Bale, groups, unavailable catalogs and failed `sendWidget` use the old text/keyboard
flow; Android and Mini App are unchanged.

The existing local `VisaCatalogService` supplies every rule, source and freshness
value. Only a saved passport present in the catalog is selected; IR is the first-use
fallback only if present. Destinations are button-paged with a popular-country
prefix, followed by the full alphabetic list. Conditions are split on UTF-8-safe
boundaries without dropping long published notes/documents. All output is text,
with no innerHTML, forms or network calls inside the QuickJS widget. Local index
check times are labeled separately from source verification/publication dates.
Missing source data stays missing; no passport validity or visa rules are inferred.

Three localized tabs (FA/EN/AR) provide summary, published conditions/documents and
source dates. HTTPS links are re-resolved from the selected catalog detail and
sent to the requesting user's private chat only after an explicit source tap.
No arbitrary URL, user ID or subscription ID supplied by the widget is trusted.

Queries use `vi:<nonce>:<revision>:<allowlisted action>`. Before service work, the
router acknowledges the query and verifies private chat ownership, data query
kind, positive integer message/sender IDs, non-shared widget and byte limits.
The nonce binds each message to its server-side owner session. A per-message lock
serializes work; revisions reject late/replayed actions. Watch operations are
explicit set-on/set-off (never a toggle) and use `VisaWatchService` ownership,
unique subscription and active-limit checks. Subscriptions survive process restart;
reopened widgets reload their real state. View sessions are bounded to 20 messages
per user; after restart/expiry the user is prompted to send `/visa` again.

Personal selections and watch status appear only in message-specific chat_data;
public_data remains empty. Failed actions retain the previous result with an error.
No test notification, private passport document or new personal data is collected.
Alerts report changed published data, not guaranteed real-world legal changes.

## Validation and rollout

Run `ruff check src tests migrations` and `pytest` (includes real SQLite watch
persistence/ownership, duplicate/late requests, UTF-8 limits, fallbacks and sources).
The existing poller already subscribes to widget_query; no new endpoint, secret or
migration is needed. Deploy the bot normally and test a **new** `/visa` message
with a Telegram 10.4 widget-capable client: passport/destination, all tabs/pages,
watch on/off, reopen, source link, search fallback and back menu. This live-client
smoke is a post-deployment step; automated tests use mocked Telegram transport.
Rollback the bot binary; existing text/keyboard flows and durable watches remain.

Official contracts checked: https://core.telegram.org/bots/api#sendwidget,
https://core.telegram.org/bots/api#answerwidgetquery,
https://core.telegram.org/bots/api#editmessagewidgetdata and
https://core.telegram.org/bots/widgets. HTML <=32768 bytes / zlib-9 <=4096 bytes,
chat/public data <=1024 bytes, action payload <=64 bytes; queries acknowledge
before slow work. Each language and every paginated state are size-checked.
