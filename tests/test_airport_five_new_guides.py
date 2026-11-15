"""Source and privacy guardrails for five newly cataloged Iranian airports."""
import json
from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[1]
validate = run_path(str(ROOT / "scripts/validate_airport_content.py"))["validate_dataset"]
NEW = {"AZD": "OIYY", "RAS": "OIGG", "SRY": "OINZ", "BUZ": "OIBB", "ABD": "OIAA"}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_new_airports_identity_index_and_per_airport_guides():
    validate()
    index = read(ROOT / "data/airports/airport-index.v1.json")["airports"]
    identities = read(ROOT / "src/flightiran/modules/airport/data/airports.json")
    assert len(index) == len(identities) == 34
    assert len({row["iata"] for row in index}) == 34
    assert len([row for row in identities if row["country"] == "IR"]) == 18
    assert all(row["enabled"] for row in index)
    for code, icao in NEW.items():
        assert any(row["code"] == code for row in identities)
        assert any(row["iata"] == code for row in index)
        guide = read(ROOT / f"data/airports/details/{code}.v1.json")
        assert guide["iata"] == code
        sections = guide["sections"]
        assert [s["id"] for s in sections[:5]] == [
            "baggage-rules", "flight-status", "traveler-experiences",
            "airport-map", "airport-videos"]
        published = [s for s in sections if s["status"] == "published"]
        drafts = [s for s in sections if s["status"] == "draft"]
        assert len(published) >= 14, code
        assert {"traveler-experiences", "airport-videos", "lounges"}.issubset(
            {s["id"] for s in drafts})
        assert all(s["source_urls"] and s["blocks"] and s["reviewed_at"] for s in published)
        assert all(not s["source_urls"] and not s["blocks"] and s["reviewed_at"] is None for s in drafts)
        assert not any(b["type"] in {"video", "experience", "image", "flight_board"}
                       for s in published for b in s["blocks"])
        assert any(b.get("type") == "map" for s in published for b in s["blocks"])
        identity = next(s for s in published if s["id"] == "airport-identity")
        assert any(icao in b.get("text_fa", "") for b in identity["blocks"])

def test_sari_runway_work_is_not_presented_as_verified_reopening():
    status = next(s for s in read(ROOT / "data/airports/details/SRY.v1.json")["sections"]
                  if s["id"] == "flight-status")
    assert status["status"] == "published"
    text = " ".join(b.get("text_fa", "") for b in status["blocks"])
    assert "بهسازی باند" in text and "احراز نشد" in text
