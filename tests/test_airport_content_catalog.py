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
    assert len(expected) >= 29
    assert "GSM" in expected
    assert {e["iata"] for e in index["airports"]} == expected

    enabled = {e["iata"] for e in index["airports"] if e["enabled"]}
    assert {"IKA", "MHD", "TBZ", "GSM"}.issubset(enabled)

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

    gsm = load(root / "details/GSM.v1.json")
    published_gsm = [s for s in gsm["sections"] if s["status"] == "published"]
    assert len(published_gsm) == 11
    assert {s["id"] for s in gsm["sections"] if s["status"] == "draft"} == {
        "traveler-experiences", "airport-videos",
    }
    assert any(b["type"] == "map" for s in published_gsm for b in s["blocks"])

    mhd = load(root / "details/MHD.v1.json")
    assert len([s for s in mhd["sections"] if s["status"] == "published"]) >= 17
    assert {
        s["id"] for s in mhd["sections"] if s["status"] == "draft"
    } == {"traveler-experiences", "airport-videos"}


def test_tabrix_bundled_catalog_has_source_backed_sections():
    airport = load(ROOT / "data/airports/details/TBZ.v1.json")
    assert airport["iata"] == "TBZ"
    assert len(airport["sections"]) == 15
    published = [s for s in airport["sections"] if s["status"] == "published"]
    drafts = [s for s in airport["sections"] if s["status"] == "draft"]
    assert len(published) == 13
    assert {s["id"] for s in drafts} == {"traveler-experiences", "airport-videos"}
    assert all(s["blocks"] and s["source_urls"] and s["reviewed_at"] for s in published)
    assert all(not s["blocks"] and not s["source_urls"] for s in drafts)


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

def test_istanbul_airport_guide_is_enabled_and_uses_evidence():
    """Istanbul guide has published source-backed data but no fabricated experiences."""
    validate_dataset()
    base = ROOT / "data" / "airports"
    index = load(base / "airport-index.v1.json")
    ist_entry = next(e for e in index["airports"] if e["iata"] == "IST")
    assert ist_entry["enabled"] is True
    detail = load(base / ist_entry["detail_path"])
    assert detail["iata"] == "IST"
    sections = detail["sections"]
    assert len({s["id"] for s in sections}) == len(sections)
    published = [s for s in sections if s["status"] == "published"]
    assert len(published) >= 18
    assert all(s["source_urls"] and s["blocks"] and s["reviewed_at"] for s in published)
    experiences = next(s for s in sections if s["id"] == "traveler-experiences")
    assert experiences["status"] == "draft"
    assert not experiences["blocks"]
    assert not any(
        block["type"] == "flight_board"
        for section in published
        for block in section["blocks"]
    )

def test_kish_guide_is_enabled_with_verified_sections_and_reserved_drafts():
    """Kish has source-backed sections without unlicensed media or live flight data."""
    validate_dataset()
    base = ROOT / "data" / "airports"
    index = load(base / "airport-index.v1.json")
    entry = next(e for e in index["airports"] if e["iata"] == "KIH")
    assert entry["enabled"] is True
    detail = load(base / entry["detail_path"])
    assert detail["iata"] == "KIH"
    sections = detail["sections"]
    assert len(sections) == 19
    assert len({s["id"] for s in sections}) == len(sections)
    published = [s for s in sections if s["status"] == "published"]
    drafts = [s for s in sections if s["status"] == "draft"]
    assert len(published) == 17
    assert {s["id"] for s in drafts} == {"traveler-experiences", "airport-videos"}
    assert all(not s["blocks"] and not s["source_urls"] for s in drafts)
    assert all(s["blocks"] and s["source_urls"] and s["reviewed_at"] for s in published)
    assert any(b["type"] == "map" for s in published for b in s["blocks"])
    assert all(
        b["type"] not in {"video", "experience", "flight_board"}
        for s in published for b in s["blocks"]
    )

