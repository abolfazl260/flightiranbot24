"""Publication, consent, ownership, exact source archives and real numeric statistics."""

import hashlib
import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from flightiran.config import Settings
from flightiran.db import initialize_database
from flightiran.db.models import ExperienceAudit, TravelExperience
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.modules.experiences.persistent import ExperienceError, SQLiteExperienceService
from flightiran.webapp.app import create_app

ARCHIVE = Path("data/experiences/archive/github-168.v1.json")


@pytest.mark.asyncio
async def test_all_51_original_messages_round_trip_immutable_and_withheld(tmp_path):
    raw = json.loads(ARCHIVE.read_text())
    assert len(raw["records"]) == 51
    assert len({r["archive_id"] for r in raw["records"]}) == 51
    assert [r["order"] for r in raw["records"]] == list(range(1, 52))
    for block in raw["blocks"]:
        records = [r for r in raw["records"] if r["source_comment_id"] == block["comment_id"]]
        assert "".join(r["raw_message"] for r in records) == block["verbatim"]
        assert hashlib.sha256(block["verbatim"].encode()).hexdigest() == block["sha256"]
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'archive.db'}")
    service = SQLiteExperienceService(db)
    assert await service.import_archive(ARCHIVE) == 51
    assert await service.import_archive(ARCHIVE) == 51
    async with db.session() as session:
        rows = (await session.scalars(select(TravelExperience).order_by(TravelExperience.id))).all()
        assert [r.raw_source for r in rows] == raw["records"]
        assert all(r.rating is None and not r.consent and r.public_text is None for r in rows)
        assert await session.scalar(select(func.count()).select_from(ExperienceAudit)) == 51
    assert not (await service.public())["items"]
    with pytest.raises(ExperienceError):
        await service.moderate(rows[0].id, state="approved", reason="test", actor="operator")
    await service.moderate(
        rows[0].id,
        state="approved",
        reason="Reviewed redacted view",
        actor="operator",
        consent_evidence="test-only permission reference",
        public_text="Approved redacted text",
        display_name="Anonymous",
        targets=["airport:IKA", "airline:iran-air", "country:IR"],
    )
    public = await service.public(target="airport:IKA")
    assert public["stats"]["average"] is None
    assert public["items"][0]["text"] == "Approved redacted text"
    assert public["items"][0]["rating"] is None
    async with db.session() as session:
        preserved = await session.get(TravelExperience, rows[0].id)
        assert preserved.raw_source == raw["records"][0]
        assert preserved.body == raw["records"][0]["raw_message"]
    await db.close()


@pytest.mark.asyncio
async def test_persistent_user_review_consent_moderation_edit_delete_votes_and_reports(tmp_path):
    path = tmp_path / "reviews.db"
    db = await initialize_database(f"sqlite+aiosqlite:///{path}")
    users = SQLiteUserRepository(db)
    a = await users.create(123)
    b = await users.create(456)
    service = SQLiteExperienceService(db)
    values = dict(
        targets=["airport:IKA", "country:IR"],
        body="Real travel experience <script>alert(1)</script>",
        rating=4,
        criteria={"cleanliness": 5},
        consent=True,
        display_name="Chosen name",
    )
    result = await service.submit(a.id, **values)
    identifier = result["id"]
    with pytest.raises(ExperienceError):
        await service.submit(a.id, **values)
    assert not (await service.public())["items"]
    with pytest.raises(ExperienceError):
        await service.update(b.id, identifier, remove=True)
    await service.moderate(identifier, state="approved", reason="Reviewed", actor="operator")
    public = await service.public(target="airport:IKA")
    assert public["stats"] == {
        "criteria": {"cleanliness": {"count": 1, "average": 5.0, "low_sample": True}},
        "rating_count": 1,
        "average": 4.0,
        "low_sample": True,
        "comparison_allowed": False,
    }
    assert not any(
        k in str(public)
        for k in ("owner_id", "raw_source", "consent_evidence", "moderation_reason")
    )
    await service.interact(b.id, identifier, helpful=True)
    await service.interact(b.id, identifier, helpful=True)
    assert (await service.public())["items"][0]["helpful"] == 1
    with pytest.raises(ExperienceError):
        await service.interact(a.id, identifier, helpful=True)
    await service.interact(b.id, identifier, report="privacy")
    changed = await service.update(a.id, identifier, **{**values, "consent": False})
    assert changed["experience_mutation"] is True and changed["modified_at"]
    assert not (await service.public())["items"]
    with pytest.raises(ExperienceError):
        await service.moderate(identifier, state="approved", reason="No consent", actor="operator")
    await service.update(a.id, identifier, **values)
    await service.moderate(identifier, state="approved", reason="Re-reviewed", actor="operator")
    await db.close()
    db = await initialize_database(f"sqlite+aiosqlite:///{path}")
    service = SQLiteExperienceService(db)
    assert len((await service.own(a.id))["items"]) == 1
    await service.update(a.id, identifier, remove=True)
    assert not (await service.public())["items"]
    await db.close()


