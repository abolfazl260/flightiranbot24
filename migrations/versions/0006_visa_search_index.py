"""Indexed visa passport/destination lookups for Telegram browsing."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_visa_search_index"
down_revision: Union[str, None] = "0005_visa_dataset_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visa_rule_index",
        sa.Column("passport", sa.String(2), nullable=False),
        sa.Column("destination", sa.String(2), nullable=False),
        sa.Column("country_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("stay_days", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("verified_on", sa.String(32), nullable=True),
        sa.Column("source_level", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("passport", "destination", name="pk_visa_rule_index"),
    )
    op.create_index(
        "ix_visa_rule_passport_status",
        "visa_rule_index",
        ["passport", "status"],
    )
    op.create_index(
        "ix_visa_rule_destination",
        "visa_rule_index",
        ["destination"],
    )


def downgrade() -> None:
    op.drop_index("ix_visa_rule_destination", table_name="visa_rule_index")
    op.drop_index("ix_visa_rule_passport_status", table_name="visa_rule_index")
    op.drop_table("visa_rule_index")
