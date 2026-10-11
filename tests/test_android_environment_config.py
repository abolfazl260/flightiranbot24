"""Check single Android package identity and CI-derived versions."""

from pathlib import Path
from runpy import run_path

import pytest

ROOT = Path(__file__).resolve().parents[1]
verifier = run_path(str(ROOT / "scripts/check_android_environments.py"))
APP_ID = verifier["APP_ID"]
DEBUG_ID = verifier["DEBUG_ID"]
package_data = verifier["package_data"]
verify_outputs = verifier["verify_outputs"]


def test_android_package_identity_and_version_from_real_apk_metadata():
    assert package_data(
        "package: name='com.abolfazl260.flightiranbot24.debug' "
        "versionCode='42' versionName='1.0.42-debug'\n"
    ) == (DEBUG_ID, 42, "1.0.42-debug")
    with pytest.raises(ValueError):
        package_data("application-label:'Flight Iran'\n")
    assert APP_ID == "com.abolfazl260.flightiranbot24"


def test_android_artifact_gate_fails_without_built_outputs(tmp_path):
    for release in (True, False):
        with pytest.raises(RuntimeError, match="exactly one APK"):
            verify_outputs(tmp_path, Path("/fake/aapt"), release, 42, "1.0.42")


def test_single_app_release_paths_and_auto_version_numbers():
    workflow = (ROOT / ".github/workflows/android.yml").read_text()
    assert ":app:assembleRelease :app:bundleRelease" in workflow
    assert "outputs/apk/release/" in workflow
    assert "outputs/bundle/release/" in workflow
    assert "GITHUB_RUN_NUMBER" in workflow
    assert "assembleProductionRelease" not in workflow
    assert "assembleStaging" not in workflow
    gradle = (ROOT / "android/app/build.gradle").read_text()
    assert "productFlavors" not in gradle
    assert "flavorDimensions" not in gradle
    assert "appVersionBase" in gradle
    assert "GITHUB_RUN_NUMBER" in gradle
    assert "applicationId 'com.abolfazl260.flightiranbot24'" in gradle
    assert "ANDROID_PRODUCTION_API_ORIGIN" in gradle


def test_single_app_keeps_native_prices_and_other_service_handoff():
    base = ROOT / "android/app/src/main/java/com/abolfazl260/flightiranbot24"
    activity = (base / "MainActivity.kt").read_text()
    assert "BuildConfig.APP_ENVIRONMENT" not in activity
    assert "HomeDestination.TICKET_PRICES ->" in activity
    assert "startActivity(Intent(this, TicketPricesActivity::class.java))" in activity
    assert "HomeDestination.TELEGRAM_VISA -> openUrl(BotLinks.VISA)" in activity
