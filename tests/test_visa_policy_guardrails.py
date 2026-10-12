"""Visa-rule validity, waiver scope and source-schema safety regressions."""

from copy import deepcopy

import pytest

from flightiran.interfaces.telegram.visa_presentation import (
    render_overview,
    render_rich_report,
    render_section,
    rule_validity_notice,
)
from flightiran.interfaces.telegram.visa_watches import render_change_alert
from flightiran.modules.visa.catalog import VisaDetail, VisaRule
from flightiran.modules.visa.sync import _build_destination_validator
from flightiran.modules.visa.watch import (
    PendingNotification,
    matching_waivers,
    rule_changes,
    semantic_rule,
)


def example_detail(passport="AF", *, valid_until=None):
    record = {
        "requirement": "embassy-visa",
        "maxStayDays": None,
        "notes": "Confirm requirements with the embassy.",
    }
    if valid_until is not None:
        record["validUntil"] = valid_until
    data = {
        "id": "example",
        "iso2": "TR",
        "names": {"common": "Turkey"},
        "meta": {"lastUpdated": "2026-10-07"},
        "visaPolicy": {
            "defaultSource": {
                "url": "https://www.mfa.gov.tr",
                "name": "Government",
                "type": "government",
                "lastVerified": "2026-10-01",
            },
            "byPassport": {passport: record},
            "conditionalWaivers": [
                {"id": "us-visa", "appliesTo": ["IR"], "requirement": "evisa",
                 "text": "Only the Iranian passport exception"},
                {"id": "residence-permit", "appliesTo": "visa-required",
                 "requirement": "visa-on-arrival",
                 "text": "Applicants may qualify with supporting documents"},
                {"id": "gcc-residence", "appliesTo": ["US"],
                 "requirement": "visa-free", "text": "Only the US passport exception"},
            ],
        },
        "visaTypes": [],
    }
    rule = VisaRule(
        passport, "TR", "Turkey", "embassy-visa", None,
        record["notes"], "https://www.mfa.gov.tr", "2026-10-01", "policy",
    )
    return VisaDetail(rule, data, record, ())


@pytest.mark.parametrize("passport,expected", [
    ("AF", ["Applicants may qualify with supporting documents"]),
    ("IR", ["Only the Iranian passport exception",
            "Applicants may qualify with supporting documents"]),
    ("US", ["Applicants may qualify with supporting documents",
            "Only the US passport exception"]),
])
def test_waiver_display_only_for_selected_passport(passport, expected):
    detail = example_detail(passport)
    rendered = render_overview(detail, "fa")
    for text in expected:
        assert text in rendered
    for other in {
        "Only the Iranian passport exception",
        "Applicants may qualify with supporting documents",
        "Only the US passport exception",
    } - set(expected):
        assert other not in rendered

    policy = detail.destination_data["visaPolicy"]
    scopes = matching_waivers(policy, "embassy-visa", passport)
    assert [waiver["text"] for waiver in scopes] == expected
    semantic = semantic_rule(detail.destination_data, passport)
    assert [waiver["text"] for waiver in semantic["conditional_waivers"]] == expected


def test_unknown_waiver_scope_never_leaks_into_card_or_alert():
    detail = example_detail()
    policy = detail.destination_data["visaPolicy"]
    policy["conditionalWaivers"] = [
        {"appliesTo": ["DE"], "text": "German-only waiver"},
        {"text": "Unscoped waiver"},
        {"appliesTo": ["visa-required"], "text": "Unsupported array category"},
    ]
    assert matching_waivers(policy, "embassy-visa", "AF") == []
    assert "German-only waiver" not in render_overview(detail, "fa")
    assert semantic_rule(detail.destination_data, "AF")["conditional_waivers"] == []


def test_expired_and_future_source_rules_are_visibly_distinct_from_visa_validity():
    expired = example_detail(valid_until="2001-01-02")
    overview = render_overview(expired, "fa")
    rich = render_rich_report(expired, "fa")["html"]
    sources = render_section(expired, "fa", "sources")
    for text in (overview, rich, sources):
        assert "2001-01-02" in text
        assert "منقضی" in text or "پایان" in text
    assert "تاریخ" in rule_validity_notice(expired, "en") or "rule" in (
        rule_validity_notice(expired, "en").lower()
    )
    assert "valid until" in render_overview(
        example_detail(valid_until="2999-01-01"), "en"
    )
    assert not rule_validity_notice(example_detail(valid_until="not-a-date"), "fa")
    assert not rule_validity_notice(example_detail(), "fa")


def test_missing_passport_rule_is_a_semantic_event_and_has_explicit_warning():
    detail = example_detail()
    old = semantic_rule(detail.destination_data, "AF")
    missing = deepcopy(detail.destination_data)
    missing["visaPolicy"]["byPassport"].pop("AF")
    assert rule_changes(old, semantic_rule(missing, "AF")) == ("availability",)
    assert rule_changes(None, old) == ("availability",)
    assert rule_changes(None, None) == ()
    notification = PendingNotification(
        event_id=1, telegram_id=111, passport="AF", destination="TR",
        payload={
            "categories": ["availability"],
            "before": {"status": "embassy-visa", "stay_days": None},
            "after": {"status": None, "stay_days": None},
        },
    )
    message = render_change_alert(notification, "fa")
    assert "حذف شده" in message
    assert "پاسپورت" in message or "جواز" in message


def test_schema_validator_rejects_incomplete_source_data_and_remote_references():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["id", "visaPolicy"],
        "properties": {
            "id": {"type": "string"},
            "visaPolicy": {
                "type": "object",
                "required": ["byPassport"],
                "properties": {"byPassport": {"type": "object"}},
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    }
    validator = _build_destination_validator(schema)
    assert list(validator.iter_errors({"id": "turkey", "visaPolicy": {"byPassport": {}}})) == []
    assert list(validator.iter_errors({"id": "turkey", "visaPolicy": {}}))
    assert list(validator.iter_errors({
        "id": "turkey", "visaPolicy": {"byPassport": {}, "unexpected": True}
    }))
    with pytest.raises(ValueError, match="references"):
        _build_destination_validator({
            "type": "object", "required": ["id"],
            "properties": {"id": {"$ref": "https://malicious.example/schema.json"}},
        })
