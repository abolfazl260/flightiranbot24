"""Real dataset snapshots and publication guardrails, independent of Android builds."""
import copy
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "airline_validator", ROOT / "scripts/validate_airline_content.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = datetime(2026, 11, 11, tzinfo=timezone.utc)


def test_actual_catalog_and_independent_snapshots():
    module.validate_dataset(now=NOW)
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    ids = [r["airline_id"] for r in index["airlines"]]
    assert ids == [
        "iran-air", "emirates", "mahan-air", "iran-aseman",
        "iran-airtour", "qeshm-air", "kish-air", "zagros-air", "meraj-air",
        "ata-air", "varesh-air", "caspian-air", "sepehran-air",
    ]
    coverage = {}
    for entry in index["airlines"]:
        detail = module.read_json(ROOT / "data/airlines" / entry["detail_path"])
        assert detail["airline_id"] == entry["airline_id"]
        assert detail["published_reviews"] == detail["experience_links"] == []
        coverage[entry["airline_id"]] = {
            status: sum(s["metadata"]["status"] == status for s in detail["sections"])
            for status in ("published", "draft")
        }
    assert coverage == {"iran-air": {"published": 17, "draft": 1},
                        "emirates": {"published": 18, "draft": 0},
                        "mahan-air": {"published": 19, "draft": 1},
                        "iran-aseman": {"published": 14, "draft": 4},
                        "iran-airtour": {"published": 13, "draft": 6},
                        "qeshm-air": {"published": 17, "draft": 2},
                        "kish-air": {"published": 15, "draft": 5},
                        "zagros-air": {"published": 14, "draft": 6},
                        "meraj-air": {"published": 14, "draft": 6},
                        "ata-air": {"published": 16, "draft": 4},
                        "varesh-air": {"published": 18, "draft": 2},
                        "caspian-air": {"published": 14, "draft": 6},
                        "sepehran-air": {"published": 19, "draft": 2}}
    emirates_detail = module.read_json(ROOT / "data/airlines/details/emirates.v1.json")
    fleet = next(s for s in emirates_detail["sections"] if s["id"] == "fleet")
    models = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert sum(b["count"] for b in models) == 277
    assert sum(b["count"] for b in models if b["relationship"] == "owned") == 190
    assert sum(b["count"] for b in models if b["relationship"] == "leased") == 87
    assert all(b["status"] == "unknown" for b in models)
    assert {b["observed_at"] for b in models} == {"2026-03-31T00:00:00Z"}
    assert not any("787" in b["model"] or "777-X" in b["model"] for b in models)


@pytest.fixture
def dataset(tmp_path):
    shutil.copytree(ROOT / "data/airlines", tmp_path / "data/airlines")
    (tmp_path / "data/airports").mkdir()
    shutil.copy(ROOT / "data/airports/airport-index.v1.json", tmp_path / "data/airports")
    return tmp_path


def edit(root, path, mutation):
    file = root / "data/airlines" / path
    data = module.read_json(file)
    mutation(data)
    file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(airline_id="another-airline"),
    lambda d: d["metadata"].update(source_urls=[]),
    lambda d: d["metadata"].update(verified_at=None),
    lambda d: d["metadata"].update(verified_at="not-a-date"),
    lambda d: d["metadata"].update(verified_at="2026-11-04T00:00:00"),
    lambda d: d["metadata"].update(source_urls=["https://not a host/"]),
    lambda d: d["metadata"].update(verified_at="2099-01-01T00:00:00Z"),
    lambda d: d["metadata"].update(source_urls=["http://example.com/"]),
    lambda d: d["metadata"].update(source_urls=["https://user:secret@example.com/"]),
    lambda d: d["metadata"].update(effective_from="2026-11-06T00:00:00Z",
                                  effective_to="2026-11-01T00:00:00Z"),
    lambda d: d["sections"].append(copy.deepcopy(d["sections"][0])),
    lambda d: d["sections"][0].update(blocks=[]),
    lambda d: d["sections"][0].update(scope=None),
    lambda d: d["sections"][0].update(blocks=[{
        "type": "image", "url": "https://example.com/image.jpg", "title_fa": "تصویر"
    }]),
    lambda d: d["sections"][0].update(blocks=[{
        "type": "airport_link", "iata": "ZZZ", "title_fa": "ناشناخته"
    }]),
])
def test_invalid_publication_is_rejected(dataset, mutation):
    edit(dataset, "details/emirates.v1.json", mutation)
    with pytest.raises((ValueError, ValidationError)):
        module.validate_dataset(dataset, NOW)


