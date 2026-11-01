"""Read-only, privacy-preserving operating report from persisted bot data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from flightiran.db.engine import Database
from flightiran.db.models import (
    AuditLog,
    JobRun,
    Mz724PriceSnapshot,
    Mz724RouteAverage,
    PriceAlert,
    PriceSnapshot,
    ProviderRequest,
    SavedRoute,
    User,
    UserPreference,
    VisaWatch,
)


@dataclass(frozen=True)
class UserActivityRow:
    """Private admin-only snapshot. Event totals count tracked user actions."""

    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    events_total: int
    events_7d: int
    active_price_alerts: int
    active_visa_watches: int
    last_active_at: datetime | None


@dataclass(frozen=True)
class BotReport:
    generated_at: datetime
    counts: dict[str, int]
    language_counts: tuple[tuple[str, int], ...]
    top_events: tuple[tuple[str, int], ...]
    top_origins: tuple[tuple[str, int], ...]
    price_alert_status: tuple[tuple[str, int], ...]
    provider_status: tuple[tuple[str, str, int], ...]
    job_status: tuple[tuple[str, str, int], ...]
    last_price_capture: datetime | None
    user_activity: tuple[UserActivityRow, ...] = ()


class BotReportRepository:
    """Collect aggregate metrics and private administrator-only per-user stats."""

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    async def _count(session: AsyncSession, model, *filters) -> int:
        statement = select(func.count()).select_from(model)
        if filters:
            statement = statement.where(*filters)
        return int(await session.scalar(statement) or 0)

    @staticmethod
    async def _status_counts(session: AsyncSession, model, column):
        rows = await session.execute(
            select(column, func.count()).select_from(model).group_by(column)
        )
        return tuple((str(status), int(count)) for status, count in rows.all())

    async def collect(self, now: datetime | None = None) -> BotReport:
        """Use UTC windows. Uninstrumented providers/jobs naturally have no rows."""

        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("Report clock must be timezone-aware")
        windows = {
            "24h": now - timedelta(days=1),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30),
        }

        async with self.database.session() as session:
            counts = {
                "users_total": await self._count(session, User),
                "audit_total": await self._count(session, AuditLog),
                "saved_routes": await self._count(session, SavedRoute),
                "price_snapshots": await self._count(session, Mz724PriceSnapshot),
                "tracked_routes": await self._count(session, Mz724RouteAverage),
                "origins": int(
                    await session.scalar(
                        select(func.count(distinct(Mz724RouteAverage.origin)))
                    ) or 0
                ),
                "price_alerts": await self._count(session, PriceAlert),
                "price_notifications": await self._count(
                    session, PriceSnapshot, PriceSnapshot.notified.is_(True)
                ),
                "provider_requests": await self._count(session, ProviderRequest),
                "job_runs": await self._count(session, JobRun),
            }
            for label, cutoff in windows.items():
                counts[f"new_users_{label}"] = await self._count(
                    session, User, User.created_at >= cutoff
                )
                counts[f"events_{label}"] = await self._count(
                    session, AuditLog, AuditLog.created_at >= cutoff
                )
                counts[f"active_users_{label}"] = int(
                    await session.scalar(
                        select(func.count(distinct(AuditLog.user_id))).where(
                            AuditLog.created_at >= cutoff,
                            AuditLog.user_id.is_not(None),
                        )
                    ) or 0
                )
            counts["price_samples_24h"] = await self._count(
                session,
                Mz724PriceSnapshot,
                Mz724PriceSnapshot.captured_at >= windows["24h"],
            )
            counts["failed_provider_7d"] = await self._count(
                session,
                ProviderRequest,
                ProviderRequest.created_at >= windows["7d"],
                ProviderRequest.status.in_(("error", "failed", "failure")),
            )
            counts["failed_jobs_7d"] = await self._count(
                session,
                JobRun,
                JobRun.created_at >= windows["7d"],
                JobRun.status.in_(("error", "failed", "failure")),
            )
            counts["runtime_errors_7d"] = await self._count(
                session,
                AuditLog,
                AuditLog.created_at >= windows["7d"],
                AuditLog.event_type == "system.error",
            )

            language_rows = await session.execute(
                select(UserPreference.language, func.count())
                .group_by(UserPreference.language)
                .order_by(func.count().desc())
            )
            language_counts = tuple(
                (str(name), int(total)) for name, total in language_rows.all()
            )
            action_rows = await session.execute(
                select(AuditLog.event_type, func.count())
                .where(AuditLog.created_at >= windows["7d"])
                .group_by(AuditLog.event_type)
                .order_by(func.count().desc(), AuditLog.event_type)
                .limit(12)
            )
            top_events = tuple(
                (str(name), int(total)) for name, total in action_rows.all()
            )
            origin_field = AuditLog.payload["origin"].as_string()
            origin_rows = await session.execute(
                select(origin_field, func.count())
                .where(
                    AuditLog.created_at >= windows["30d"],
                    AuditLog.event_type == "ticket.origin.selected",
                    origin_field.is_not(None),
                )
                .group_by(origin_field)
                .order_by(func.count().desc())
                .limit(7)
            )
            top_origins = tuple(
                (str(name), int(total)) for name, total in origin_rows.all()
            )

            provider_rows = await session.execute(
                select(
                    ProviderRequest.provider,
                    ProviderRequest.status,
                    func.count(),
                )
                .where(ProviderRequest.created_at >= windows["7d"])
                .group_by(ProviderRequest.provider, ProviderRequest.status)
                .order_by(func.count().desc())
                .limit(12)
            )
            provider_status = tuple(
                (str(provider), str(status), int(count))
                for provider, status, count in provider_rows.all()
            )
            job_rows = await session.execute(
                select(JobRun.job_name, JobRun.status, func.count())
                .where(JobRun.created_at >= windows["7d"])
                .group_by(JobRun.job_name, JobRun.status)
                .order_by(func.count().desc())
                .limit(12)
            )
            job_status = tuple(
                (str(name), str(status), int(count))
                for name, status, count in job_rows.all()
            )
            last_price_capture = await session.scalar(
                select(func.max(Mz724PriceSnapshot.captured_at))
            )
            price_status = await self._status_counts(
                session, PriceAlert, PriceAlert.status
            )

            # Aggregate each source before joining to avoid event/alert
            # multiplication for users owning multiple subscriptions.
            # A tracked interaction is an attributable audit event, excluding
            # registration bookkeeping and internal error records.
            user_events = (
                select(
                    AuditLog.user_id.label("user_id"),
                    func.count().label("total"),
                    func.sum(
                        case((AuditLog.created_at >= windows["7d"], 1), else_=0)
                    ).label("recent"),
                    func.max(AuditLog.created_at).label("last_event"),
                )
                .where(
                    AuditLog.user_id.is_not(None),
                    AuditLog.event_type.notin_(("system.error", "user.registered")),
                )
                .group_by(AuditLog.user_id)
                .subquery()
            )
            active_prices = (
                select(PriceAlert.user_id.label("user_id"), func.count().label("total"))
                .where(PriceAlert.status == "active")
                .group_by(PriceAlert.user_id)
                .subquery()
            )
            active_visas = (
                select(VisaWatch.user_id.label("user_id"), func.count().label("total"))
                .where(VisaWatch.active.is_(True))
                .group_by(VisaWatch.user_id)
                .subquery()
            )
            activity_rows = await session.execute(
                select(
                    User.telegram_id, User.username, User.first_name, User.last_name,
                    User.last_active_at, user_events.c.last_event,
                    func.coalesce(user_events.c.total, 0),
                    func.coalesce(user_events.c.recent, 0),
                    func.coalesce(active_prices.c.total, 0),
                    func.coalesce(active_visas.c.total, 0),
                )
                .outerjoin(user_events, user_events.c.user_id == User.id)
                .outerjoin(active_prices, active_prices.c.user_id == User.id)
                .outerjoin(active_visas, active_visas.c.user_id == User.id)
                .order_by(func.coalesce(user_events.c.total, 0).desc(), User.id.asc())
            )
            user_activity = []
            for (tg_id, username, first_name, last_name, active_at, last_event,
                 events_total, events_7d, price_count, visa_count) in activity_rows.all():
                # Datetimes can be naive after SQLite round-tripping; treat them
                # as UTC consistently with the existing _timestamp renderer.
                recorded = [value.replace(tzinfo=timezone.utc)
                            if value.tzinfo is None else value.astimezone(timezone.utc)
                            for value in (active_at, last_event) if value is not None]
                user_activity.append(UserActivityRow(
                    telegram_id=int(tg_id),
                    username=username, first_name=first_name, last_name=last_name,
                    events_total=int(events_total),
                    events_7d=int(events_7d),
                    active_price_alerts=int(price_count),
                    active_visa_watches=int(visa_count),
                    last_active_at=max(recorded) if recorded else None,
                ))

        return BotReport(
            generated_at=now,
            counts=counts,
            language_counts=language_counts,
            top_events=top_events,
            top_origins=top_origins,
            price_alert_status=price_status,
            provider_status=provider_status,
            job_status=job_status,
            last_price_capture=last_price_capture,
            user_activity=tuple(user_activity),
        )
