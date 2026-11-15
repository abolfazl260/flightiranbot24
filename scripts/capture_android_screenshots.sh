#!/usr/bin/env bash
set -euo pipefail

# GitHub-hosted Android emulators can briefly disappear from ADB while the
# process is still alive. Put a retrying ADB shim on PATH so both Bash and the
# Python UIAutomator helpers use the same recovery behavior.
REAL_ADB="$(command -v adb)"
ADB_RETRY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/flightiran-adb-retry.XXXXXX")"
cat > "$ADB_RETRY_DIR/adb" <<'ADB_RETRY_WRAPPER'
#!/usr/bin/env bash
set -u

real="${FLIGHTIRAN_REAL_ADB:?FLIGHTIRAN_REAL_ADB is not set}"
max_attempts=4
attempt=1

while (( attempt <= max_attempts )); do
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/flightiran-adb-call.XXXXXX")"
  "$real" "$@" >"$tmp/stdout" 2>"$tmp/stderr"
  status=$?

  if (( status == 0 )); then
    cat "$tmp/stdout"
    cat "$tmp/stderr" >&2
    rm -rf "$tmp"
    exit 0
  fi

  cat "$tmp/stdout" "$tmp/stderr" > "$tmp/all"
  if ! grep -Eiq 'device offline|no devices/emulators found|cannot connect to daemon|connection refused|device not found|closed' "$tmp/all"; then
    cat "$tmp/stdout"
    cat "$tmp/stderr" >&2
    rm -rf "$tmp"
    exit "$status"
  fi

  if (( attempt == max_attempts )); then
    cat "$tmp/stdout"
    cat "$tmp/stderr" >&2
    rm -rf "$tmp"
    exit "$status"
  fi

  printf '::warning::ADB transport unavailable (attempt %s/%s); reconnecting emulator...\n' "$attempt" "$max_attempts" >&2
  "$real" reconnect offline >/dev/null 2>&1 || true
  "$real" start-server >/dev/null 2>&1 || true

  # If a stale ADB server survives the first reconnect, restart it once.
  if (( attempt == 2 )); then
    "$real" kill-server >/dev/null 2>&1 || true
    "$real" start-server >/dev/null 2>&1 || true
  fi

  for _ in $(seq 1 20); do
    devices="$("$real" devices 2>/dev/null || true)"
    if grep -Eq '^emulator-[0-9]+[[:space:]]+device([[:space:]]|$)' <<< "$devices"; then
      break
    fi
    sleep 1
  done

  rm -rf "$tmp"
  attempt=$((attempt + 1))
done

exit 1
ADB_RETRY_WRAPPER
chmod +x "$ADB_RETRY_DIR/adb"
export FLIGHTIRAN_REAL_ADB="$REAL_ADB"
export PATH="$ADB_RETRY_DIR:$PATH"
trap 'rm -rf "$ADB_RETRY_DIR"' EXIT