def test_ahvaz_airport_guide_has_sourced_content_and_safe_drafts():
    """AWZ is individually enabled without fabricated experiences or media."""
    validate_dataset()
    root = ROOT / "data/airports"
    index = load(root / "airport-index.v1.json")
    awz_entry = next(e for e in index["airports"] if e["iata"] == "AWZ")
    assert awz_entry["enabled"] is True
    data = load(root / awz_entry["detail_path"])
    assert data["iata"] == "AWZ"
    assert len(data["sections"]) == 19
    published = [s for s in data["sections"] if s["status"] == "published"]
    drafts = [s for s in data["sections"] if s["status"] == "draft"]
    assert len(published) == 17
    assert {s["id"] for s in drafts} == {"traveler-experiences", "airport-videos"}
    assert all(s["source_urls"] and s["reviewed_at"] and s["blocks"] for s in published)
    assert all(not s["source_urls"] and not s["blocks"] for s in drafts)
    assert any(b["type"] == "map" for s in published for b in s["blocks"])
    assert not any(
        b["type"] in {"experience", "video", "flight_board"}
        for s in published
        for b in s["blocks"]
    )


def test_urmia_and_zahedan_publish_verified_passenger_guides_but_not_fake_reviews():
    root = ROOT / "data/airports/details"
    for code, expected_video_url in (
        ("OMH", "https://t.me/airportnews/42349"),
        ("ZAH", "https://t.me/zahedanairport/10175"),
    ):
        airport = load(root / f"{code}.v1.json")
        published = [s for s in airport["sections"] if s["status"] == "published"]
        drafts = [s for s in airport["sections"] if s["status"] == "draft"]
        assert len(published) == 18
        assert {s["id"] for s in drafts} == {"traveler-experiences"}
        assert all(s["blocks"] and s["source_urls"] and s["reviewed_at"] for s in published)
        assert all(not s["blocks"] and not s["source_urls"] for s in drafts)
        video = next(s for s in published if s["id"] == "airport-videos")
        assert any(
            b["type"] == "video" and b["url"] == expected_video_url
            for b in video["blocks"]
        )
        assert not any(
            b["type"] == "experience"
            for section in airport["sections"]
            for b in section["blocks"]
        )

    urmia = load(root / "OMH.v1.json")
    ground = next(s for s in urmia["sections"] if s["id"] == "ground-transport")
    assert "تاکسی و اتوبوس" in " ".join(
        b.get("text_fa", "") for b in ground["blocks"]
    )
    zah = load(root / "ZAH.v1.json")
    terminal = next(s for s in zah["sections"] if s["id"] == "terminals")
    assert any("داخلی و خارجی" in b.get("text_fa", "") for b in terminal["blocks"])


def test_six_international_airports_publish_official_parking_lounge_and_transfer_guides():
    base = ROOT / "data/airports/details"
    expected = {
        "AMS": {"parking", "lounges"},
        "ATH": {"lounges", "connections"},
        "AUH": {"parking"},
        "BKK": {"parking", "lounges"},
        "CDG": {"parking", "lounges"},
        "DEL": {"parking"},
    }
    for code, section_ids in expected.items():
        airport = load(base / f"{code}.v1.json")
        sections = {s["id"]: s for s in airport["sections"]}
        for section_id in section_ids:
            section = sections[section_id]
            assert section["status"] == "published"
            assert section["reviewed_at"] == "2026-11-11T00:00:00Z"
            assert section["source_urls"]
            assert section["blocks"]
            assert all(b["type"] in {"text", "bullets", "link"} for b in section["blocks"])
        drafts = {s["id"] for s in airport["sections"] if s["status"] == "draft"}
        assert drafts == {"traveler-experiences", "airport-videos"}
        assert all(
            not any(b["type"] == "experience" for b in s["blocks"])
            for s in airport["sections"]
        )


