"""Regression guard for the 20 remaining curated airport guides."""
import json
from pathlib import Path

from scripts.validate_airport_content import validate_dataset

ROOT = Path(__file__).resolve().parents[1]
CODES = ["AMS","ATH","AUH","AWZ","BKK","CDG","DEL","DOH","DXB","FRA","IFN","KIH","KUL","LHR","MAD","MSQ","MUC","OMH","PEK","ZAH"]


def test_all_original_29_airports_enabled_and_remaining_guides_are_source_backed():
    validate_dataset()
    base = ROOT / "data" / "airports"
    idx = json.loads((base / "airport-index.v1.json").read_text(encoding="utf-8"))
    assert len(idx["airports"]) == 29
    assert all(e["enabled"] for e in idx["airports"])
    for code in CODES:
        detail = json.loads((base / "details" / (code + ".v1.json")).read_text(encoding="utf-8"))
        assert detail["iata"] == code
        assert [s["id"] for s in detail["sections"][:5]] == [
            "baggage-rules", "flight-status", "traveler-experiences", "airport-map", "airport-videos"
        ]
        published = [s for s in detail["sections"] if s["status"] == "published"]
        assert len(published) >= 9, code
        assert all(s["blocks"] and s["reviewed_at"] and s["source_urls"] for s in published)
        assert {s["id"] for s in detail["sections"] if s["status"] == "draft"} >= {"traveler-experiences", "airport-videos"}
        assert not any(b["type"] in ("video", "experience") for s in published for b in s["blocks"])
        assert not any(b["type"] == "flight_board" for s in published for b in s["blocks"])
