"""Track the latest user activity for the daily admin report."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_user_last_active"
down_revision: Union[str, None] = "0007_visa_default_passport"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_active_at", sa.DateTime(timezone=True)))
    op.create_index("ix_users_last_active_at", "users", ["last_active_at"])


def downgrade() -> None:
    op.drop_index("ix_users_last_active_at", table_name="users")
    op.drop_column("users", "last_active_at")
