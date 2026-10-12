"""Verify the shipped Persian Android copy and live ticket API build defaults.

This deliberately scans only app runtime sources/resources, not old tests or
technical documentation that may describe earlier iterations of the product.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "android" / "app" / "src" / "main"
BUILD = ROOT / "android" / "app" / "build.gradle"
DEFAULT_ORIGIN = "https://flightiran-public-api.abolfazl260.workers.dev/"


def check() -> None:
    target_files = (
        p for p in APP.rglob("*")
        if p.is_file() and p.suffix in {".java", ".kt", ".xml"}
    )
    forbidden = []
    for path in target_files:
        content = path.read_text(encoding="utf-8")
        if "آفلاین" in content:
            forbidden.append(path.relative_to(ROOT).as_posix())
    if forbidden:
        raise SystemExit(
            "Remove the unwanted status word from Android runtime source/resources: "
            + ", ".join(forbidden)
        )

    gradle = BUILD.read_text(encoding="utf-8")
    if DEFAULT_ORIGIN not in gradle or "getOrElse(defaultPublicApiOrigin)" not in gradle:
        raise SystemExit("All Android build variants must use a known HTTPS Worker origin")
    print("Android Persian copy and HTTPS ticket API configuration validated")


if __name__ == "__main__":
    check()
