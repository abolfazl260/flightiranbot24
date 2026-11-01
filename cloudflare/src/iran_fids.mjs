/**
 * Native Iran flight-board adapter.
 *
 * IMPORTANT: fids.airport.ir has no verified public JSON contract in this repo.
 * An operator must inspect an authorized, real JSON feed and explicitly configure
 * FIDS_SOURCE_URL_TEMPLATE on the Worker before this endpoint is usable.
 * Never substitute synthetic flights, scrape unknown HTML or open the website
 * inside the Android app. Keep malformed/blocked feeds unavailable (503).
 */
const ALLOWED_AIRPORTS = new Set([
  "THR", "MHD", "SYZ", "IFN", "TBZ", "AWZ", "BND", "KER", "ZAH", "OMH"
]);
const MAX_RESPONSE_BYTES = 350_000;
const MAX_FLIGHTS = 250;
const SOURCE_HOST = "fids.airport.ir";

const fail = (status, error) => Response.json({ error }, {
  status, headers: { "Cache-Control": "no-store" }
});

const safe = (value, max = 120) =>
  typeof value === "string" && value.trim() && value.trim().length <= max
    ? value.trim().replace(/[\u0000-\u001f\u007f]/g, "") : null;

function officialUrl(template, airport, direction) {
  if (typeof template !== "string" || template.length > 900 ||
      !template.includes("{airport}") || !template.includes("{direction}")) return null;
  // Only the two explicitly documented placeholders may be substituted.
  const stripped = template.replaceAll("{airport}", "").replaceAll("{direction}", "");
  if (/[{}]/.test(stripped)) return null;
  try {
    const uri = new URL(template.replaceAll("{airport}", airport)
      .replaceAll("{direction}", direction));
    if (uri.protocol !== "https:" || uri.hostname !== SOURCE_HOST ||
        uri.username || uri.password || uri.port || uri.hash ||
        !uri.pathname.startsWith("/")) return null;
    return uri.href;
  } catch { return null; }
}

const optional = (obj, names, max = 120) => {
  for (const name of names) {
    if (Object.prototype.hasOwnProperty.call(obj, name)) {
      const value = obj[name];
      if (value == null || value === "") return null;
      // Flight numbers can be represented numerically by some feeds.
      return safe(typeof value === "number" && Number.isSafeInteger(value)
        ? String(value) : value, max);
    }
  }
  return null;
};

function validDate(value) {
  const text = safe(value, 40);
  if (!text || !/^\d{4}-\d{2}-\d{2}T/.test(text) ||
      !/(Z|[+-]\d{2}:\d{2})$/.test(text)) return null;
  const ms = Date.parse(text);
  if (!Number.isFinite(ms) || ms > Date.now() + 300_000) return null;
  return text;
}

function normalizeFlight(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return null;
  const flightNumber = optional(item, ["flight_number", "flightNumber", "FlightNumber"], 24);
  const city = optional(item, ["city", "route", "origin_destination", "destination", "origin"], 128);
  const scheduled = optional(item, ["scheduled_time", "scheduledTime", "time", "Time"], 40);
  if (!flightNumber || !city || !scheduled ||
      !(/^\d{1,2}:\d{2}$/.test(scheduled) ||
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(scheduled))) return null;
  return {
    flight_number: flightNumber,
    airline: optional(item, ["airline", "airlineName", "Airline"], 128),
    city,
    scheduled_time: scheduled,
    estimated_time: optional(item, ["estimated_time", "estimatedTime"], 40),
    actual_time: optional(item, ["actual_time", "actualTime"], 40),
    status: optional(item, ["status", "flightStatus", "remarks"], 100),
    terminal: optional(item, ["terminal"], 20),
    gate: optional(item, ["gate"], 20),
  };
}

/** Exported pure normalizer, deliberately narrow until a real feed is verified. */
export function normalizeFidsPayload(payload, airport, direction, fetchedAt) {
  if (!payload || Array.isArray(payload) || typeof payload !== "object") return null;
  const rawFlights = payload.flights ?? payload.data?.flights;
  if (!Array.isArray(rawFlights) || rawFlights.length > MAX_FLIGHTS) return null;
  if (payload.airport && payload.airport !== airport) return null;
  if (payload.direction && payload.direction !== direction) return null;
  const flights = rawFlights.map(normalizeFlight);
  // An unknown provider format is not "no flights". Do not omit invalid rows.
  if (flights.some(row => row === null)) return null;
  const sourceUpdatedAt = validDate(payload.source_updated_at ?? payload.updated_at);
  return {
    airport, direction,
    source: "Iran Airports and Air Navigation Company FIDS",
    source_url: "https://fids.airport.ir/",
    fetched_at: fetchedAt,
    source_updated_at: sourceUpdatedAt,
    freshness: sourceUpdatedAt ? "reported" : "unverified",
    flights
  };
}

/** Called only from the first-party public Worker; upstream never touches APK. */
export async function getIranFidsBoard(request, env, upstreamFetch = fetch) {
  if (request.method !== "GET") return fail(405, "Method not allowed");
  const uri = new URL(request.url);
  const match = /^\/api\/v1\/iran\/fids\/([A-Z]{3})\/(arrivals|departures)$/.exec(uri.pathname);
  if (!match || uri.search) return fail(400, "Invalid airport/direction");
  const [, airport, direction] = match;
  if (!ALLOWED_AIRPORTS.has(airport)) return fail(404, "Airport feed not verified");
  const url = officialUrl(env.FIDS_SOURCE_URL_TEMPLATE, airport, direction);
  if (!url) return fail(503, "Official FIDS feed is not configured or verified");
  try {
    const response = await upstreamFetch(url, {
      method: "GET", redirect: "manual", signal: AbortSignal.timeout(8_000),
      headers: { Accept: "application/json", "User-Agent": "FlightIranBot24/1.0" }
    });
    if (!response.ok || response.status !== 200) return fail(503, "Official FIDS feed unavailable");
    if (!(response.headers.get("content-type") || "").toLowerCase().includes("application/json"))
      return fail(503, "Unexpected upstream format");
    if (Number(response.headers.get("content-length") || 0) > MAX_RESPONSE_BYTES)
      return fail(503, "Official response too large");
    // Bound the stream even when upstream omits or lies about Content-Length.
    const reader = response.body?.getReader();
    if (!reader) return fail(503, "Empty official response");
    let size = 0;
    const chunks = [];
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_RESPONSE_BYTES) {
          await reader.cancel();
          return fail(503, "Official response too large");
        }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const payload = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    const snapshot = normalizeFidsPayload(payload, airport, direction, new Date().toISOString());
    if (!snapshot) return fail(503, "Unverified FIDS response format");
    return Response.json(snapshot, {
      headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" }
    });
  } catch {
    return fail(503, "Official FIDS feed unreachable");
  }
}
