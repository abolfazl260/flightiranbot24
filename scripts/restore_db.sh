#!/usr/bin/env bash
set -euo pipefail
backup="${1:?usage: restore_db.sh BACKUP TARGET_DB}"
target="${2:-flightiran.db}"
if [ ! -f "$backup" ]; then
  echo "Backup not found: $backup" >&2
  exit 1
fi
tmp="${target}.restore.tmp"
python - "$backup" "$tmp" <<'PY'
import sqlite3
import sys

source, destination = sys.argv[1:]
with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
    source_connection.backup(destination_connection)
PY
mv "$tmp" "$target"
echo "Database restored to $target"
