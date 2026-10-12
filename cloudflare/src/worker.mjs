// Public, read-only Android API. The only writes are protected, fixed-shape imports.
// R2 holds recorded ticket snapshots; D1 holds whitelisted visa/airport projections.
const PRICE_KEY = "public/v1/tickets/prices.json";
const MAX_BYTES = 1_500_000;
const CODE2 = /^[A-Z]{2}$/;
const CODE3 = /^[A-Z]{3}$/;
const bad = (status, message) => Response.json({ error: message }, { status, headers: { "Cache-Control": "no-store" } });
const good = (payload, cache = 60) => Response.json(payload, { headers: { "Cache-Control": `public, max-age=${cache}`, "X-Content-Type-Options": "nosniff" } });
const ack = payload => Response.json(payload, { headers: { "Cache-Control": "no-store" } });
const text = (value, limit = 160) => typeof value === "string" && value.trim().length > 0 && value.length <= limit ? value.trim() : null;
const optional = (value, limit = 1000) => value == null ? null : text(value, limit);
const integer = (value, max = 1_000_000_000_000) => Number.isSafeInteger(value) && value > 0 && value <= max ? value : null;
const date = value => typeof value === "string" && /^\d{4}-\d\d-\d\dT/.test(value) && Number.isFinite(Date.parse(value)) && /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? Date.parse(value) : null;
const https = value => {
  if (value == null) return null;
  try { const u = new URL(value); return u.protocol === "https:" && !u.username && !u.password && value.length <= 600 ? u.href : null; }
  catch { return null; }
};
async function authorized(request, env) {
  if (!env.PUBLISH_TOKEN || env.PUBLISH_TOKEN.length < 32) return false;
  const supplied = request.headers.get("Authorization") || "";
  const expected = `Bearer ${env.PUBLISH_TOKEN}`;
  const a = new TextEncoder().encode(supplied);
  const b = new TextEncoder().encode(expected);
  if (a.length !== b.length) return false;
  const [ha, hb] = await Promise.all([crypto.subtle.digest("SHA-256", a), crypto.subtle.digest("SHA-256", b)]);
  return new Uint8Array(ha).every((v, i) => v === new Uint8Array(hb)[i]);
}
async function bodyJson(request) {
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) throw Error("content-type");
  if (Number(request.headers.get("content-length") || 0) > MAX_BYTES) throw Error("body-too-large");
  const reader = request.body?.getReader();
  if (!reader) throw Error("empty-body");
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) { await reader.cancel(); throw Error("body-too-large"); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const raw = new Uint8Array(size);
  let offset = 0;
  for (const c of chunks) { raw.set(c, offset); offset += c.byteLength; }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
}
function validatedPrices(data) {
  if (!data || data.currency !== "TOMAN" || !Array.isArray(data.routes) ||
      data.routes.length < 1 || data.routes.length > 150 || date(data.observed_at) === null ||
      Date.parse(data.observed_at) > Date.now() + 300_000 || typeof data.stale !== "boolean") return null;
  const routes = [];
  for (const route of data.routes) {
    const origin = text(route?.origin, 128);
    if (!origin || !Array.isArray(route.destinations) ||
        route.destinations.length < 1 || route.destinations.length > 150) return null;
    const destinations = [];
    for (const fare of route.destinations) {
      const name = text(fare?.name, 128), price = integer(fare?.price_toman);
      if (!name || !price) return null;
      const avg = fare.average_price_toman == null ? null : integer(fare.average_price_toman);
      if (fare.average_price_toman != null && avg == null) return null;
      const samples = fare.average_sample_count == null ? 0 : fare.average_sample_count;
      if (!Number.isSafeInteger(samples) || samples < 0 || samples > 100000) return null;
      destinations.push({
        name, price_toman: price, average_price_toman: avg,
        change_percent: avg === null || samples === 0 ? null : Math.round(1000 * (price - avg) / avg) / 10,
        average_sample_count: samples
      });
    }
    routes.push({ origin, destinations });
  }
  return { currency: "TOMAN", observed_at: data.observed_at, stale: data.stale, routes };
}
function validatedAirports(data) {
  if (!Array.isArray(data?.airports) || data.airports.length < 1 || data.airports.length > 1000) return null;
  const rows = [], codes = new Set();
  for (const a of data.airports) {
    const code = a?.code, name = text(a?.name, 160), country = a?.country, timezone = text(a?.timezone, 80);
    if (!CODE3.test(code) || !CODE2.test(country) || !name || !timezone || codes.has(code)) return null;
    codes.add(code); rows.push({ code, name, country, timezone });
  }
  return rows;
}
function validatedVisa(data, destination) {
  if (!Array.isArray(data?.rules) || data.destination !== destination || data.rules.length < 1 || data.rules.length > 250) return null;
  const rows = [], codes = new Set();
  for (const r of data.rules) {
    const passport = r?.passport, country = text(r?.country_name, 128), status = text(r?.status, 40), sourceLevel = text(r?.source_level, 16);
    const stay = r?.stay_days == null ? null : integer(r.stay_days, 36500);
    const notes = optional(r?.notes, 2500), url = https(r?.source_url), verified = optional(r?.verified_on, 32);
    if (!CODE2.test(passport) || codes.has(passport) || !country || !status || !sourceLevel ||
        (r?.stay_days != null && stay == null) || (r?.notes != null && notes === null) ||
        (r?.source_url != null && url === null) || (r?.verified_on != null && verified === null)) return null;
    codes.add(passport); rows.push({ passport, destination, country_name: country, status, stay_days: stay,
      notes, source_url: url, verified_on: verified, source_level: sourceLevel });
  }
  return rows;
}
export async function handleRequest(request, env) {
  const url = new URL(request.url), path = url.pathname;
  if (request.method === "GET" && path === "/healthz") return good({ status: "ok" }, 0);
  if (request.method === "GET" && path === "/api/v1/tickets/prices") {
    if (!env.PUBLIC_SNAPSHOTS) return bad(503, "Snapshot storage unavailable");
    const item = await env.PUBLIC_SNAPSHOTS.get(PRICE_KEY);
    if (!item) return bad(503, "No published ticket prices");
    let snapshot;
    try { snapshot = validatedPrices(JSON.parse(await item.text())); } catch { return bad(503, "Invalid published ticket data"); }
    if (!snapshot) return bad(503, "Invalid published ticket data");
    const fresh = Date.now() - Date.parse(snapshot.observed_at) <= 3 * 60 * 60 * 1000;
    return good({ ...snapshot, stale: snapshot.stale || !fresh }, fresh && !snapshot.stale ? 60 : 0);
  }
  if (request.method === "GET" && path === "/api/v1/airports") {
    if (!env.PUBLIC_DB) return bad(503, "Public index unavailable");
    const { results } = await env.PUBLIC_DB.prepare("SELECT code, name, country, timezone FROM airports ORDER BY code LIMIT 1000").all();
    if (!results?.length) return bad(503, "No published airport catalog");
    return good({ airports: results }, 3600);
  }
  if (request.method === "GET" && path === "/api/v1/visa/rule") {
    const passport = url.searchParams.get("passport"), destination = url.searchParams.get("destination");
    if (!CODE2.test(passport) || !CODE2.test(destination)) return bad(400, "Invalid passport or destination");
    if (!env.PUBLIC_DB) return bad(503, "Public index unavailable");
    const rule = await env.PUBLIC_DB.prepare("SELECT passport, destination, country_name, status, stay_days, notes, source_url, verified_on, source_level, published_at FROM visa_rules WHERE passport = ? AND destination = ?").bind(passport, destination).first();
    if (!rule) return bad(404, "Visa rule unavailable");
    return good(rule, 900);
  }
  if (request.method === "GET" && path === "/api/v1/visa/list") {
    const passport = url.searchParams.get("passport");
    if (!CODE2.test(passport)) return bad(400, "Invalid passport");
    if (!env.PUBLIC_DB) return bad(503, "Public index unavailable");
    const { results } = await env.PUBLIC_DB.prepare("SELECT passport, destination, country_name, status, stay_days, verified_on, source_level FROM visa_rules WHERE passport = ? ORDER BY country_name LIMIT 250").bind(passport).all();
    if (!results?.length) return bad(503, "Visa catalog unavailable");
    return good({ passport, rules: results }, 900);
  }
  if (path.startsWith("/internal/")) {
    if (request.method !== "POST") return bad(405, "Method not allowed");
    if (!await authorized(request, env)) return bad(401, "Unauthorized");
    let payload;
    try { payload = await bodyJson(request); } catch { return bad(400, "Invalid JSON payload"); }
    if (path === "/internal/v1/tickets/prices") {
      if (!env.PUBLIC_SNAPSHOTS) return bad(503, "Snapshot storage unavailable");
      const snapshot = validatedPrices(payload);
      if (!snapshot) return bad(422, "Invalid public ticket snapshot");
      const old = await env.PUBLIC_SNAPSHOTS.get(PRICE_KEY);
      if (old) {
        try {
          const prior = JSON.parse(await old.text());
          if (date(prior.observed_at) !== null && date(prior.observed_at) > date(snapshot.observed_at))
            return bad(409, "Refusing older ticket snapshot");
        } catch { /* a corrupt previous object may be replaced by validated data */ }
      }
      await env.PUBLIC_SNAPSHOTS.put(PRICE_KEY, JSON.stringify(snapshot), { httpMetadata: { contentType: "application/json" } });
      return ack({ published: true, routes: snapshot.routes.length });
    }
    if (path === "/internal/v1/airports") {
      if (!env.PUBLIC_DB) return bad(503, "Public index unavailable");
      const rows = validatedAirports(payload);
      if (!rows) return bad(422, "Invalid public airport snapshot");
      const statements = [env.PUBLIC_DB.prepare("DELETE FROM airports")];
      // D1 limits each SQL statement to 100 bound parameters.
      for (let i = 0; i < rows.length; i += 24) {
        const group = rows.slice(i, i + 24);
        const sql = "INSERT INTO airports(code,name,country,timezone) VALUES " + group.map(() => "(?,?,?,?)").join(",");
        statements.push(env.PUBLIC_DB.prepare(sql).bind(...group.flatMap(a => [a.code, a.name, a.country, a.timezone])));
      }
      await env.PUBLIC_DB.batch(statements);
      return ack({ published: true, airports: rows.length });
    }
    const visaMatch = /^\/internal\/v1\/visa\/destination\/([A-Z]{2})$/.exec(path);
    if (visaMatch) {
      if (!env.PUBLIC_DB) return bad(503, "Public index unavailable");
      const destination = visaMatch[1], rows = validatedVisa(payload, destination), now = new Date().toISOString();
      if (!rows) return bad(422, "Invalid public visa rules");
      const statements = [env.PUBLIC_DB.prepare("DELETE FROM visa_rules WHERE destination = ?").bind(destination)];
      // 10 rows per INSERT = exactly 100 bindings; <=26 statements for 250 rules.
      // Keep delete + every insert atomic in a single D1 transaction.
      for (let i = 0; i < rows.length; i += 10) {
        const group = rows.slice(i, i + 10);
        const sql = "INSERT INTO visa_rules(passport,destination,country_name,status,stay_days,notes,source_url,verified_on,source_level,published_at) VALUES " + group.map(() => "(?,?,?,?,?,?,?,?,?,?)").join(",");
        statements.push(env.PUBLIC_DB.prepare(sql).bind(...group.flatMap(r =>
          [r.passport,r.destination,r.country_name,r.status,r.stay_days,r.notes,r.source_url,r.verified_on,r.source_level,now])));
      }
      await env.PUBLIC_DB.batch(statements);
      return ack({ published: true, destination, rules: rows.length });
    }
    return bad(404, "Unknown import");
  }
  return bad(404, "Not found");
}
export default { fetch(request, env) { return handleRequest(request, env).catch(() => bad(503, "Service temporarily unavailable")); } };
