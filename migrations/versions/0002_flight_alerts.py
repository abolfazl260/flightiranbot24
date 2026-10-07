"""flight alert subscriptions and deduplicated events"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_flight_alerts"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    common = [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]
    op.create_table(
        "flight_alerts",
        *common,
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("flight_number", sa.String(16), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_snapshot_hash", sa.String(64)),
    )
    op.create_table(
        "flight_alert_events",
        *common,
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("flight_alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("delivery_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint("alert_id", "snapshot_hash", "event_type"),
    )


def downgrade() -> None:
    op.drop_table("flight_alert_events")
    op.drop_table("flight_alerts")
