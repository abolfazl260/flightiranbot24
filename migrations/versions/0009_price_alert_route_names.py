"""Support full mz724 city names in saved ticket alert routes."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_price_alert_route_names"
down_revision: Union[str, None] = "0008_user_last_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("saved_routes") as batch:
        batch.alter_column(
            "origin", existing_type=sa.String(8), type_=sa.String(128), nullable=False
        )
        batch.alter_column(
            "destination", existing_type=sa.String(8), type_=sa.String(128), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("saved_routes") as batch:
        batch.alter_column(
            "origin", existing_type=sa.String(128), type_=sa.String(8), nullable=False
        )
        batch.alter_column(
            "destination", existing_type=sa.String(128), type_=sa.String(8), nullable=False
        )
