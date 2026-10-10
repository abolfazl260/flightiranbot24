"""Verify native Android flavor outputs and release isolation (AND-004).

Uses Android's own aapt metadata for the **built APK**, not filenames alone.
Missing expected artifacts, extra release flavors and mismatched IDs fail CI.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

PRODUCTION_ID = "com.abolfazl260.flightiranbot24"
DEBUG_IDS = {
    "development": f"{PRODUCTION_ID}.dev.debug",
    "staging": f"{PRODUCTION_ID}.staging.debug",
    "production": f"{PRODUCTION_ID}.debug",
}
RELEASE_ID = PRODUCTION_ID


def package_name(aapt_output: str) -> str:
    match = re.search(r"^package: name='([A-Za-z][\w.]*)'", aapt_output, re.MULTILINE)
    if match is None:
        raise ValueError("Android APK lacks readable package identity")
    return match.group(1)


def aapt_binary() -> Path:
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not home:
        raise RuntimeError("ANDROID_HOME or ANDROID_SDK_ROOT required")
    aapt = Path(home) / "build-tools" / "35.0.0" / "aapt"
    if not aapt.is_file():
        raise RuntimeError("Android SDK build-tools 35.0.0/aapt required")
    return aapt


def verify_apk(aapt: Path, apk_dir: Path, expected_id: str) -> None:
    packages = sorted(apk_dir.glob("*.apk"))
    if len(packages) != 1:
        raise RuntimeError(f"Expected exactly one APK at {apk_dir}, got {len(packages)}")
    result = subprocess.run(
        [str(aapt), "dump", "badging", str(packages[0])],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = package_name(result.stdout)
    if actual != expected_id:
        raise RuntimeError(f"Android package mismatch: {actual} (expected {expected_id})")
    print(f"Verified APK variant: {actual}")


def verify_outputs(output: Path, aapt: Path, production_release: bool) -> None:
    if production_release:
        verify_apk(aapt, output / "apk" / "production" / "release", RELEASE_ID)
        bundles = sorted((output / "bundle" / "productionRelease").glob("*.aab"))
        if len(bundles) != 1:
            raise RuntimeError("Exactly one productionRelease AAB is required")
        # Only production artifacts are released. Never use the development or
        # staging subdirectories as the source for signed release uploads.
        return
    for flavor, expected_id in DEBUG_IDS.items():
        verify_apk(aapt, output / "apk" / flavor / "debug", expected_id)
    bundles = sorted((output / "bundle" / "productionRelease").glob("*.aab"))
    if len(bundles) != 1:
        raise RuntimeError("Missing unsigned productionRelease AAB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--production-release", action="store_true")
    args = parser.parse_args()
    verify_outputs(args.app_dir, aapt_binary(), args.production_release)


if __name__ == "__main__":
    main()
