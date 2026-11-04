"""Regression guards for real Android screenshot navigation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/capture_android_screenshots.sh"
WORKFLOW = ROOT / ".github/workflows/android-screenshots.yml"


def test_airport_screenshot_scrolls_to_ika_after_directory_loads():
    script = SCRIPT.read_text(encoding="utf-8")
    section = script.split("# Open the published airport guide", 1)[1].split(
        "# Native visa discovery", 1
    )[0]
    assert 'wait_for_activity AirportDirectoryActivity' in section
    assert 'wait_for_text "جست‌وجوی نام فرودگاه یا کد IATA"' in section
    assert 'wait_for_text "امام خمینی تهران"' not in section
    assert section.index('capture 08-airports.png') < section.index(
        'tap_service_row "امام خمینی تهران"'
    )
    assert section.index('tap_service_row "امام خمینی تهران"') < section.index(
        'wait_for_text "بار مجاز و قوانین حمل بار"'
    )
    assert "for attempt in range(9):" in script  # UIAutomator scrolls lazy lists.
    assert 'capture 08-airport-ika-baggage.png' in section


def test_screenshot_workflow_is_only_manual_on_main():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "  workflow_dispatch:" in workflow
    assert "  push:" not in workflow
    assert "  pull_request:" not in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