def test_independent_edit_and_archive_preserve_other_airline(dataset):
    iran = dataset / "data/airlines/details/iran-air.v1.json"
    before = hashlib.sha256(iran.read_bytes()).digest()
    edit(dataset, "details/emirates.v1.json", lambda d: d["metadata"].update(status="archived"))
    module.validate_dataset(dataset, NOW)
    assert hashlib.sha256(iran.read_bytes()).digest() == before


def test_codes_can_be_absent_historical_or_explicitly_shared(dataset):
    edit(dataset, "airline-index.v1.json", lambda d: d["airlines"][0]["identity"].update(codes=[]))
    module.validate_dataset(dataset, NOW)
    def assign(d):
        code = copy.deepcopy(d["airlines"][1]["identity"]["codes"][0])
        d["airlines"][0]["identity"]["codes"] = [code]
    edit(dataset, "airline-index.v1.json", assign)
    with pytest.raises(ValueError, match="Overlapping"):
        module.validate_dataset(dataset, NOW)
    def share(d):
        for entry in d["airlines"]:
            entry["identity"]["codes"][0]["shared"] = True
    edit(dataset, "airline-index.v1.json", share)
    module.validate_dataset(dataset, NOW)


@pytest.mark.parametrize("field,value", [
    ("consent_status", "unknown"), ("privacy_reviewed", False),
    ("moderation_status", "pending"), ("verified_origin", False),
    ("conflict_of_interest", True), ("ratings", {"overall": 4.5}),
    ("ratings", {"overall": 6}), ("ratings", {}),
])
def test_unpublishable_ratings_rejected(dataset, field, value):
    review = dict(review_id="test-review", airline_id="emirates", experience_id=None,
                  visit_date=None, publication_timestamp="2026-11-04T00:00:00Z",
                  consent_status="granted", moderation_status="approved", verified_origin=True,
                  privacy_reviewed=True, conflict_of_interest=False, ratings={"overall": 4})
    review[field] = value
    edit(dataset, "details/emirates.v1.json", lambda d: d.update(published_reviews=[review]))
    with pytest.raises((ValueError, ValidationError)):
        module.validate_dataset(dataset, NOW)


def test_fleet_count_needs_own_source_and_observation(dataset):
    def mutate(d):
        block = next(b for s in d["sections"] if s["id"] == "fleet"
                     for b in s["blocks"] if b["type"] == "fleet_snapshot")
        block["count"] = 19
        block["metadata"]["source_urls"] = []
    edit(dataset, "details/emirates.v1.json", mutate)
    with pytest.raises(ValueError, match="sources"):
        module.validate_dataset(dataset, NOW)


def test_public_archive_association_cannot_bypass_archive_integration(dataset):
    association = dict(experience_id="source-report", airline_ids=["emirates"],
                       relationship="mentioned", source_url="https://github.com/example/report",
                       consent_status="unknown", moderation_status="pending",
                       privacy_reviewed=False)
    edit(dataset, "details/emirates.v1.json", lambda d: d.update(experience_links=[association]))
    module.validate_dataset(dataset, NOW)
    edit(dataset, "details/emirates.v1.json",
         lambda d: d["experience_links"][0].update(moderation_status="approved"))
    with pytest.raises(ValueError, match="archive integration"):
        module.validate_dataset(dataset, NOW)


def test_historical_code_reuse_and_duplicate_assignment(dataset):
    def historical(d):
        code = copy.deepcopy(d["airlines"][1]["identity"]["codes"][0])
        code["valid_to"] = "2020-01-01T00:00:00Z"
        d["airlines"][0]["identity"]["codes"] = [code]
        d["airlines"][1]["identity"]["codes"][0]["valid_from"] = "2020-01-02T00:00:00Z"
    edit(dataset, "airline-index.v1.json", historical)
    module.validate_dataset(dataset, NOW)
    def duplicate(d):
        codes = d["airlines"][1]["identity"]["codes"]
        codes[0]["shared"] = True
        codes.append(copy.deepcopy(codes[0]))
    edit(dataset, "airline-index.v1.json", duplicate)
    with pytest.raises(ValueError, match="Duplicate code"):
        module.validate_dataset(dataset, NOW)


