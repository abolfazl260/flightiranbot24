"""Full fake-HTTP sync integration: watchers receive only substantive dataset updates."""

from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, select

from flightiran.db import initialize_database
from flightiran.db.models import VisaWatchEvent
from flightiran.db.repositories import SQLiteUserRepository
from flightiran.modules.visa.sync import VisaSyncService
from flightiran.modules.visa.watch import VisaWatchService


def iso_code(index: int) -> str:
    return chr(65 + index // 26) + chr(65 + index % 26)


@pytest.mark.asyncio
async def test_full_sync_emits_only_semantic_change_events(monkeypatch, tmp_path):
    # The upstream full matrix is 190+ destinations by 190+ passports. Use
    # valid but synthetic data and never connect to the external provider.
    countries = []
    documents = {}
    passports = [iso_code(i) for i in range(190)]
    for i in range(190):
        slug = f"example-{i}"
        code = iso_code(i)
        url = f"https://travelrequirements.info/data/destinations/{slug}.json"
        countries.append({
            "id": slug, "iso2": code, "url": url, "lastUpdated": "2026-10-08",
        })
        documents[url] = {
            "id": slug,
            "iso2": code,
            "names": {"common": f"Example {i}"},
            "meta": {"lastUpdated": "2026-10-08"},
            "visaPolicy": {
                "defaultSource": {
                    "url": "https://official.example/visa",
                    "type": "government", "lastVerified": "2026-10-08",
                },
                "byPassport": {
                    passport: {
                        "requirement": "visa-free", "maxStayDays": 30,
                    }
                    for passport in passports
                },
            },
            "visaTypes": [],
        }

    state = {"version": "initial"}

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return deepcopy(self.data)

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url):
            if url.endswith("/index.json"):
                return Response({
                    "version": state["version"],
                    "license": {"spdx": "CC-BY-4.0"},
                    "destinations": countries,
                })
            return Response(documents[url])

    monkeypatch.setattr("flightiran.modules.visa.sync.httpx.AsyncClient", Client)
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'sync-watch.db'}")
    sync = VisaSyncService(db)
    imported = await sync.sync()
    assert imported.status == "updated"
    assert imported.downloaded == 190
    assert imported.alerts_queued == 0

    user = await SQLiteUserRepository(db).create(88123)
    watchers = VisaWatchService(db)
    chosen = await watchers.subscribe(user.id, passports[0], iso_code(0))
    assert chosen.active

    country = countries[0]
    url = country["url"]
    newer = deepcopy(documents[url])
    newer["visaPolicy"]["byPassport"][passports[0]]["requirement"] = "embassy-visa"
    newer["visaPolicy"]["byPassport"][passports[0]]["maxStayDays"] = None
    newer["meta"]["lastUpdated"] = "2026-10-09"
    documents[url] = newer
    country["lastUpdated"] = "2026-10-09"
    state["version"] = "status-changed"

    changed = await sync.sync()
    assert changed.status == "updated"
    assert changed.downloaded == 1
    assert changed.alerts_queued == 1
    assert changed.changed == ("example-0",)

    # A third import with only upstream metadata changes must not notify users.
    newer = deepcopy(documents[url])
    newer["meta"]["lastUpdated"] = "2026-10-10"
    newer["visaPolicy"]["defaultSource"]["lastVerified"] = "2026-10-10"
    documents[url] = newer
    country["lastUpdated"] = "2026-10-10"
    state["version"] = "metadata-updated"

    editorial = await sync.sync()
    assert editorial.downloaded == 1
    assert editorial.status == "updated"  # admin sees changed JSON
    assert editorial.alerts_queued == 0    # user sees no meaningless alert

    async with db.session() as session:
        count = await session.scalar(
            select(func.count()).select_from(VisaWatchEvent)
        )
    assert count == 1
    await db.close()
