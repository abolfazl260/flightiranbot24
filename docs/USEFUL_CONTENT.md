# Useful travel content

The `useful_content` module owns the travel-information catalogue. Telegram
handlers only render the catalogue and never contain provider URLs.

## Categories

- `general`: compensation, airline ratings, exit restrictions, prohibited
  items, exit fees, insurance, travel tips, passport and academic exemption.
- `flight-rules`: country and region guidance for flight and baggage rules.
- `travel-sites`: country and region directories of related travel websites.

Each entry has a stable ID, label, absolute HTTP(S) URL, optional description,
review date and active flag. To replace a legacy Telegram post with an
official source, update `default_catalog()` or replace the catalog dependency
with a repository-backed implementation; the Telegram handler does not need to
change.