def test_code_assignment_dates_do_not_need_optional_format_plugins(dataset):
    edit(dataset, "airline-index.v1.json", lambda d:
         d["airlines"][0]["identity"]["codes"][0].update(valid_from="invalid"))
    with pytest.raises((ValueError, ValidationError)):
        module.validate_dataset(dataset, NOW)


def test_draft_fleet_can_hold_unverified_counts_without_publishing(dataset):
    def mutate(d):
        section = next(s for s in d["sections"] if s["id"] == "fleet")
        section["metadata"]["status"] = "draft"
        block = next(b for b in section["blocks"] if b["type"] == "fleet_snapshot")
        block["count"] = 19
        block["configuration_fa"] = "پیش‌نویس نیازمند بررسی"
        block["metadata"].update(status="draft", source_urls=[], verified_at=None,
                                 confidence="unverified")
    edit(dataset, "details/emirates.v1.json", mutate)
    module.validate_dataset(dataset, NOW)
    edit(dataset, "details/emirates.v1.json",
         lambda d: next(s for s in d["sections"] if s["id"] == "fleet")[
             "metadata"].update(status="published"))
    with pytest.raises(ValueError, match="published sources"):
        module.validate_dataset(dataset, NOW)


def test_dated_network_does_not_promote_listing_to_active_schedule():
    detail = module.read_json(ROOT / 'data/airlines/details/emirates.v1.json')
    network = next(s for s in detail['sections'] if s['id'] == 'network')
    routes = [b for b in network['blocks'] if b['type'] == 'route_snapshot']
    assert {(b['origin'], b['destination']) for b in routes} == {('DXB', 'LHR'), ('DXB', 'IKA')}
    tehran = next(b for b in routes if b['destination'] == 'IKA')
    assert tehran['status'] == 'listed'
    assert tehran['service_type'] == 'unknown' and tehran['operating_carrier'] is None
    assert all(b['metadata']['effective_to'] is None for b in routes)
    assert all('flight_number' not in b and 'price' not in b for b in routes)


@pytest.mark.parametrize('mutation', [
    lambda b: b.update(origin='ZZZ'),
    lambda b: b.update(destination=b['origin']),
    lambda b: b.update(operating_carrier='nonexistent'),
    lambda b: b.update(observed_at='2099-01-01T00:00:00Z'),
    lambda b: b['metadata'].update(source_urls=[]),
    lambda b: b['metadata'].update(status='draft'),
    lambda b: b.update(service_type='daily'),
    lambda b: b.update(status='active'),
])
def test_route_provenance_and_relations_fail_closed(dataset, mutation):
    def mutate(d):
        route = next(b for s in d['sections'] for b in s['blocks']
                     if b['type'] == 'route_snapshot')
        mutation(route)
    edit(dataset, 'details/emirates.v1.json', mutate)
    with pytest.raises((ValueError, ValidationError)):
        module.validate_dataset(dataset, NOW)


