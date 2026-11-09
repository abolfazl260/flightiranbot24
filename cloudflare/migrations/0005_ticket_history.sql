-- Public daily aggregates only. Existing tables and private user data untouched.
CREATE TABLE IF NOT EXISTS ticket_route_history (
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  last_day TEXT NOT NULL,
  observed_epoch_ms INTEGER NOT NULL,
  snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
  PRIMARY KEY(origin,destination)
);
CREATE INDEX IF NOT EXISTS ix_ticket_history_last_day ON ticket_route_history(last_day);
