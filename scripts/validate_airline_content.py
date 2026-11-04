"""Validate independent, read-only airline guides. No network or private inputs.

Run: python scripts/validate_airline_content.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def timestamp(value: str) -> datetime:
    # jsonschema format plugins are optional; enforce RFC3339 without them.
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError("Invalid timezone-aware timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_metadata(meta: dict, now: datetime) -> None:
    for key in ("verified_at", "effective_from", "effective_to"):
        if meta[key] is not None:
            timestamp(meta[key])
    start, end = meta["effective_from"], meta["effective_to"]
    if start and end and timestamp(start) > timestamp(end):
        raise ValueError("Inverted effective period")
    if meta["verified_at"] and timestamp(meta["verified_at"]) > now:
        raise ValueError("Future verification date")
    if meta["status"] == "published":
        if not meta["source_urls"] or not meta["verified_at"]:
            raise ValueError("Published content requires sources and verification")
        if meta["confidence"] == "unverified":
            raise ValueError("Unverified published content")


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate_dataset(root: Path = ROOT, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    base = root / "data/airlines"
    validators = {}
    for kind in ("index", "detail"):
        schema = read_json(base / f"airline-{kind}.schema.json")
        Draft202012Validator.check_schema(schema)
        validators[kind] = Draft202012Validator(schema, format_checker=FormatChecker())
    index = read_json(base / "airline-index.v1.json")
    validators["index"].validate(index)
    if (base / "airline-index.v1.json").stat().st_size > 64_000:
        raise ValueError("Airline index exceeds Android transport bound")
    airport_index = read_json(root / "data/airports/airport-index.v1.json")
    airports = {row["iata"] for row in airport_index["airports"]}
    ids, paths, code_claims, review_ids, experience_ids = set(), set(), {}, set(), set()
    for entry in index["airlines"]:
        aid = entry["airline_id"]
        path = entry["detail_path"]
        if aid in ids or path != f"details/{aid}.v1.json":
            raise ValueError("Duplicate identity or invalid path: " + aid)
        ids.add(aid)
        paths.add(path)
        seen_codes = set()
        for code in entry["identity"]["codes"]:
            assignment = (code["system"], code["value"], code["valid_from"], code["valid_to"])
            if assignment in seen_codes:
                raise ValueError("Duplicate code assignment")
            seen_codes.add(assignment)
            expected = 2 if code["system"] == "iata" else 3
            if len(code["value"]) != expected or (
                expected == 3 and not code["value"].isalpha()
            ):
                raise ValueError("Invalid IATA/ICAO code")
            start, end = code["valid_from"], code["valid_to"]
            for assigned_date in (start, end):
                if assigned_date:
                    timestamp(assigned_date)
            if start and end and timestamp(start) > timestamp(end):
                raise ValueError("Inverted code validity")
            claims = code_claims.setdefault((code["system"], code["value"]), [])
            for previous in claims:
                overlaps = not (
                    end and previous["valid_from"]
                    and timestamp(end) < timestamp(previous["valid_from"])
                    or previous["valid_to"] and start
                    and timestamp(previous["valid_to"]) < timestamp(start)
                )
                if overlaps and not (code["shared"] and previous["shared"]):
                    raise ValueError("Overlapping code assignments require shared=true")
            claims.append(code)
        if (base / path).stat().st_size > 512_000:
            raise ValueError("Airline detail exceeds Android transport bound")
        detail = read_json(base / path)
        validators["detail"].validate(detail)
        if detail["airline_id"] != aid:
            raise ValueError("Airline identity mismatch")
        for node in walk([entry, detail]):
            if "metadata" in node:
                check_metadata(node["metadata"], now)
            for key in ("website", "url", "source_url"):
                if key in node:
                    check_url(node[key])
            for url in node.get("source_urls", []):
                check_url(url)
        seen_sections = set()
        for section in detail["sections"]:
            if section["id"] in seen_sections:
                raise ValueError("Duplicate section ID")
            seen_sections.add(section["id"])
            if section["kind"] == "policy" and section["scope"] is None:
                raise ValueError("Policy requires explicit scope, including unknowns")
            if section["scope"] and section["scope"]["operating_carrier"] not in (
                None, *[e["airline_id"] for e in index["airlines"]]
            ):
                raise ValueError("Unknown operating carrier")
            if section["metadata"]["status"] == "published" and not section["blocks"]:
                raise ValueError("Empty published section")
            for block in section["blocks"]:
                if block["type"] == "airport_link" and block["iata"] not in airports:
                    raise ValueError("Unknown airport link")
                if block["type"] == "fleet_snapshot":
                    if section["kind"] != "fleet":
                        raise ValueError("Fleet block outside fleet section")
                    if timestamp(block["observed_at"]) > now:
                        raise ValueError("Future fleet observation")
                    if section["metadata"]["status"] == "published" and (
                        block["count"] is not None or block["configuration_fa"] is not None
                    ):
                        check_metadata(block["metadata"], now)
                        if (block["metadata"]["status"] != "published"
                                or not block["metadata"]["source_urls"]):
                            raise ValueError("Fleet counts/configuration require published sources")
        for review in detail["published_reviews"]:
            if review["review_id"] in review_ids or review["airline_id"] != aid:
                raise ValueError("Duplicate or mismatched published review")
            review_ids.add(review["review_id"])
            if timestamp(review["publication_timestamp"]) > now:
                raise ValueError("Future review publication")
        for association in detail["experience_links"]:
            key = (aid, association["experience_id"])
            if key in experience_ids:
                raise ValueError("Duplicate experience association")
            experience_ids.add(key)
            if aid not in association["airline_ids"] or not set(
                association["airline_ids"]
            ).issubset({e["airline_id"] for e in index["airlines"]}):
                raise ValueError("Unknown airline experience association")
            # Until #168 supplies immutable originals + publication permissions,
            # associations can be prepared but never published by this reader.
            if association["moderation_status"] == "approved":
                raise ValueError("Experience publication requires the #168 archive integration")
    if paths != {str(p.relative_to(base)) for p in (base / "details").glob("*.v1.json")}:
        raise ValueError("Orphan or missing airline detail")


def check_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.port == 0
            or any(c.isspace() for c in url)
            or not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                       for label in parsed.hostname.split("."))):
        raise ValueError("Invalid public HTTPS URL")


if __name__ == "__main__":
    validate_dataset()
    print("Airline content catalog valid")
