// Recorded fares only. Do not trust a client-supplied change_percent as a discount.
export function validDropPercent(fare) {
  const p = fare.price_toman, a = Object.hasOwn(fare, "historical_average_toman") ? fare.historical_average_toman : fare.average_price_toman, n = fare.average_sample_count;
  if (!Number.isSafeInteger(p) || p <= 0 || p > 1e12 || typeof a !== "number" ||
      !Number.isFinite(a) || a <= p || a > 1e12 || !Number.isInteger(n) || n < 3 || n > 100000) return null;
  const value = Math.floor((a - p) * 1000 / a + 0.5) / 10;
  return value > 0 && Number.isFinite(value) ? value : null;
}
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
export function rankTicketFares(routes, {mode = "cheap", origin = "", search = ""} = {}) {
  const term = search.trim().toLowerCase();
  return (routes || []).flatMap(route => (route.destinations || []).map(f => ({...f, origin: route.origin})))
    .filter(f => typeof f.origin === "string" && typeof f.name === "string" &&
      Number.isSafeInteger(f.price_toman) && f.price_toman > 0 && f.price_toman <= 1e12 &&
      (!origin || f.origin === origin) && f.name.toLowerCase().includes(term) &&
      (mode !== "drops" || validDropPercent(f) !== null))
    .sort((a,b) => (mode === "drops" ? validDropPercent(b) - validDropPercent(a) : 0) ||
      a.price_toman - b.price_toman || compare(a.origin,b.origin) || compare(a.name,b.name));
}

// Refresh request order and freshness are part of the public feed contract.
export function pricesAreStale(snapshot, now = Date.now()) {
  const observed = Date.parse(snapshot?.observed_at);
  return snapshot?.stale !== false || !Number.isFinite(observed) ||
    observed > now + 300000 || now - observed > 10800000;
}
