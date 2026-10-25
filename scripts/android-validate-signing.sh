#!/usr/bin/env bash
# Validates the keystore, alias and both passwords without publishing an APK/AAB.
# Never log the keystore, its base64 value, or the passwords.
set -euo pipefail

for name in ANDROID_KEYSTORE_FILE ANDROID_KEYSTORE_PASSWORD ANDROID_KEY_ALIAS ANDROID_KEY_PASSWORD; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required signing variable: $name" >&2
    exit 1
  fi
done
for executable in keytool jar jarsigner grep mktemp; do
  command -v "$executable" >/dev/null || { echo "Missing $executable" >&2; exit 1; }
done
if [[ ! -r "$ANDROID_KEYSTORE_FILE" || ! -s "$ANDROID_KEYSTORE_FILE" ]]; then
  echo "Signing keystore is missing, empty or unreadable" >&2
  exit 1
fi

# keytool checks the store password and alias. Signing a disposable JAR also
# checks that the selected private key can be unlocked with the key password.
keytool -list -keystore "$ANDROID_KEYSTORE_FILE" \
  -storepass:env ANDROID_KEYSTORE_PASSWORD \
  -alias "$ANDROID_KEY_ALIAS" >/dev/null

workdir="$(mktemp -d "${TMPDIR:-/tmp}/flightiran-signing.XXXXXXXX")"
trap 'rm -rf "$workdir"' EXIT
printf 'FlightIranBot24 signing test\n' > "$workdir/payload.txt"
jar --create --file "$workdir/unsigned.jar" -C "$workdir" payload.txt
jarsigner -keystore "$ANDROID_KEYSTORE_FILE" \
  -storepass:env ANDROID_KEYSTORE_PASSWORD \
  -keypass:env ANDROID_KEY_PASSWORD \
  -signedjar "$workdir/signed.jar" "$workdir/unsigned.jar" \
  "$ANDROID_KEY_ALIAS" >/dev/null
verification="$(jarsigner -verify "$workdir/signed.jar")"
if ! grep -Fxq 'jar verified.' <<< "$verification"; then
  echo 'Signing test did not produce a valid signed JAR' >&2
  exit 1
fi
printf 'Android signing credentials verified (no release created).\n'
