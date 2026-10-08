"""Persist per-user preferred visa passport, defaulting to Iran."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_visa_default_passport"
down_revision: Union[str, None] = "0006_visa_search_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("visa_passport", sa.String(2), server_default="IR", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "visa_passport")
