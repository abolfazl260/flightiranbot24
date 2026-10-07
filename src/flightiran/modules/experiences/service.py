"""Review validation, moderation and duplicate prevention."""

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum


class ModerationState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELETED = "deleted"


@dataclass(frozen=True)
class Experience:
    id: int
    user_id: int
    target_type: str
    target: str
    route: str
    travel_date: date
    cabin_class: str
    text: str
    rating: int
    state: ModerationState = ModerationState.PENDING
    helpful_votes: int = 0


class ExperienceRepository:
    def __init__(self) -> None:
        self._items: list[Experience] = []
        self._next_id = 1

    def submit(self, experience: Experience) -> Experience:
        if not 1 <= experience.rating <= 5 or not experience.text.strip():
            raise ValueError("review text and rating are required")
        if any(
            item.user_id == experience.user_id
            and item.target == experience.target
            and item.route == experience.route
            for item in self._items
        ):
            raise ValueError("duplicate review")
        result = replace(experience, id=self._next_id, state=ModerationState.PENDING)
        self._next_id += 1
        self._items.append(result)
        return result

    def moderate(self, experience_id: int, state: ModerationState) -> None:
        self._items = [
            replace(item, state=state) if item.id == experience_id else item for item in self._items
        ]

    def list_public(self, target: str) -> list[Experience]:
        return [
            item
            for item in self._items
            if item.target == target and item.state == ModerationState.APPROVED
        ]
