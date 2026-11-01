# FlightIranBot24

FlightIranBot24 is a Telegram travel assistant with a Telegram Mini App and a separate Android application. It provides ticket-price information, visa guidance, alerts, and travel resources.

## Temporarily disabled Telegram features (2026-11-01)

To keep the public Telegram destination focused on fully functional services, **Airports** and **Traveler Rules** are intentionally hidden **until further notice**. They are disabled, **not deleted**, so their implementation can be completed and restored later.

| Feature | Telegram bot | Telegram Mini App |
| --- | --- | --- |
| Airports / فرودگاه‌ها | Main-menu button disabled/commented out; removed from welcome and `/help` | Home-page airport card and placeholder screen commented out |
| Traveler Rules / قوانین مسافر | Main-menu button disabled/commented out; no longer advertised in `/help` | No standalone traveler-rules destination to expose |

**Compatibility and access:** Previously sent `menu:airports`, `airports:page:*`, `airport:*`, and `menu:rules` inline buttons safely return users to the normal main menu. Existing `/start airports` deep links also show the main menu instead of the airport placeholder. This prevents old links from surfacing a disabled screen.

**Implementation retained:** Telegram airport services and traveler-rules modules remain in the repository; their public menu entries and Mini App airport markup are commented out. This is a **Telegram-specific change**; the Android application's airport directory is not modified.

**Re-enabling:** Complete and verify the features, restore the commented menu items and Mini App markup, update localized welcome/help descriptions, re-enable the corresponding routes and deep links, update tests, and remove this temporary-disabled status from the README. Validate both mobile and desktop Telegram before publishing.

## Project components

- Telegram bot: `src/flightiran/interfaces/telegram/`
- Telegram Mini App: `src/flightiran/webapp/static/` (see [Mini App documentation](docs/TELEGRAM_MINI_APP.md))
- Android app: `android/` (see [Android README](android/README.md))
- Automated tests: `tests/`

