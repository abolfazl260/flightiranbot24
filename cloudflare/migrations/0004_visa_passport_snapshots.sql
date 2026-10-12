-- Compact, public visa projection for Workers Free / D1 Free.
-- One document per passport (about 199 documents), replacing the old
-- passport × destination relational projection (~40,000 indexed records).
-- Keep the old visa_rules table untouched for transitional read fallback.
-- No bot users, private alerts, tokens or raw upstream documents are stored.
CREATE TABLE IF NOT EXISTS visa_passport_snapshots (
  passport TEXT PRIMARY KEY NOT NULL CHECK (length(passport) = 2),
  snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
  published_at TEXT NOT NULL
);
