// Recorded fares only. Do not trust a client-supplied change_percent as a discount.
export function validDropPercent(fare) {
  const p = fare.price_toman, a = fare.average_price_toman, n = fare.average_sample_count;
  if (!Number.isSafeInteger(p) || p <= 0 || typeof a !== "number" ||
      !Number.isFinite(a) || a <= p || !Number.isInteger(n) || n < 3) return null;
  const value = Math.floor((a - p) * 1000 / a + 0.5) / 10;
  return value > 0 && Number.isFinite(value) ? value : null;
}
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
export function rankTicketFares(routes, {mode = "cheap", origin = "", search = ""} = {}) {
  const term = search.trim().toLowerCase();
  return (routes || []).flatMap(route => (route.destinations || []).map(f => ({...f, origin: route.origin})))
    .filter(f => typeof f.origin === "string" && typeof f.name === "string" &&
      Number.isSafeInteger(f.price_toman) && f.price_toman > 0 &&
      (!origin || f.origin === origin) && f.name.toLowerCase().includes(term) &&
      (mode !== "drops" || validDropPercent(f) !== null))
    .sort((a,b) => (mode === "drops" ? validDropPercent(b) - validDropPercent(a) : 0) ||
      a.price_toman - b.price_toman || compare(a.origin,b.origin) || compare(a.name,b.name));
}
