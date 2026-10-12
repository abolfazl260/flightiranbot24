// Public visa projection read adapter. New deployments use one D1 row per
// passport; partially migrated databases fall back to the existing indexed
// visa_rules table. Private Telegram state NEVER belongs in this projection.
const PASSPORT_COLUMNS = [
  "passport", "destination", "country_name", "status", "stay_days",
  "notes", "source_url", "verified_on", "source_level"
];
const LIST_COLUMNS = [
  "passport", "destination", "country_name", "status", "stay_days",
  "verified_on", "source_level"
];

async function snapshot(db, passport) {
  const record = await db.prepare(
    "SELECT snapshot_json,published_at FROM visa_passport_snapshots WHERE passport=?"
  ).bind(passport).first();
  if (!record) return null;
  // SQL json_valid guards syntax. Validate structure defensively as well,
  // so bad data cannot silently be treated as absence and show stale records.
  const data = JSON.parse(record.snapshot_json);
  if (data?.passport !== passport || !Array.isArray(data?.rules) ||
      data.rules.length < 190 || data.rules.length > 250) {
    throw Error("Invalid public visa passport snapshot");
  }
  return { rules: data.rules, publishedAt: record.published_at };
}

function project(row, columns) {
  return Object.fromEntries(columns.map(column => [column, row[column] ?? null]));
}

export async function publicVisaRule(db, passport, destination) {
  const document = await snapshot(db, passport);
  if (document) {
    const result = document.rules.find(row => row.destination === destination);
    return result ? { ...project(result, PASSPORT_COLUMNS),
      published_at: document.publishedAt } : null;
  }
  return db.prepare(
    "SELECT passport,destination,country_name,status,stay_days,notes," +
    "source_url,verified_on,source_level,published_at FROM visa_rules " +
    "WHERE passport=? AND destination=?"
  ).bind(passport, destination).first();
}

export async function publicVisaList(db, passport, {includeNotes = false} = {}) {
  const document = await snapshot(db, passport);
  if (document) {
    const fields = includeNotes ? PASSPORT_COLUMNS : LIST_COLUMNS;
    return document.rules.map(row => project(row, fields))
      .sort((a,b) => a.country_name.localeCompare(b.country_name));
  }
  const cols = (includeNotes ? PASSPORT_COLUMNS : LIST_COLUMNS).join(",");
  const {results} = await db.prepare(
    "SELECT " + cols + " FROM visa_rules WHERE passport=? " +
    "ORDER BY country_name LIMIT 250"
  ).bind(passport).all();
  return results || [];
}
