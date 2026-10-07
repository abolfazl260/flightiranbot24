"""saved routes and ticket price alerts"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_price_alerts"
down_revision: Union[str, None] = "0002_flight_alerts"
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
        "saved_routes",
        *common,
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("origin", sa.String(8), nullable=False),
        sa.Column("destination", sa.String(8), nullable=False),
        sa.Column("passengers", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "price_alerts",
        *common,
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "route_id",
            sa.Integer(),
            sa.ForeignKey("saved_routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_snapshot_hash", sa.String(64)),
    )
    op.create_table(
        "price_snapshots",
        *common,
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("price_alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("alert_id", "snapshot_hash"),
    )


def downgrade() -> None:
    for table in ("price_snapshots", "price_alerts", "saved_routes"):
        op.drop_table(table)
