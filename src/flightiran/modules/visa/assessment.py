"""Reproducible, rule-based visa eligibility assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from .knowledge import VisaKnowledgeRepository, VisaStatus


class AssessmentState(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class AssessmentInput:
    nationality: str | None = None
    destination: str | None = None
    purpose: str | None = None
    stay_days: int | None = None
    age: int | None = None
    occupation: str | None = None
    travel_history: str | None = None
    documents: set[str] = field(default_factory=set)
    consent: bool = False


@dataclass(frozen=True)
class AssessmentResult:
    state: AssessmentState
    route: str | None
    required_documents: tuple[str, ...]
    missing_documents: tuple[str, ...]
    risks: tuple[str, ...]
    source_url: str | None
    assessed_at: datetime | None
    informational_notice: str = "Informational guidance only; this is not an embassy decision."


class VisaAssessmentService:
    def __init__(self, repository: VisaKnowledgeRepository) -> None:
        self.repository = repository

    def assess(self, answers: AssessmentInput) -> AssessmentResult:
        if not answers.consent:
            return AssessmentResult(
                AssessmentState.IN_PROGRESS, None, (), (), ("Consent is required",), None, None
            )
        if not answers.nationality or not answers.destination or not answers.purpose:
            return AssessmentResult(
                AssessmentState.IN_PROGRESS,
                None,
                (),
                (),
                ("Required answers are incomplete",),
                None,
                None,
            )
        profile = self.repository.find(answers.nationality, answers.destination)
        if profile is None:
            return AssessmentResult(
                AssessmentState.COMPLETED,
                "official embassy process",
                (),
                (),
                ("No current profile found",),
                None,
                datetime.now(timezone.utc),
            )
        missing = tuple(
            document for document in profile.required_documents if document not in answers.documents
        )
        risks = list(
            filter(
                None,
                [
                    "Long stay requires extra review"
                    if answers.stay_days and answers.stay_days > 90
                    else None
                ],
            )
        )
        route = profile.status.value
        if profile.status == VisaStatus.EMBASSY:
            route = "embassy application"
        return AssessmentResult(
            AssessmentState.COMPLETED,
            route,
            profile.required_documents,
            missing,
            tuple(risks),
            profile.source_url,
            datetime.now(timezone.utc),
        )

    @staticmethod
    def cancel() -> AssessmentResult:
        return AssessmentResult(AssessmentState.CANCELLED, None, (), (), (), None, None)
