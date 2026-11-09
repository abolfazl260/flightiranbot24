-- Contains only approved, consented public views. Original archives/actors stay in SQLite.
CREATE TABLE IF NOT EXISTS public_experiences (
 id INTEGER PRIMARY KEY,
 modified_ms INTEGER NOT NULL,
 rating INTEGER,
 helpful INTEGER NOT NULL,
 targets_json TEXT NOT NULL CHECK(json_valid(targets_json)),
 search_key TEXT NOT NULL,
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json))
);
CREATE TABLE IF NOT EXISTS experience_projection_meta (
 id INTEGER PRIMARY KEY CHECK(id=1),
 generated_ms INTEGER NOT NULL DEFAULT 0,
 invalid_after_ms INTEGER NOT NULL DEFAULT 0,
 expires_ms INTEGER NOT NULL DEFAULT 0
);