def test_six_more_international_airports_publish_official_parking_and_lounge_guides():
    base = ROOT / "data/airports/details"
    expected = {
        "DOH": {"parking", "lounges"},
        "DXB": {"parking", "lounges"},
        "FRA": {"parking", "lounges"},
        "KUL": {"parking", "lounges"},
        "LHR": {"parking", "lounges"},
        "MAD": {"parking", "lounges"},
    }
    for code, section_ids in expected.items():
        airport = load(base / f"{code}.v1.json")
        sections = {s["id"]: s for s in airport["sections"]}
        for section_id in section_ids:
            section = sections[section_id]
            assert section["status"] == "published"
            assert section["reviewed_at"] == "2026-11-11T00:00:00Z"
            assert section["source_urls"]
            assert section["blocks"]
            assert all(b["type"] in {"text", "bullets", "link"} for b in section["blocks"])
        drafts = {s["id"] for s in airport["sections"] if s["status"] == "draft"}
        assert drafts == {"traveler-experiences", "airport-videos"}

    doha = load(base / "DOH.v1.json")
    parking = next(s for s in doha["sections"] if s["id"] == "parking")
    assert "۳٬۳۲۵" in " ".join(b.get("text_fa", "") for b in parking["blocks"])
    dxb = load(base / "DXB.v1.json")
    lounges = next(s for s in dxb["sections"] if s["id"] == "lounges")
    assert "Assisted Travel Lounge" in " ".join(
        b.get("text_fa", "") for b in lounges["blocks"]
    )
    kul = load(base / "KUL.v1.json")
    assert "۵٬۷۰۰" in " ".join(
        b.get("text_fa", "")
        for b in next(s for s in kul["sections"] if s["id"] == "parking")["blocks"]
    )
    heathrow = load(base / "LHR.v1.json")
    heathrow_parking = next(
        s for s in heathrow["sections"] if s["id"] == "parking"
    )
    heathrow_parking_text = " ".join(
        b.get("text_fa", "") + " " + " ".join(b.get("items_fa", []))
        for b in heathrow_parking["blocks"]
    )
    assert "۲۳ ژوئن" in heathrow_parking_text
    madrid = load(base / "MAD.v1.json")
    assert "Neptuno" in " ".join(
        b.get("text_fa", "")
        for b in next(s for s in madrid["sections"] if s["id"] == "lounges")["blocks"]
    )


def test_munich_minsk_and_beijing_publish_official_parking_and_lounge_guides():
    base = ROOT / "data/airports/details"
    for code in ("MUC", "MSQ", "PEK"):
        airport = load(base / f"{code}.v1.json")
        sections = {s["id"]: s for s in airport["sections"]}
        for section_id in ("parking", "lounges"):
            section = sections[section_id]
            assert section["status"] == "published"
            assert section["reviewed_at"] == "2026-11-11T00:00:00Z"
            assert section["source_urls"]
            assert section["blocks"]
            assert all(b["type"] in {"text", "bullets", "link"} for b in section["blocks"])
        assert {
            s["id"] for s in airport["sections"] if s["status"] == "draft"
        } == {"traveler-experiences", "airport-videos"}

    munich = load(base / "MUC.v1.json")
    munich_parking = next(s for s in munich["sections"] if s["id"] == "parking")
    munich_text = " ".join(
        b.get("text_fa", "") + " " + " ".join(b.get("items_fa", []))
        for b in munich_parking["blocks"]
    )
    assert "۲ نوامبر ۲۰۲۶" in munich_text
    assert "P8" in munich_text

    minsk = load(base / "MSQ.v1.json")
    minsk_parking = next(s for s in minsk["sections"] if s["id"] == "parking")
    minsk_text = " ".join(
        b.get("text_fa", "") + " " + " ".join(b.get("items_fa", []))
        for b in minsk_parking["blocks"]
    )
    assert "۱٬۲۳۵" in minsk_text
    assert "متفاوت" in minsk_text
    minsk_lounge = next(s for s in minsk["sections"] if s["id"] == "lounges")
    assert "VIP/CIP" in " ".join(b.get("text_fa", "") for b in minsk_lounge["blocks"])

    beijing = load(base / "PEK.v1.json")
    beijing_parking = next(s for s in beijing["sections"] if s["id"] == "parking")
    beijing_text = " ".join(
        b.get("text_fa", "") + " " + " ".join(b.get("items_fa", []))
        for b in beijing_parking["blocks"]
    )
    assert "۴٬۳۰۰" in beijing_text
    beijing_lounge = next(s for s in beijing["sections"] if s["id"] == "lounges")
    beijing_text = " ".join(
        b.get("text_fa", "") + " " + " ".join(b.get("items_fa", []))
        for b in beijing_lounge["blocks"]
    )
    assert "Ji Hotel" in beijing_text
