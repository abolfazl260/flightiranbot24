# FlightIranBot24

FlightIranBot24 is a Telegram travel assistant with an optional Bale bot, a Telegram Mini App and a separate Android application. It provides ticket-price information, visa guidance, alerts, and travel resources.

Bale uses the same bot handlers and travel services through a separate polling process. To enable it, see [Bale Bot setup](docs/BALE_BOT.md). Telegram deployment remains unchanged by default.

## Telegram main-menu availability

The **29-airport guide** is available from the private Telegram bot menu,
the `/airports` command and `https://t.me/Flightiranbot?start=airports`.
It uses the Bot API 10.4 HTML widget to browse the GitHub-maintained,
published guide sections without leaving the chat. Traveler Rules is still
hidden until a full public reader is approved. The Mini App button is shown
when `WEB_APP_ENABLED=true` and `WEB_APP_URL` is valid HTTPS.

| Feature | Telegram bot | Telegram Mini App |
| --- | --- | --- |
| Airports / فرودگاه‌ها | Private HTML widget with 29 airports and source-backed sections | Native searchable airport guide; same JSON data |
| Traveler Rules / قوانین مسافر | Separate menu hidden | No standalone traveler-rules destination |
| Telegram Mini App | Configured HTTPS Web App launch button | Full travel Mini App |

**Compatibility:** The previously hidden `menu:airports` button now opens
the widget in a Telegram private chat. Legacy `airports:page:*` and `airport:*`
buttons still return to the main menu; `menu:rules` remains disabled. Bale
retains its previous menu. Source links are sent only on an explicit request.
Airport facts update when the Docker image is rebuilt with the reviewed JSON.
See [the airport widget guide](docs/TELEGRAM_AIRPORT_WIDGET.md).

**BotFather menu button:** The inline launch button shown after `/start` is independent of a persistent Telegram menu button configured through `@BotFather` (`/setmenubutton`). This change does not modify BotFather settings.

## Private administrator reports

The `📊 گزارش کامل ربات` button is available **only to the configured
administrator in a private Telegram chat**. It delivers the comprehensive
aggregate Rich Text report plus paginated per-user Rich Text tables showing
Telegram username/name and numeric ID, total tracked interactions, interactions
during the past seven days, active **price** and **visa-change** bells, and
last recorded activity time in UTC. A tracked interaction is a user-attributable
audit event (excluding registration bookkeeping and system errors), not a
guaranteed unique session. A user with no recorded activity displays zero and
an unknown last-use time. The report preserves all registered users and pages
results rather than truncating them. If Telegram Rich Messages are unavailable,
the per-user pages fall back to escaped HTML text messages. No personal user
details are included in publicly visible aggregate reports.

## Project components

- Shared Telegram/Bale bot handlers: `src/flightiran/interfaces/telegram/`
- Bale transport: `src/flightiran/interfaces/bale.py`
- Telegram Mini App: `src/flightiran/webapp/static/` (see [Mini App documentation](docs/TELEGRAM_MINI_APP.md))
- Android app: `android/` (see [Android README](android/README.md))
- Automated tests: `tests/`

