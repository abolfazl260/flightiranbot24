#!/usr/bin/env bash
# Run locally on a trusted computer. Never commit or paste the private upload key.
set -euo pipefail
repo="abolfazl260/flightiranbot24"
if [[ $# -ne 1 || ! -f "$1" || ! -s "$1" ]]; then
  echo "Usage: bash scripts/android-configure-signing.sh /secure/path/upload-key.jks" >&2
  exit 2
fi
if [[ ! -t 0 ]]; then
  echo "Run interactively in a local terminal, not inside CI or a pipe" >&2
  exit 1
fi
for executable in gh base64 tr keytool jarsigner jar; do
  command -v "$executable" >/dev/null || { echo "Missing $executable" >&2; exit 1; }
done
gh auth status >/dev/null || { echo "Run gh auth login first" >&2; exit 1; }
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf 'Configure upload signing for %s. Back up your keystore and passwords offline.\n' "$repo"
read -r -s -p "Keystore password: " store_password
printf '\n'
read -r -p "Key alias [flightiran-upload]: " key_alias
key_alias="${key_alias:-flightiran-upload}"
read -r -s -p "Key password: " key_password
printf '\n'
if [[ -z "$store_password" || -z "$key_password" || -z "$key_alias" ]]; then
  echo 'Passwords and alias are required' >&2
  exit 1
fi
export ANDROID_KEYSTORE_FILE="$1"
export ANDROID_KEYSTORE_PASSWORD="$store_password"
export ANDROID_KEY_ALIAS="$key_alias"
export ANDROID_KEY_PASSWORD="$key_password"
unset store_password key_password key_alias
bash "$script_dir/android-validate-signing.sh"

# Write secrets only after the local cryptographic preflight succeeds.
base64 < "$ANDROID_KEYSTORE_FILE" | tr -d '\r\n' | gh secret set ANDROID_KEYSTORE_BASE64 -R "$repo"
printf '%s' "$ANDROID_KEYSTORE_PASSWORD" | gh secret set ANDROID_KEYSTORE_PASSWORD -R "$repo"
printf '%s' "$ANDROID_KEY_ALIAS" | gh secret set ANDROID_KEY_ALIAS -R "$repo"
printf '%s' "$ANDROID_KEY_PASSWORD" | gh secret set ANDROID_KEY_PASSWORD -R "$repo"
unset ANDROID_KEYSTORE_PASSWORD ANDROID_KEY_PASSWORD
printf 'Four GitHub Actions secrets uploaded. Verify them with the Android Signing Preflight workflow before tagging a release.\n'
