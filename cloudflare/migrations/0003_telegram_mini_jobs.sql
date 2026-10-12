-- Private, short-lived inbox for signed Telegram Mini App requests.
-- The Ubuntu bridge remains the sole writer of actual user preferences/alerts in SQLite.
-- This D1 table is never exposed by the public Android API.
CREATE TABLE IF NOT EXISTS telegram_mini_jobs (
  id TEXT PRIMARY KEY,
  telegram_id INTEGER NOT NULL CHECK (telegram_id > 0),
  user_json TEXT NOT NULL CHECK (json_valid(user_json) AND length(user_json) <= 1024),
  operation TEXT NOT NULL CHECK (length(operation) <= 32),
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json) AND length(payload_json) <= 8192),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'leased', 'complete')),
  result_status INTEGER,
  result_json TEXT CHECK (result_json IS NULL OR json_valid(result_json)),
  created_at_ms INTEGER NOT NULL,
  lease_until_ms INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_telegram_mini_jobs_pending
  ON telegram_mini_jobs(status, created_at_ms);
CREATE INDEX IF NOT EXISTS ix_telegram_mini_jobs_owner
  ON telegram_mini_jobs(telegram_id, created_at_ms);
