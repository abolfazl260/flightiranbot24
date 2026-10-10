"""Make Persian the default for newly-created Telegram preferences.

Only the column's server default changes; no existing user preference values
are rewritten. SQLite requires a batch table rebuild for ALTER DEFAULT.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_default_persian_language"
down_revision: Union[str, None] = "0010_percentage_ticket_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.alter_column(
            "language",
            existing_type=sa.String(length=8),
            existing_nullable=False,
            existing_server_default="en",
            server_default="fa",
        )


def downgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.alter_column(
            "language",
            existing_type=sa.String(length=8),
            existing_nullable=False,
            existing_server_default="fa",
            server_default="en",
        )
