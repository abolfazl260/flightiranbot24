#!/usr/bin/env bash
set -euo pipefail
source_db="${1:-flightiran.db}"
destination="${2:-backups/flightiran-$(date -u +%Y%m%dT%H%M%SZ).db}"
mkdir -p "$(dirname "$destination")"
if [ ! -f "$source_db" ]; then
  echo "Database not found: $source_db" >&2
  exit 1
fi
python - "$source_db" "$destination" <<'PY'
import sqlite3
import sys

source, destination = sys.argv[1:]
with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
    source_connection.backup(destination_connection)
PY
echo "Backup written to $destination"
