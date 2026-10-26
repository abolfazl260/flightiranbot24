"""Validate the shared, remotely hosted Persian travel website catalog and thumbnails."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "data" / "travel-websites"


def test_shared_catalog_matches_schema_and_contains_26_unique_sites():
    catalog = json.loads((CATALOG_DIR / "catalog.v1.json").read_text(encoding="utf-8"))
    schema = json.loads((CATALOG_DIR / "catalog.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(catalog)

    categories = catalog["categories"]
    websites = catalog["websites"]
    category_ids = [item["id"] for item in categories]
    site_ids = [item["id"] for item in websites]
    site_urls = [item["url"] for item in websites]

    assert catalog["schema_version"] == 1
    assert len(categories) == 8
    assert len(set(category_ids)) == len(category_ids)
    assert len(websites) == 26
    assert len(set(site_ids)) == 26
    assert len(set(site_urls)) == 26
    assert sum(item["id"] == "iata-travel-centre" for item in websites) == 1
    assert all(item["category_id"] in category_ids for item in websites)
    assert all(item["enabled"] is True for item in websites)
    assert all(item["url"].startswith("https://") for item in websites)


def test_each_catalog_entry_has_a_valid_local_webp_thumbnail():
    catalog = json.loads((CATALOG_DIR / "catalog.v1.json").read_text(encoding="utf-8"))
    for website in catalog["websites"]:
        relative = Path(website["image"])
        assert relative.parts[0] == "images"
        assert len(relative.parts) == 2
        assert relative.suffix == ".webp"
        image = (CATALOG_DIR / relative).read_bytes()
        assert image[:4] == b"RIFF"
        assert image[8:12] == b"WEBP"
        assert 12 < len(image) <= 25 * 1024