@pytest.mark.asyncio
async def test_invalid_votes_no_consent_rate_limit_and_public_api_leak_boundaries(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    user = await SQLiteUserRepository(db).create(123)
    service = SQLiteExperienceService(db)
    args = dict(
        targets=["airline:iran-air"],
        body="A genuine user report, not an invented rating.",
        consent=True,
    )
    for rating in (True, 0, 6, 1.5):
        with pytest.raises(ExperienceError):
            await service.submit(user.id, **args, rating=rating)
    with pytest.raises(ExperienceError):
        await service.submit(user.id, **args, criteria={"safety": 5})
    for index in range(5):
        row = await service.submit(
            user.id, **{**args, "body": args["body"] + str(index)}, rating=index + 1
        )
        await service.moderate(row["id"], state="approved", reason="Fixture reviewed", actor="test")
    with pytest.raises(ExperienceError) as error:
        await service.submit(user.id, **{**args, "body": args["body"] + "extra"}, rating=5)
    assert error.value.status == 429
    stats = (await service.public())["stats"]
    assert stats["rating_count"] == 5 and stats["average"] == 3 and stats["comparison_allowed"]
    app = create_app(Settings(TELEGRAM_BOT_TOKEN="123456:fake-token"), activity_database=db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        response = await client.get("/api/v1/experiences?target=airline:iran-air&sort=rating")
        assert response.status_code == 200 and len(response.json()["items"]) == 5
        assert response.headers["cache-control"] == "no-store"
        assert "actor" not in response.text and "duplicate_key" not in response.text
        assert (await client.get("/api/v1/experiences/999")).status_code == 404
        assert (await client.get("/api/mini/experiences/mine")).status_code == 401
        assert (
            await client.post("/api/mini/experiences", json={**args, "user_id": user.id})
        ).status_code in (401, 422)
    await db.close()


@pytest.mark.asyncio
async def test_signed_identity_controls_private_experience_api_and_public_fixture(tmp_path):
    import hmac
    import time
    from urllib.parse import urlencode

    token = "123456:EXPERIENCES_SIGNED_TEST_TOKEN"

    def headers(who):
        values = {
            "auth_date": str(int(time.time())),
            "user": json.dumps({"id": who, "first_name": "Private actor"}),
        }
        key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
        values["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
        return {"X-Telegram-Init-Data": urlencode(values)}

    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'signed.db'}")
    app = create_app(
        Settings(
            TELEGRAM_BOT_TOKEN=token, WEB_APP_ENABLED=True, WEB_APP_URL="https://example.org/mini/"
        ),
        activity_database=db,
    )
    fixture = json.loads(Path("docs/fixtures/experiences-public-v1.json").read_text())
    row = fixture["items"][0]
    payload = {
        "targets": row["targets"],
        "body": row["text"],
        "rating": row["rating"],
        "criteria": row["criteria"],
        "consent": True,
        "display_name": row["display_name"],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        for extra in ({"user_id": 999}, {"state": "approved"}, {"consent": 1}, {"rating": True}):
            assert (
                await client.post(
                    "/api/mini/experiences", headers=headers(101), json={**payload, **extra}
                )
            ).status_code == 422
        created = await client.post("/api/mini/experiences", headers=headers(101), json=payload)
        assert created.status_code == 200
        identifier = created.json()["id"]
        assert not (await client.get("/api/mini/experiences/mine", headers=headers(202))).json()[
            "items"
        ]
        assert (
            await client.delete(f"/api/mini/experiences/{identifier}", headers=headers(202))
        ).status_code == 404
        service = SQLiteExperienceService(db)
        await service.moderate(
            identifier, state="approved", actor="fixture", reason="Reviewed consent"
        )
        actor = await SQLiteUserRepository(db).get_by_telegram_id(202)
        await service.interact(actor.id, identifier, helpful=True)
        body = (await client.get("/api/v1/experiences?target=airport:IKA")).json()
        actual = body["items"][0]
        for key in ("created_at", "modified_at"):
            actual[key] = row[key]
        assert body == fixture
        response = await client.patch(
            f"/api/mini/experiences/{identifier}",
            headers=headers(101),
            json={**payload, "consent": False},
        )
        assert response.status_code == 200 and response.json()["experience_mutation"]
        assert not (await client.get("/api/v1/experiences")).json()["items"]
    await db.close()


@pytest.mark.asyncio
async def test_airline_criteria_have_independent_denominators_and_publication_gates(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'criteria.db'}")
    users = SQLiteUserRepository(db)
    service = SQLiteExperienceService(db)
    for index, criteria in enumerate(
        [
            {"crew": 5, "checkin": 2, "baggage": 1, "value": 4},
            {"crew": 4, "value": 5},
            {"crew": 1},
            {"value": 1},
        ]
    ):
        user = await users.create(1000 + index)
        row = await service.submit(
            user.id,
            targets=["airline:iran-air", "route:IKA-IST"],
            body=f"Genuine test experience with distinct body {index}",
            rating=None,
            criteria=criteria,
            consent=True,
            display_name="Test",
        )
        if index != 3:
            await service.moderate(row["id"], state="approved", actor="test", reason="Reviewed")
    stats = (await service.public(target="airline:iran-air"))["stats"]
    assert stats["rating_count"] == 0 and stats["average"] is None
    assert stats["criteria"] == {
        "crew": {"count": 3, "average": 3.33, "low_sample": True},
        "checkin": {"count": 1, "average": 2.0, "low_sample": True},
        "baggage": {"count": 1, "average": 1.0, "low_sample": True},
        "value": {"count": 2, "average": 4.5, "low_sample": True},
    }
    assert not (await service.public(target="airline:emirates"))["stats"]["criteria"]
    assert (await service.public(target="route:IKA-IST"))["stats"] == stats
    other = await users.create(2000)
    with pytest.raises(ExperienceError):
        await service.submit(
            other.id,
            targets=["airport:IKA"],
            body="An airport-only review cannot rate airline baggage handling.",
            rating=None,
            criteria={"baggage": 5},
            consent=True,
            display_name="Test",
        )
    await db.close()
