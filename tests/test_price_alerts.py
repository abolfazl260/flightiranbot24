import pytest
from sqlalchemy import select

from flightiran.db.models import PriceAlert, PriceSnapshot

from flightiran.db import initialize_database
from flightiran.db.models import User
from flightiran.modules.tickets.alerts import PriceAlertService


@pytest.mark.asyncio
async def test_price_alert_threshold_and_snapshot_dedup(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'prices.db'}")
    async with db.session() as session:
        user = User(telegram_id=55)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = PriceAlertService(db)
    route = await service.save_route(user_id, "ika", "fra")
    alert = await service.create(user_id, route.id, 90, "EUR")
    notified = []

    async def notify(alert, snapshot):
        notified.append(snapshot.price)

    assert not await service.process_price(alert.id, 100, notify)
    assert not await service.process_price(alert.id, 100, notify)
    assert await service.process_price(alert.id, 80, notify)
    assert not await service.process_price(alert.id, 80, notify)
    assert notified == [80]
    await db.close()


@pytest.mark.asyncio
async def test_price_alert_limit_and_failed_notification(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'limits.db'}")
    async with db.session() as session:
        user = User(telegram_id=56)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = PriceAlertService(db, max_alerts_per_user=1)
    route = await service.save_route(user_id, "IKA", "FRA")
    alert = await service.create(user_id, route.id, 90, "EUR")
    with pytest.raises(ValueError):
        await service.create(user_id, route.id, 80, "EUR")

    async def fail(alert, snapshot):
        raise RuntimeError("send failed")

    await service.process_price(alert.id, 70, fail)
    await service.set_status(alert.id, "paused")
    await db.close()

@pytest.mark.asyncio
async def test_failed_price_notification_retries_without_duplicate_snapshot(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'price_retry.db'}")
    async with db.session() as session:
        user = User(telegram_id=88)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = PriceAlertService(db)
    route = await service.save_route(user_id, "IKA", "FRA")
    alert = await service.create(user_id, route.id, 90, "EUR")
    attempts = []
    async def fail(alert, snapshot):
        attempts.append(snapshot.id)
        raise RuntimeError("telegram down")
    async def succeed(alert, snapshot):
        attempts.append(snapshot.id)

    assert not await service.process_price(alert.id, 70, fail)
    async with db.session() as session:
        assert (await session.get(PriceAlert, alert.id)).last_snapshot_hash is None
    assert await service.process_price(alert.id, 70, succeed)
    assert not await service.process_price(alert.id, 70, succeed)
    assert len(attempts) == 2 and attempts[0] == attempts[1]
    async with db.session() as session:
        snapshots = (await session.scalars(select(PriceSnapshot))).all()
        assert len(snapshots) == 1 and snapshots[0].notified
    await db.close()
