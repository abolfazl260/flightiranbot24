"""Persist TravelRequirements.info visa destination JSON and sync status."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_visa_dataset_sync"
down_revision: Union[str, None] = "0004_mz724_price_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visa_destination_data",
        sa.Column("slug", sa.String(128), primary_key=True),
        sa.Column("iso2", sa.String(2), nullable=False, unique=True),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("manifest_updated", sa.String(32), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "visa_dataset_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("dataset_version", sa.String(64), nullable=True),
        sa.Column("manifest_hash", sa.String(64), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("visa_dataset_state")
    op.drop_table("visa_destination_data")
