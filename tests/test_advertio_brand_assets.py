"""Brand assets are rendered on Mini App and Android home without changing launcher icons."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mini_brand_is_served_by_worker_allowlist():
    index = (ROOT / "src/flightiran/webapp/static/index.html").read_text()
    worker = (ROOT / "cloudflare/src/mini.mjs").read_text()
    logo = ROOT / "src/flightiran/webapp/static/advertio-brand.webp"
    assert logo.read_bytes().startswith(b"RIFF")
    assert b"WEBP" in logo.read_bytes()[:16]
    assert 'src="/assets/advertio-brand.webp"' in index
    assert '"/assets/advertio-brand.webp":"/advertio-brand.webp"' in worker
    assert '"/assets/advertio-brand.webp"].includes(path)' in worker


def test_android_home_uses_brand_but_launcher_stays_intact():
    activity = (ROOT / "android/app/src/main/java/com/abolfazl260/flightiranbot24/MainActivity.kt").read_text()
    legacy = (ROOT / "android/app/src/main/res/layout/activity_main.xml").read_text()
    logo = ROOT / "android/app/src/main/res/drawable-nodpi/advertio_brand.webp"
    assert logo.read_bytes().startswith(b"RIFF")
    assert "R.drawable.advertio_brand" in activity
    assert 'android:src="@drawable/advertio_brand"' in legacy
    assert 'android:icon="@drawable/ic_launcher"' in (ROOT / "android/app/src/main/AndroidManifest.xml").read_text()
