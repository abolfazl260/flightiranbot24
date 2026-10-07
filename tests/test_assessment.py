from datetime import date, timedelta

from flightiran.modules.visa.assessment import (
    AssessmentInput,
    AssessmentState,
    VisaAssessmentService,
)
from flightiran.modules.visa.knowledge import VisaKnowledgeRepository, VisaProfile, VisaStatus


def service():
    return VisaAssessmentService(
        VisaKnowledgeRepository(
            [
                VisaProfile(
                    "IR",
                    "DE",
                    VisaStatus.E_VISA,
                    ("passport", "photo"),
                    "https://source.test",
                    date.today(),
                    date.today() + timedelta(days=20),
                )
            ]
        )
    )


def test_assessment_incomplete_and_cancel():
    assert service().assess(AssessmentInput(consent=True)).state == AssessmentState.IN_PROGRESS
    assert service().cancel().state == AssessmentState.CANCELLED


def test_assessment_reproducible_and_lists_missing_documents():
    answers = AssessmentInput(
        nationality="IR",
        destination="DE",
        purpose="tourism",
        stay_days=10,
        consent=True,
        documents={"passport"},
    )
    result = service().assess(answers)
    assert result.state == AssessmentState.COMPLETED
    assert result.missing_documents == ("photo",)
    assert result.source_url == "https://source.test"
    assert result.informational_notice.startswith("Informational")
