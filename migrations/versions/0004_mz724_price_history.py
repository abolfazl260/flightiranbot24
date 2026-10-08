"""mz724 hourly price history and rolling averages"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_mz724_price_history"
down_revision: Union[str, None] = "0003_price_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mz724_price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("origin", sa.String(128), nullable=False),
        sa.Column("destination", sa.String(128), nullable=False),
        sa.Column("price_toman", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "origin", "destination", "captured_at", name="uq_mz724_route_hour"
        ),
    )
    op.create_index(
        "ix_mz724_price_snapshots_captured_at",
        "mz724_price_snapshots",
        ["captured_at"],
    )
    op.create_index(
        "ix_mz724_route_captured",
        "mz724_price_snapshots",
        ["origin", "destination", "captured_at"],
    )

    op.create_table(
        "mz724_route_averages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("origin", sa.String(128), nullable=False),
        sa.Column("destination", sa.String(128), nullable=False),
        sa.Column("average_price_toman", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("origin", "destination", name="uq_mz724_route_average"),
    )
    op.create_index("ix_mz724_route_averages_origin", "mz724_route_averages", ["origin"])
    op.create_index(
        "ix_mz724_route_averages_destination", "mz724_route_averages", ["destination"]
    )


def downgrade() -> None:
    op.drop_index("ix_mz724_route_averages_destination", table_name="mz724_route_averages")
    op.drop_index("ix_mz724_route_averages_origin", table_name="mz724_route_averages")
    op.drop_table("mz724_route_averages")
    op.drop_index("ix_mz724_route_captured", table_name="mz724_price_snapshots")
    op.drop_index("ix_mz724_price_snapshots_captured_at", table_name="mz724_price_snapshots")
    op.drop_table("mz724_price_snapshots")
