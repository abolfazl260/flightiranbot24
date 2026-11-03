#!/usr/bin/env bash
set -euo pipefail

# Executed in one shell: emulator-runner otherwise launches every script line
# independently and loses shell variables / breaks multi-line Python heredocs.
gradle --no-daemon -p android :app:assembleDebug
apk="android/app/build/outputs/apk/debug/app-debug.apk"
test -s "$apk"
adb install -r "$apk"
mkdir -p android/screenshots
rm -f android/screenshots/*.png android/screenshots/failed-window.xml

# Capture emulator diagnostics even when a UI assertion or instrumentation fails.
on_capture_failure() {
  adb exec-out screencap -p > android/screenshots/failed-navigation.png || true
  adb shell uiautomator dump /sdcard/flightiran-failed-window.xml || true
  adb exec-out cat /sdcard/flightiran-failed-window.xml > android/screenshots/failed-window.xml || true
}
trap on_capture_failure ERR

# Only the launcher is exported. Never make private screens exported
# just for test automation: navigate via visible Persian controls as users do.
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
    local resumed
    resumed="$(adb shell dumpsys activity activities | grep -E '(topResumedActivity|mResumedActivity)' || true)"
    if grep -Fq "$activity_prefix.$expected" <<< "$resumed"; then
      return 0
    fi
    sleep 1
  done
  echo "Expected $expected to be foreground after navigation" >&2
  adb shell dumpsys activity activities | grep -E '(topResumedActivity|mResumedActivity)' >&2 || true
  # Persist useful diagnostics instead of hiding the failing UI behind a
  # transient emulator window. Artifacts are uploaded even if this job fails.
  adb exec-out screencap -p > "android/screenshots/failed-navigation.png" || true
  adb shell uiautomator dump /sdcard/flightiran-failed-window.xml || true
  adb exec-out cat /sdcard/flightiran-failed-window.xml > "android/screenshots/failed-window.xml" || true
  return 1
}

tap_persian_control() {
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
    # Compose clickable cards and navigation items expose semantics labels.
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
    # Prefer the lowest matching node if a label appears in more than one area.
    _, x, y = max(candidates)
else:
    # Some emulator/Compose combinations omit NavigationBarItem labels
    # from uiautomator's merged semantics. The bar has four equal slots.
    # Feature-card labels must be present; no coordinate fallback for cards.
    # Use an explicit, documented slot fallback; the subsequent assertion
    # verifies that the expected Activity actually opened, so a wrong tap
    # still fails the screenshot job instead of passing silently.
    slots = {"خانه": 0, "قیمت بلیت": 1,
             "چک‌لیست": 2, "خدمات": 3}
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
    x = int(width * (3.5 - slots[label]) / 4)
    # Android window bounds are *physical pixels*, not density-independent
    # pixels. The previous fallback (height - 105 pixels) struck the system
    # gesture area on the Pixel 6 emulator and never triggered navigation.
    # Compose Material3 NavigationBar is 80dp high, above a roughly 24dp
    # system navigation inset. Tap its center: 24dp + 40dp from bottom.
    density_output = subprocess.check_output(
        ["adb", "shell", "wm", "density"], text=True
    )
    density_match = re.search(r"(?:Override|Physical) density:\s*(\d+)", density_output)
    if not density_match:
        raise SystemExit(f"Cannot determine device density: {density_output!r}")
    pixels_per_dp = int(density_match.group(1)) / 160.0
    y = height - round(64 * pixels_per_dp)
    print(
        f"Accessibility label {label!r} missing; using RTL nav slot at "
        f"{(x,y)}, display={width}x{height}, px_per_dp={pixels_per_dp:.3f}",
        flush=True,
    )
subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=True)
PY
}

capture() {
  local file="$1"
  sleep 2
  adb exec-out screencap -p > "android/screenshots/$file"
}


# Service rows may be below the fold. Locate the ACTUAL visible Persian
# control through UIAutomator, scrolling the page without guessed coordinates.
tap_service_row() {
  local label="$1"
  python3 - "$label" <<'PY'
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

label = sys.argv[1]
size = subprocess.check_output(["adb", "shell", "wm", "size"], text=True)
match = re.search(r"(\d+)x(\d+)", size)
if match is None:
    raise SystemExit(f"Unknown emulator size: {size}")
width, height = map(int, match.groups())
for attempt in range(9):
    subprocess.run(
        ["adb", "shell", "uiautomator", "dump", "/sdcard/flightiran-service.xml"],
        check=True, stdout=subprocess.DEVNULL,
    )
    data = subprocess.check_output(["adb", "exec-out", "cat", "/sdcard/flightiran-service.xml"])
    root = ET.fromstring(data)
    candidates = []
    for node in root.iter("node"):
        title = node.attrib.get("text", "")
        description = node.attrib.get("content-desc", "")
        if label != title and label not in description:
            continue
        match = re.fullmatch(
            r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", "")
        )
        if match is None:
            continue
        left, top, right, bottom = map(int, match.groups())
        if right > left and bottom > top:
            candidates.append(((left + right)//2, (top + bottom)//2))
    if candidates:
        x, y = candidates[-1]
        print(f"Tapping service {label!r} at {(x, y)}, scrolls={attempt}", flush=True)
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=True)
        sys.exit(0)
    if attempt < 8:
        subprocess.run(
            ["adb", "shell", "input", "swipe", str(width//2),
             str(height*78//100), str(width//2), str(height*35//100), "430"],
            check=True,
        )
        time.sleep(0.7)
raise SystemExit(f"Service row not reachable through UI: {label}")
PY
}

scroll_down() {
  local count="$1"
  local display width height
  display="$(adb shell wm size | grep -Eo '[0-9]+x[0-9]+' | tail -1)"
  width="$(cut -dx -f1 <<< "$display")"
  height="$(cut -dx -f2 <<< "$display")"
  for _ in $(seq 1 "$count"); do
    adb shell input swipe "$((width / 2))" "$((height * 78 / 100))" \
      "$((width / 2))" "$((height * 35 / 100))" 430
    sleep 1
  done
}

wait_for_text() {
  local expected="$1"
  for _ in $(seq 1 15); do
    adb shell uiautomator dump /sdcard/flightiran-assert.xml >/dev/null 2>&1 || true
    local xml
    xml="$(adb exec-out cat /sdcard/flightiran-assert.xml || true)"
    if grep -Fq "$expected" <<< "$xml"; then
      return 0
    fi
    sleep 1
  done
  echo "Expected native Persian text not visible: $expected" >&2
  return 1
}

wait_for_prices() {
  # Both successful live data and the genuine API error state count as a
  # rendered screen. Never photograph a loading spinner or invent fares.
  for _ in $(seq 1 25); do
    adb shell uiautomator dump /sdcard/flightiran-prices.xml >/dev/null 2>&1 || true
    local xml
    xml="$(adb exec-out cat /sdcard/flightiran-prices.xml || true)"
    if grep -Fq "شهر مبدأ" <<< "$xml"; then
      echo "Prices screen: real API prices rendered"
      return 0
    fi
    if grep -Fq "دریافت اطلاعات ممکن نیست" <<< "$xml"; then
      echo "::warning::Captured the authentic ticket API error state, not sample fares"
      return 0
    fi
    sleep 1
  done
  echo "Ticket screen did not finish loading" >&2
  return 1
}

open_launcher
wait_for_activity MainActivity
wait_for_text "دستیار هوشمند سفر"
capture 01-home.png
scroll_down 1
capture 01-home-details.png

open_launcher
wait_for_activity MainActivity
# Verify a Services-only row, not a heading also present on the Home tab.
tap_persian_control "خدمات"
wait_for_text "اطلاعات پرواز ایران"
capture 02-services.png
scroll_down 2
capture 02-services-bottom.png

open_launcher
wait_for_activity MainActivity
tap_persian_control "قیمت بلیت"
wait_for_activity TicketPricesActivity
wait_for_prices
capture 03-ticket-prices.png

open_launcher
wait_for_activity MainActivity
tap_persian_control "چک‌لیست"
wait_for_activity ChecklistActivity
capture 04-checklist.png
scroll_down 2
capture 04-checklist-bottom.png

open_launcher
wait_for_activity MainActivity
tap_persian_control "خدمات"
wait_for_text "اطلاعات پرواز ایران"
tap_service_row "اطلاعات پرواز ایران"
wait_for_activity IranFlightsActivity
wait_for_text "وب‌سایت رسمی FIDS در داخل برنامه"
# Allow the third-party WebView to render (or display its genuine error).
sleep 8
capture 05-iran-flights.png

open_launcher
wait_for_activity MainActivity
tap_persian_control "خدمات"
wait_for_text "اطلاعات پرواز ایران"
tap_service_row "حریم خصوصی"
wait_for_activity PrivacyPolicyActivity
wait_for_text "اطلاعات ذخیره‌شده در گوشی"
capture 06-privacy.png
scroll_down 2
capture 06-privacy-bottom.png

# Navigate via the existing Services row, then capture the native directory.
open_launcher
wait_for_activity MainActivity
tap_persian_control "خدمات"
wait_for_text "اطلاعات پرواز ایران"
tap_service_row "اطلاعات کاربردی سفر"
wait_for_activity TravelWebsitesActivity
wait_for_text "جست‌وجوی نام یا توضیحات وب‌سایت"
capture 07-travel-websites.png
scroll_down 2
capture 07-travel-websites-bottom.png

# All seven reachable in-app screens, plus scrolled variants for longer screens.
# Offline airport directory is intentionally excluded: it is currently disabled.
python3 - <<'PY'
from pathlib import Path
import struct

folder = Path("android/screenshots")
expected = {
    "01-home.png", "01-home-details.png",
    "02-services.png", "02-services-bottom.png",
    "03-ticket-prices.png",
    "04-checklist.png", "04-checklist-bottom.png",
    "05-iran-flights.png",
    "06-privacy.png", "06-privacy-bottom.png",
    "07-travel-websites.png", "07-travel-websites-bottom.png",
}
actual = {p.name for p in folder.glob("*.png")}
assert actual == expected, f"Missing: {expected - actual}; unexpected: {actual - expected}"
for name in sorted(expected):
    data = (folder / name).read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), name
    width, height = struct.unpack(">II", data[16:24])
    assert width >= 320 and height >= 480, (name, width, height)
    print(f"{name}: {width}x{height}")
PY

gradle --no-daemon -p android :app:connectedDebugAndroidTest
trap - ERR
