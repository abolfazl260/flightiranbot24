/* WEB-002: shared read-only GitHub catalog. No credentials or Telegram data.
 * The data owner (#104) publishes this JSON and its WebP images on main.
 */
export const CATALOG_URL = "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/travel-websites/catalog.v1.json";
const IMAGE_BASE = "https://raw.githubusercontent.com/abolfazl260/flightiranbot24/main/data/travel-websites/";
const IMAGE_PATTERN = /^images\/[a-z0-9][a-z0-9._-]*\.webp$/i;
const ID_PATTERN = /^[a-z0-9][a-z0-9_-]{1,79}$/i;
const MAX_ITEMS = 100;

function nonempty(value, limit) {
  return typeof value === "string" && value.trim() && value.length <= limit
    ? value.trim() : null;
}
function safeId(value) {
  return typeof value === "string" && ID_PATTERN.test(value) ? value : null;
}
function order(value, fallback) {
  return Number.isSafeInteger(value) && value >= 0 && value <= 10000
    ? value : fallback;
}
export function approvedExternalUrl(value) {
  if (!nonempty(value, 2048)) return null;
  try {
    const u = new URL(value);
    if (u.protocol !== "https:" || u.username || u.password ||
        u.hostname.endsWith(".localhost") || u.hostname === "localhost" ||
        u.hostname === "0.0.0.0" || u.hostname === "127.0.0.1" ||
        u.hostname === "[::1]" || !u.hostname.includes(".")) return null;
    return u.href;
  } catch { return null; }
}
export function approvedImageUrl(value) {
  const text = nonempty(value, 400);
  if (!text) return null;
  const relative = text.startsWith(IMAGE_BASE) ? text.slice(IMAGE_BASE.length) : text;
  if (!IMAGE_PATTERN.test(relative) || relative.includes("..")) return null;
  return IMAGE_BASE + relative;
}
export function normalizePersian(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase("fa")
    .replace(/[يى]/g, "ی").replace(/ك/g, "ک")
    .replace(/[\u064b-\u065f\u0670\u0640]/g, "")
    .replace(/[\u200c\u200d]/g, " ")
    .replace(/[۰-۹]/g, digit => String(digit.charCodeAt(0)-1776))
    .replace(/[٠-٩]/g, digit => String(digit.charCodeAt(0)-1632))
    .replace(/\s+/g, " ").trim();
}
export function filterWebsites(sites, category, term) {
  const query = normalizePersian(term);
  return sites.filter(site =>
    (category === "all" || site.categoryId === category) &&
    (!query || normalizePersian([site.name, site.description, site.categoryName]
      .join(" ")).includes(query))
  );
}
function stringField(object, keys, limit) {
  for (const key of keys) {
    const text = nonempty(object?.[key], limit);
    if (text) return text;
  }
  return null;
}
/* Accept only v1. Field-name aliases bridge initial Android JSON serialization
 * styles without embedding any website inventory in client code.
 */
export function parseCatalog(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw))
    throw new Error("ساختار فهرست وب‌سایت‌ها معتبر نیست.");
  const version = raw.schemaVersion ?? raw.schema_version ?? raw.version;
  if (![1, "1", "1.0", "v1"].includes(version))
    throw new Error("نسخه این فهرست با مینی‌اپ سازگار نیست.");
  if (!Array.isArray(raw.categories) || !Array.isArray(raw.websites) ||
      raw.categories.length < 1 || raw.categories.length > 30 ||
      raw.websites.length < 1 || raw.websites.length > MAX_ITEMS)
    throw new Error("ساختار فهرست وب‌سایت‌ها معتبر نیست.");

  const categories = [];
  const categoryIds = new Set();
  for (const [index, item] of raw.categories.entries()) {
    const id = safeId(item?.id);
    const name = stringField(item, ["name_fa","title_fa","nameFa","titleFa","name","title"], 120);
    if (!id || !name || categoryIds.has(id))
      throw new Error("دسته‌بندی‌های فهرست معتبر نیستند.");
    categoryIds.add(id);
    categories.push({id, name, order:order(item.order ?? item.sort_order, index), index});
  }
  categories.sort((a,b)=>a.order-b.order || a.index-b.index);
  const labels = new Map(categories.map(item=>[item.id,item.name]));
  const sites = [], ids = new Set(), urls = new Set();
  for (const [index, item] of raw.websites.entries()) {
    const id = safeId(item?.id);
    const categoryId = item?.categoryId ?? item?.category_id ?? item?.category;
    const name = stringField(item, ["name_fa","title_fa","nameFa","titleFa"], 160);
    const description = stringField(item, ["description_fa","descriptionFa"], 800);
    const url = approvedExternalUrl(item?.url);
    const image = approvedImageUrl(item?.image ?? item?.image_path ?? item?.imagePath);
    if (!id || ids.has(id) || !labels.has(categoryId) ||
        !name || !description || !url || !image || urls.has(url) ||
        typeof item?.enabled !== "boolean")
      throw new Error("یکی از موارد فهرست وب‌سایت‌ها معتبر نیست.");
    ids.add(id);urls.add(url);
    if (item.enabled) sites.push({id, categoryId, categoryName:labels.get(categoryId),
      name, description, url, image,
      order:order(item.order ?? item.sort_order,index), index});
  }
  const ranks = new Map(categories.map((item,index)=>[item.id,index]));
  sites.sort((a,b)=>ranks.get(a.categoryId)-ranks.get(b.categoryId) ||
    a.order-b.order || a.index-b.index);
  return {categories:categories.map(({id,name})=>({id,name})), sites, schemaVersion:1};
}
export async function fetchCatalog(fetcher = fetch, timeoutMs = 9000, cacheMode = "default") {
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(),timeoutMs);
  try {
    const response = await fetcher(CATALOG_URL,{
      method:"GET", mode:"cors", redirect:"error", credentials:"omit",
      referrerPolicy:"no-referrer", cache:cacheMode,
      headers:{"Accept":"application/json"}, signal:controller.signal
    });
    if (!response.ok) throw new Error(
      response.status === 404 ? "فهرست وب‌سایت‌ها هنوز منتشر نشده است." :
      response.status === 429 ? "دریافت فهرست موقتاً محدود شده است." :
      "دریافت فهرست با خطای سرور مواجه شد."
    );
    const size = Number(response.headers?.get?.("content-length") || 0);
    if (size > 150000) throw new Error("حجم فهرست بیشتر از حد مجاز است.");
    const body = await response.text();
    if (body.length > 150000) throw new Error("حجم فهرست بیشتر از حد مجاز است.");
    let json;
    try { json = JSON.parse(body); }
    catch { throw new Error("پاسخ فهرست وب‌سایت‌ها JSON معتبر نیست."); }
    return parseCatalog(json);
  } catch (error) {
    if (error?.name === "AbortError")
      throw new Error("زمان دریافت فهرست به پایان رسید.");
    if (error instanceof TypeError)
      throw new Error("ارتباط با منبع فهرست برقرار نشد.");
    throw error;
  } finally { clearTimeout(timer); }
}
