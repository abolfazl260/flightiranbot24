from datetime import date

import pytest

from flightiran.modules.experiences import Experience, ExperienceRepository, ModerationState


def review(user=1):
    return Experience(0, user, "airline", "IR", "IKA-FRA", date.today(), "economy", "Good crew", 4)


def test_pending_reviews_are_hidden_and_duplicates_blocked():
    repo = ExperienceRepository()
    item = repo.submit(review())
    assert repo.list_public("IR") == []
    repo.moderate(item.id, ModerationState.APPROVED)
    assert len(repo.list_public("IR")) == 1
    with pytest.raises(ValueError):
        repo.submit(review())
