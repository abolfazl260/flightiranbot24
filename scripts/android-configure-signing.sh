#!/usr/bin/env bash
# Run locally: never commit your private upload keystore.
set -euo pipefail
repo="abolfazl260/flightiranbot24"
if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Usage: bash scripts/android-configure-signing.sh /secure/path/upload-key.jks" >&2
  exit 2
fi
for executable in gh base64 tr; do
  command -v "$executable" >/dev/null || { echo "Missing $executable" >&2; exit 1; }
done
gh auth status >/dev/null || { echo "Run gh auth login first" >&2; exit 1; }
echo "Set private signing secrets for $repo. Back up keystore/passwords offline!"
base64 < "$1" | tr -d '\r\n' | gh secret set ANDROID_KEYSTORE_BASE64 -R "$repo"
read -r -s -p "Keystore password: " store_password
printf '\n'
printf '%s' "$store_password" | gh secret set ANDROID_KEYSTORE_PASSWORD -R "$repo"
unset store_password
read -r -p "Key alias: " key_alias
[[ -n "$key_alias" ]] || exit 1
printf '%s' "$key_alias" | gh secret set ANDROID_KEY_ALIAS -R "$repo"
unset key_alias
read -r -s -p "Key password: " key_password
printf '\n'
printf '%s' "$key_password" | gh secret set ANDROID_KEY_PASSWORD -R "$repo"
unset key_password
echo "Signing secrets have been configured. Keep the private key backed up."
