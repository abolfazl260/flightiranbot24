"""Contracts for editable airport-specific content (no invented live flight data)."""

import copy
import json
import shutil
from pathlib import Path
from runpy import run_path

import pytest

ROOT = Path(__file__).resolve().parents[1]
validate_dataset = run_path(str(ROOT / "scripts/validate_airport_content.py"))["validate_dataset"]


def copy_catalog(tmp_path: Path) -> Path:
    src = ROOT / "data" / "airports"
    dst = tmp_path / "data" / "airports"
    dst.parent.mkdir(parents=True)
    shutil.copytree(src, dst)
    canonical = tmp_path / "src/flightiran/modules/airport/data"
    canonical.mkdir(parents=True)
    identity = ROOT / "src/flightiran/modules/airport/data/airports.json"
    shutil.copy(identity, canonical / "airports.json")
    return dst


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_third_party_content_is_draft_and_extensible():
    validate_dataset()
    root = ROOT / "data" / "airports"
    index = load(root / "airport-index.v1.json")
    detail = load(root / "details/THR.v1.json")
    assert index["airports"] == [
        {"iata": "THR", "detail_path": "details/THR.v1.json", "enabled": False}
    ]
    assert [section["id"] for section in detail["sections"]] == [
        "baggage-rules", "flight-status", "traveler-experiences",
        "airport-map", "airport-videos",
    ]
    assert all(
        section["status"] == "draft" and not section["blocks"]
        for section in detail["sections"]
    )


def test_new_airport_and_new_section_need_no_schema_change(tmp_path):
    base = copy_catalog(tmp_path)
    index = load(base / "airport-index.v1.json")
    index["airports"].append({
        "iata": "MHD", "detail_path": "details/MHD.v1.json", "enabled": False,
    })
    save(base / "airport-index.v1.json", index)
    save(base / "details/MHD.v1.json", {
        "schema_version": 1, "iata": "MHD",
        "sections": [{
            "id": "parking", "title_fa": "پارکینگ", "icon": "car", "order": 60,
            "status": "draft", "reviewed_at": None, "source_urls": [], "blocks": [],
        }],
    })
    validate_dataset(tmp_path)


def test_published_section_requires_review_and_evidence(tmp_path):
    base = copy_catalog(tmp_path)
    content = load(base / "details/THR.v1.json")
    first = content["sections"][0]
    first["status"] = "published"
    first["blocks"] = [{"type": "text", "text_fa": "قوانین بر اساس ایرلاین متفاوت است."}]
    save(base / "details/THR.v1.json", content)
    with pytest.raises(ValueError, match="reviewed content"):
        validate_dataset(tmp_path)
    first["reviewed_at"] = "2026-11-03T12:00:00Z"
    save(base / "details/THR.v1.json", content)
    with pytest.raises(ValueError, match="require sources"):
        validate_dataset(tmp_path)
    first["source_urls"] = ["https://www.iata.org/"]
    save(base / "details/THR.v1.json", content)
    validate_dataset(tmp_path)


def test_rejects_duplicate_sections_and_unsafe_urls(tmp_path):
    base = copy_catalog(tmp_path)
    path = base / "details/THR.v1.json"
    detail = load(path)
    detail["sections"].append(copy.deepcopy(detail["sections"][0]))
    save(path, detail)
    with pytest.raises(ValueError, match="Duplicate section"):
        validate_dataset(tmp_path)
    detail["sections"].pop()
    section = detail["sections"][0]
    section.update({
        "status": "published",
        "reviewed_at": "2026-11-03T12:00:00Z",
        "source_urls": ["http://unsafe.example.com/"],
        "blocks": [{"type": "text", "text_fa": "Example"}],
    })
    save(path, detail)
    with pytest.raises(Exception):
        validate_dataset(tmp_path)


def test_unapproved_experiences_never_publish(tmp_path):
    base = copy_catalog(tmp_path)
    path = base / "details/THR.v1.json"
    detail = load(path)
    section = next(s for s in detail["sections"] if s["id"] == "traveler-experiences")
    section.update({
        "status": "published",
        "reviewed_at": "2026-11-03T12:00:00Z",
        "blocks": [{
            "type": "experience", "id": "review-001", "text_fa": "تجربه ثبت‌شده مسافر",
            "rating": 4, "visit_date": "2026-10-29", "approved": False,
        }],
    })
    save(path, detail)
    with pytest.raises(ValueError, match="Unapproved experience"):
        validate_dataset(tmp_path)
