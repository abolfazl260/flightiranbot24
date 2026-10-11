"""Verify the one Android application's APK/AAB identities and CI versions.

Uses Android's aapt metadata, never only the APK filename.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

APP_ID = "com.abolfazl260.flightiranbot24"
DEBUG_ID = f"{APP_ID}.debug"


def package_data(aapt_output: str) -> tuple[str, int, str]:
    match = re.search(
        r"^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'",
        aapt_output, re.MULTILINE,
    )
    if match is None:
        raise ValueError("Android APK lacks readable package and version metadata")
    return match.group(1), int(match.group(2)), match.group(3)


def aapt_binary() -> Path:
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not home:
        raise RuntimeError("ANDROID_HOME or ANDROID_SDK_ROOT required")
    aapt = Path(home) / "build-tools" / "35.0.0" / "aapt"
    if not aapt.is_file():
        raise RuntimeError("Android SDK build-tools 35.0.0/aapt required")
    return aapt


def verify_apk(
    aapt: Path,
    apk_dir: Path,
    expected_id: str,
    expected_version_code: int,
    expected_version_name: str,
) -> None:
    packages = sorted(apk_dir.glob("*.apk"))
    if len(packages) != 1:
        raise RuntimeError(f"Expected exactly one APK at {apk_dir}, got {len(packages)}")
    result = subprocess.run(
        [str(aapt), "dump", "badging", str(packages[0])],
        check=True, capture_output=True, text=True,
    )
    identity, code, name = package_data(result.stdout)
    if (identity, code, name) != (
        expected_id, expected_version_code, expected_version_name,
    ):
        raise RuntimeError(
            f"Android package/version mismatch: {identity}/{code}/{name} "
            f"(expected {expected_id}/{expected_version_code}/{expected_version_name})"
        )
    print(f"Verified Android APK: {identity} v{name} ({code})")


def verify_outputs(
    output: Path, aapt: Path, release: bool, code: int, version_name: str,
) -> None:
    if release:
        verify_apk(aapt, output / "apk" / "release", APP_ID, code, version_name)
        bundles = sorted((output / "bundle" / "release").glob("*.aab"))
    else:
        verify_apk(
            aapt, output / "apk" / "debug", DEBUG_ID, code,
            f"{version_name}-debug",
        )
        bundles = sorted((output / "bundle" / "release").glob("*.aab"))
    if len(bundles) != 1:
        raise RuntimeError("Exactly one release AAB is required")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--version-name", required=True)
    args = parser.parse_args()
    if args.version_code <= 0 or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version_name):
        parser.error("Expected positive version code and MAJOR.MINOR.PATCH version name")
    verify_outputs(
        args.app_dir, aapt_binary(), args.release,
        args.version_code, args.version_name,
    )


if __name__ == "__main__":
    main()
