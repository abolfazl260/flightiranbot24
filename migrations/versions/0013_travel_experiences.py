"""Persistent moderated experiences, exact archives, votes and abuse reports."""

from alembic import op

from flightiran.db.models import (
    ExperienceAudit,
    ExperienceReport,
    ExperienceTarget,
    ExperienceVote,
    TravelExperience,
)

revision = "0013_travel_experiences"
down_revision = "0012_ticket_price_units_alert_arming"
branch_labels = None
depends_on = None


def upgrade():
    for model in (
        TravelExperience,
        ExperienceTarget,
        ExperienceVote,
        ExperienceReport,
        ExperienceAudit,
    ):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Preserve user content and immutable archive on rollback. Old code ignores these tables.
    pass
