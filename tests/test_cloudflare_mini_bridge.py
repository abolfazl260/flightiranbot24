"""Integration tests for the free workers.dev Mini App outbound SQLite bridge."""

import hashlib
import hmac
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from flightiran.cloudflare_mini_bridge import (
    MiniAppBridge,
    job_destination,
    signed_local_init_data,
)
from flightiran.config import Settings
from flightiran.db import initialize_database
from flightiran.db.models import VisaRuleIndex
from flightiran.db.repositories import SQLiteMz724PriceHistoryRepository
from flightiran.modules.webapp import WebAppAuthenticator
from flightiran.webapp.app import create_app

BOT_TOKEN = "123456:AA-test-bot-token-that-is-long-enough"
PUBLISH_TOKEN = "p" * 48
WORKER = "https://flightiran-public-api.abolfazl260.workers.dev/"


def test_internal_bridge_attestation_is_local_and_validated():
    job = {
        "telegram_id": 42,
        "user": {"first_name": "رضا", "username": "traveler", "last_name": None},
        "operation": "bootstrap",
        "payload": {},
    }
    signed = signed_local_init_data(BOT_TOKEN, job)
    result = WebAppAuthenticator(BOT_TOKEN).validate(signed)
    user = json.loads(result["user"])
    assert user["id"] == 42
    assert user["first_name"] == "رضا"
    assert "auth_date=" in signed
    assert int(result["auth_date"]) >= int(time.time()) - 2

    with pytest.raises(ValueError, match="identifier"):
        signed_local_init_data(BOT_TOKEN, {**job, "telegram_id": "42"})
    with pytest.raises(ValueError, match="profile"):
        signed_local_init_data(BOT_TOKEN, {**job, "user": {"username": "x" * 200}})
    with pytest.raises(ValueError, match="operation"):
        job_destination({**job, "operation": "../../api/admin"})
    with pytest.raises(ValueError, match="alert identifier"):
        job_destination({**job, "operation": "price_delete", "payload": {"id": -10}})
    assert job_destination({**job, "operation": "price_status", "payload": {
        "id": 18, "status": "paused"
    }}) == ("PATCH", "/api/mini/alerts/prices/18", {"status": "paused"})


