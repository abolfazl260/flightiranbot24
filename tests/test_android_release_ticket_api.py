"""Offline tests for the release-ticket health probe (no network access)."""
import io
import json
from datetime import datetime, timedelta, timezone
from email.message import Message
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

# The scripts/ directory is not an installed Python package in the project.
# Import the checked-in executable by its exact path without modifying sys.path.
source = Path(__file__).resolve().parents[1] / "scripts" / "check_android_release_ticket_api.py"
spec = spec_from_file_location("check_android_release_ticket_api", source)
assert spec and spec.loader
module = module_from_spec(spec)
spec.loader.exec_module(module)
_fresh_snapshot = module._fresh_snapshot
probe_ticket_api = module.probe_ticket_api
validate_origin = module.validate_origin


def snapshot(minutes_old=10, stale=False):
    return {
        "currency": "TOMAN",
        "stale": stale,
        "observed_at": (datetime.now(timezone.utc) - timedelta(minutes=minutes_old))
            .isoformat(),
        "routes": [{"origin": "تهران", "destination": "مشهد"}],
    }


class FakeResponse:
    def __init__(self, payload, url, *, status=200, content_type="application/json"):
        self.status = status
        self.url = url
        self.headers = {"Content-Type": content_type}
        self.stream = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size):
        return self.stream.read(size)

    def geturl(self):
        return self.url


ORIGIN = "https://example.workers.dev/"
ENDPOINT = ORIGIN + "api/v1/tickets/prices"


def open_response(data, *, url=ENDPOINT, content_type="application/json"):
    encoded = json.dumps(data).encode("utf-8")
    def opener(req, timeout):
        assert req.full_url == ENDPOINT
        assert timeout == 15
        return FakeResponse(encoded, url, content_type=content_type)
    return opener


@pytest.mark.parametrize("bad", [
    "", "http://example.workers.dev/", "https://example.workers.dev/path/",
    "https://alice:secret@example.workers.dev/",
    "https://example.workers.dev/?x=1", "https://example.workers.dev/#frag",
    "https://example.workers.dev",
])
def test_rejects_bad_api_origin(bad):
    with pytest.raises(ValueError):
        validate_origin(bad)


def test_accepts_strict_https_origin():
    assert validate_origin(ORIGIN) == ORIGIN


def test_good_recent_snapshot_allows_check_to_pass():
    ok, message = probe_ticket_api(ORIGIN, open_response(snapshot()))
    assert ok is True
    assert "fresh" in message


@pytest.mark.parametrize("bad", [
    snapshot(minutes_old=360), snapshot(stale=True), {},
    {"currency": "TOMAN", "routes": [], "stale": False},
])
def test_stale_or_incomplete_prices_never_report_healthy(bad):
    ok, msg = probe_ticket_api(ORIGIN, open_response(bad))
    assert not ok
    assert "stale" in msg or "missing" in msg


def test_rejects_future_date_and_undated_records():
    assert not _fresh_snapshot(snapshot(minutes_old=-30))
    item = snapshot()
    item["observed_at"] = "2026-11-01"
    assert not _fresh_snapshot(item)


def test_403_reports_edge_status_and_ray_without_leaking_body():
    def opener(req, timeout):
        headers = Message()
        headers["CF-Ray"] = "test-ray-identifier"
        raise HTTPError(req.full_url, 403, "Forbidden", headers, None)
    ok, detail = probe_ticket_api(ORIGIN, opener)
    assert not ok
    assert "403" in detail and "CF-Ray" in detail
    assert "test-ray-identifier" in detail


@pytest.mark.parametrize("code", [429, 500, 503])
def test_other_http_errors_not_healthy(code):
    def opener(req, timeout):
        raise HTTPError(req.full_url, code, "Upstream error", Message(), None)
    ok, _ = probe_ticket_api(ORIGIN, opener)
    assert not ok


def test_network_failure_is_advisory_not_healthy():
    def opener(req, timeout):
        raise URLError("network failure")
    ok, detail = probe_ticket_api(ORIGIN, opener)
    assert not ok
    assert "network" in detail


def test_invalid_content_type_or_redirect_is_not_healthy():
    ok, detail = probe_ticket_api(ORIGIN, open_response(snapshot(),
        content_type="text/html"))
    assert not ok and "content type" in detail
    ok, detail = probe_ticket_api(ORIGIN, open_response(snapshot(),
        url="https://elsewhere.example/api/v1/tickets/prices"))
    assert not ok and "redirected" in detail


def test_oversized_or_invalid_json_response_is_not_healthy():
    def oversized(req, timeout):
        return FakeResponse(b"x" * 1_500_001, ENDPOINT)
    assert probe_ticket_api(ORIGIN, oversized)[0] is False

    def invalid_json(req, timeout):
        return FakeResponse(b"not-json", ENDPOINT)
    assert probe_ticket_api(ORIGIN, invalid_json)[0] is False