def test_iran_air_source_scoped_content_and_unknown_fleet():
    detail = module.read_json(ROOT / "data/airlines/details/iran-air.v1.json")
    sections = {section["id"]: section for section in detail["sections"]}
    assert len(sections) == 18
    assert detail["published_reviews"] == detail["experience_links"] == []
    assert sections["onboard-connectivity"]["metadata"]["status"] == "draft"
    assert sections["onboard-connectivity"]["blocks"] == []
    for section_id in ("baggage", "ticket-rules", "checkin", "fleet",
                       "special-assistance", "seat-selection", "batteries",
                       "lost-baggage", "network"):
        section = sections[section_id]
        assert section["metadata"]["status"] == "published"
        assert section["metadata"]["source_urls"]
        assert section["blocks"]
        assert section["metadata"]["verified_at"] == "2026-11-11T00:00:00Z"
        if section["kind"] == "policy":
            assert section["scope"]["operating_carrier"] == "iran-air"
            assert section["scope"]["seller"] == "unknown"
    models = [b for b in sections["fleet"]["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(models) == 9
    assert all(b["count"] is None and b["configuration_fa"] is None for b in models)
    assert all(b["status"] == b["relationship"] == "unknown" for b in models)
    assert all(b["metadata"]["source_urls"] for b in models)
    assert not any(b["type"] == "route_snapshot" for b in sections["network"]["blocks"])
    assert {b["iata"] for b in sections["network"]["blocks"] if
            b["type"] == "airport_link"} == {"THR", "IKA", "MHD", "BND", "DXB", "IST"}



@pytest.mark.parametrize("airline_id,published,draft,fleet_models", [
    ("mahan-air", 19, 1, 6),
    ("iran-aseman", 14, 4, 5),
])
def test_new_carriers_have_independent_sourced_sections(airline_id, published, draft, fleet_models):
    detail = module.read_json(ROOT / "data/airlines/details" / f"{airline_id}.v1.json")
    assert detail["airline_id"] == airline_id
    assert len(detail["sections"]) == published + draft
    assert len({s["id"] for s in detail["sections"]}) == len(detail["sections"])
    assert detail["published_reviews"] == detail["experience_links"] == []
    assert sum(s["metadata"]["status"] == "published" for s in detail["sections"]) == published
    for section in detail["sections"]:
        if section["metadata"]["status"] == "published":
            assert section["metadata"]["source_urls"]
            assert section["blocks"]
            assert section["metadata"]["verified_at"] == "2026-11-11T00:00:00Z"
        else:
            assert section["metadata"]["status"] == "draft"
            assert section["metadata"]["verified_at"] is None
            assert not section["blocks"]
        if section["kind"] == "policy":
            assert section["scope"]["operating_carrier"] == airline_id
            assert section["scope"]["seller"] == "unknown"
    fleet = next(s for s in detail["sections"] if s["id"] == "fleet")
    models = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(models) == fleet_models
    assert all(b["count"] is None and b["configuration_fa"] is None for b in models)
    assert all(b["status"] == "unknown" and b["relationship"] == "unknown" for b in models)
    network = next(s for s in detail["sections"] if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])


def test_new_airline_codes_and_official_domains():
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    entries = {e["airline_id"]: e for e in index["airlines"]}
    mahan = entries["mahan-air"]
    aseman = entries["iran-aseman"]
    assert {(x["system"], x["value"]) for x in mahan["identity"]["codes"]} == {
        ("iata", "W5"), ("icao", "IRM")}
    assert {(x["system"], x["value"]) for x in aseman["identity"]["codes"]} == {
        ("iata", "EP"), ("icao", "IRC")}
    assert mahan["identity"]["website"] == "https://www.mahanair.co.ir/"
    assert aseman["identity"]["website"] == "https://www.iaa.ir/"


def test_iran_airtour_sourced_scope_and_draft_exclusion():
    airline_id = "iran-airtour"
    detail = module.read_json(ROOT / "data/airlines/details/iran-airtour.v1.json")
    assert detail["airline_id"] == airline_id
    assert len(detail["sections"]) == 19
    assert len({s["id"] for s in detail["sections"]}) == 19
    assert detail["published_reviews"] == detail["experience_links"] == []
    published = [s for s in detail["sections"] if s["metadata"]["status"] == "published"]
    drafts = [s for s in detail["sections"] if s["metadata"]["status"] == "draft"]
    assert len(published) == 13
    assert len(drafts) == 6
    assert {s["id"] for s in drafts} == {
        "checkin", "seat-selection", "cabin", "catering",
        "lounges", "onboard-connectivity",
    }
    assert all(s["blocks"] and s["metadata"]["source_urls"] for s in published)
    assert all(s["blocks"] == [] and s["metadata"]["verified_at"] is None for s in drafts)
    for s in detail["sections"]:
        if s["kind"] == "policy":
            assert s["scope"]["operating_carrier"] == airline_id
            assert s["scope"]["seller"] == "unknown"
    fleet = next(s for s in published if s["id"] == "fleet")
    models = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(models) == 6
    assert all(b["count"] is None and b["configuration_fa"] is None for b in models)
    assert all(b["status"] == b["relationship"] == "unknown" for b in models)
    network = next(s for s in published if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    entry = next(x for x in index["airlines"] if x["airline_id"] == airline_id)
    assert {(x["system"], x["value"]) for x in entry["identity"]["codes"]} == {
        ("iata", "B9"), ("icao", "IRB"),
    }
    assert entry["identity"]["website"] == "https://www.iranairtour.ir/"


@pytest.mark.parametrize("airline_id,published,draft,models", [
    ("qeshm-air", 17, 2, 4),
    ("kish-air", 15, 5, 4),
])
def test_qeshm_kish_independent_sourced_guides(airline_id, published, draft, models):
    detail = module.read_json(ROOT / "data/airlines/details" / f"{airline_id}.v1.json")
    assert detail["airline_id"] == airline_id
    assert len(detail["sections"]) == published + draft
    assert len({s["id"] for s in detail["sections"]}) == published + draft
    assert detail["published_reviews"] == detail["experience_links"] == []
    active = [s for s in detail["sections"] if s["metadata"]["status"] == "published"]
    hidden = [s for s in detail["sections"] if s["metadata"]["status"] == "draft"]
    assert len(active) == published
    assert len(hidden) == draft
    assert all(s["blocks"] and s["metadata"]["source_urls"] for s in active)
    assert all(s["metadata"]["verified_at"] == "2026-11-11T00:00:00Z" for s in active)
    assert all(not s["blocks"] and s["metadata"]["verified_at"] is None for s in hidden)
    assert {s["id"] for s in hidden}.issuperset({"onboard-connectivity"})
    for s in detail["sections"]:
        if s["kind"] == "policy":
            assert s["scope"]["operating_carrier"] == airline_id
            assert s["scope"]["seller"] == "unknown"
    fleet = next(s for s in active if s["id"] == "fleet")
    blocks = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(blocks) == models
    assert all(b["count"] is None and b["configuration_fa"] is None for b in blocks)
    assert all(b["status"] == b["relationship"] == "unknown" for b in blocks)
    network = next(s for s in active if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])


def test_qeshm_kish_codes_and_draft_publication_limits():
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    lookup = {x["airline_id"]: x for x in index["airlines"]}
    assert {(c["system"], c["value"]) for c in
            lookup["qeshm-air"]["identity"]["codes"]} == {
        ("iata", "QB"), ("icao", "QSM"),
    }
    assert {(c["system"], c["value"]) for c in
            lookup["kish-air"]["identity"]["codes"]} == {
        ("iata", "Y9"), ("icao", "KIS"),
    }
    assert lookup["qeshm-air"]["identity"]["website"] == "https://www.qeshm-air.com/"
    assert lookup["kish-air"]["identity"]["website"] == "https://kishairlines.ir/"
    qeshm = module.read_json(ROOT / "data/airlines/details/qeshm-air.v1.json")
    kish = module.read_json(ROOT / "data/airlines/details/kish-air.v1.json")
    assert {s["id"] for s in qeshm["sections"] if
            s["metadata"]["status"] == "draft"} == {
        "catering", "onboard-connectivity",
    }
    assert {s["id"] for s in kish["sections"] if
            s["metadata"]["status"] == "draft"} == {
        "checkin", "seat-selection", "lounges", "pets", "onboard-connectivity",
    }



@pytest.mark.parametrize("airline_id,iata,icao,models", [
    ("zagros-air", "ZO", "IZG", 4),
    ("meraj-air", "IJ", "MRJ", 4),
])
def test_zagros_meraj_independent_source_and_publication_gates(
    airline_id, iata, icao, models
):
    details = ROOT / "data/airlines/details" / f"{airline_id}.v1.json"
    detail = module.read_json(details)
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    row = next(e for e in index["airlines"] if e["airline_id"] == airline_id)
    assert detail["airline_id"] == airline_id
    assert len(detail["sections"]) == 20
    assert len({s["id"] for s in detail["sections"]}) == 20
    assert detail["published_reviews"] == detail["experience_links"] == []
    assert row["detail_path"] == f"details/{airline_id}.v1.json"
    assert {(c["system"], c["value"]) for c in row["identity"]["codes"]} == {
        ("iata", iata), ("icao", icao),
    }
    assert row["metadata"]["status"] == "published"
    assert row["metadata"]["source_urls"]

    published = [s for s in detail["sections"] if
                 s["metadata"]["status"] == "published"]
    draft = [s for s in detail["sections"] if
             s["metadata"]["status"] == "draft"]
    assert len(published) == 14
    assert len(draft) == 6
    expected_draft = {
        "checkin", "seat-selection", "catering",
        "lounges", "pets", "onboard-connectivity",
    }
    assert {s["id"] for s in draft} == expected_draft
    assert all(s["blocks"] and s["metadata"]["source_urls"] for s in published)
    assert all(s["metadata"]["verified_at"] == "2026-11-11T00:00:00Z"
               for s in published)
    assert all(s["blocks"] == [] and s["metadata"]["verified_at"] is None
               for s in draft)
    for section in detail["sections"]:
        if section["kind"] == "policy":
            assert section["scope"]["operating_carrier"] == airline_id
            assert section["scope"]["seller"] == "unknown"
            assert section["scope"]["route"] is None

    fleet = next(s for s in published if s["id"] == "fleet")
    aircraft = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(aircraft) == models
    assert all(b["count"] is None and b["configuration_fa"] is None
               for b in aircraft)
    assert all(b["status"] == "unknown" and b["relationship"] == "unknown"
               for b in aircraft)
    network = next(s for s in published if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])


