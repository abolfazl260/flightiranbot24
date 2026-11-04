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
NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


def test_actual_catalog_and_independent_snapshots():
    module.validate_dataset(now=NOW)
    index = module.read_json(ROOT / "data/airlines/airline-index.v1.json")
    assert [r["airline_id"] for r in index["airlines"]] == ["iran-air", "emirates"]
    coverage = {}
    for entry in index["airlines"]:
        detail = module.read_json(ROOT / "data/airlines" / entry["detail_path"])
        assert detail["airline_id"] == entry["airline_id"]
        assert detail["published_reviews"] == detail["experience_links"] == []
        coverage[entry["airline_id"]] = {
            status: sum(s["metadata"]["status"] == status for s in detail["sections"])
            for status in ("published", "draft")
        }
    assert coverage == {"iran-air": {"published": 1, "draft": 4},
                        "emirates": {"published": 7, "draft": 2}}
    fleet = next(s for s in detail["sections"] if s["id"] == "fleet")
    models = [b for b in fleet["blocks"] if b["type"] == "fleet_snapshot"]
    assert [b["model"] for b in models] == ["A350", "A380", "777"]
    assert all(b["count"] is None and b["relationship"] == "operated" for b in models)


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
        block = next(s for s in d["sections"] if s["id"] == "fleet")["blocks"][1]
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
