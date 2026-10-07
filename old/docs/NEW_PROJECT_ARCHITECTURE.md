# تحلیل معماری نسخه جدید Flight Iran Bot 24

این سند معماری پیشنهادی برای بازسازی پروژه از صفر است. هدف آن ایجاد یک زیرساخت ماژولار است که توسعه هر قابلیت کمترین اثر را روی قابلیت‌های دیگر داشته باشد.

## نتیجه بررسی ساختار فعلی

نسخه فعلی برای نمونه اولیه مناسب بوده، اما برای توسعه قابلیت‌های جدید آماده نیست:

- راه‌اندازی، منو، Callbackها، زبان، احراز مدیر و پیام‌رسانی در Main.py جمع شده‌اند.
- سرویس‌های خارجی مستقیماً از Handlerها فراخوانی می‌شوند.
- درخواست‌های blocking با requests در توابع async اجرا می‌شوند.
- token، کلید API و شناسه‌های حساس داخل کد هستند.
- CSV جای دیتابیس را گرفته است.
- وضعیت‌های موقت در حافظه هستند و با restart از بین می‌روند.
- قرارداد مشخصی برای پاسخ providerهای خارجی وجود ندارد.
- retry، cache، rate limit، migration، تست و observability ساختارمند نیستند.

نتیجه: نسخه جدید باید Modular Monolith باشد؛ نسخه قبلی فقط archive شود و برای مقایسه رفتار نگه داشته شود.

## اصول معماری

معماری پیشنهادی ترکیبی از Modular Monolith و Hexagonal Architecture است. همه بخش‌ها ابتدا در یک سرویس deploy می‌شوند، اما هر بخش مرز، مدل، repository و service مستقل دارد و بعداً در صورت نیاز می‌تواند به سرویس جدا منتقل شود.

قواعد:

1. Handler فقط ورودی Telegram را می‌گیرد و Use Case را اجرا می‌کند.
2. Use Case منطق کاربردی را اجرا می‌کند و به Telegram یا HTTP وابسته نیست.
3. Domain قوانین کسب‌وکار را نگه می‌دارد.
4. Repository قرارداد ذخیره‌سازی است.
5. Adapter به Telegram، FlightRadar24، TGJU، RapidAPI و تأمین‌کننده بلیط وصل می‌شود.
6. هیچ ماژولی مستقیماً به جدول داخلی ماژول دیگر دسترسی ندارد.
7. ارتباط ماژول‌ها با public interface یا domain event انجام می‌شود.
8. JSON خام provider هرگز به UI یا Domain منتقل نمی‌شود و ابتدا به DTO داخلی تبدیل می‌شود.
9. Jobهای پس‌زمینه idempotent هستند.
10. تنظیمات فقط از environment یا secret manager خوانده می‌شوند.

## ساختار پیشنهادی

~~~text
flightiranbot24/
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── migrations/
├── src/flightiran/
│   ├── main.py
│   ├── bootstrap.py
│   ├── config/
│   ├── shared/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── http/
│   │   ├── cache/
│   │   ├── queue/
│   │   └── telemetry/
│   ├── interfaces/
│   │   ├── telegram/
│   │   └── web/
│   └── modules/
│       ├── identity/
│       ├── localization/
│       ├── flight_tracking/
│       ├── airport/
│       ├── ticket_search/
│       ├── flight_experiences/
│       ├── visa/
│       ├── traveler_rules/
│       ├── cargo_marketplace/
│       ├── currency/
│       ├── travel_assistant/
│       ├── community/
│       ├── admin/
│       └── content/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
└── docs/
~~~

## مرز مسئولیت ماژول‌ها

| ماژول | مسئولیت |
| --- | --- |
| Identity | کاربر، نقش، زبان، رضایت، دسترسی و احراز هویت |
| Localization | ترجمه، قالب پیام، timezone، ارز و تقویم |
| Flight Tracking | جستجو، وضعیت، زمان، گیت، ترمینال و هشدار پرواز |
| Airport | فهرست فرودگاه، ورودی/خروجی، آب‌وهوا، خدمات و نقشه |
| Ticket Search | جستجو، مقایسه، فیلتر، ذخیره مسیر و هشدار قیمت |
| Flight Experiences | تجربه، امتیاز، عکس، moderation و گزارش تخلف |
| Visa | پروفایل ویزا، مدارک، شرایط شخصی و checklist |
| Traveler Rules | گمرک، ارز، دارو، بار، رجیستری، مشمولان و بیمه |
| Cargo Marketplace | آگهی بار، ظرفیت مسافر، matching، تحویل و تسویه |
| Currency | نرخ، تاریخچه، تبدیل، نمودار و هشدار |
| Travel Assistant | پاسخ هوشمند، پیشنهاد سفر و تحلیل مدارک |
| Community | پرسش‌وپاسخ، اعتبار، نشان و referral |
| Admin | داشبورد، محتوا، گزارش، نقش‌ها و audit |

## مسیر استاندارد داده

~~~text
Telegram/Web Request
  → Handler
  → Application Use Case
  → Domain Rules
  → Repository یا Provider Port
  → Adapter خارجی یا دیتابیس
  → DTO داخلی
  → Renderer
  → Telegram/Web Response
~~~

Handler نباید JSON خام provider را parse کند. هر provider باید adapter و contract test جدا داشته باشد.

## قرارداد providerها

برای سرویس‌ها interface مستقل تعریف شود:

~~~python
class FlightProvider(Protocol):
    async def search(self, query: FlightQuery) -> list[Flight]:
        ...

    async def details(self, provider_id: str) -> FlightDetails:
        ...
~~~

