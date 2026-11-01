#!/usr/bin/env python3
"""Advisory health probe for the public ticket feed.

Signed Android releases must not be suppressed by a temporary operational
outage of an independent HTTPS data service. This probe still fails loudly
(and marks the GitHub Action step as failed / continue-on-error), so a 403,
stale records, or malformed data never looks like a healthy production feed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

_MAX_BYTES = 1_500_000
_MAX_AGE = timedelta(hours=3)
_FUTURE_SKEW = timedelta(minutes=5)


class RejectRedirects(HTTPRedirectHandler):
    """Do not turn an edge redirect into an accidental success at another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.params
        or parsed.path not in ("", "/")
        or not origin.endswith("/")
        or len(origin) > 300
    ):
        raise ValueError("Production API origin must be a bare HTTPS origin ending in /")
    return origin


def _fresh_snapshot(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    if (
        data.get("currency") != "TOMAN"
        or data.get("stale") is not False
        or not isinstance(data.get("routes"), list)
        or not data["routes"]
        or not isinstance(data.get("observed_at"), str)
    ):
        return False
    try:
        observed = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if observed.tzinfo is None:
        return False
    age = datetime.now(timezone.utc) - observed.astimezone(timezone.utc)
    return -_FUTURE_SKEW <= age <= _MAX_AGE


def probe_ticket_api(origin: str, opener=None) -> tuple[bool, str]:
    """Read-only reachability/freshness check. Never changes or publishes data."""
    origin = validate_origin(origin)
    url = urljoin(origin, "api/v1/tickets/prices")
    if opener is None:
        opener = build_opener(RejectRedirects()).open
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "FlightIranBot24-ReleaseCheck/1.0"},
    )
    try:
        with opener(request, timeout=15) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}: ticket API is not healthy"
            if "application/json" not in response.headers.get("Content-Type", "").lower():
                return False, "Unexpected content type from ticket API"
            if response.geturl() != url:
                return False, "Ticket API redirected away from the configured endpoint"
            payload_bytes = response.read(_MAX_BYTES + 1)
        if len(payload_bytes) > _MAX_BYTES:
            return False, "Ticket API response exceeded size limit"
        payload = json.loads(payload_bytes)
    except HTTPError as exc:
        ray = exc.headers.get("CF-Ray", "") if exc.headers else ""
        # Never include response body (may contain an edge challenge or private info).
        suffix = f" (CF-Ray: {ray[:100]})" if ray else ""
        return False, f"HTTP {exc.code} from ticket API{suffix}; inspect edge access/WAF policies"
    except (URLError, TimeoutError, OSError) as exc:
        return False, f"Ticket API network error: {type(exc).__name__}"
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return False, "Ticket API returned invalid JSON"
    if not _fresh_snapshot(payload):
        return False, "Ticket API returned missing, invalid, or stale recorded prices"
    return True, "Ticket API reachable with verified fresh recorded prices"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    origin = os.environ.get("ANDROID_PRODUCTION_API_ORIGIN", "")
    try:
        validate_origin(origin)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    if args.validate_only:
        print("Production API origin is HTTPS and syntactically valid")
        return 0
    okay, detail = probe_ticket_api(origin)
    if okay:
        print(detail)
        return 0
    print(f"::warning::{detail}. The signed release may still be published; "
          "the Android app handles an unavailable price API.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
