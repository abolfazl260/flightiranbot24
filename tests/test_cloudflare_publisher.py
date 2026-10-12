"""The replica only uploads whitelisted public facts; failures never checkpoint."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from flightiran.cloudflare_publish import (
    PublicPublisher,
    clean_source_url,
    public_airports,
    public_visa_row,
    validate_origin,
)


def test_api_origin_is_https_root_without_credentials():
    assert validate_origin("https://flightiran-public-api.example.workers.dev/").startswith("https://")
    for origin in (
        "http://example.com/", "https://example.com/a/", "https://u:p@example.com/",
        "https://example.com/?token=sensitive", "https://example.com", "",
    ):
        with pytest.raises(ValueError):
            validate_origin(origin)


def test_airport_projection_and_visa_allowlist_cannot_contain_private_fields():
    data = public_airports()
    assert len(data["airports"]) > 10
    assert set(data["airports"][0]) == {"code", "country", "name", "timezone"}
    row = SimpleNamespace(
        passport="IR", country_name="ترکیه", status="visa-free", stay_days=90,
        notes="شرایط ورود", source_url="https://example.org/visa",
        verified_on="2026-10-11", source_level="official",
        telegram_user_id=123456, passport_holder="SECRET",
    )
    result = public_visa_row(row)
    assert set(result) == {
        "passport", "country_name", "status", "stay_days", "notes",
        "source_url", "verified_on", "source_level",
    }
    assert "123456" not in json.dumps(result)
    assert "SECRET" not in json.dumps(result)
    assert clean_source_url("http://insecure.invalid/") is None
    assert clean_source_url("https://example.com/rule") == "https://example.com/rule"


@pytest.mark.asyncio
async def test_incremental_upload_checkpoint_no_replay_or_secret_on_disk(tmp_path: Path):
    sent = []

    def receive(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        assert request.headers["authorization"] == "Bearer " + ("S" * 40)
        assert request.url.path == "/internal/v1/airports"
        assert request.headers["content-type"] == "application/json"
        return httpx.Response(200, json={"published": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
        checkpoint = tmp_path / "synced.json"
        publisher = PublicPublisher(
            database=None, origin="https://public.example/", token="S" * 40,
            checkpoint=checkpoint, client=client,
        )
        payload = {"airports": [{"code": "IKA", "name": "تهران", "country": "IR"}]}
        assert await publisher.publish("airports", "internal/v1/airports", payload)
        assert not await publisher.publish("airports", "internal/v1/airports", payload)
        assert len(sent) == 1
        assert "SSSS" not in checkpoint.read_text()
        again = PublicPublisher(None, "https://public.example/", "S" * 40, checkpoint, client)
        assert not await again.publish("airports", "internal/v1/airports", payload)
        assert len(sent) == 1


@pytest.mark.asyncio
async def test_failed_import_does_not_commit_checkpoint(tmp_path: Path):
    async def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as client:
        checkpoint = tmp_path / "failure.json"
        publisher = PublicPublisher(None, "https://public.example/", "S" * 40, checkpoint, client)
        with pytest.raises(httpx.HTTPStatusError):
            await publisher.publish("airports", "internal/v1/airports", {"airports": []})
        assert publisher.state == {}
        assert not checkpoint.exists()


@pytest.mark.asyncio
async def test_migration_from_legacy_r2_checkpoint_replays_into_new_d1(tmp_path: Path):
    """Old R2 fingerprints must not skip the first D1 publication."""
    origin = "https://public.example/"
    old_scope = hashlib.sha256(origin.encode()).hexdigest()[:16]
    checkpoint = tmp_path / "sync.json"
    checkpoint.write_text(json.dumps({
        "scope": old_scope,
        "fingerprints": {"tickets": "old-fingerprint", "airports": "old-fingerprint"},
    }), encoding="utf-8")
    seen = []

    def receive(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"published": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as client:
        publisher = PublicPublisher(None, origin, "S" * 40, checkpoint, client)
        assert publisher.state == {}
        assert await publisher.publish("tickets", "internal/v1/tickets/prices", {
            "currency": "TOMAN", "stale": True,
        })
        assert len(seen) == 1
        assert checkpoint.exists()
        assert json.loads(checkpoint.read_text())["scope"] != old_scope


def test_d1_incremental_migration_preserves_existing_public_data():
    """Exercise migrations against SQLite, including guarded single-row pricing."""
    root = Path(__file__).resolve().parent.parent / "cloudflare" / "migrations"
    connection = sqlite3.connect(":memory:")
    try:
        for script in ("0001_public_data.sql", "0002_d1_ticket_prices.sql"):
            connection.executescript((root / script).read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO airports(code,name,country,timezone) VALUES (?,?,?,?)",
            ("IKA", "امام خمینی", "IR", "Asia/Tehran"),
        )
        statement = (
            "INSERT INTO ticket_price_snapshots(id,observed_epoch_ms,snapshot_json,published_at) "
            "VALUES (1,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "observed_epoch_ms=excluded.observed_epoch_ms, "
            "snapshot_json=excluded.snapshot_json, "
            "published_at=excluded.published_at "
            "WHERE excluded.observed_epoch_ms >= ticket_price_snapshots.observed_epoch_ms"
        )
        fresh = '{"routes":[{"origin":"تهران"}]}'
        older = '{"routes":[{"origin":"قدیمی"}]}'
        assert connection.execute(statement, (200, fresh, "2026-10-12")).rowcount == 1
        assert connection.execute(statement, (100, older, "2026-10-11")).rowcount == 0
        assert connection.execute(
            "SELECT observed_epoch_ms,snapshot_json FROM ticket_price_snapshots WHERE id=1"
        ).fetchone() == (200, fresh)
        assert connection.execute(
            "SELECT count(*) FROM ticket_price_snapshots"
        ).fetchone()[0] == 1
        assert connection.execute("SELECT name FROM airports WHERE code='IKA'").fetchone()[0] == "امام خمینی"
    finally:
        connection.close()
