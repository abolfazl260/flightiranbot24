import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from flightiran.config import Settings
from flightiran.webapp.app import create_app


def signed_init_data(token: str) -> str:
    values = {
        "auth_date": str(int(time.time())),
        "query_id": "q1",
        "user": '{"id":42,"first_name":"Test"}',
    }
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    payload = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    values["hash"] = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_webapp_health_and_authenticated_dashboard():
    settings = Settings(
        TELEGRAM_BOT_TOKEN="123456:AA-valid-token",
        WEB_APP_ENABLED=True,
        WEB_APP_URL="https://app.test",
    )
    client = TestClient(create_app(settings))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/api/dashboard").status_code == 401
    response = client.get(
        "/api/dashboard",
        headers={
            "X-Telegram-Init-Data": signed_init_data(settings.telegram_bot_token.get_secret_value())
        },
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == 42


@pytest.mark.asyncio
async def test_authenticated_web_app_activity_counts_in_daily_report(tmp_path):
    from httpx import ASGITransport, AsyncClient

    from flightiran.db import initialize_database
    from flightiran.modules.admin.daily_active import ActiveUsersReportRepository

    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'web-activity.db'}")
    settings = Settings(
        TELEGRAM_BOT_TOKEN="123456:AA-valid-token",
        WEB_APP_ENABLED=True,
        WEB_APP_URL="https://app.test",
    )
    app = create_app(settings, activity_database=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://app") as client:
        assert (await client.get("/api/dashboard")).status_code == 401
        assert await ActiveUsersReportRepository(db).collect() == []
        headers = {
            "X-Telegram-Init-Data": signed_init_data(
                settings.telegram_bot_token.get_secret_value()
            )
        }
        result = await client.get("/api/dashboard", headers=headers)
        assert result.status_code == 200
        assert result.json()["user_id"] == 42
        assert (await client.get("/api/session", headers=headers)).status_code == 200
    report = await ActiveUsersReportRepository(db).collect()
    assert len(report) == 1
    assert report[0].telegram_id == 42
    assert report[0].first_name == "Test"
    await db.close()
