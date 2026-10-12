#!/usr/bin/env bash
set -euo pipefail

# Executed in one shell: emulator-runner otherwise launches every script line
# independently and loses shell variables / breaks multi-line Python heredocs.
gradle --no-daemon -p android :app:assembleDebug
apk="android/app/build/outputs/apk/debug/app-debug.apk"
test -s "$apk"
adb install -r "$apk"
mkdir -p android/screenshots

capture() {
  local activity="$1" file="$2"
  adb shell am start -W -n "com.abolfazl260.flightiranbot24.debug/com.abolfazl260.flightiranbot24.$activity" | tee /tmp/flightiran-launch.txt
  grep -q 'Status: ok' /tmp/flightiran-launch.txt
  sleep 2
  adb exec-out screencap -p > "android/screenshots/$file"
}
capture MainActivity 01-home.png
capture AirportDirectoryActivity 02-airports.png
capture ChecklistActivity 03-checklist.png

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
