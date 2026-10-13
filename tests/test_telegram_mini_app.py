"""Telegram Mini App end-to-end contract: authentication, UI, own data only."""

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from flightiran.config import Settings
from flightiran.db import initialize_database
from flightiran.db.models import VisaRuleIndex
from flightiran.db.repositories import SQLiteMz724PriceHistoryRepository
from flightiran.modules.webapp import WebAppAuthenticator
from flightiran.webapp.app import create_app

BOT_TOKEN = "123456:AA-valid-token-for-miniapp"
URL = "https://travel.example/mini/"


def signed_user(
    telegram_id: int = 42, *, token: str = BOT_TOKEN,
    auth_date: int | None = None, name: str = "مسافر",
) -> str:
    values = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "user": json.dumps(
            {"id": telegram_id, "first_name": name, "username": "test_telegram"},
            ensure_ascii=False, separators=(",", ":"),
        ),
    }
    key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    values["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def headers(telegram_id: int = 42) -> dict[str, str]:
    return {"X-Telegram-Init-Data": signed_user(telegram_id)}


def mini_settings(enabled: bool = True) -> Settings:
    return Settings(
        TELEGRAM_BOT_TOKEN=BOT_TOKEN, WEB_APP_ENABLED=enabled,
        WEB_APP_URL=URL, TELEGRAM_BOT_USERNAME="Flightiranbot",
    )


def test_rtl_shell_and_static_assets_have_safe_browser_headers():
    with TestClient(create_app(mini_settings())) as client:
        for route in ("/", "/mini", "/mini/"):
            response = client.get(route)
            assert response.status_code == 200
            assert 'lang="fa" dir="rtl"' in response.text
            assert "https://telegram.org/js/telegram-web-app.js" in response.text
            assert 'id="screen-visa"' in response.text
            assert 'id="screen-airports"' in response.text
            assert response.headers["cache-control"] == "no-store"
            assert "object-src 'none'" in response.headers["content-security-policy"]
            assert "unsafe-inline" not in response.headers["content-security-policy"]
        js = client.get("/assets/mini.js")
        css = client.get("/assets/mini.css")
        assert js.status_code == css.status_code == 200
        assert 'window.Telegram' in js.text
        assert "innerHTML" not in js.text
        assert "eval(" not in js.text
        assert "dir" in css.text or "RTL-first" in css.text


def test_webapp_key_validation_rejects_duplicate_and_future_signed_values():
    auth = WebAppAuthenticator(BOT_TOKEN)
    signed = signed_user()
    assert auth.validate(signed)["user"]
    with pytest.raises(ValueError):
        auth.validate(signed + "&auth_date=1")
    with pytest.raises(ValueError):
        auth.validate(signed_user(auth_date=int(time.time()) + 3600))
    with pytest.raises(ValueError):
        auth.validate(signed_user(auth_date=int(time.time()) - 90000))
    with pytest.raises(ValueError):
        auth.validate("a" * 8193)


@pytest.mark.asyncio
async def test_mini_api_authenticated_user_alerts_visas_and_fare_workflow(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'mini.db'}")
    await SQLiteMz724PriceHistoryRepository(db).record_snapshot(
        [("تهران", "مشهد", 3_400_000), ("تهران", "کیش", 4_500_000)],
        captured_at=datetime.now(timezone.utc).replace(microsecond=0),
        retention_days=21,
    )
    async with db.session() as session:
        session.add_all([
            VisaRuleIndex(
                passport="IR", destination="TR", country_name="ترکیه",
                status="visa-free", stay_days=90, notes="تا ۹۰ روز",
                source_url="https://example.com/visa", verified_on="2026-10-11",
                source_level="official",
            ),
            VisaRuleIndex(
                passport="US", destination="IR", country_name="ایران",
                status="embassy-visa", stay_days=None, notes=None,
                source_url="https://example.com/iran", verified_on="2026-10-11",
                source_level="official",
            ),
        ])
    app = create_app(mini_settings(), activity_database=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://server") as c:
        assert (await c.get("/api/mini/bootstrap")).status_code == 401
        assert (await c.get("/api/mini/visa")).status_code == 401
        assert (await c.get("/api/mini/alerts")).status_code == 401
        assert (await c.post("/api/mini/alerts/prices", json={})).status_code == 401
        assert (await c.get(
            "/api/mini/bootstrap", headers={"X-Telegram-Init-Data": signed_user(token="wrong")}
        )).status_code == 401
        bootstrap = await c.get("/api/mini/bootstrap", headers=headers())
        assert bootstrap.status_code == 200
        assert bootstrap.headers["cache-control"] == "no-store"
        assert bootstrap.json()["passport"] == "IR"
        assert bootstrap.json()["links"]["bot"] == "https://t.me/Flightiranbot"
        assert bootstrap.json()["links"]["cargo"] == "https://t.me/advertio_cargo"
        assert "id" not in bootstrap.json()["user"]
        assert any(x["code"] == "TR" for x in bootstrap.json()["countries"])

        visa = await c.get("/api/mini/visa", headers=headers())
        assert visa.status_code == 200
        assert len(visa.json()["rules"]) == 1
        assert visa.json()["rules"][0]["destination"] == "TR"
        detail = await c.get(
            "/api/mini/visa/rule?passport=IR&destination=TR", headers=headers()
        )
        assert detail.status_code == 200
        assert detail.json()["source_url"] == "https://example.com/visa"
        assert "raw_data" not in detail.json()
        assert (await c.get("/api/mini/visa?passport=I!", headers=headers())).status_code == 422

        assert (await c.post("/api/mini/passport",headers=headers(),json={
            "passport":"US"
        })).status_code == 200
        assert (await c.get("/api/mini/bootstrap",headers=headers())).json()["passport"] == "US"
        assert (await c.get("/api/mini/bootstrap",headers=headers(84))).json()[
            "passport"
        ] == "IR"
        assert (await c.post("/api/mini/passport",headers=headers(),json={
            "passport":"!R"
        })).status_code == 422

        prices = await c.get("/api/v1/tickets/prices")
        assert prices.status_code == 200
        assert prices.json()["stale"] is False
        created = await c.post("/api/mini/alerts/prices",headers=headers(),json={
            "origin":"تهران","destination":"مشهد",
            "kind":"percent","threshold_percent":10,
        })
        assert created.status_code == 201, created.text
        price_id = created.json()["id"]
        assert (await c.post("/api/mini/alerts/prices",headers=headers(),json={
            "origin":"ساختگی","destination":"مشهد",
            "kind":"percent","threshold_percent":10,
        })).status_code == 422
        assert (await c.post("/api/mini/alerts/prices",headers=headers(),json={
            "origin":"تهران","destination":"مشهد",
            "kind":"percent","threshold_percent":51,
        })).status_code == 422
        assert (await c.post("/api/mini/alerts/prices",headers=headers(),json={
            "origin":"تهران","destination":"مشهد",
            "kind":"percent","threshold_percent":11,
        })).status_code == 422
        watch = await c.post("/api/mini/alerts/visa",headers=headers(),json={
            "passport":"IR","destination":"TR"
        })
        assert watch.status_code == 201,watch.text
        watch_id = watch.json()["id"]
        assert (await c.post("/api/mini/alerts/visa",headers=headers(),json={
            "passport":"IR","destination":"ZZ"
        })).status_code == 422

        own = (await c.get("/api/mini/alerts",headers=headers())).json()
        assert len(own["prices"]) == len(own["visa"]) == 1
        assert own["prices"][0]["target_percent"] == 10
        other = (await c.get("/api/mini/alerts",headers=headers(84))).json()
        assert other == {"prices":[],"visa":[]}
        assert (await c.patch(f"/api/mini/alerts/prices/{price_id}",headers=headers(84),
          json={"status":"paused"})).status_code == 404
        assert (await c.delete(f"/api/mini/alerts/visa/{watch_id}",
          headers=headers(84))).status_code == 404
        assert (await c.patch(f"/api/mini/alerts/prices/{price_id}",headers=headers(),
          json={"status":"paused"})).status_code == 200
        assert (await c.patch(f"/api/mini/alerts/prices/{price_id}",headers=headers(),
          json={"status":"active"})).status_code == 200
        assert (await c.patch(f"/api/mini/alerts/visa/{watch_id}",headers=headers(),
          json={"active":False})).status_code == 200
        assert (await c.delete(f"/api/mini/alerts/prices/{price_id}",
          headers=headers())).status_code == 200
        assert (await c.delete(f"/api/mini/alerts/visa/{watch_id}",
          headers=headers())).status_code == 200
        assert (await c.get("/api/mini/alerts",headers=headers())).json() == {
            "prices":[],"visa":[]
        }
        useful = await c.get("/api/mini/useful",headers=headers())
        assert useful.status_code == 200
        all_links = [
            item["url"] for group in useful.json()["categories"] for item in group["links"]
        ]
        assert "https://t.me/advertio_cargo/526" in all_links
        assert all(link.startswith("https://") for link in all_links)
    await db.close()


def test_disabled_mini_app_denies_identity_and_protected_data():
    app = create_app(mini_settings(enabled=False))
    with TestClient(app) as c:
        assert c.get("/healthz").json() == {"status":"ok"}
        assert c.get("/api/mini/bootstrap",headers=headers()).status_code == 401
        assert c.get("/api/mini/alerts",headers=headers()).status_code == 401
        assert c.get("/api/v1/tickets/prices").status_code == 503


@pytest.mark.asyncio
async def test_resuming_prices_cannot_exceed_active_alert_limit(tmp_path):
    from flightiran.db.repositories import SQLiteUserRepository
    from flightiran.modules.tickets.alerts import PriceAlertService

    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'limit.db'}")
    users = SQLiteUserRepository(db)
    user = await users.get_or_create(12345)
    service = PriceAlertService(db, max_alerts_per_user=1)
    route = await service.save_route(user.id, "تهران", "کیش")
    first = await service.create_percent(user.id, route.id, 10)
    assert await service.set_user_status(user.id, first.id, "paused")
    second = await service.create_percent(user.id, route.id, 15)
    assert second.id != first.id
    with pytest.raises(ValueError, match="limit"):
        await service.set_user_status(user.id, first.id, "active")
    rows = await service.list_user_alerts(user.id)
    assert sum(item.status == "active" for item in rows) == 1
    await db.close()


def test_android_and_mini_travel_checklist_parity():
    """Prevent future drift in the Persian twelve-item checklist and airport launch state."""
    import re
    from pathlib import Path
    from xml.etree import ElementTree

    root = Path(__file__).resolve().parents[1]
    android = root / "android/app/src/main"
    mini = root / "src/flightiran/webapp/static"
    java = (android / "java/com/abolfazl260/flightiranbot24/ChecklistActivity.java").read_text()
    js = (mini / "mini.js").read_text()
    html = (mini / "index.html").read_text()
    strings = {
        item.attrib["name"]: item.text
        for item in ElementTree.parse(android / "res/values/strings.xml").getroot()
        if item.tag == "string"
    }

    java_keys = re.search(r"static final String\[\] KEYS = \{(.*?)\};", java, re.S)
    assert java_keys is not None
    native_keys = re.findall(r'"([a-z]+)"', java_keys.group(1))
    assert len(native_keys) == 12 and len(set(native_keys)) == 12

    mini_groups = js.split("const checklistGroups = [", 1)[1].split(
        "const checklistKeys =", 1
    )[0]
    mini_items = re.findall(r'\["([a-z]+)","([^"]+)"\]', mini_groups)
    assert len(mini_items) == 12
    assert [key for key, _ in mini_items] == native_keys
    assert all(label == strings["check_" + key] for key, label in mini_items)
    for group in ("documents", "health", "essentials"):
        assert strings["checklist_category_" + group] in mini_groups
        assert strings["checklist_category_" + group + "_detail"] in mini_groups

    for marker in ('id="screen-checklist"', 'id="checklist-progress"',
                   'id="checklist-reset"', 'data-go="checklist"'):
        assert marker in html
    assert 'lang="fa" dir="rtl"' in html
    assert "localStorage.setItem(state.checklistKey" in js
    assert 'telegram?.initDataUnsafe?.user?.id' in js
    assert "state.checklist.clear()" in js

    airport = (android / "java/com/abolfazl260/flightiranbot24/"
               "AirportDirectoryActivity.kt").read_text()
    assert "AirportComingSoonScreen" in airport
    assert "loadOfflineCatalog()" not in airport
    assert "TravelFormField" not in airport
    assert "airports_coming_soon_message" in airport
    assert 'id="screen-airports"' in html
    assert "اطلاعات فرودگاه‌ها به‌زودی" in html
