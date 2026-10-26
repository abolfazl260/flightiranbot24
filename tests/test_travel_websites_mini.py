"""WEB-002 integration guards: the Mini App consumes only the GitHub v1 catalog."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/flightiran/webapp/static"


def test_websites_navigation_and_travel_guide_preserved():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    mini = (STATIC / "mini.js").read_text(encoding="utf-8")
    assert 'id="screen-websites"' in html
    assert 'lang="fa" dir="rtl"' in html
    assert 'id="website-search"' in html
    assert 'id="website-category"' in html
    assert 'id="website-results"' in html
    assert html.count('data-go="websites"') >= 2
    assert 'id="screen-useful"' in html
    assert 'id="useful-results"' in html
    assert 'id="screen-checklist"' in html
    assert 'type="module" src="/assets/mini.js' in html
    assert 'from "./travel-catalog.mjs"' in mini
    assert 'if (screen === "websites") loadWebsites()' in mini
    assert 'fetchCatalog(fetch,9000,force?"reload":"default")' in mini
    assert 'loading:"lazy"' in mini
    assert "image.addEventListener(\"error\"" in mini
    assert 'onClick:()=>{' in mini


def test_catalog_security_contract_and_first_party_hosts():
    catalog = (STATIC / "travel-catalog.mjs").read_text(encoding="utf-8")
    worker = (ROOT / "cloudflare/src/mini.mjs").read_text(encoding="utf-8")
    api = (ROOT / "src/flightiran/webapp/app.py").read_text(encoding="utf-8")

    assert 'main/data/travel-websites/catalog.v1.json' in catalog
    assert 'credentials:"omit"' in catalog
    assert 'referrerPolicy:"no-referrer"' in catalog
    assert 'redirect:"error"' in catalog
    assert 'approvedImageUrl' in catalog
    assert 'approvedExternalUrl' in catalog
    assert "https://raw.githubusercontent.com" in worker
    assert "https://raw.githubusercontent.com" in api
    assert '"/assets/travel-catalog.mjs":"/travel-catalog.mjs"' in worker
    assert "el(\"h3\",{text:site.name})" in (STATIC / "mini.js").read_text(encoding="utf-8")
    assert "innerHTML" not in (STATIC / "mini.js").read_text(encoding="utf-8")

    # The Python wheel must include the ES module imported by mini.js.
    import tomllib
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = project["tool"]["setuptools"]["package-data"]["flightiran"]
    assert "webapp/static/*.mjs" in package_data
