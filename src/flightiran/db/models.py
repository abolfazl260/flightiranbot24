"""SQLAlchemy models for the first persistence slice."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by all modules."""


class TimestampedModel(Base):
    """Common integer identity and UTC timestamps."""

    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampedModel):
    __tablename__ = "users"
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))


class UserPreference(TimestampedModel):
    __tablename__ = "user_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)


class Role(TimestampedModel):
    __tablename__ = "roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ProviderRequest(TimestampedModel):
    __tablename__ = "provider_requests"
    provider: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))


class JobRun(TimestampedModel):
    __tablename__ = "job_runs"
    job_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class FlightAlert(TimestampedModel):
    __tablename__ = "flight_alerts"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    flight_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    event_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    last_snapshot_hash: Mapped[str | None] = mapped_column(String(64))


class FlightAlertEvent(TimestampedModel):
    __tablename__ = "flight_alert_events"
    __table_args__ = (UniqueConstraint("alert_id", "snapshot_hash", "event_type"),)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("flight_alerts.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class SavedRoute(TimestampedModel):
    __tablename__ = "saved_routes"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    origin: Mapped[str] = mapped_column(String(8), nullable=False)
    destination: Mapped[str] = mapped_column(String(8), nullable=False)
    passengers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PriceAlert(TimestampedModel):
    __tablename__ = "price_alerts"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("saved_routes.id", ondelete="CASCADE"), index=True
    )
    target_price: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    last_snapshot_hash: Mapped[str | None] = mapped_column(String(64))


class PriceSnapshot(TimestampedModel):
    __tablename__ = "price_snapshots"
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("price_alerts.id", ondelete="CASCADE"), index=True
    )
    price: Mapped[float] = mapped_column(nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    notified: Mapped[bool] = mapped_column(default=False, nullable=False)
    __table_args__ = (UniqueConstraint("alert_id", "snapshot_hash"),)


class Mz724PriceSnapshot(TimestampedModel):
    """Hourly normalized ticket price for one mz724 route."""

    __tablename__ = "mz724_price_snapshots"
    __table_args__ = (
        UniqueConstraint("origin", "destination", "captured_at", name="uq_mz724_route_hour"),
        Index("ix_mz724_route_captured", "origin", "destination", "captured_at"),
    )
    origin: Mapped[str] = mapped_column(String(128), nullable=False)
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    price_toman: Mapped[int] = mapped_column(BigInteger, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class Mz724RouteAverage(TimestampedModel):
    """Materialized 21-day rolling average for one mz724 route."""

    __tablename__ = "mz724_route_averages"
    __table_args__ = (
        UniqueConstraint("origin", "destination", name="uq_mz724_route_average"),
    )
    origin: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    average_price_toman: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
