import hashlib
import hmac
import time
from urllib.parse import urlencode

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