# Executed in one shell: emulator-runner otherwise launches every script line
# independently and loses shell variables / breaks multi-line Python heredocs.
gradle --no-daemon -p android :app:assembleDebug
apk="android/app/build/outputs/apk/debug/app-debug.apk"
test -s "$apk"
adb install -r "$apk"
mkdir -p android/screenshots
rm -f android/screenshots/*.png android/screenshots/failed-window.xml

# Reject truncated/corrupt screenshots before publishing them as artifacts.
validate_png() {
  python3 - "$1" <<'PY'
import pathlib
import struct
import sys
import zlib

path = pathlib.Path(sys.argv[1])
data = path.read_bytes()
if len(data) < 57 or data[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit(f"Invalid or truncated PNG: {path}")
if data[12:16] != b"IHDR":
    raise SystemExit(f"Missing PNG IHDR: {path}")
width, height = struct.unpack_from(">II", data, 16)
if width < 320 or height < 480:
    raise SystemExit(f"Unexpected screenshot dimensions {width}x{height}: {path}")

offset = 8
saw_iend = False
while offset + 12 <= len(data):
    length = struct.unpack_from(">I", data, offset)[0]
    kind = data[offset + 4:offset + 8]
    end = offset + 12 + length
    if end > len(data):
        raise SystemExit(f"Truncated PNG chunk in {path}")
    payload = data[offset + 8:offset + 8 + length]
    expected_crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
    if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
        raise SystemExit(f"PNG CRC mismatch in {path}")
    offset = end
    if kind == b"IEND":
        if length != 0:
            raise SystemExit(f"Invalid PNG IEND chunk: {path}")
        saw_iend = True
        break

if not saw_iend or offset != len(data):
    raise SystemExit(f"PNG is incomplete or has trailing data: {path}")
PY
}

# Capture diagnostics while the emulator action still owns the device.
# Disable ERR handling here to avoid recursively entering this function.
on_capture_failure() {
  local failure_status=$?
  trap - ERR
  set +e
  mkdir -p android/screenshots
  printf 'Screenshot workflow failed; collecting emulator diagnostics.\n' \
    > android/screenshots/failed-diagnostics.txt
  adb devices -l >> android/screenshots/failed-diagnostics.txt 2>&1
  adb shell dumpsys activity activities >> android/screenshots/failed-diagnostics.txt 2>&1
  adb logcat -d -v threadtime -t 3000 > android/screenshots/failed-logcat.txt 2>&1

  local diagnostic_png="android/screenshots/failed-navigation.png.tmp"
  if adb exec-out screencap -p > "$diagnostic_png" && validate_png "$diagnostic_png"; then
    mv -f "$diagnostic_png" android/screenshots/failed-navigation.png
  else
    rm -f "$diagnostic_png"
  fi

  adb shell uiautomator dump /sdcard/flightiran-failed-window.xml \
    >> android/screenshots/failed-diagnostics.txt 2>&1
  adb exec-out cat /sdcard/flightiran-failed-window.xml \
    > android/screenshots/failed-window.xml 2>> android/screenshots/failed-diagnostics.txt
  exit "$failure_status"
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
  local target="android/screenshots/$file"
  local attempt=1
  local temporary

  sleep 2
  while (( attempt <= 3 )); do
    temporary="${target}.tmp.${BASHPID}"
    if adb exec-out screencap -p > "$temporary" && validate_png "$temporary"; then
      mv -f "$temporary" "$target"
      echo "Captured $file"
      return 0
    fi
    rm -f "$temporary"
    echo "::warning::Screenshot $file was incomplete (capture attempt $attempt/3); retrying." >&2
    sleep 2
    attempt=$((attempt + 1))
  done

  echo "Unable to capture a complete screenshot: $file" >&2
  return 1
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

# Open the published airport guide through the visible Services card.
# The directory is a LazyColumn sorted by IATA; IKA is below the initial
# viewport when all 29 airports are published. Wait for the visible search
# field to confirm index loading, capture the directory, then scroll via
# UIAutomator to the actual IKA card instead of asserting off-screen text.
open_launcher
wait_for_activity MainActivity
tap_persian_control "خدمات"
wait_for_text "راهنمای فرودگاه‌ها"
tap_service_row "راهنمای فرودگاه‌ها"
wait_for_activity AirportDirectoryActivity
wait_for_text "جست‌وجوی نام فرودگاه یا کد IATA"
capture 08-airports.png
tap_service_row "امام خمینی تهران"
wait_for_text "بار مجاز و قوانین حمل بار"
capture 08-airport-ika.png
tap_service_row "بار مجاز و قوانین حمل بار"
capture 08-airport-ika-baggage.png

# Native visa discovery and detail both read the APK-bundled JSON snapshot.
open_launcher
wait_for_activity MainActivity
tap_persian_control "خدمات"
wait_for_text "راهنمای ویزا و ورود"
tap_service_row "راهنمای ویزا و ورود"
wait_for_activity VisaGuideActivity
wait_for_text "کشور صادرکننده پاسپورت"
capture 09-visa-discovery.png
tap_service_row "ترکیه"
wait_for_text "جزئیات ویزا"
capture 09-visa-detail.png

# All nine reachable native/in-app views and their scrolled/detail variants.
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
    "08-airports.png", "08-airport-ika.png", "08-airport-ika-baggage.png",
    "09-visa-discovery.png", "09-visa-detail.png",
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
