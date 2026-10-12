"""The replica only uploads whitelisted public facts; failures never checkpoint."""
from __future__ import annotations

import json
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
