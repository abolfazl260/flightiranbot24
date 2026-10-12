-- Existing D1 databases already running 0001 remain intact.
-- Only the latest validated, public ticket batch is stored. No user data/history.
CREATE TABLE IF NOT EXISTS ticket_price_snapshots (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  observed_epoch_ms INTEGER NOT NULL CHECK (observed_epoch_ms > 0),
  snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
  published_at TEXT NOT NULL
);
