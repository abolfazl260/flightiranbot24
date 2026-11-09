/* Telegram Mini App: user input and API responses are rendered as text nodes.
 * No external UI framework, localStorage credentials, or unsafe HTML insertion.
 */
import {approvedExternalUrl, fetchCatalog, filterWebsites} from "./travel-catalog.mjs";

import {rankTicketFares, validDropPercent, pricesAreStale} from "./ticket-ranking.mjs";
import {createExperienceView} from "./experience-view.mjs";
import {parseHistory} from "./ticket-history.mjs";
import {createGuideView} from "./guide-view.mjs";
import {createVisaSnapshotReader,filterCountries,POPULAR_VISA,FIDS_HOME} from "./mobile-parity.mjs";

(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const telegram = window.Telegram && window.Telegram.WebApp;
  const fmt = value => new Intl.NumberFormat("fa-IR").format(value);
  const territories = new Intl.DisplayNames(["fa"], {type:"region"});
  function persianCountry(code, fallback) {
    const name = /^[A-Z]{2}$/.test(code) ? territories.of(code) : null;
    return name && name !== code ? name : (fallback || code);
  }
  const state = {
    initData: "", bootstrap: null, prices: null, origin: "", ticketSort: "cheap", pricesRequest: 0, historyRequest: 0,
    passport: "IR", visa: null, alerts: null, useful: null, active: "home",
    visaMode: "live", snapshot: null,
    websites: null, websitesFetchedAt: 0, websitesRequest: null,
    fids: null, fidsRequest: 0,
    toastTimer: null, visaRequest: 0, visaDetailRequest: 0,
    checklist: new Set(), checklistKey: null, checklistPersistent: false,
  };

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, val] of Object.entries(attrs)) {
      if (key === "className") node.className = val;
      else if (key === "text") node.textContent = String(val ?? "");
      else if (key === "value") node.value = val;
      else if (key === "type") node.type = val;
      else if (key === "onClick") node.addEventListener("click", val);
      else if (key === "onChange") node.addEventListener("change", val);
      else if (key === "disabled") node.disabled = Boolean(val);
      else if (key === "dataset") for (const [name,v] of Object.entries(val)) node.dataset[name] = v;
      else if (val !== null && val !== undefined) node.setAttribute(key, String(val));
    }
    for (const child of children.flat()) {
      if (child !== null && child !== undefined) {
        node.append(child instanceof Node ? child : document.createTextNode(String(child)));
      }
    }
    return node;
  }
  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    svg.setAttribute("class", "symbol");
    svg.setAttribute("aria-hidden", "true");
    use.setAttribute("href", "#i-" + name);
    svg.append(use);
    return svg;
  }
  function fill(id, ...nodes) { $(id).replaceChildren(...nodes.flat()); }
  function empty(title, description) {
    return el("div", {className:"empty-list"}, el("strong", {text:title}),
      el("p", {text:description}));
  }
  function toast(message) {
    clearTimeout(state.toastTimer);
    const node = $("toast");
    node.textContent = message;
    node.hidden = false;
    state.toastTimer = setTimeout(() => { node.hidden = true; }, 3800);
    telegram?.HapticFeedback?.notificationOccurred?.("success");
  }
  async function request(path, options = {}) {
    const response = await fetch(path, {
      method: options.method || "GET",
      credentials: "omit",
      cache: "no-store",
      headers: {
        ...(path.startsWith("/api/mini/")
          ? {"X-Telegram-Init-Data": state.initData} : {}),
        ...(options.body ? {"Content-Type":"application/json"} : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    let data = {};
    try { data = await response.json(); } catch { /* unavailable upstream */ }
    if (response.status === 202 && data?.job_id) {
      // Only user-scoped operations use the outbound D1->SQLite queue. Cloudflare
      // public ticket/visa reads return immediately from D1 without polling.
      const deadline = Date.now() + 48_000;
      while (Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, 1800));
        const follow = await fetch(
          "/api/mini/results/" + encodeURIComponent(data.job_id), {
            method: "GET", credentials: "omit", cache: "no-store",
            headers: {"X-Telegram-Init-Data": state.initData},
          }
        );
        const result = await follow.json();
        if (follow.status === 202 && result.state === "pending") continue;
        if (follow.ok && result.state === "complete") {
          // Return the same body/status interface as the direct FastAPI API.
          data = result.body || {};
          if (result.http_status >= 200 && result.http_status < 300) return data;
          throw new Error(
            result.http_status === 404 ? "این مورد دیگر در دسترس نیست." :
            result.http_status === 422 ? "اطلاعات واردشده معتبر نیست یا محدودیت هشدارها تکمیل شده است." :
            result.http_status === 409 && path.includes("experiences") ? "این تجربه قبلاً ثبت شده است؛ تجربه‌های من را بررسی کنید." :
            result.http_status === 409 ? "قیمت‌های فعلی نیاز به بروزرسانی دارند." :
            "درخواست انجام نشد. کمی بعد دوباره تلاش کنید."
          );
        }
        if (follow.status === 401) throw new Error("نشست تلگرام معتبر نیست. مینی‌اپ را دوباره باز کنید.");
        if (follow.status === 503) throw new Error("وضعیت درخواست مشخص نیست. پیش از ثبت دوباره، هشدارها را بررسی کنید.");
        if (follow.status === 410) throw new Error("زمان پاسخگویی تمام شد. لطفاً بعداً دوباره تلاش کنید.");
        throw new Error("ارتباط با سرویس مینی‌اپ برقرار نشد.");
      }
      throw new Error("پاسخ سرور طول کشید. قبل از تکرار درخواست، هشدارها را بررسی کنید.");
    }
    if (!response.ok) {
      if (response.status === 401) throw new Error("نشست تلگرام معتبر نیست. مینی‌اپ را دوباره از ربات باز کنید.");
      if (response.status === 409 && path.includes("experiences")) throw new Error("این تجربه قبلاً ثبت شده است. تجربه‌های من را بررسی کنید.");
      if (response.status === 409) throw new Error("قیمت‌های فعلی نیاز به بروزرسانی دارند. کمی بعد دوباره تلاش کنید.");
      if (response.status === 404) throw new Error("این مورد دیگر در دسترس نیست.");
      if (response.status === 422) throw new Error("اطلاعات واردشده معتبر نیست یا محدودیت هشدارها تکمیل شده است.");
      throw new Error("ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.");
    }
    return data;
  }
  function go(screen) {
    if (screen === "privacy") $("startup").hidden=true;
    else if (!state.bootstrap) { showStartup("برای استفاده از خدمات، مینی‌اپ را از ربات تلگرام باز کنید."); return; }
    const page = $("screen-" + screen);
    if (!page) return;
    document.querySelectorAll(".screen").forEach(item => {
      const active = item === page;
      item.hidden = !active;
      item.classList.toggle("active",active);
    });
    document.querySelectorAll(".nav-item").forEach(button => {
      const active = button.dataset.go === screen;
      button.classList.toggle("selected",active);
      if (active) button.setAttribute("aria-current","page");
      else button.removeAttribute("aria-current");
    });
    state.active = screen;
    window.scrollTo(0,0);
    if (telegram?.BackButton) {
      if (screen === "home") telegram.BackButton.hide();
      else telegram.BackButton.show();
    }
    if (guides[screen]) guides[screen].load();
    if (screen === "experiences") experiences.load();
    if (screen === "alerts") loadAlerts();
    if (screen === "useful") loadUseful();
    if (screen === "websites") loadWebsites();
    if (screen === "fids") loadFids();
    if (screen === "visa" && !state.visa) loadVisa();
    if (screen === "checklist") renderChecklist();
    telegram?.HapticFeedback?.selectionChanged?.();
  }
  function link(kind, fallback) {
    const url = state.bootstrap?.links?.[kind] || fallback;
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== "https:") return;
      if (parsed.hostname === "t.me" || parsed.hostname === "telegram.me") {
        if (telegram?.openTelegramLink) telegram.openTelegramLink(parsed.href);
        else window.open(parsed.href,"_blank","noopener,noreferrer");
      } else if (telegram?.openLink) {
        try { telegram.openLink(parsed.href); }
        catch { window.open(parsed.href,"_blank","noopener,noreferrer"); }
      } else window.open(parsed.href,"_blank","noopener,noreferrer");
    } catch { toast("لینک معتبر نیست."); }
  }
  function openUrl(url) {
    link(null,url);
  }
  const experiences = createExperienceView({root:$("experiences-view"),el,request});
  const guides = Object.fromEntries(['airports','airlines'].map(kind => [kind,
    createGuideView({kind, root:$(kind+'-guide'), el, openUrl,
      onExperiences:t=>{go('experiences');experiences.open(t);},
      onAirport:id=>{go('airports');guides.airports.open(id);}, onFids:()=>go('fids')})
  ]));
  function guideBack() {
    if (!guides[state.active]?.back()) go('home');
  }
  function modal(title, body, actions) {
    $("dialog-title").textContent = title;
    fill("dialog-body",body);
    fill("dialog-actions",el("div",{className:"dialog-actions"},actions));
    const dlg = $("mini-dialog");
    if (!dlg.open) dlg.showModal();
    telegram?.HapticFeedback?.impactOccurred?.("light");
  }
  function closeModal() { state.historyRequest++; state.visaDetailRequest++; if ($("mini-dialog").open) $("mini-dialog").close(); }
  function act(label, click, type = "primary-cta") {
    return el("button",{type:"button",className:type,onClick:click},label);
  }
  function dateLabel(raw) {
    if (!raw) return "نامشخص";
    const time = new Date(raw);
    return Number.isFinite(time.getTime())
      ? new Intl.DateTimeFormat("fa-IR",{dateStyle:"medium",timeStyle:"short"}).format(time)
      : "نامشخص";
  }
  function money(value) { return fmt(Math.round(Number(value))) + " تومان"; }
  const visas = {
    "visa-free":["بدون ویزا","good"], "freedom-of-movement":["آزاد","good"],
    "evisa":["ویزای الکترونیکی","review"], "e-visa":["ویزای الکترونیکی","review"],
    "eta":["مجوز سفر","review"], "visa-on-arrival":["ویزای فرودگاهی","review"],
    "embassy-visa":["ویزای سفارتی","review"], "visa-required":["نیازمند ویزا","review"],
    "travel-permit":["مجوز ورود","review"], "banned":["محدودیت ورود","restricted"],
    "refused":["محدودیت ورود","restricted"], "unconfirmed":["نیازمند بررسی","review"],
    "unknown":["نامشخص","review"],
  };
  function visaStatus(code) {
    return visas[code] || ["نیازمند بررسی","review"];
  }

  async function loadPrices() {
    const sequence = ++state.pricesRequest;
    $("price-status").textContent = "در حال دریافت قیمت‌ها…";
    try {
      const prices = await request("/api/v1/tickets/prices");
      if (sequence !== state.pricesRequest) return;
      if (prices.currency !== "TOMAN" || !Array.isArray(prices.routes) ||
          !Number.isFinite(Date.parse(prices.observed_at))) throw new Error("invalid prices");
      state.prices = {...prices, stale: pricesAreStale(prices)};
      const routes = state.prices.routes || [];
      if (!routes.some(r => r.origin === state.origin)) state.origin = routes[0]?.origin || "";
      const select = $("origin-select");
      select.replaceChildren(...routes.map(route =>
        el("option",{value:route.origin,text:route.origin})
      ));
      select.value = state.origin;
      const status = $("price-status");
      status.classList.toggle("warning", Boolean(state.prices.stale));
      status.textContent = (state.prices.stale
        ? "اطلاعات این بخش قدیمی است؛ پیش از رزرو قیمت را بررسی کنید. "
        : "آخرین قیمت‌های ثبت‌شده · ") +
        "زمان ثبت: " + dateLabel(state.prices.observed_at);
      renderTickets();
      renderHomePrice();
    } catch {
      if (sequence !== state.pricesRequest) return;
      if (state.prices) {
        state.prices.stale = true;
        $("price-status").classList.add("warning");
        $("price-status").textContent = "تازه‌سازی ناموفق؛ آخرین دادهٔ ذخیره‌شده از " +
          dateLabel(state.prices.observed_at) + "؛ پیش از رزرو قیمت را تأیید کنید.";
        renderTickets(); return;
      }
      state.prices = null;
      $("price-status").classList.add("warning");
      $("price-status").textContent = "داده قیمت در حال حاضر در دسترس نیست.";
      fill("ticket-results",empty("قیمت قابل نمایش نیست","بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."));
      fill("home-price-preview",el("p",{className:"muted",text:"قیمت‌های جدید هنوز در دسترس نیستند."}));
      $("ticket-count").textContent = "۰";
    }
  }
  function selectRoute(origin, destination) {
    state.origin = origin;
    $("origin-select").value = origin;
    $("ticket-search").value = destination || "";
    go("tickets");
    renderTickets();
  }
  function renderHomePrice() {
    const routes = state.prices?.routes || [];
    const quotes = rankTicketFares(routes);
    if (!quotes.length) {
      fill("home-price-preview",el("p",{className:"muted",text:"هنوز قیمتی ثبت نشده است."}));
      return;
    }
    const container = el("div");
    quotes.slice(0,3).forEach((fare,index) => {
      const btn = el("button",{type:"button",className:"preview-row",onClick:()=>selectRoute(fare.origin,fare.name)},
        el("span",{className:"preview-index",text:fmt(index+1)}),
        el("span",{className:"preview-route"},el("strong",{text:"از "+fare.origin+" به "+fare.name}),
          el("small",{text:"قیمت ثبت‌شده"})),
        el("strong",{className:"preview-price",text:money(fare.price_toman)}),
        icon("arrow")
      );
      container.append(btn);
    });
    fill("home-price-preview",container);
  }
  function percentChip(value) {
    if (typeof value !== "number" || !Number.isFinite(value))
      return el("span",{className:"fare-chip flat",text:"بدون مقایسه"});
    if (value < 0) return el("span",{className:"fare-chip down",text:"↓ "+fmt(Math.abs(value))+"٪"});
    if (value > 0) return el("span",{className:"fare-chip up",text:"↑ "+fmt(value)+"٪"});
    return el("span",{className:"fare-chip flat",text:"بدون تغییر"});
  }
  function renderTickets() {
    const term = $("ticket-search").value.trim().toLocaleLowerCase("fa-IR");
    const fares = rankTicketFares(state.prices?.routes, {
      mode: state.ticketSort, origin: state.origin, search: term,
    });
    for (const mode of ["cheap", "drops"]) {
      const tab = $("ticket-sort-" + mode), active = state.ticketSort === mode;
      tab.setAttribute("aria-selected", String(active));
      tab.classList.toggle("active", active);
    }
    $("ticket-count").textContent = fmt(fares.length);
    if (!fares.length) {
      fill("ticket-results",empty(state.ticketSort === "drops"
        ? "کاهش قیمت معتبری در داده‌های ثبت‌شده یافت نشد" : "مسیری پیدا نشد",
        "حداقل سه نمونه تاریخی برای مقایسه لازم است؛ مبدأ یا جست‌وجو را بررسی کنید."));
      return;
    }
    fill("ticket-results",fares.map(fare => {
      const avg = Number.isFinite(fare.average_price_toman) && fare.average_price_toman > 0 && fare.average_sample_count > 0
        ? "میانگین ثبت‌شده: "+money(fare.average_price_toman)
        : "میانگین در دسترس نیست";
      return el("article",{className:"fare-card"},
        el("div",{className:"fare-main"},
          el("div",{className:"fare-route"},
            el("strong",{text:"از "+state.origin+" به "+fare.name}),
            el("small",{text:avg}),
            el("small",{text:"زمان ثبت: "+dateLabel(state.prices.observed_at)})
          ),
          el("div",{className:"fare-price"},fmt(fare.price_toman)," ",el("small",{text:"تومان"}))
        ),
        el("div",{className:"fare-lower"},
          validDropPercent(fare) === null ? percentChip(null) : el("span",{className:"fare-chip down",
            text:"↓ "+new Intl.NumberFormat("fa-IR",{minimumFractionDigits:1,maximumFractionDigits:1})
              .format(validDropPercent(fare))+"٪ نسبت به میانگین"}),
          el("div",{className:"fare-actions"},
            el("button",{type:"button",className:"tiny-button",onClick:()=>link("support","https://t.me/Advertio_support")},"رزرو"),
            el("button",{type:"button",className:"tiny-button",onClick:()=>openHistory(state.origin,fare.name,fare)},"نمودار قیمت"),
            el("button",{type:"button",className:"tiny-button filled",onClick:()=>priceDialog(state.origin,fare)},"زنگوله قیمت")
          )
        )
      );
    }));
  }
  async function openHistory(origin,destination,fare=null) {
    const seq=++state.historyRequest;
    modal("نمودار قیمت ثبت‌شده",el("p",{text:"در حال دریافت تاریخچه…"}),[act("بستن",closeModal)]);
    try {
      const raw=await request("/api/v1/tickets/history?"+new URLSearchParams({origin,destination}));
      if(seq!==state.historyRequest)return;
      const h=parseHistory(raw);
      if(h.origin!==origin||h.destination!==destination)throw Error("مسیر پاسخ معتبر نیست");
      const details=el("p",{className:"dialog-text",text:"برای دیدن قیمت روز، نقطه یا ردیف آن را انتخاب کنید."});
      const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
      svg.setAttribute("viewBox","0 0 320 145");svg.setAttribute("role","img");
      svg.setAttribute("aria-label","کمترین قیمت ثبت‌شدهٔ هر روز در ۲۱ روز UTC");
      svg.style.width="100%";
      function shape(name,attrs){const n=document.createElementNS(svg.namespaceURI,name);
        for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));svg.append(n);return n;}
      for(const [a,b]of h.segments)shape("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:"#159979","stroke-width":3});
      function pointText(p){return p.day+" UTC: "+money(p.price_toman)+" · "+fmt(p.sample_count)+" ثبت";}
      for(const p of h.points){
        const dot=shape("circle",{cx:p.x,cy:p.y,r:5,fill:"#159979",tabindex:0,role:"button","aria-label":pointText(p)});
        dot.addEventListener("click",()=>{details.textContent=pointText(p);});
        dot.addEventListener("keydown",e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details.textContent=pointText(p);}});
      }
      const body=el("div",{},el("h3",{text:"از "+origin+" به "+destination}),
        el("p",{text:"کمترین قیمت واقعی هر روز · تومان · ۲۱ روز UTC · "+new Date(h.start*86400000).toISOString().slice(0,10)+" تا "+h.as_of}),
        h.points.length?svg:null,
        el("p",{className:"status-strip"+(h.stale?" warning":""),text:h.stale?"تاریخچه قدیمی یا فاقد مشاهدهٔ تازه است؛ قیمت رزرو را تأیید کنید.":"قیمت‌های ثبت‌شده؛ موجودی و رزرو تضمین‌شده نیست."}),
        el("p",{text:h.points.length?"کمینه: "+money(h.min)+" · بیشینه: "+money(h.max):"برای این مسیر تاریخچه‌ای ثبت نشده است."}),
        el("p",{text:"روزهای دارای داده: "+fmt(h.points.length)+" از ۲۱ · تعداد مشاهدات: "+fmt(h.samples)}),
        el("p",{text:"زمان آخرین مشاهده: "+dateLabel(h.observed_at)}),
        el("p",{text:h.points.length===1?"برای تشخیص روند داده کافی نیست.":"روزهای بدون ثبت، نقطه یا خط تخمینی ندارند."}),details,
        ...h.points.map(p=>el("button",{type:"button",className:"preview-row",onClick:()=>{details.textContent=pointText(p);}},pointText(p))));
      modal("نمودار قیمت ثبت‌شده",body,[act("تغییر مسیر",()=>historyRoutes()),
        act("رزرو / هماهنگی",()=>link("support","https://t.me/Advertio_support")),
        ...(fare?[act("زنگوله قیمت",()=>priceDialog(origin,fare))]:[]),act("بستن",closeModal,"secondary-cta")]);
    }catch{
      if(seq!==state.historyRequest)return;
      modal("تاریخچه در دسترس نیست",el("p",{text:"دریافت تاریخچه ناموفق بود؛ دوباره تلاش کنید."}),
        [act("تلاش دوباره",()=>openHistory(origin,destination,fare)),act("بستن",closeModal,"secondary-cta")]);
    }
  }
  async function historyRoutes(offset=0) {
    const seq=++state.historyRequest;
    modal("مسیرهای دارای تاریخچه",el("p",{text:"در حال دریافت مسیرها…"}),[act("بستن",closeModal)]);
    try {
      const data=await request("/api/v1/tickets/history/routes?offset="+offset);
      if(seq!==state.historyRequest)return;
      const rows=Array.isArray(data.routes)?data.routes:[];
      const body=el("div",{},...rows.map(r=>el("button",{type:"button",className:"preview-row",
        onClick:()=>openHistory(r.origin,r.destination)},"از "+r.origin+" به "+r.destination)));
      if(!rows.length)body.append(el("p",{text:"هنوز مسیری با تاریخچه ثبت نشده است."}));
      modal("مسیرهای دارای تاریخچه",body,[...(offset?[act("قبلی",()=>historyRoutes(Math.max(0,offset-100)))]:[]),
        ...(Number.isInteger(data.next_offset)?[act("بعدی",()=>historyRoutes(data.next_offset))]:[]),act("بستن",closeModal,"secondary-cta")]);
    }catch{if(seq===state.historyRequest)modal("مسیرها در دسترس نیست",el("p",{text:"دریافت مسیرها ناموفق بود."}),
      [act("تلاش دوباره",()=>historyRoutes(offset)),act("بستن",closeModal,"secondary-cta")]);}
  }
  function priceDialog(origin, fare) {
    if (state.prices?.stale) {
      toast("قیمت‌ها قدیمی هستند؛ لطفاً بعد از بروزرسانی دوباره تلاش کنید.");
      return;
    }
    const percent = el("select",{className:"dialog-select","aria-label":"درصد کاهش قیمت"},
      ...Array.from({length:10},(_,i)=> {
        const val=(i+1)*5;
        return el("option",{value:String(val),text:fmt(val)+" درصد"});
      })
    );
    percent.value="10";
    const body = el("div",{},
      el("p",{className:"dialog-text",text:"مسیر "+origin+" به "+fare.name+" · قیمت فعلی "+money(fare.price_toman)}),
      el("label",{className:"dialog-text",text:"درصد افت نسبت به میانگین قیمت ثبت‌شده"}),
      percent,
      el("p",{className:"footnote",text:"هنگامی که قیمت از میانگین ثبت‌شده به اندازه درصد انتخابی پایین‌تر بیاید، ربات تلگرام اعلان می‌فرستد. اگر داده کافی موجود نباشد، هشدار منتظر می‌ماند."})
    );
    let submitting=false;
    modal("ثبت زنگوله قیمت",body,[
      act("ثبت و فعال‌سازی هشدار",async () => {
        if (submitting) return;
        submitting=true;
        try {
          await request("/api/mini/alerts/prices",{method:"POST",body:{
            origin,destination:fare.name,kind:"percent",
            threshold_percent:Number(percent.value),
          }});
          closeModal(); toast("زنگوله قیمت فعال شد."); state.alerts=null;
        } catch (e) {
          submitting=false;
          toast(e.message);
        }
      }),
      act("انصراف",closeModal,"secondary-cta")
    ]);
  }

  function populatePassport() {
    const select = $("passport-select");
    const countries = state.bootstrap?.countries || [];
    select.replaceChildren(...countries.map(country =>
      el("option",{value:country.code,text:country.name+" ("+country.code+")"})
    ));
    if (!countries.length) {
      select.append(el("option",{value:"IR",text:"ایران (IR)"}));
    }
    state.passport = state.bootstrap?.passport || "IR";
    if (![...select.options].some(x => x.value === state.passport)) state.passport = "IR";
    select.value = state.passport;
  }
  function populatePassportOptions(countries) {
    const matches=filterCountries(countries,$("passport-search").value);
    const current=countries.find(c=>c.code===state.passport);
    if(current&&!matches.some(c=>c.code===current.code))matches.unshift(current);
    $("passport-select").replaceChildren(...matches.map(c=>el("option",{value:c.code,text:c.name+" ("+c.code+")"})));
    $("passport-select").value=state.passport;
  }
  const snapshotReader=createVisaSnapshotReader();
  async function loadVisa() {
    const id=++state.visaRequest;
    fill("visa-results",el("div",{className:"panel muted",text:"در حال دریافت اطلاعات ویزا…"}));
    try {
      const data = state.visaMode === "snapshot" ? await snapshotReader.get(state.passport) :
        await request("/api/mini/visa?passport="+encodeURIComponent(state.passport));
      if (state.visaRequest !== id) return;
      if (state.visaMode === "snapshot") {
        state.snapshot=data;
        populatePassportOptions(data.passportCodes.map(code=>({code,name:persianCountry(code)})));
      }
      if (state.visaRequest !== id) return;
      state.visa=data;
      renderVisa();
    } catch (error) {
      if (state.visaRequest !== id) return;
      state.visa=null;
      fill("visa-results",empty("اطلاعات ویزا در دسترس نیست",error.message));
      $("visa-summary").textContent="پایگاه اطلاعات ویزا در حال آماده‌سازی است.";
    }
  }
  function renderVisa() {
    const term = $("visa-search").value.trim().toLocaleLowerCase("fa-IR");
    fill("visa-popular",term ? [] : POPULAR_VISA.filter(code=>state.visa?.rules?.some(r=>r.destination===code)).map(code=>act(persianCountry(code),()=>visaDialog(code),"tiny-button")));
    const all = (state.visa?.rules || []).map(rule => ({
      ...rule, country_name:persianCountry(rule.destination,rule.country_name)
    }));
    const items=all.filter(x => x.country_name.toLocaleLowerCase("fa-IR").includes(term)
      || x.destination.toLocaleLowerCase().includes(term));
    $("visa-summary").textContent=fmt(all.length)+" مقصد برای گذرنامه "+
      (state.bootstrap?.countries?.find(x=>x.code===state.passport)?.name || state.passport);
    $("visa-source-note").textContent=state.visaMode === "snapshot" && state.snapshot
      ? "نسخهٔ همراه اندروید؛ تاریخ مجموعه: "+(state.snapshot.sourceDataModifiedOn||"نامشخص")+" · "+state.snapshot.attribution+
        (state.snapshot.cached ? " · نسخهٔ ذخیره‌شده؛ دریافت داده تازه ممکن نشد." : " · این مجموعه اطلاعات زنده نیست.")
      : "دادهٔ سرویس آنلاین؛ تاریخ بررسی هر منبع در جزئیات نمایش داده می‌شود.";
    if (!items.length) {
      fill("visa-results",empty("مقصدی پیدا نشد","نام یا کد کشور را بررسی کنید."));
      return;
    }
    fill("visa-results",items.map(rule => {
      const [title,tone]=visaStatus(rule.status);
      return el("button",{type:"button",className:"visa-card",
        onClick:()=>visaDialog(rule.destination)},
        el("div",{className:"visa-card-info"},
          el("strong",{text:rule.country_name}),
          el("small",{text:rule.destination+" · "+(rule.stay_days ? fmt(rule.stay_days)+" روز اقامت" : "جزئیات شرایط ورود")})
        ),
        el("span",{className:"visa-tag "+tone,text:title}),icon("arrow")
      );
    }));
  }
  async function visaDialog(destination) {
    const detailRequest=++state.visaDetailRequest;
    const passport=state.passport;
    modal("شرایط ورود",el("p",{className:"dialog-text",text:"در حال دریافت جزئیات…"}),[]);
    try {
      const data = state.visaMode === "snapshot"
        ? state.snapshot?.rules.find(r=>r.destination===destination)
        : await request("/api/mini/visa/rule?passport="+encodeURIComponent(passport)+"&destination="+encodeURIComponent(destination));
      if(detailRequest!==state.visaDetailRequest)return;
      if (!data) throw new Error("اطلاعات این مقصد در دسترس نیست.");
      const [status,tone]=visaStatus(data.status);
      const country=state.bootstrap?.countries?.find(x=>x.code===destination)?.name ||
        persianCountry(destination,data.country_name);
      const body=el("div",{},
        el("p",{className:"dialog-text",text:country+" · گذرنامه "+passport}),
        el("span",{className:"visa-tag "+tone,text:status}),
        detail("مدت اقامت",data.stay_days?fmt(data.stay_days)+" روز":"براساس نوع ویزا"),
        detail("آخرین بررسی منبع",data.verified_on || "ثبت نشده"),
        detail("به‌روزرسانی فایل مقصد",data.destination_updated_on || "ثبت نشده"),
        detail("سطح منبع",({official:"رسمی",secondary:"ثانویه",aggregated:"تجمیعی",row:"مختص پاسپورت",passport:"مختص پاسپورت",shared:"سیاست کلی مقصد",default:"سیاست کلی مقصد",destination:"سیاست کلی مقصد",policy:"سیاست کلی مقصد"})[data.source_level] || "نامشخص"),
        ...(data.notes?[el("h3",{className:"page-subhead",text:"توضیحات"}),el("p",{className:"detail-notes",text:data.notes})]:[]),
        el("p",{className:"footnote",text:"برای تصمیم‌گیری نهایی، منابع رسمی کشور مقصد را کنترل کنید."})
      );
      const actions=[
        act("دنبال‌کردن تغییرات این ویزا",async()=>{
          try {
            await request("/api/mini/alerts/visa",{method:"POST",
              body:{passport,destination}});
            closeModal();state.alerts=null;toast("هشدار تغییرات ویزا فعال شد.");
          } catch(e) { toast(e.message); }
        })
      ];
      if (data.source_url) actions.push(act("مشاهده منبع",()=>openUrl(data.source_url),"secondary-cta"));
      actions.push(act("بستن",closeModal,"secondary-cta"));
      if ($("mini-dialog").open) modal("شرایط ویزای "+country,body,actions);
    } catch (e) {
      if(detailRequest!==state.visaDetailRequest)return;
      if ($("mini-dialog").open)
        modal("اطلاعات موجود نیست",el("p",{className:"dialog-text",text:e.message}),
          [act("بستن",closeModal,"secondary-cta")]);
    }
  }
  function detail(label,value) {
    return el("div",{className:"detail-line"},el("span",{text:label}),el("strong",{text:value}));
  }
  async function loadAlerts() {
    fill("price-alert-list",el("div",{className:"panel muted",text:"در حال دریافت هشدارها…"}));
    fill("visa-alert-list",el("div",{className:"panel muted",text:"در حال دریافت هشدارها…"}));
    try {
      state.alerts=await request("/api/mini/alerts");
      renderAlerts();
    } catch(e) {
      fill("price-alert-list",empty("هشدارها بارگذاری نشدند",e.message));
      fill("visa-alert-list",empty("لطفاً دوباره تلاش کنید","اتصال به سرور را بررسی کنید."));
    }
  }
  function renderAlerts() {
    const alerts=state.alerts || {prices:[],visa:[]};
    $("alert-price-count").textContent=fmt(alerts.prices.length);
    $("alert-visa-count").textContent=fmt(alerts.visa.length);
    fill("price-alert-list",alerts.prices.length
      ? alerts.prices.map(x=>alertCard("prices",x))
      : [empty("زنگوله قیمتی ندارید","از صفحه بلیت‌ها مسیر موردنظر را انتخاب کنید.")]);
    fill("visa-alert-list",alerts.visa.length
      ? alerts.visa.map(x=>alertCard("visa",x))
      : [empty("هشدار ویزا ندارید","در بخش ویزا، مقصد موردنظر را دنبال کنید.")]);
  }
  function alertCard(type,data) {
    const isPrice=type==="prices";
    const enabled=isPrice ? data.status === "active" : data.active;
    const label=isPrice ? "از "+data.origin+" به "+data.destination :
      "گذرنامه "+data.passport+" · مقصد "+data.destination;
    const desc=isPrice
      ? (data.threshold_type === "percent"
        ? "کاهش حداقل "+fmt(data.target_percent)+" درصد"
        : "سقف قیمت "+money(data.target_price))
      : "اعلان تغییرات مهم قوانین ویزا";
    return el("article",{className:"alert-card"},
      el("div",{className:"alert-header"},
        el("div",{},el("strong",{text:label}),el("p",{text:desc})),
        el("span",{className:"alert-state"+(enabled?"":" paused"),text:enabled?"فعال":"متوقف"})
      ),
      el("div",{className:"alert-controls"},
        el("button",{type:"button",className:"tiny-button",
          onClick:()=>updateAlert(type,data,!enabled)},enabled?"توقف موقت":"فعال‌سازی"),
        el("button",{type:"button",className:"tiny-button danger",
          onClick:()=>confirmRemove(type,data)},"حذف")
      )
    );
  }
  async function updateAlert(type,data,enable) {
    try {
      await request("/api/mini/alerts/"+type+"/"+data.id,{method:"PATCH",
        body:type==="prices"?{status:enable?"active":"paused"}:{active:enable}});
      toast(enable?"هشدار فعال شد.":"هشدار موقتاً متوقف شد.");
      await loadAlerts();
    } catch(e) { toast(e.message); }
  }
  function confirmRemove(type,data) {
    modal("حذف هشدار",el("p",{className:"dialog-text",text:"این هشدار از حساب شما حذف می‌شود. ادامه می‌دهید؟"}),[
      act("بله، حذف کن",async()=>{
        try {
          await request("/api/mini/alerts/"+type+"/"+data.id,{method:"DELETE"});
          closeModal();toast("هشدار حذف شد.");await loadAlerts();
        } catch(e) { toast(e.message); }
      }),
      act("انصراف",closeModal,"secondary-cta"),
    ]);
  }
  async function loadUseful() {
    if (state.useful) { renderUseful(); return; }
    try {
      state.useful=await request("/api/mini/useful");
      renderUseful();
    } catch(e) { fill("useful-results",empty("منابع فعلاً در دسترس نیستند",e.message)); }
  }
  function renderUseful() {
    fill("useful-results",(state.useful?.categories || []).map((category,index)=>
      el("details",{className:"useful-group", ...(index===0?{open:""}:{})},
        el("summary",{},category.title,icon("arrow")),
        ...category.links.map(x=>el("a",{className:"useful-link",href:x.url,
          target:"_blank",rel:"noopener noreferrer",onClick:event=>{
            event.preventDefault();openUrl(x.url);
          }},el("span",{text:x.title}),icon("external")))
      )));
  }

  // WEB-002: website inventory, names, categories, images and ordering are
  // always taken from the shared GitHub JSON, never bundled with the Mini App.
  const WEBSITE_TTL_MS = 15 * 60 * 1000;
  function websiteSkeletons() {
    return Array.from({length:3},()=>
      el("div",{className:"website-skeleton","aria-hidden":"true"},
        el("span",{className:"website-skeleton-image"}),
        el("span",{className:"website-skeleton-copy"},
          el("span",{className:"website-skeleton-line"}),
          el("span",{className:"website-skeleton-line short"}))));
  }
  function websiteFailure(message) {
    $("website-count").textContent="—";
    fill("website-status",el("div",{className:"website-warning",text:message}));
    fill("website-results",el("div",{className:"empty-list"},
      el("strong",{text:"فهرست وب‌سایت‌ها در دسترس نیست"}),
      el("p",{text:"لطفاً اتصال اینترنت را بررسی کنید و دوباره تلاش کنید."}),
      el("button",{type:"button",className:"secondary-cta website-retry",
        onClick:()=>loadWebsites(true)},"تلاش دوباره",icon("refresh"))));
  }
  async function loadWebsites(force=false) {
    if (!force && state.websites && Date.now()-state.websitesFetchedAt < WEBSITE_TTL_MS) {
      renderWebsites();
      return;
    }
    if (state.websitesRequest) return state.websitesRequest;
    fill("website-status",el("p",{className:"muted",text:"در حال دریافت فهرست وب‌سایت‌ها…"}));
    fill("website-results",websiteSkeletons());
    const operation=(async()=>{
      try {
        // No initData or authentication headers ever leave this WebView.
        const catalog=await fetchCatalog(fetch,9000,force?"reload":"default");
        state.websites=catalog;
        state.websitesFetchedAt=Date.now();
        const select=$("website-category"), previous=select.value;
        select.replaceChildren(el("option",{value:"all",text:"همه دسته‌بندی‌ها"}),
          ...catalog.categories.map(category=>
            el("option",{value:category.id,text:category.name})));
        select.value=catalog.categories.some(item=>item.id===previous) ? previous : "all";
        renderWebsites();
      } catch(error) {
        if(state.websites) {
          renderWebsites();
          fill("website-status",el("p",{className:"website-warning",text:"داده تازه دریافت نشد؛ فهرست همین نشست نمایش داده می‌شود. آخرین دریافت: "+dateLabel(state.websitesFetchedAt)}));
        } else websiteFailure(error?.message || "دریافت اطلاعات با خطا مواجه شد.");
      } finally {
        state.websitesRequest=null;
      }
    })();
    state.websitesRequest=operation;
    return operation;
  }
  function websiteCard(site) {
    const image=el("img",{className:"website-image",src:site.image,
      loading:"lazy",decoding:"async",alt:site.name,
      width:"108",height:"88",referrerpolicy:"no-referrer"});
    image.addEventListener("error",()=>{
      image.replaceWith(el("span",{className:"website-image-fallback",
        text:"تصویر در دسترس نیست"}));
    },{once:true});
    return el("article",{className:"website-card",dataset:{websiteId:site.id}},
      el("div",{className:"website-card-top"},
        el("div",{className:"website-image-wrap"},image),
        el("div",{className:"website-card-detail"},
          el("span",{className:"website-category",text:site.categoryName}),
          el("h3",{text:site.name}),
          el("p",{text:site.description}))),
      el("button",{type:"button",className:"website-open",
        onClick:()=>{
          if (site.id === "iran-fids") { go("fids"); return; }
          const url=approvedExternalUrl(site.url);
          if (url) openUrl(url);
          else toast("نشانی این وب‌سایت معتبر نیست.");
        }},site.id === "iran-fids" ? "مشاهده داخل مینی‌اپ" : "مشاهده وب‌سایت",
        icon(site.id === "iran-fids" ? "arrow" : "external")));
  }
  function renderWebsites() {
    if (!state.websites) return;
    fill("website-status");
    const sites=filterWebsites(state.websites.sites,
      $("website-category").value,$("website-search").value);
    $("website-count").textContent=fmt(sites.length);
    if (!sites.length) {
      fill("website-results",empty("موردی پیدا نشد",
        "عبارت جست‌وجو یا دسته‌بندی را تغییر دهید."));
      return;
    }
    fill("website-results",sites.map(websiteCard));
  }

  // Native Mini App flight board for the already-listed "iran-fids" website card.
  // Requests the same public, read-only Worker endpoint as native Android.
  // Never embeds/opens the upstream FIDS website or displays fabricated rows.
  function fidsDate(value) {
    if (!value) return "اعلام نشده";
    const time=new Date(value);
    if (!Number.isFinite(time.getTime())) return "نامشخص";
    return new Intl.DateTimeFormat("fa-IR",{
      dateStyle:"short",timeStyle:"short",timeZone:"Asia/Tehran"
    }).format(time);
  }
  function renderFids() {
    const board=state.fids;
    if (!board) return;
    const query=$("fids-search").value.trim().toLocaleLowerCase("fa");
    const filtered=board.flights.filter(row=>
      [row.flight_number,row.city,row.airline].some(value=>
        String(value || "").toLocaleLowerCase("fa").includes(query)));
    const sourceOld=!board.source_updated_at ||
      Date.now()-Date.parse(board.source_updated_at)>15*60*1000;
    fill("fids-status",
      el("div",{},
        el("strong",{text:"منبع: سامانه رسمی اطلاعات پرواز فرودگاه‌ها (FIDS)"}),
        el("p",{text:"زمان دریافت توسط سامانه: "+fidsDate(board.fetched_at)}),
        el("p",{text:"آخرین بروزرسانی اعلام‌شده توسط منبع: "+
          fidsDate(board.source_updated_at)}),
        ...(sourceOld?[el("p",{text:
          "تازگی داده‌ها تأیید نشده است؛ وضعیت را پیش از عزیمت بررسی کنید."})]:[])
      ));
    if (!filtered.length) {
      fill("fids-results",empty("پروازی برای نمایش موجود نیست",
        query ? "عبارت جست‌وجو را تغییر دهید." :
          "در پاسخ دریافتی منبع، پروازی ثبت نشده است."));
      return;
    }
    fill("fids-results",filtered.map(row=>
      el("article",{className:"panel"},
        el("strong",{text:row.flight_number+" · "+row.city}),
        el("p",{text:row.airline || "ایرلاین اعلام نشده"}),
        el("p",{text:"زمان برنامه‌ای: "+row.scheduled_time}),
        el("p",{text:"وضعیت: "+(row.status || "اعلام نشده")}),
        ...(row.estimated_time?[el("p",{text:"زمان تخمینی: "+row.estimated_time})]:[]),
        ...(row.actual_time?[el("p",{text:"زمان واقعی: "+row.actual_time})]:[]),
        ...(row.terminal?[el("p",{text:"ترمینال: "+row.terminal})]:[]),
        ...(row.gate?[el("p",{text:"گیت: "+row.gate})]:[])
      )));
  }
  async function loadFids() {
    const airport=$("fids-airport").value;
    const direction=$("fids-direction").value;
    if (!/^[A-Z]{3}$/.test(airport) ||
        !["arrivals","departures"].includes(direction)) return;
    const current=++state.fidsRequest;
    state.fids=null;
    fill("fids-results");
    $("fids-status").textContent="در حال دریافت اطلاعات از منبع رسمی…";
    const abort=new AbortController();
    const timer=setTimeout(()=>abort.abort(),10000);
    try {
      const response=await fetch("/api/v1/iran/fids/"+airport+"/"+direction,{
        method:"GET",cache:"no-store",credentials:"omit",signal:abort.signal,
        headers:{Accept:"application/json"}
      });
      if (!response.ok) throw new Error("اطلاعات معتبر FIDS در دسترس نیست؛ اتصال رسمی یا پوشش فرودگاه ممکن است تأیید نشده باشد.");
      const board=await response.json();
      if (board.airport!==airport || board.direction!==direction ||
          board.source!=="Iran Airports and Air Navigation Company FIDS" ||
          !Array.isArray(board.flights) || board.flights.length>250 ||
          !board.fetched_at) throw new Error("پاسخ اطلاعات پرواز معتبر نیست.");
      if (current!==state.fidsRequest) return;
      state.fids=board;
      renderFids();
    } catch(error) {
      if (current!==state.fidsRequest) return;
      $("fids-status").textContent=error?.message || "دریافت اطلاعات پرواز ناموفق بود.";
      fill("fids-results",empty("داده‌ای برای نمایش وجود ندارد",
        "پاسخ رسمی تأییدشده‌ای دریافت نشده است؛ دوباره تلاش کنید."));
    } finally { clearTimeout(timer); }
  }

  // Keep the Mini App checklist in step with the 12 native Android tasks.
  // Save only non-sensitive completion keys, never Telegram initData or tokens.
  // Per-account browser storage is intentionally device-local, just like Android.
  const checklistGroups = [
    {title:"مدارک و رزروها",hint:"اطمینان از اعتبار مدارک و برنامه سفر",items:[
      ["passport","اعتبار گذرنامه و تاریخ انقضا"],
      ["visa","ویزای مقصد و شرایط ورود"],
      ["tickets","بلیت و شماره رزرو پرواز"],
      ["boarding","مدارک پذیرش و کارت پرواز"],
      ["stay","نشانی و تأییدیه اقامتگاه"],
    ]},
    {title:"سلامت و امنیت",hint:"برای شرایط غیرمنتظره آماده باش",items:[
      ["insurance","بیمه سفر و پوشش درمان"],
      ["essentials","داروهای شخصی و نسخه پزشک"],
      ["emergency","شماره‌های ضروری و مدارک پشتیبان"],
    ]},
    {title:"وسایل و هماهنگی‌ها",hint:"جزئیات کوچک، سفر آسوده‌تر",items:[
      ["money","ارز، کارت و هزینه‌های ضروری"],
      ["connectivity","اینترنت و ارتباط در مقصد"],
      ["luggage","وزن، اندازه و قوانین بار"],
      ["transfers","مسیر فرودگاه تا محل اقامت"],
    ]},
  ];
  const checklistKeys = new Set(checklistGroups.flatMap(group => group.items.map(item => item[0])));
  function initChecklist() {
    // SDK initDataUnsafe is only a local storage namespace hint. Authorization
    // remains server-side via the verified, signed Telegram initData.
    const userId = Number(telegram?.initDataUnsafe?.user?.id);
    if (Number.isSafeInteger(userId) && userId > 0) {
      state.checklistKey = "flightiran:checklist:v1:" + String(userId);
      try {
        const stored = localStorage.getItem(state.checklistKey);
        const values = stored === null ? [] : JSON.parse(stored);
        if (Array.isArray(values)) {
          state.checklist = new Set(values.filter(key => checklistKeys.has(key)));
          state.checklistPersistent = true;
        }
      } catch { state.checklistPersistent = false; }
    }
    renderChecklist();
  }
  function saveChecklist() {
    if (!state.checklistKey) return false;
    try {
      localStorage.setItem(state.checklistKey, JSON.stringify([...state.checklist]));
      state.checklistPersistent = true;
      return true;
    } catch {
      state.checklistPersistent = false;
      return false;
    }
  }
  function updateChecklistProgress() {
    const completed = state.checklist.size;
    const total = checklistKeys.size;
    const percentage = Math.round(100 * completed / total);
    $("checklist-percent").textContent = fmt(percentage) + "٪";
    $("checklist-count").textContent = fmt(completed) + " مورد از " + fmt(total) + " انجام شده";
    $("checklist-progress").value = completed;
    $("checklist-remaining").textContent = completed === total
      ? "همه کارها انجام شده؛ سفرت به‌خیر!"
      : fmt(total - completed) + " کار تا پایان آماده‌سازی";
    $("checklist-storage-note").textContent = state.checklistPersistent
      ? "انتخاب‌ها روی همین دستگاه و برای حساب تلگرام شما ذخیره می‌شوند؛ با چک‌لیست اپ اندروید همگام نیستند."
      : "ذخیره محلی در این مرورگر در دسترس نیست. تیک‌ها ممکن است پس از بستن مینی‌اپ حفظ نشوند.";
  }
  function renderChecklist() {
    fill("checklist-groups", checklistGroups.map(group =>
      el("section",{className:"checklist-group"},
        el("h2",{text:group.title}),
        el("p",{text:group.hint}),
        ...group.items.map(([key,title]) => {
          const check = el("input",{
            type:"checkbox",name:"travel-"+key,"aria-label":title,
          });
          check.checked = state.checklist.has(key);
          check.addEventListener("change", () => {
            if (check.checked) state.checklist.add(key);
            else state.checklist.delete(key);
            if (!saveChecklist()) toast("ذخیره انتخاب‌ها در این دستگاه در دسترس نیست.");
            updateChecklistProgress();
          });
          return el("label",{className:"checklist-item"},check,el("span",{text:title}));
        })
      )
    ));
    updateChecklistProgress();
  }
  function confirmChecklistReset() {
    modal("پاک‌کردن چک‌لیست",el("p",{className:"dialog-text",text:"تمام انتخاب‌های شما پاک شوند؟"}),[
      act("پاک شود",()=>{
        state.checklist.clear();
        const saved = saveChecklist();
        closeModal();
        renderChecklist();
        if (saved) toast("چک‌لیست پاک شد.");
        else toast("چک‌لیست فعلی پاک شد، اما ذخیره محلی در دسترس نیست.");
      }),
      act("انصراف",closeModal,"secondary-cta"),
    ]);
  }

  function showStartup(message) {
    $("startup-message").textContent=message;
    $("startup").hidden=false;
  }
  async function initialize() {
    if (!telegram?.initData) {
      showStartup("برای استفاده امن از دستیار سفر، از دکمه «مینی‌اپ» داخل ربات تلگرام وارد شوید.");
      return;
    }
    state.initData=telegram.initData;
    try {
      telegram.ready();
      telegram.expand();
      telegram.BackButton?.onClick?.(guideBack);
    } catch { /* Telegram webview version without optional methods */ }
    try {
      state.bootstrap=await request("/api/mini/bootstrap");
      $("user-name").textContent=state.bootstrap.user.first_name || "مسافر";
      populatePassport();
      initChecklist();
      await Promise.all([loadPrices(),loadVisa()]);
      const entry=new URLSearchParams(window.location.search);
      if(entry.get('screen')==='experiences'){go('experiences');if(/^\d{1,12}$/.test(entry.get('review')||''))experiences.openReview(Number(entry.get('review')));else experiences.open(entry.get('target')||'');}
    } catch(e) {
      showStartup(e.message);
    }
  }
  document.addEventListener("click",event=>{
    const button=event.target.closest("[data-go],[data-link]");
    if (!button) return;
    if (button.dataset.go) go(button.dataset.go);
    else if(button.dataset.link) link(button.dataset.link);
  });
  $("refresh-button").addEventListener("click",async()=>{
    await Promise.all([loadPrices(),loadVisa()]);
    if (guides[state.active]) await guides[state.active].load(true);
    if (state.active === "alerts") await loadAlerts();
    if (state.active === "useful") { state.useful=null; await loadUseful(); }
    if (state.active === "websites") await loadWebsites(true);
    if (state.active === "fids") await loadFids();
    toast("اطلاعات دریافت شد.");
  });
  $("origin-select").addEventListener("change",event=>{
    state.origin=event.target.value; renderTickets();
  });
  $("ticket-search").addEventListener("input",renderTickets);
  for (const mode of ["cheap", "drops"]) {
    $("ticket-sort-"+mode).addEventListener("click", () => {
      state.ticketSort = mode; renderTickets();
    });
  }
  $("ticket-refresh").addEventListener("click", loadPrices);
  $("ticket-history-routes").addEventListener("click", ()=>historyRoutes());
  $("visa-search").addEventListener("input",renderVisa);
  $("website-search").addEventListener("input",renderWebsites);
  $("website-category").addEventListener("change",renderWebsites);
  $("fids-airport").addEventListener("change",loadFids);
  $("fids-direction").addEventListener("change",loadFids);
  $("fids-search").addEventListener("input",renderFids);
  $("fids-reload").addEventListener("click",loadFids);
  $("passport-search").addEventListener("input",()=>populatePassportOptions(state.visaMode === "snapshot" && state.snapshot
    ? state.snapshot.passportCodes.map(code=>({code,name:persianCountry(code)})) : state.bootstrap?.countries||[]));
  $("visa-snapshot").addEventListener("click",()=>{state.visaMode="snapshot";state.visa=null;loadVisa();});
  $("visa-live").addEventListener("click",()=>{state.visaMode="live";state.visa=null;$("passport-search").value="";populatePassport();loadVisa();});
  $("fids-official").addEventListener("click",()=>openUrl(FIDS_HOME));
  $("privacy-checklist").addEventListener("click",()=>go("checklist"));
  $("privacy-clear-visa").addEventListener("click",()=>modal("حذف نسخهٔ ذخیره‌شدهٔ ویزا",el("p",{text:"نسخهٔ عمومی ذخیره‌شده پاک شود؟ هشدارهای سرور و چک‌لیست تغییر نمی‌کنند."}),[
    act("پاک شود",async()=>{try{await snapshotReader.clear();state.snapshot=null;if(state.visaMode==="snapshot"){state.visa=null;fill("visa-results",empty("نسخه پاک شد","برای دریافت دوباره، نسخهٔ همراه اندروید را انتخاب کنید."));}closeModal();toast("نسخهٔ ذخیره‌شده پاک شد.");}catch{toast("پاک‌کردن داده در این مرورگر ممکن نشد.");}}),act("انصراف",closeModal,"secondary-cta")]));
  $("passport-select").addEventListener("change",async event=>{
    const previous=state.passport;
    const selected=event.target.value;
    try {
      if(state.visaMode!=="snapshot")await request("/api/mini/passport",{method:"POST",body:{passport:selected}});
      state.passport=selected;state.visa=null;
      await loadVisa();
    } catch(e) {
      $("passport-select").value=previous;
      toast(e.message);
    }
  });
  $("checklist-reset").addEventListener("click",confirmChecklistReset);
  $("dialog-close").addEventListener("click",closeModal);
  $("dialog-form").addEventListener("submit",event=>event.preventDefault());
  initialize();
})();
