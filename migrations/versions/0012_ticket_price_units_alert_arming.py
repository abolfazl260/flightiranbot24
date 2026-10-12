"""Normalize legacy mz724 thousand-toman quotes and deduplicate price alerts.

Old mz724 prices were stored as displayed (for example 13,282 rather than
13,282,000 tomans). Fix the historical amounts before the next capture mixes
different price units. Previously delivered alerts remain disarmed until the
fare stops qualifying.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_ticket_price_units_alert_arming"
down_revision: Union[str, None] = "0011_default_persian_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column("is_armed", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # Prevent an immediate repeat after deployment of an alert already sent
    # under the former exact-price deduplication implementation.
    op.execute(
        """
        UPDATE price_alerts SET is_armed = 0
        WHERE EXISTS (
            SELECT 1 FROM price_snapshots
            WHERE price_snapshots.alert_id = price_alerts.id
              AND price_snapshots.notified = 1
        )
        """
    )

    # Only small bare-source quotes were misinterpreted as toman. Existing
    # fully denominated prices (>= 1,000,000) must remain unchanged.
    op.execute(
        """
        UPDATE mz724_price_snapshots
        SET price_toman = price_toman * 1000
        WHERE price_toman > 0 AND price_toman < 1000000
        """
    )
    op.execute(
        """
        UPDATE mz724_route_averages
        SET average_price_toman = average_price_toman * 1000
        WHERE average_price_toman > 0 AND average_price_toman < 1000000
        """
    )
    op.execute(
        """
        UPDATE price_snapshots SET
            price = CASE WHEN price > 0 AND price < 1000000
                         THEN price * 1000 ELSE price END,
            reference_average_toman = CASE
                WHEN reference_average_toman > 0
                 AND reference_average_toman < 1000000
                THEN reference_average_toman * 1000
                ELSE reference_average_toman END
        WHERE alert_id IN (
            SELECT id FROM price_alerts WHERE currency = 'TOMAN'
        )
        """
    )


def downgrade() -> None:
    # Corrected monetary records cannot be safely mapped back to their former
    # inconsistent units; keep them normalized when reverting the schema.
    op.drop_column("price_alerts", "is_armed")
