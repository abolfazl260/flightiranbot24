"""Safely scaffold new airport pages and sections without publishing empty content.

Examples:
  python scripts/airport_content.py add-airport MHD
  python scripts/airport_content.py add-section THR --id parking --title "پارکینگ" --icon parking --order 60
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_airport_content import ROOT, read_json, validate_dataset

BASE = ROOT / "data" / "airports"
INDEX = BASE / "airport-index.v1.json"


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add unpublished airport data or a draft section")
    sub = parser.add_subparsers(dest="command", required=True)
    airport_parser = sub.add_parser("add-airport")
    airport_parser.add_argument("iata")
    section_parser = sub.add_parser("add-section")
    section_parser.add_argument("iata")
    section_parser.add_argument("--id", required=True)
    section_parser.add_argument("--title", required=True)
    section_parser.add_argument("--icon", default="info")
    section_parser.add_argument("--order", type=int, default=100)
    args = parser.parse_args()
    validate_dataset()
    code = args.iata.strip().upper()
    identities = read_json(ROOT / "src/flightiran/modules/airport/data/airports.json")
    if code not in {entry["code"] for entry in identities}:
        parser.error("IATA code not found in the canonical airport identity registry")

    index = read_json(INDEX)
    entry = next((item for item in index["airports"] if item["iata"] == code), None)
    if args.command == "add-airport":
        if entry:
            parser.error("Airport page already exists")
        detail_file = BASE / "details" / (code + ".v1.json")
        save(detail_file, {"schema_version": 1, "iata": code, "sections": []})
        index["airports"].append({
            "iata": code, "detail_path": "details/" + code + ".v1.json", "enabled": False
        })
        index["airports"].sort(key=lambda item: item["iata"])
        save(INDEX, index)
    else:
        if not entry:
            parser.error("Create the airport page first with add-airport")
        detail_file = BASE / entry["detail_path"]
        detail = read_json(detail_file)
        if any(section["id"] == args.id for section in detail["sections"]):
            parser.error("Section ID already exists for this airport")
        if not args.id or not args.id[0].islower() or not all(
            char.islower() or char.isdigit() or char == "-" for char in args.id
        ):
            parser.error("Section ID must be lowercase kebab-case")
        detail["sections"].append({
            "id": args.id,
            "title_fa": args.title,
            "icon": args.icon,
            "order": args.order,
            "status": "draft",
            "reviewed_at": None,
            "source_urls": [],
            "blocks": [],
        })
        detail["sections"].sort(key=lambda section: (section["order"], section["id"]))
        save(detail_file, detail)
    validate_dataset()
    print("Draft created for " + code + "; nothing has been published")


if __name__ == "__main__":
    main()
