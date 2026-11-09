# Telegram airport guides — Bot API 10.4 HTML Widget

This feature exposes all enabled airports from data/airports/airport-index.v1.json and data/airports/details/{IATA}.v1.json. The name and country are taken from the canonical src/flightiran/modules/airport/data/airports.json. No parallel airport dataset is created.

## How to open
Private Telegram chat: use the «فرودگاه‌ها» button or send /airports.
Direct link: https://t.me/Flightiranbot?start=airports

The widget supports three directory filters (all / Iran / foreign), selection among 29 airports, section navigation and paginated full Persian content. Sections are taken from the same published, source-attributed JSON used by Android and the Mini App. Draft, archived and undated sections are not published. User experiences are hidden pending consent and moderation.

The page size and UTF-8-safe content splitting honor the Telegram widget's 1024-byte chat data limit. Page changes use answerWidgetQuery and editMessageWidgetData without sending extra messages. **Only when the user taps "منابع و لینک‌ها"** does the bot send source links separately in a regular message, using validated and HTML-escaped HTTPS URLs. Static airport guide data is never labelled live FIDS data.

## Deployment
Dockerfile now copies data/airports into /app/data/airports, using the repository's reviewed JSON data. A bot image rebuild is necessary after content changes; the widget's QuickJS runtime performs no networking.

    cd /opt/Flightiran/flightiranbot24
    git status --short
    git pull --ff-only origin main
    docker compose up -d --build bot
    docker compose logs --tail=100 bot

Review local uncommitted files before pulling. No bot tokens, database migrations, Cloudflare changes or new ports are needed. Existing Bale menus remain unchanged. The installed Python Telegram library receives new widget_query fields through Update.api_kwargs; existing polling already subscribes to widget_query.

## Test and security
- All 29 enabled airports are checked against the canonical IATA identity catalog.
- Only private chat queries matching the user's own chat and a message ID are accepted.
- Actions are strictly allowlisted and numeric indices are range-checked.
- HTML is self-contained and under 32KiB / 4KiB compressed; widget state is under 1024 UTF-8 bytes.
- Guide text uses DOM textContent, not remote HTML. URLs require HTTPS.
- All published paragraphs and bullets are paginated rather than truncated.
- When widgets cannot be sent, the bot provides a fallback explanation and Mini App link if configured.
- Read or API errors are logged by exception type without leaking token-bearing URLs.

    python -m pip install -e '.[dev]'
    ruff check src tests migrations
    pytest tests/test_telegram_airport_widget.py
    pytest

After deployment send /airports again: old Telegram widget messages retain their original HTML.
