"""Validate the public, extensible per-airport content catalog before publication.

Run: python scripts/validate_airport_content.py
The 28-airport identity catalog remains the source of airport identity; this is
a separate, optional registry for curated content. Drafts are never published.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_https(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port == 0
    ):
        raise ValueError("Invalid public HTTPS URL: " + url)


def validate_dataset(root: Path = ROOT) -> None:
    base = root / "data" / "airports"
    index_schema = read_json(base / "airport-index.schema.json")
    detail_schema = read_json(base / "airport-detail.schema.json")
    for schema in (index_schema, detail_schema):
        Draft202012Validator.check_schema(schema)
    index_validator = Draft202012Validator(index_schema, format_checker=FormatChecker())
    detail_validator = Draft202012Validator(detail_schema, format_checker=FormatChecker())
    index = read_json(base / "airport-index.v1.json")
    index_validator.validate(index)
    identities = read_json(root / "src" / "flightiran" / "modules" / "airport" / "data" / "airports.json")
    known_codes = {entry["code"] for entry in identities}

    seen: set[str] = set()
    paths: set[str] = set()
    for entry in index["airports"]:
        code = entry["iata"]
        path = entry["detail_path"]
        if code in seen:
            raise ValueError("Duplicate indexed airport: " + code)
        if code not in known_codes or path != "details/" + code + ".v1.json":
            raise ValueError("Unknown airport or invalid detail path: " + code)
        seen.add(code)
        paths.add(path)
        detail = read_json(base / path)
        detail_validator.validate(detail)
        if detail["iata"] != code:
            raise ValueError("Airport identity mismatch in " + path)

        section_ids: set[str] = set()
        published = 0
        for section in detail["sections"]:
            section_id = section["id"]
            if section_id in section_ids:
                raise ValueError("Duplicate section: " + code + "/" + section_id)
            section_ids.add(section_id)
            if section["status"] != "published":
                continue
            published += 1
            if not section["blocks"] or section["reviewed_at"] is None:
                raise ValueError("Published section must contain reviewed content: " + code + "/" + section_id)
            if not section["source_urls"] and any(
                block["type"] != "experience" for block in section["blocks"]
            ):
                raise ValueError("Published factual sections require sources: " + code + "/" + section_id)
            for source in section["source_urls"]:
                _verify_https(source)
            experiences = [block for block in section["blocks"] if block["type"] == "experience"]
            if any(not block["approved"] for block in experiences):
                raise ValueError("Unapproved experience in published section: " + code + "/" + section_id)
            if len({block["id"] for block in experiences}) != len(experiences):
                raise ValueError("Duplicate experience ID: " + code + "/" + section_id)
            for block in section["blocks"]:
                for key in ("url", "external_url", "image_url", "thumbnail_url"):
                    if key in block:
                        _verify_https(block[key])

        if entry["enabled"] and not published:
            raise ValueError("Enabled airport has no published sections: " + code)

    on_disk = {str(path.relative_to(base)) for path in (base / "details").glob("*.v1.json")}
    if paths != on_disk:
        raise ValueError("Orphan or missing airport detail files: " + str(paths ^ on_disk))


if __name__ == "__main__":
    validate_dataset()
    print("Airport content catalog valid")
