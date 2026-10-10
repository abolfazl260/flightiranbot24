"""Pure-Python checks for the Android environment artifact verifier."""

from pathlib import Path
from runpy import run_path

import pytest

# scripts/ is an executable directory, not a distributable Python package.
# Load the standalone verifier by its checked-in path instead.
ROOT = Path(__file__).resolve().parents[1]
verifier = run_path(str(ROOT / "scripts/check_android_environments.py"))
DEBUG_IDS = verifier["DEBUG_IDS"]
RELEASE_ID = verifier["RELEASE_ID"]
package_name = verifier["package_name"]
verify_outputs = verifier["verify_outputs"]


def test_android_package_name_parser_uses_actual_aapt_metadata():
    assert package_name(
        "package: name='com.abolfazl260.flightiranbot24.dev.debug' versionCode='1'\n"
    ) == DEBUG_IDS["development"]
    with pytest.raises(ValueError):
        package_name("application-label:'Flight Iran'\n")
    assert len({*DEBUG_IDS.values(), RELEASE_ID}) == 4


def test_android_environment_artifact_gate_fails_on_absent_build_outputs(tmp_path):
    with pytest.raises(RuntimeError, match="exactly one APK"):
        verify_outputs(tmp_path, Path("/fake/aapt"), production_release=False)
    with pytest.raises(RuntimeError, match="exactly one APK"):
        verify_outputs(tmp_path, Path("/fake/aapt"), production_release=True)


def test_android_release_build_not_renamed_to_staging_artifact():
    workflow = (Path(__file__).resolve().parents[1]
        / ".github/workflows/android.yml").read_text()
    assert ":app:assembleProductionRelease :app:bundleProductionRelease" in workflow
    assert "outputs/apk/production/release/" in workflow
    assert "outputs/bundle/productionRelease/" in workflow
    assert "outputs/apk/staging/release/" not in workflow


def test_android_app_keeps_production_only_telegram_handoff():
    base = Path(__file__).resolve().parents[1]
    activity = (base / "android/app/src/main/java/com/abolfazl260/"
                "flightiranbot24/MainActivity.kt").read_text()
    assert 'BuildConfig.APP_ENVIRONMENT != "production"' in activity
    assert "state.sections.online.filter" in activity
    assert 'HomeDestination.TELEGRAM_VISA -> openUrl(BotLinks.VISA)' in activity
    build_file = (base / "android/app/build.gradle").read_text()
    assert "applicationIdSuffix '.dev'" in build_file
    assert "applicationIdSuffix '.staging'" in build_file
    assert "'productionApiOrigin'" in build_file
    assert "'APP_ENVIRONMENT'" in build_file
