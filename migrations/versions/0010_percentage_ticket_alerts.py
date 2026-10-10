"""Add explicit percentage thresholds to ticket price alerts.

Legacy price alerts and notification snapshots are preserved. No referenced
tables are rebuilt, so SQLite foreign keys remain intact.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_percentage_ticket_alerts"
down_revision: Union[str, None] = "0009_visa_watch_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column(
            "threshold_type", sa.String(length=12),
            nullable=False, server_default="price",
        ),
    )
    op.add_column(
        "price_alerts",
        sa.Column("target_percent", sa.Integer(), nullable=True),
    )
    op.add_column(
        "price_snapshots",
        sa.Column("reference_average_toman", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("price_snapshots", "reference_average_toman")
    op.drop_column("price_alerts", "target_percent")
    op.drop_column("price_alerts", "threshold_type")
