"""Persist visa-change subscriptions and delivery outbox."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_visa_watch_notifications"
down_revision: Union[str, None] = "0008_user_last_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visa_watches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("passport", sa.String(2), nullable=False),
        sa.Column("destination", sa.String(2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "passport", "destination", name="uq_visa_watch_route"),
    )
    op.create_index("ix_visa_watches_user_id", "visa_watches", ["user_id"])
    op.create_index(
        "ix_visa_watch_destination_active", "visa_watches", ["destination", "active"]
    )
    op.create_table(
        "visa_watch_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("watch_id", sa.Integer(),
                  sa.ForeignKey("visa_watches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("watch_id", "change_hash", name="uq_visa_watch_change"),
    )
    op.create_index("ix_visa_watch_events_watch_id", "visa_watch_events", ["watch_id"])
    op.create_index(
        "ix_visa_watch_event_pending", "visa_watch_events", ["sent_at", "attempts"]
    )


def downgrade() -> None:
    op.drop_index("ix_visa_watch_event_pending", table_name="visa_watch_events")
    op.drop_index("ix_visa_watch_events_watch_id", table_name="visa_watch_events")
    op.drop_table("visa_watch_events")
    op.drop_index("ix_visa_watch_destination_active", table_name="visa_watches")
    op.drop_index("ix_visa_watches_user_id", table_name="visa_watches")
    op.drop_table("visa_watches")
