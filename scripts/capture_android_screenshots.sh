#!/usr/bin/env bash
set -euo pipefail

# Executed in one shell: emulator-runner otherwise launches every script line
# independently and loses shell variables / breaks multi-line Python heredocs.
gradle --no-daemon -p android :app:assembleDebug
apk="android/app/build/outputs/apk/debug/app-debug.apk"
test -s "$apk"
adb install -r "$apk"
mkdir -p android/screenshots

# Only the launcher is exported. Never make private screens exported
# just for test automation: navigate via the same Persian tabs as users.
package="com.abolfazl260.flightiranbot24.debug"
activity_prefix="com.abolfazl260.flightiranbot24"

open_launcher() {
  # Merely starting MainActivity again can deliver the intent to the task
  # while a non-exported child Activity remains foreground (Android task reuse).
  # Force-stop the test app before launch so every screenshot starts from home.
  # This does not clear user preferences or other app data.
  adb shell am force-stop "$package"
  adb shell am start -W -n "$package/$activity_prefix.MainActivity" | tee /tmp/flightiran-launch.txt
  grep -q 'Status: ok' /tmp/flightiran-launch.txt
}

wait_for_activity() {
  local expected="$1"
  for _ in $(seq 1 30); do
    if adb shell dumpsys activity activities |
       grep -E '(topResumedActivity|mResumedActivity)' |
       grep -Fq "$activity_prefix.$expected"; then
      return 0
    fi
    sleep 1
  done
  echo "Expected $expected to be foreground after navigation" >&2
  adb shell dumpsys activity activities | grep -E '(topResumedActivity|mResumedActivity)' >&2 || true
  return 1
}

tap_persian_navigation() {
  local label="$1"
  python3 - "$label" <<'PY'
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

label = sys.argv[1]
subprocess.run(
    ["adb", "shell", "uiautomator", "dump", "/sdcard/flightiran-window.xml"],
    check=True, capture_output=True, text=True,
)
xml_data = subprocess.check_output(
    ["adb", "exec-out", "cat", "/sdcard/flightiran-window.xml"]
)
root = ET.fromstring(xml_data)
candidates = []
for node in root.iter("node"):
    desc = node.attrib.get("content-desc", "")
    text = node.attrib.get("text", "")
    # Compose NavigationBarItem can expose either text or contentDescription.
    if label != text and label not in desc:
        continue
    match = re.fullmatch(
        r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", "")
    )
    if match is None:
        continue
    left, top, right, bottom = map(int, match.groups())
    if right > left and bottom > top:
        candidates.append((top, (left + right) // 2, (top + bottom) // 2))

if candidates:
    # The bottom bar is below similarly named feature cards.
    _, x, y = max(candidates)
else:
    # Some emulator/Compose combinations omit the NavigationBarItem text
    # from uiautomator's merged semantics. The bar has five equal slots.
    # Use an explicit, documented slot fallback; the subsequent assertion
    # verifies that the expected Activity actually opened, so a wrong tap
    # still fails the screenshot job instead of passing silently.
    slots = {"خانه": 0, "قیمت بلیت": 1, "فرودگاه‌ها": 2,
             "چک‌لیست": 3, "خدمات": 4}
    if label not in slots:
        raise SystemExit(f"Unknown Persian navigation slot: {label}")
    size = subprocess.check_output(
        ["adb", "shell", "wm", "size"], text=True
    ).strip()
    resolution = re.search(r"(\d+)x(\d+)", size)
    if not resolution:
        raise SystemExit(f"Unable to determine emulator size: {size}")
    width, height = map(int, resolution.groups())
    # Main Compose screen forces RTL: slots are arranged right-to-left.
    x = int(width * (4.5 - slots[label]) / 5)
    # NavigationBar sits immediately above the Android system gesture bar.
    # Typical bottom navigation is 80dp; 100 physical px from bottom
    # lands within it on the pixel_6 screenshot emulator.
    y = height - 105
    print(f"Accessibility label {label!r} missing; using verified nav slot at {(x,y)}", flush=True)
subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=True)
PY
}

capture() {
  local file="$1"
  sleep 2
  adb exec-out screencap -p > "android/screenshots/$file"
}

open_launcher
wait_for_activity MainActivity
capture 01-home.png

open_launcher
wait_for_activity MainActivity
tap_persian_navigation "فرودگاه‌ها"
wait_for_activity AirportDirectoryActivity
capture 02-airports.png

open_launcher
wait_for_activity MainActivity
tap_persian_navigation "چک‌لیست"
wait_for_activity ChecklistActivity
capture 03-checklist.png

python3 - <<'PY'
import pathlib
import struct

shots = sorted(pathlib.Path("android/screenshots").glob("*.png"))
assert len(shots) == 3, shots
for path in shots:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), path
    width, height = struct.unpack(">II", data[16:24])
    assert width >= 320 and height >= 480, (path, width, height)
PY

gradle --no-daemon -p android :app:connectedDebugAndroidTest