پیاده‌سازی‌ها می‌توانند شامل FlightRadarProvider، RapidApiAirportProvider، TgjuCurrencyProvider، TicketWebsiteProvider و FactbookProvider باشند. تغییر API خارجی نباید Use Case یا UI را تغییر دهد.

## مدل داده اصلی

حداقل جدول‌های پیشنهادی:

- users و user_preferences
- roles و audit_logs
- airports، airlines، flights و flight_snapshots
- flight_alerts و flight_alert_events
- ticket_searches، ticket_offers، saved_routes و price_alerts
- flight_experiences و experience_media
- visa_profiles، visa_requirements و visa_sources
- traveler_rules
- cargo_requests، traveler_capacity_offers، cargo_matches و identity_verifications
- currency_quotes، currency_history و travel_budgets
- content_items، provider_requests و job_runs

همه جدول‌ها باید id، created_at و updated_at داشته باشند. داده منبع‌دار باید source_url، source_name، checked_at و valid_until داشته باشد.

## رویدادهای داخلی

- FlightStatusChanged
- FlightDelayed
- FlightGateChanged
- FlightLanded
- FlightCancelled
- BoardingStarted
- TicketPriceChanged
- VisaProfileUpdated
- CargoMatchCreated
- CargoDelivered
- UserVerified
- ExperienceSubmitted
- ContentExpired

برای نمونه Flight Tracking فقط FlightDelayed منتشر می‌کند و Notification تصمیم می‌گیرد چه پیامی بفرستد.

## پردازش پس‌زمینه

این فعالیت‌ها باید با worker و scheduler اجرا شوند، نه داخل درخواست کاربر:

- بررسی هشدارهای پرواز
- بررسی کاهش قیمت بلیط
- به‌روزرسانی ارز و فرودگاه
- منقضی‌کردن قوانین ویزا
- ارسال اعلان
- پردازش فایل و moderation
- گزارش‌گیری و پاک‌سازی cache

هر job باید lock، timeout، retry، backoff، dead-letter و ثبت job_runs داشته باشد.

## جلوگیری از آسیب بین ماژول‌ها

- import از internals ماژول دیگر ممنوع باشد.
- مدل دیتابیس یک ماژول در ماژول دیگر استفاده نشود.
- تغییر دیتابیس فقط با Alembic migration باشد.
- providerها همیشه پشت adapter باشند.
- متن Telegram فقط در renderer ساخته شود.
- feature flag مستقل برای قابلیت‌های پرریسک وجود داشته باشد.
- unit، integration و contract test اجباری باشند.
- event payload اطلاعات حساس نداشته باشد.
- هر ماژول public API مشخص داشته باشد.

## امنیت

- token ربات و API key در secret manager باشند.
- tokenها و کلیدهای قدیمی که در کد قبلی بوده‌اند revoke شوند.
- Telegram WebApp init data سمت سرور validate شود.
- نقش و دسترسی روی همه endpointها بررسی شود.
- مدارک هویتی رمزگذاری و طبق retention policy حذف شوند.
- اطلاعات تماس کاربران بازار بار محدود و audit شود.
- rate limit برای command، inline، هشدار و provider فعال باشد.
- ورودی HTML/Markdown، فایل و شناسه‌ها validate و escape شوند.
- عملیات مالی idempotency key داشته باشد.

## مشاهده‌پذیری

هر درخواست باید request_id و correlation_id داشته باشد. این موارد ثبت شوند:

- ماژول و Use Case
- کاربر به‌صورت ناشناس‌سازی‌شده
- provider و endpoint
- latency و status code
- تعداد retry
- نتیجه و error ID

شاخص‌های ضروری: latency providerها، درصد خطا، موفقیت هشدارها، jobهای شکست‌خورده، پیام‌های ناموفق Telegram، کاربران فعال و نرخ تبدیل.

## مراحل اجرای نسخه جدید

### فاز صفر: پایه

- pyproject، lint، type check و test
- settings، logging و خطای سراسری
- Docker، CI، migration و health check

### فاز یک: هسته

- Telegram، Identity، Localization
- منوی اصلی
- دیتابیس کاربر و audit
- مدیریت خطا

### فاز دو: پرواز

- فرودگاه‌ها
- Flight Tracking
- پروازهای ورودی و خروجی ایران
- جستجوی تاریخی
- هشدار پرواز

### فاز سه: بلیط و ارز

- قرارداد provider
- مقایسه offers
- مسیرهای ذخیره‌شده
- هشدار قیمت
- تاریخچه و تبدیل ارز

### فاز چهار: ویزا و قوانین

- پروفایل ویزا
- ارزیابی شخصی
- پایگاه قوانین مسافر
- مدیریت محتوا و منبع

### فاز پنج: جامعه و بازار

- تجربه پرواز
- اعتبار کاربران
- احراز هویت
- بازار حمل بار
- dispute و settlement

### فاز شش: هوش مصنوعی و Web App

- retrieval منبع‌دار
- پاسخ AI با citation
- تحلیل مدارک
- Web App
- داشبورد مدیریت

## معیار تکمیل هر قابلیت

هر قابلیت باید Use Case، مدل داده، migration، ترجمه سه‌زبانه، timeout، retry، logging، permission، rate limit، تست، metric، audit event، مستندات و مسیر rollback داشته باشد.

## وضعیت مخزن پس از انتقال

نسخه قبلی بدون تغییر در old/ قرار گرفته است:

- old/Main.py
- old/flight_info.py
- old/airportinformation.py
- old/exchange.py
- old/tickets.py
- old/country.py
- old/inlinemode.py
- old/countries.json
- old/languages.json
- old/user_info.csv
- old/README.md
- old/docs/FEATURE_IDEAS.md

ریشه مخزن برای شروع نسخه جدید خالی نگه داشته شده و فقط old/ در آن وجود دارد. هیچ فایل قدیمی حذف نشده است.
