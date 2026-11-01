# Flight Iran Bot 24 — Android privacy notice

**Reviewed for app UI:** 2026-11-01  
**Contact:** https://t.me/Advertio_support  
**Package:** `com.abolfazl260.flightiranbot24`  
**In-app location:** Services → Privacy (native offline screen, no GitHub redirect)

## English

### Local data
The Android app does not create a user account. Travel checklist selections are stored on the device in local app preferences. Non-sensitive travel preferences may be held locally using DataStore; the app also includes a local airport-cache foundation. These are not synced to a user account. Use **Clear my checklist** to erase checklist selections, or clear app data / uninstall to erase the app's local data.

### Network services
The application requests the normal Android **INTERNET** permission. Opening the ticket price list retrieves public ticket data from the project's HTTPS API, currently configured by default at `https://flightiran-public-api.abolfazl260.workers.dev/`. The Iranian flight information screen opens a third-party FIDS website *inside* the application in a WebView. Those servers may receive connection metadata (for example an IP address) when you use those features. The application does not automatically query these services simply by launching its home screen.

The application does not request permissions for contacts, location, camera, microphone, external storage or notifications. No advertising or analytics SDK is integrated into the Android app.

### Telegram and other services
Choosing a Telegram service or support launches Telegram or an external browser. The Android app does not directly collect Telegram account details. The **separate Telegram bot** may process Telegram user IDs, usernames, names, messages, language/service preferences and service activity for functionality and administrator reports. Telegram and third-party websites have their own privacy practices.

### Questions, deletion and limitations
Contact [@Advertio_support](https://t.me/Advertio_support) to ask about bot-side records or request deletion. The operator must verify the requester and applicable retention obligations. This notice does **not** promise immediate or unconditional deletion of server-side bot records.

Flight, travel and visa details must be confirmed with official sources.

## فارسی

### داده‌های محلی
اپ اندروید حساب کاربری ایجاد نمی‌کند. انتخاب‌های چک‌لیست و تنظیمات عمومی سفر روی خود گوشی ذخیره می‌شوند و به حساب آنلاین متصل نیستند. برای پاک‌کردن انتخاب‌های چک‌لیست از دکمه «پاک‌کردن چک‌لیست من» استفاده کنید. پاک‌کردن داده‌های اپ یا حذف برنامه نیز اطلاعات محلی آن را پاک می‌کند.

### ارتباطات اینترنتی
برنامه تنها مجوز عادی اینترنت را درخواست می‌کند. در صفحه قیمت بلیت، داده‌های عمومی قیمت از API امن HTTPS پروژه دریافت می‌شود (نشانی پیش‌فرض فعلی: `https://flightiran-public-api.abolfazl260.workers.dev/`). بخش اطلاعات پرواز ایران، وب‌سایت مربوط را در صفحه داخلی WebView نمایش می‌دهد. سرویس‌های آنلاین ممکن است داده‌های فنی اتصال، از جمله نشانی IP، را دریافت کنند. صرف باز کردن صفحه اصلی اپ باعث فراخوانی خودکار این سرویس‌ها نمی‌شود.

برنامه مجوز مخاطبین، موقعیت مکانی، دوربین، میکروفون، حافظه خارجی یا اعلان‌ها درخواست نمی‌کند. در نسخه اندروید SDK تبلیغاتی یا تحلیل رفتار کاربر تعبیه نشده است.

### خدمات تلگرام
با انتخاب خدمات تلگرام یا پشتیبانی، تلگرام یا مرورگر باز می‌شود. اپ اندروید مستقیماً اطلاعات حساب تلگرام را دریافت نمی‌کند. ربات مستقل تلگرام ممکن است شناسه، نام، نام کاربری، پیام‌ها، زبان، تنظیمات خدمات و فعالیت‌های کاربر را برای ارائه سرویس و گزارش مدیریتی پردازش کند. خدمات شخص ثالث سیاست‌های مستقل دارند.

### درخواست حذف داده و پشتیبانی
برای پرسش درباره داده‌های ربات یا درخواست حذف اطلاعات با [@Advertio_support](https://t.me/Advertio_support) تماس بگیرید. بررسی هویت و الزامات نگهداری اطلاعات پیش از تصمیم‌گیری لازم است. این متن وعده حذف فوری داده‌های سمت سرور نمی‌دهد. اطلاعات سفر و ویزا را با منابع رسمی بررسی کنید.

**Publication gate:** Before store publication, the operator must audit actual bot/server retention, access logging, deletion procedures, third-party service disclosures and app-store Data Safety requirements. The in-app text reflects the implementation as reviewed here; it is not a substitute for legal/privacy approval.
