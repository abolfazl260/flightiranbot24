# Telegram interactive /help widget (Bot API 10.4)

Telegram private chats show an interactive Help Centre instead of a long command list. The previous localized text is preserved for Bale, group chats and Telegram clients that cannot display `sendWidget`.

## Entry points

- `/help`
- `https://t.me/Flightiranbot?start=help`
- **❔ راهنمای تعاملی ربات** on the private Telegram main menu

## UX

The widget contains three locally switchable tabs: **Services**, **Commands**, and **FAQs**. The Services tab offers six currently implemented features (fares, airport guides, checklist, visa, price history chart, price alerts). Selecting a tile updates its description locally; **Open service** issues an allowlisted widget query that invokes the existing feature handler in a **new Telegram chat message**. Only the service launch sends a new message; switching tabs and reading FAQs do not.

The Commands tab lists the public, non-administrative commands actually registered by the bot. For actionable commands, tapping an entry invokes the same server-side service handler. `/help` and `/cancel` remain reference-only entries. FAQs are locally expandable. Support opens the existing configured Telegram support flow.

Localized UI: Persian, English and Arabic based on the user's saved bot-language preference. The widget follows Telegram theme variables for dark/light modes, with an explicit selected tab state and accessible labels. HTML is self-contained and QuickJS uses no external network or form controls.

## Security and compatibility

- New actions are strictly allowlisted as `hp:open:{id}` and only processed if the raw `widget_query` belongs to the same **private chat and user** with an original message ID; shared widget IDs and foreign chats are rejected.
- The bot acknowledges `answerWidgetQuery` promptly and then dispatches the chosen service, using existing bot permissions, datasets and services. It does **not** invoke privileged `/visa_sync` or administrator actions.
- Other widget routers (`fare:`, `ap:`, `cl:`) are unchanged. The installed python-telegram-bot version forwards new `widget_query` metadata via `Update.api_kwargs` with one polling connection.
- Telegram HTML size is checked against **32KiB raw / 4KiB zlib-compressed** at render time.
- If a widget cannot be sent, the original text help and main keyboard are delivered. The Bale bot continues to receive the original text help.
- The bot reuses the actual Telegram user's per-user state for chart/visa flows; it does not derive that state from the widget's client-side values.
- Uncaught service failures are logged by exception type only and reported to the requesting chat without exposing tokens or internal URLs.

## Deployment

No new environment variables, migrations, ports, Cloudflare Worker, Android or Mini App changes are required.

```bash
cd /opt/Flightiran/flightiranbot24
git status --short
git pull --ff-only origin main
docker compose up -d --build bot
docker compose logs --tail=100 bot
```

Before pulling, check and preserve server-local changes. Send **/help again** after deployment to create a new HTML widget; already-sent Telegram widgets retain their original HTML.

## Verification

```bash
python -m pip install -e '.[dev]'
ruff check src tests migrations
pytest tests/test_telegram_help_widget.py
pytest
```

Manually open /help on a current private Telegram client, switch all three tabs, expand a FAQ, open each of the six services and contact support. Test the group-chat help and Bale help to ensure they remain text-only.