def test_zagros_meraj_airline_baggage_cannot_be_read_as_universal_allowance():
    zagros = module.read_json(ROOT / "data/airlines/details/zagros-air.v1.json")
    meraj = module.read_json(ROOT / "data/airlines/details/meraj-air.v1.json")
    for detail in (zagros, meraj):
        baggage = next(s for s in detail["sections"] if s["id"] == "baggage")
        assert baggage["metadata"]["confidence"] == "secondary"
        assert baggage["scope"]["fare_brand"] is None
        assert baggage["scope"]["operating_carrier"] == detail["airline_id"]
    meraj_text = " ".join(
        b["text_fa"] for b in
        next(s for s in meraj["sections"] if s["id"] == "baggage")["blocks"]
        if b["type"] == "text"
    )
    assert "رشت" in meraj_text
    assert "همه" in meraj_text


@pytest.mark.parametrize("airline_id,published,draft,fleet_models,draft_ids", [
    ("ata-air", 16, 4, 7,
     {"seat-selection", "catering", "lounges", "onboard-connectivity"}),
    ("varesh-air", 18, 2, 3,
     {"seat-selection", "onboard-connectivity"}),
])
def test_ata_varesh_independent_source_scoped_guides(
    airline_id, published, draft, fleet_models, draft_ids
):
    detail = module.read_json(
        ROOT / "data/airlines/details" / f"{airline_id}.v1.json"
    )
    assert detail["airline_id"] == airline_id
    assert len(detail["sections"]) == 20
    assert len({s["id"] for s in detail["sections"]}) == 20
    assert detail["published_reviews"] == detail["experience_links"] == []
    released = [s for s in detail["sections"] if s["metadata"]["status"] == "published"]
    hidden = [s for s in detail["sections"] if s["metadata"]["status"] == "draft"]
    assert len(released) == published
    assert len(hidden) == draft
    assert {s["id"] for s in hidden} == draft_ids
    assert all(s["blocks"] and s["metadata"]["source_urls"] for s in released)
    assert all(s["metadata"]["verified_at"] == "2026-11-11T00:00:00Z"
               for s in released)
    assert all(s["blocks"] == [] and s["metadata"]["verified_at"] is None
               for s in hidden)
    for section in detail["sections"]:
        if section["kind"] == "policy":
            assert section["scope"]["operating_carrier"] == airline_id
            assert section["scope"]["seller"] == "unknown"
            assert section["scope"]["fare_brand"] is None
    fleet = next(s for s in released if s["id"] == "fleet")
    snapshots = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(snapshots) == fleet_models
    assert all(b["count"] is None and b["configuration_fa"] is None
               for b in snapshots)
    assert all(b["status"] == b["relationship"] == "unknown" for b in snapshots)
    network = next(s for s in released if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])


