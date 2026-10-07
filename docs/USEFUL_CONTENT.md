# Useful travel content

The Telegram landing page is a six-category inline keyboard. Selecting a
category displays its curated links and a back button to the landing page.

- `documents`: passport, travel restrictions and student exemptions.
- `flights`: flight compensation and airline comparison. Also links to country rules.
- `baggage`: prohibited items and country-specific flight/baggage rules.
- `international`: country-specific travel resource directory.
- `payments`: exit fees and travel insurance.
- `tips`: travel tips and preparation checklist.

Legacy country submenus remain `flight-rules` and `travel-sites`.
Their Back buttons navigate to `baggage` and `international` respectively.
Stable link IDs, link URLs, content ordering and audit events are preserved.

Content is curated and should be verified periodically. Some source URLs point
to legacy Telegram posts, not official government guidance. New legal or
financial guidance must not be fabricated or published without authoritative
sources. Topics such as visa eligibility, airport check-in deadlines, currency
allowances, pet travel and medication restrictions are candidates for separately
verified articles rather than placeholder buttons.

Run `pytest tests/test_useful_content.py` after changes.
