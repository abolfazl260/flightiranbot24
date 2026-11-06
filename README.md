# FlightIranBot24

FlightIranBot24 is a Telegram travel assistant with an optional Bale bot, a Telegram Mini App and a separate Android application. It provides ticket-price information, visa guidance, alerts, and travel resources.

Bale uses the same bot handlers and travel services through a separate polling process. To enable it, see [Bale Bot setup](docs/BALE_BOT.md). Telegram deployment remains unchanged by default.

## Telegram main-menu availability

**Airports** and **Traveler Rules** remain hidden from the Telegram bot until those features are ready. The **Telegram Mini App launch button is enabled** in the shared inline menu for `/start`, `/help`, language changes, and back-to-main-menu navigation when `WEB_APP_ENABLED=true` and `WEB_APP_URL` is a valid HTTPS URL.

| Feature | Telegram bot | Telegram Mini App |
| --- | --- | --- |
| Airports / فرودگاه‌ها | Main-menu button disabled/commented out; removed from welcome and `/help` | Home-page airport card and placeholder screen commented out |
| Traveler Rules / قوانین مسافر | Main-menu button disabled/commented out; no longer advertised in `/help` | No standalone traveler-rules destination to expose |
| Telegram Mini App launch / ورود به مینی‌اپ سفر | `🚀 ورود به مینی‌اپ سفر` opens the configured HTTPS Mini App via Telegram Web App; omitted if disabled or URL is invalid | Mini App implementation, backend endpoints, assets, and direct URL remain available |

**Compatibility:** Previously sent `menu:airports`, `airports:page:*`, `airport:*`, and `menu:rules` inline buttons safely return users to the normal main menu. Existing `/start airports` deep links also show the main menu rather than the airport placeholder.

**Implementation retained:** Telegram airport services and traveler-rules modules remain in the repository; their public menu entries and Mini App airport markup are commented out. Android functionality is unaffected.

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