def test_ata_varesh_codes_and_official_websites():
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    entries = {e["airline_id"]: e for e in index["airlines"]}
    ata = entries["ata-air"]
    varesh = entries["varesh-air"]
    assert {(c["system"], c["value"]) for c in ata["identity"]["codes"]} == {
        ("iata", "I3"), ("icao", "TBZ")
    }
    assert {(c["system"], c["value"]) for c in varesh["identity"]["codes"]} == {
        ("icao", "VRH")
    }
    assert ata["identity"]["website"] == "https://ataair.ir/"
    assert varesh["identity"]["website"] == "https://vareshair.ir/"
    assert varesh["identity"]["former_names"] == []
    # Without verified IATA code for Varesh, never create a guessed placeholder.
    assert all(c["system"] != "iata" for c in varesh["identity"]["codes"])



@pytest.mark.parametrize("airline_id,published,drafts,models,hidden_ids", [
    ("caspian-air", 14, 6, 7,
     {"checkin", "seat-selection", "catering", "lounges", "pets",
      "onboard-connectivity"}),
    ("sepehran-air", 19, 2, 5, {"lounges", "onboard-connectivity"}),
])
def test_caspian_sepehran_independent_source_and_publishing_gates(
    airline_id, published, drafts, models, hidden_ids
):
    data = module.read_json(
        ROOT / "data/airlines/details" / f"{airline_id}.v1.json"
    )
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    row = next(e for e in index["airlines"] if e["airline_id"] == airline_id)
    assert data["airline_id"] == airline_id
    assert len(data["sections"]) == published + drafts
    assert len({s["id"] for s in data["sections"]}) == published + drafts
    assert data["published_reviews"] == data["experience_links"] == []
    assert row["detail_path"] == f"details/{airline_id}.v1.json"
    active = [s for s in data["sections"] if s["metadata"]["status"] == "published"]
    hidden = [s for s in data["sections"] if s["metadata"]["status"] == "draft"]
    assert len(active) == published
    assert len(hidden) == drafts
    assert {s["id"] for s in hidden} == hidden_ids
    assert all(s["blocks"] and s["metadata"]["source_urls"] for s in active)
    assert all(s["metadata"]["verified_at"] == "2026-11-11T00:00:00Z"
               for s in active)
    assert all(s["blocks"] == [] and s["metadata"]["verified_at"] is None
               for s in hidden)
    for section in data["sections"]:
        if section["kind"] == "policy":
            assert section["scope"]["operating_carrier"] == airline_id
            assert section["scope"]["seller"] == "unknown"
            assert section["scope"]["route"] is None
    fleet = next(s for s in active if s["id"] == "fleet")
    aircraft = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert len(aircraft) == models
    assert all(b["count"] is None and b["configuration_fa"] is None
               for b in aircraft)
    assert all(b["status"] == b["relationship"] == "unknown" for b in aircraft)
    network = next(s for s in active if s["id"] == "network")
    assert not any(b["type"] == "route_snapshot" for b in network["blocks"])


