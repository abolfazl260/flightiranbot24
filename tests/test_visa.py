from datetime import date, timedelta

from flightiran.interfaces.telegram.visa import render_visa_profile
from flightiran.modules.visa import VisaKnowledgeRepository, VisaProfile, VisaStatus


def profile(valid_until):
    return VisaProfile(
        "IR",
        "France",
        VisaStatus.REQUIRED,
        ("Passport", "<photo>"),
        "https://gov.test/visa",
        date.today(),
        valid_until,
        version="2",
    )


def test_source_backed_import_search_and_expiry():
    repo = VisaKnowledgeRepository([profile(date.today() + timedelta(days=2))])
    assert repo.find("IR", "France").version == "2"
    repo.add(profile(date.today() - timedelta(days=1)))
    assert repo.find("IR", "France") is None
    assert repo.search("france")
    assert repo.find("IR", "France", include_expired=True).is_expired


def test_render_escapes_documents_and_source():
    output = render_visa_profile(profile(date.today() + timedelta(days=1)))
    assert "&lt;photo&gt;" in output
    assert "gov.test" in output
    assert "<photo>" not in output
