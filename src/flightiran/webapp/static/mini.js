/* Telegram Mini App: user input and API responses are rendered as text nodes.
 * No external UI framework, localStorage credentials, or unsafe HTML insertion.
 */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const telegram = window.Telegram && window.Telegram.WebApp;
  const fmt = value => new Intl.NumberFormat("fa-IR").format(value);
  const state = {
    initData: "", bootstrap: null, prices: null, origin: "",
    passport: "IR", visa: null, alerts: null, useful: null, active: "home",
    toastTimer: null, visaRequest: 0,
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
    if (!response.ok) {
      if (response.status === 401) throw new Error("نشست تلگرام معتبر نیست. مینی‌اپ را دوباره از ربات باز کنید.");
      if (response.status === 409) throw new Error("قیمت‌های فعلی نیاز به بروزرسانی دارند. کمی بعد دوباره تلاش کنید.");
      if (response.status === 404) throw new Error("این مورد دیگر در دسترس نیست.");
      if (response.status === 422) throw new Error("اطلاعات واردشده معتبر نیست یا محدودیت هشدارها تکمیل شده است.");
      throw new Error("ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.");
    }
    return data;
  }
  function go(screen) {
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
    if (screen === "alerts") loadAlerts();
    if (screen === "useful") loadUseful();
    if (screen === "visa" && !state.visa) loadVisa();
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
      } else if (telegram?.openLink) telegram.openLink(parsed.href);
      else window.open(parsed.href,"_blank","noopener,noreferrer");
    } catch { toast("لینک معتبر نیست."); }
  }
  function openUrl(url) {
    link(null,url);
  }
  function modal(title, body, actions) {
    $("dialog-title").textContent = title;
    fill("dialog-body",body);
    fill("dialog-actions",el("div",{className:"dialog-actions"},actions));
    const dlg = $("mini-dialog");
    if (!dlg.open) dlg.showModal();
    telegram?.HapticFeedback?.impactOccurred?.("light");
  }
  function closeModal() { if ($("mini-dialog").open) $("mini-dialog").close(); }
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
    $("price-status").textContent = "در حال دریافت قیمت‌ها…";
    try {
      state.prices = await request("/api/v1/tickets/prices");
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
    const quotes = routes.flatMap(route =>
      (route.destinations || []).map(fare => ({...fare,origin:route.origin}))
    ).filter(quote => Number(quote.price_toman) > 0);
    if (!quotes.length) {
      fill("home-price-preview",el("p",{className:"muted",text:"هنوز قیمتی ثبت نشده است."}));
      return;
    }
    quotes.sort((a,b) => a.price_toman - b.price_toman);
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
    const route = state.prices?.routes?.find(r => r.origin === state.origin);
    const fares = (route?.destinations || []).filter(f => f.name.toLocaleLowerCase("fa-IR").includes(term));
    $("ticket-count").textContent = fmt(fares.length);
    if (!fares.length) {
      fill("ticket-results",empty("مسیری پیدا نشد","مبدأ یا عبارت جست‌وجو را تغییر دهید."));
      return;
    }
    fill("ticket-results",fares.map(fare => {
      const avg = fare.average_price_toman && fare.average_sample_count
        ? "میانگین ثبت‌شده: "+money(fare.average_price_toman)
        : "میانگین در دسترس نیست";
      return el("article",{className:"fare-card"},
        el("div",{className:"fare-main"},
          el("div",{className:"fare-route"},
            el("strong",{text:"از "+state.origin+" به "+fare.name}),
            el("small",{text:avg})
          ),
          el("div",{className:"fare-price"},fmt(fare.price_toman)," ",el("small",{text:"تومان"}))
        ),
        el("div",{className:"fare-lower"},
          percentChip(fare.change_percent),
          el("div",{className:"fare-actions"},
            el("button",{type:"button",className:"tiny-button",onClick:()=>link("support","https://t.me/Advertio_support")},"رزرو"),
            el("button",{type:"button",className:"tiny-button filled",onClick:()=>priceDialog(state.origin,fare)},"زنگوله قیمت")
          )
        )
      );
    }));
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
  async function loadVisa() {
    const id=++state.visaRequest;
    fill("visa-results",el("div",{className:"panel muted",text:"در حال دریافت اطلاعات ویزا…"}));
    try {
      const data = await request("/api/mini/visa?passport="+encodeURIComponent(state.passport));
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
    const all = state.visa?.rules || [];
    const items=all.filter(x => x.country_name.toLocaleLowerCase("fa-IR").includes(term)
      || x.destination.toLocaleLowerCase().includes(term));
    $("visa-summary").textContent=fmt(all.length)+" مقصد برای گذرنامه "+
      (state.bootstrap?.countries?.find(x=>x.code===state.passport)?.name || state.passport);
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
    modal("شرایط ورود",el("p",{className:"dialog-text",text:"در حال دریافت جزئیات…"}),[]);
    try {
      const data = await request("/api/mini/visa/rule?passport="+
        encodeURIComponent(state.passport)+"&destination="+encodeURIComponent(destination));
      const [status,tone]=visaStatus(data.status);
      const country=state.bootstrap?.countries?.find(x=>x.code===destination)?.name ||
        data.country_name || destination;
      const body=el("div",{},
        el("p",{className:"dialog-text",text:country+" · گذرنامه "+state.passport}),
        el("span",{className:"visa-tag "+tone,text:status}),
        detail("مدت اقامت",data.stay_days?fmt(data.stay_days)+" روز":"براساس نوع ویزا"),
        detail("آخرین بررسی منبع",data.verified_on || "ثبت نشده"),
        detail("سطح منبع",({official:"رسمی",secondary:"ثانویه",aggregated:"تجمیعی"})[data.source_level] || "نامشخص"),
        ...(data.notes?[el("h3",{className:"page-subhead",text:"توضیحات"}),el("p",{className:"detail-notes",text:data.notes})]:[]),
        el("p",{className:"footnote",text:"برای تصمیم‌گیری نهایی، منابع رسمی کشور مقصد را کنترل کنید."})
      );
      const actions=[
        act("دنبال‌کردن تغییرات این ویزا",async()=>{
          try {
            await request("/api/mini/alerts/visa",{method:"POST",
              body:{passport:state.passport,destination}});
            closeModal();state.alerts=null;toast("هشدار تغییرات ویزا فعال شد.");
          } catch(e) { toast(e.message); }
        })
      ];
      if (data.source_url) actions.push(act("مشاهده منبع",()=>openUrl(data.source_url),"secondary-cta"));
      actions.push(act("بستن",closeModal,"secondary-cta"));
      if ($("mini-dialog").open) modal("شرایط ویزای "+country,body,actions);
    } catch (e) {
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
      telegram.BackButton?.onClick?.(()=>go("home"));
    } catch { /* Telegram webview version without optional methods */ }
    try {
      state.bootstrap=await request("/api/mini/bootstrap");
      $("user-name").textContent=state.bootstrap.user.first_name || "مسافر";
      populatePassport();
      await Promise.all([loadPrices(),loadVisa()]);
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
    if (state.active === "alerts") await loadAlerts();
    if (state.active === "useful") { state.useful=null; await loadUseful(); }
    toast("اطلاعات دریافت شد.");
  });
  $("origin-select").addEventListener("change",event=>{
    state.origin=event.target.value; renderTickets();
  });
  $("ticket-search").addEventListener("input",renderTickets);
  $("visa-search").addEventListener("input",renderVisa);
  $("passport-select").addEventListener("change",async event=>{
    const previous=state.passport;
    const selected=event.target.value;
    try {
      await request("/api/mini/passport",{method:"POST",body:{passport:selected}});
      state.passport=selected;state.visa=null;
      await loadVisa();
    } catch(e) {
      $("passport-select").value=previous;
      toast(e.message);
    }
  });
  $("dialog-close").addEventListener("click",closeModal);
  $("dialog-form").addEventListener("submit",event=>event.preventDefault());
  initialize();
})();
