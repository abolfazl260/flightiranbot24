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
    visa_passport: Mapped[str] = mapped_column(String(2), default="IR", nullable=False)


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
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


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


class VisaDestinationData(Base):
    """Latest validated raw TravelRequirements destination data."""

    __tablename__ = "visa_destination_data"
    slug: Mapped[str] = mapped_column(String(128), primary_key=True)
    iso2: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    manifest_updated: Mapped[str | None] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)


class VisaDatasetState(Base):
    """Persist sync metadata across Docker restarts."""

    __tablename__ = "visa_dataset_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(64))
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VisaRuleIndex(Base):
    """Denormalized lookup index rebuilt from verified destination JSON."""

    __tablename__ = "visa_rule_index"
    __table_args__ = (
        Index("ix_visa_rule_passport_status", "passport", "status"),
        Index("ix_visa_rule_destination", "destination"),
    )

    passport: Mapped[str] = mapped_column(String(2), primary_key=True)
    destination: Mapped[str] = mapped_column(String(2), primary_key=True)
    country_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    stay_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(512))
    verified_on: Mapped[str | None] = mapped_column(String(32))
    source_level: Mapped[str] = mapped_column(String(16), nullable=False)
