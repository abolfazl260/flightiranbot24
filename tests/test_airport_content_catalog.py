"""Per-airport JSON fixtures remain independently editable in GitHub."""

import copy
import json
import shutil
from pathlib import Path
from runpy import run_path

import pytest

ROOT = Path(__file__).resolve().parents[1]
validate_dataset = run_path(str(ROOT / "scripts/validate_airport_content.py"))[
    "validate_dataset"
]


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


def test_each_existing_airport_has_independent_content_and_valid_publication():
    """Published airport content may grow without rewriting a static allowlist."""
    validate_dataset()
    root = ROOT / "data" / "airports"
    canonical = load(ROOT / "src/flightiran/modules/airport/data/airports.json")
    index = load(root / "airport-index.v1.json")
    expected = {a["code"] for a in canonical}
    assert len(expected) == 28
    assert {e["iata"] for e in index["airports"]} == expected

    enabled = {e["iata"] for e in index["airports"] if e["enabled"]}
    assert {"IKA", "MHD"}.issubset(enabled)

    for entry in index["airports"]:
        detail = load(root / entry["detail_path"])
        assert detail["iata"] == entry["iata"]
        assert [s["id"] for s in detail["sections"][:5]] == [
            "baggage-rules", "flight-status", "traveler-experiences",
            "airport-map", "airport-videos",
        ]
        published = [s for s in detail["sections"] if s["status"] == "published"]
        if entry["enabled"]:
            assert published, entry["iata"]
        assert all(s["blocks"] and s["source_urls"] and s["reviewed_at"] for s in published)

    mhd = load(root / "details/MHD.v1.json")
    assert len([s for s in mhd["sections"] if s["status"] == "published"]) >= 17
    assert {
        s["id"] for s in mhd["sections"] if s["status"] == "draft"
    } == {"traveler-experiences", "airport-videos"}


def test_add_section_to_one_airport_does_not_affect_other_airports(tmp_path):
    base = copy_catalog(tmp_path)
    thr = base / "details/THR.v1.json"
    mhd = base / "details/MHD.v1.json"
    original_mhd = load(mhd)
    airport = load(thr)
    airport["sections"].append({
        "id": "test-independent-section", "title_fa": "بخش آزمایشی", "icon": "info",
        "order": max(s["order"] for s in airport["sections"]) + 10,
        "status": "draft", "reviewed_at": None, "source_urls": [], "blocks": [],
    })
    save(thr, airport)
    validate_dataset(tmp_path)
    assert load(mhd) == original_mhd


def test_published_section_requires_review_and_evidence(tmp_path):
    base = copy_catalog(tmp_path)
    content = load(base / "details/THR.v1.json")
    first = next(s for s in content["sections"] if s["id"] == "airport-videos")
    first["status"] = "published"
    first["reviewed_at"] = None
    first["source_urls"] = []
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
    section = next(s for s in detail["sections"] if s["id"] == "airport-videos")
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
