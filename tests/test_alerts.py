import pytest
from sqlalchemy import select

from flightiran.db import initialize_database
from flightiran.db.models import FlightAlertEvent, User
from flightiran.modules.flight_tracking.alerts import AlertService


@pytest.mark.asyncio
async def test_alert_lifecycle_and_snapshot_deduplication(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'alerts.db'}")
    async with db.session() as session:
        user = User(telegram_id=7)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = AlertService(db)
    alert = await service.create(user_id, "KLM561", ["delay", "cancellation"])
    delivered = []

    async def notify(alert, event):
        delivered.append(event.event_type)

    first = await service.process_snapshot(alert.id, {"status": "scheduled"}, notify)
    same = await service.process_snapshot(alert.id, {"status": "scheduled"}, notify)
    changed = await service.process_snapshot(
        alert.id, {"status": "delayed", "event_type": "delay"}, notify
    )
    assert not first and not same and changed
    assert delivered == ["delay"]
    async with db.session() as session:
        assert await session.scalar(select(FlightAlertEvent.delivery_status)) == "delivered"
    await service.pause(alert.id)
    assert (await service.list(user_id))[0].status == "paused"
    await service.resume(alert.id)
    await service.delete(alert.id)
    assert (await service.list(user_id))[0].status == "deleted"
    await db.close()


@pytest.mark.asyncio
async def test_failed_notification_is_recorded_without_disabling_alert(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'failure.db'}")
    async with db.session() as session:
        user = User(telegram_id=8)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = AlertService(db)
    alert = await service.create(user_id, "IR123", ["delay"])

    async def fail(alert, event):
        raise RuntimeError("telegram unavailable")

    await service.process_snapshot(alert.id, {"s": 1}, fail)
    await service.process_snapshot(alert.id, {"s": 2}, fail)
    assert (await service.list(user_id))[0].status == "active"
    await db.close()

@pytest.mark.asyncio
async def test_failed_flight_notification_retries_same_snapshot_without_duplicate_event(tmp_path):
    db = await initialize_database(f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}")
    async with db.session() as session:
        user = User(telegram_id=99)
        session.add(user)
        await session.flush()
        user_id = user.id
    service = AlertService(db)
    alert = await service.create(user_id, "IR123", ["delay"])
    async def fail(alert, event):
        raise RuntimeError("temporary failure")
    sent = []
    async def succeed(alert, event):
        sent.append(event.id)

    assert not await service.process_snapshot(alert.id, {"status": "normal"}, succeed)
    changed = {"status": "delayed", "event_type": "delay"}
    assert not await service.process_snapshot(alert.id, changed, fail)
    async with db.session() as session:
        event = await session.scalar(select(FlightAlertEvent))
        assert event.delivery_status == "failed"
        assert (await session.get(type(alert), alert.id)).last_snapshot_hash is not None
    assert await service.process_snapshot(alert.id, changed, succeed)
    assert not await service.process_snapshot(alert.id, changed, succeed)
    assert sent == [event.id]
    async with db.session() as session:
        events = (await session.scalars(select(FlightAlertEvent))).all()
        assert len(events) == 1
        assert events[0].delivery_status == "delivered"
    await db.close()