def test_caspian_icao_only_and_sepehran_industry_codes():
    catalog = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    rows = {x["airline_id"]: x for x in catalog["airlines"]}
    assert {(c["system"], c["value"]) for c in
            rows["caspian-air"]["identity"]["codes"]} == {
        ("icao", "CPN")
    }
    assert {(c["system"], c["value"]) for c in
            rows["sepehran-air"]["identity"]["codes"]} == {
        ("iata", "IS"), ("icao", "SHI")
    }
    assert rows["caspian-air"]["identity"]["website"] == (
        "https://caspianairlines.com/"
    )
    assert rows["sepehran-air"]["identity"]["website"] == (
        "https://flysepehran.com/"
    )
    sepehran = module.read_json(
        ROOT / "data/airlines/details/sepehran-air.v1.json"
    )
    seat = next(s for s in sepehran["sections"] if s["id"] == "seat-selection")
    seat_text = " ".join(b["text_fa"] for b in seat["blocks"]
                         if b["type"] == "text")
    assert "۳ ساعت" in seat_text and "۴ ساعت" in seat_text
    assert "تعارض" in seat_text
    caspian = module.read_json(
        ROOT / "data/airlines/details/caspian-air.v1.json"
    )
    bags = next(s for s in caspian["sections"] if s["id"] == "baggage")
    assert bags["metadata"]["confidence"] == "secondary"
    assert "تاریخ" in bags["scope"]["note_fa"]