def test_d1_job_queue_migration_is_additive_and_bounds_private_storage():
    root = Path(__file__).resolve().parents[1] / "cloudflare" / "migrations"
    connection = sqlite3.connect(":memory:")
    try:
        for name in (
            "0001_public_data.sql",
            "0002_d1_ticket_prices.sql",
            "0003_telegram_mini_jobs.sql",
        ):
            connection.executescript((root / name).read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO airports(code,name,country,timezone) VALUES (?,?,?,?)",
            ("IKA", "فرودگاه", "IR", "Asia/Tehran"),
        )
        connection.execute(
            "INSERT INTO telegram_mini_jobs(id,telegram_id,user_json,operation,"
            "payload_json,status,created_at_ms) VALUES (?,?,?,?,?,'pending',?)",
            ("job-123", 42, '{"first_name":"رضا"}', "bootstrap", "{}", 1000),
        )
        assert connection.execute(
            "SELECT telegram_id,operation FROM telegram_mini_jobs"
        ).fetchone() == (42, "bootstrap")
        assert connection.execute(
            "SELECT name FROM airports WHERE code='IKA'"
        ).fetchone()[0] == "فرودگاه"
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO telegram_mini_jobs(id,telegram_id,user_json,operation,"
                "payload_json,status,created_at_ms) VALUES (?,?,?,?,?,'pending',?)",
                ("bad-job", 52, "invalid-json", "alerts", "{}", 1000),
            )
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_bridge_reuses_bot_sqlite_with_no_inbound_port_and_owner_scoping(tmp_path):
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'mini-bridge.db'}")
    await SQLiteMz724PriceHistoryRepository(database).record_snapshot(
        [("تهران", "کیش", 5_000_000)],
        captured_at=datetime.now(timezone.utc).replace(microsecond=0),
        retention_days=21,
    )
    async with database.session() as session:
        session.add(VisaRuleIndex(
            passport="IR", destination="TR", country_name="ترکیه",
            status="visa-free", stay_days=90, notes=None,
            source_url="https://example.org/visa",
            verified_on="2026-10-11", source_level="official",
        ))
    settings = Settings(
        TELEGRAM_BOT_TOKEN=BOT_TOKEN,
        WEB_APP_ENABLED=True,
        WEB_APP_URL="https://flightiran-public-api.abolfazl260.workers.dev/mini/",
    )
    app = create_app(settings, activity_database=database)
    uuid = lambda n: f"11111111-1111-4111-8111-{n:012d}"  # noqa: E731
    def user_job(n, uid, operation, payload=None):
        return {
            "id": uuid(n), "telegram_id": uid,
            "user": {"first_name": f"User{uid}", "username": f"visitor{uid}"},
            "operation": operation, "payload": payload or {},
        }
    jobs = [
        user_job(1, 42, "bootstrap"),
        user_job(2, 42, "passport", {"passport": "IR"}),
        user_job(3, 42, "price_create", {
            "origin": "تهران", "destination": "کیش", "kind": "percent",
            "threshold_percent": 10,
        }),
        user_job(4, 84, "alerts"),
        user_job(5, 42, "alerts"),
        user_job(6, 42, "visa_create", {"passport": "IR", "destination": "TR"}),
        user_job(7, 84, "alerts"),
        user_job(8, 42, "useful"),
    ]
    responses = {}
    outbound_headers = []

    def server(request: httpx.Request) -> httpx.Response:
        assert request.url.scheme == "https"
        assert request.headers["authorization"] == "Bearer " + PUBLISH_TOKEN
        assert "x-telegram-init-data" not in request.headers
        assert BOT_TOKEN not in str(request.url)
        outbound_headers.append(request.headers)
        if request.method == "GET":
            return httpx.Response(200, json={"jobs": jobs})
        identifier = request.url.path.split("/")[-2]
        data = json.loads(request.content)
        assert isinstance(data["http_status"], int)
        assert BOT_TOKEN not in json.dumps(data, ensure_ascii=False)
        responses[identifier] = data
        return httpx.Response(200, json={"accepted": True})

    try:
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://localhost",
            ) as local,
            httpx.AsyncClient(transport=httpx.MockTransport(server)) as remote,
        ):
            bridge = MiniAppBridge(WORKER, PUBLISH_TOKEN, BOT_TOKEN, local, remote)
            assert await bridge.sync_once() == len(jobs)
        assert responses[uuid(1)]["http_status"] == 200
        assert responses[uuid(1)]["body"]["passport"] == "IR"
        assert "id" not in responses[uuid(1)]["body"]["user"]
        assert responses[uuid(3)]["http_status"] == 201
        assert len(responses[uuid(4)]["body"]["prices"]) == 0
        assert len(responses[uuid(5)]["body"]["prices"]) == 1
        assert responses[uuid(6)]["http_status"] == 201
        assert len(responses[uuid(7)]["body"]["visa"]) == 0
        links = [
            item["url"] for cat in responses[uuid(8)]["body"]["categories"]
            for item in cat["links"]
        ]
        assert "https://t.me/advertio_cargo/526" in links
        assert len(outbound_headers) == len(jobs) + 1
    finally:
        await database.close()


@pytest.mark.asyncio
async def test_bridge_rejects_invalid_jobs_without_issuing_signed_side_effects(tmp_path):
    database = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'invalid.db'}")
    settings = Settings(TELEGRAM_BOT_TOKEN=BOT_TOKEN, WEB_APP_ENABLED=True,
        WEB_APP_URL=WORKER+"mini/")
    app = create_app(settings, activity_database=database)
    posted = []
    job = {
        "id": "22222222-2222-4222-8222-222222222222",
        "telegram_id": "not-an-id", "user": {"first_name": "hacker"},
        "operation": "price_create",
        "payload": {"origin": "fake", "destination": "fake",
                    "kind": "percent", "threshold_percent": 10},
    }

    def server(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"jobs": [job]})
        posted.append(json.loads(request.content))
        return httpx.Response(200, json={"accepted": True})

    try:
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://localhost"
            ) as local,
            httpx.AsyncClient(transport=httpx.MockTransport(server)) as remote,
        ):
            bridge = MiniAppBridge(WORKER, PUBLISH_TOKEN, BOT_TOKEN, local, remote)
            assert await bridge.sync_once() == 1
        assert posted[0]["http_status"] == 422
    finally:
        await database.close()
