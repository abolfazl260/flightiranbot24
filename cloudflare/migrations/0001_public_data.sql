-- Only public reference data. Never replicate bot users, preferences, alerts or tokens.
CREATE TABLE IF NOT EXISTS airports (
  code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT NOT NULL,
  timezone TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visa_rules (
  passport TEXT NOT NULL,
  destination TEXT NOT NULL,
  country_name TEXT NOT NULL,
  status TEXT NOT NULL,
  stay_days INTEGER,
  notes TEXT,
  source_url TEXT,
  verified_on TEXT,
  source_level TEXT NOT NULL,
  published_at TEXT NOT NULL,
  PRIMARY KEY (passport, destination)
);
CREATE INDEX IF NOT EXISTS ix_visa_public_passport ON visa_rules (passport);
