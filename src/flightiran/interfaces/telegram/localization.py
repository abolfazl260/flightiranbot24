"""Small, explicit localization catalog with English fallback."""

from html import escape

SUPPORTED_LANGUAGES = ("fa", "en", "ar")

MESSAGES = {
    "en": {
        "ticket_choose_origin": "Choose your departure city to view its fares:",
        "ticket_selected_origin": (
            ""Flights from {origin}: select another "
            "city or view the results below."
        ),
        "ticket_expired": "This flight list has expired. Open Tickets again to refresh the cities.",

        "welcome": "Welcome to Flight Iran Bot 24",
        "menu": "Choose a travel service:",
        "language_changed": "Language changed.",
        "unknown_action": "This action is unavailable. Please choose an option from the menu.",
        "language_prompt": "Choose your language:",
        "back": "Back to menu",
        "flights": "Flights",
        "airports": "Airports",
        "tickets": "Tickets",
        "currency": "Currency",
        "visa": "Visa / Passport",
        "rules": "Traveler rules",
        "cargo": "Cargo marketplace",
        "useful": "Useful information",
        "support": "Support",
        "support_open_chat": "Chat with support",
        "settings": "Settings",
    },
    "fa": {
        "ticket_choose_origin": (
            ""✈️ شهر مبدأ را انتخاب کنید تا فقط "
            "قیمت‌های همان شهر نمایش داده شود:"
        ),
        "ticket_selected_origin": "✈️ قیمت‌های پرواز از {origin} در ادامه نمایش داده می‌شود.",
        "ticket_expired": (
            ""فهرست مبدأها منقضی شده است. برای دریافت "
            "فهرست جدید دوباره بلیط را انتخاب کنید."
        ),

        "welcome": "به ربات پرواز ایران ۲۴ خوش آمدید",
        "menu": "یک خدمت سفر را انتخاب کنید:",
        "language_changed": "زبان تغییر کرد.",
        "unknown_action": "این گزینه در دسترس نیست. یکی از گزینه‌های منو را انتخاب کنید.",
        "language_prompt": "زبان خود را انتخاب کنید:",
        "back": "بازگشت به منو",
        "flights": "پروازها",
        "airports": "فرودگاه‌ها",
        "tickets": "بلیط",
        "currency": "نرخ ارز",
        "visa": "ویزا / پاسپورت",
        "rules": "قوانین مسافر",
        "cargo": "بازار حمل بار",
        "useful": "اطلاعات کاربردی",
        "support": "پشتیبانی",
        "support_open_chat": "گفتگو با پشتیبانی",
        "settings": "تنظیمات",
    },
    "ar": {
        "ticket_choose_origin": "✈️ اختر مدينة المغادرة لعرض أسعار رحلاتها فقط:",
        "ticket_selected_origin": "✈️ أسعار الرحلات من {origin} معروضة أدناه.",
        "ticket_expired": "انتهت صلاحية قائمة المدن. افتح قسم التذاكر مرة أخرى.",

        "welcome": "مرحباً بكم في روبوت طيران إيران 24",
        "menu": "اختر خدمة سفر:",
        "language_changed": "تم تغيير اللغة.",
        "unknown_action": "هذا الخيار غير متاح. اختر خياراً من القائمة.",
        "language_prompt": "اختر لغتك:",
        "back": "العودة إلى القائمة",
        "flights": "الرحلات",
        "airports": "المطارات",
        "tickets": "التذاكر",
        "currency": "العملة",
        "visa": "التأشيرة / جواز السفر",
        "rules": "قواعد المسافر",
        "cargo": "سوق الشحن",
        "useful": "معلومات مفيدة",
        "support": "الدعم",
        "support_open_chat": "التواصل مع الدعم",
        "settings": "الإعدادات",
    },
}


# Expanded welcome and command help in all supported languages.
MESSAGES["fa"].update({
    "welcome_greeting": "سلام {name}",
    "welcome_title": "Flight Iran Bot 24 | دستیار هوشمند سفر",
    "welcome_intro": "به دستیار خدمات پرواز و سفر خوش آمدید!",
    "welcome_description": (
        "از جست‌وجوی اطلاعات پرواز تا برنامه‌ریزی سفر، خدمات موردنی"
        "ازتان را در یک مکان پیدا کنید."
    ),
    "welcome_services": "خدمات پرواز و سفر",
    "welcome_items": [
        "✈️ اطلاعات پرواز و وضعیت پروازها",
        "🎫 جست‌وجوی بلیط هواپیما",
        "🛂 اطلاعات ویزا و شرایط سفر",
        "🛬 اطلاعات فرودگاه‌ها و مسیرهای پروازی",
        "🔔 هشدارها و اطلاع‌رسانی پرواز",
        "💱 نرخ ارز و اطلاعات کاربردی سفر",
    ],
    "welcome_choose": "برای شروع، یکی از گزینه‌های زیر را انتخاب کنید.",
    "help_title": "راهنمای Flight Iran Bot 24",
    "help_intro": "از منوی زیر سرویس موردنظر را انتخاب کنید یا از دستورات زیر استفاده کنید.",
    "help_commands": "دستورات ربات",
    "help_start": "نمایش صفحه اصلی و خدمات سفر",
    "help_help": "نمایش همین راهنما",
    "help_language": "انتخاب زبان فارسی، انگلیسی یا عربی",
    "help_flight": "جست‌وجوی وضعیت پرواز با شماره پرواز (مثال: /flight TK874)",
    "help_price": "نمایش نرخ ارز؛ در صورت پیکربندی منبع اطلاعات",
    "help_menu": "بخش‌های منوی اصلی",
    "help_menu_body": (
        "✈️ پروازها: راهنمای جست‌وجوی پرواز با شماره\n"
        "🛬 فرودگاه‌ها: فهرست و مشخصات فرودگاه‌ها\n"
        "🎫 بلیط: مشاهده مسیرها و قیمت‌های موجود، در صورت فعال بودن "
        "سرویس\n"
        "💱 نرخ ارز: مشاهده نرخ‌ها در صورت اتصال منبع\n"
        "📚 اطلاعات کاربردی: راهنماهای سفر\n"
        "⚙️ تنظیمات: تغییر زبان\n"
        "🛂 ویزا و قوانین مسافر: بخش‌های نیازمند منبع رسمی\n"
        "📦 حمل بار: ورود مستقیم به کانال @advertio_cargo\n"
        "📩 پشتیبانی: پرسش درباره رزرو، قیمت‌ها و استفاده از ربات"
    ),
    "help_note": (
        "برخی خدمات به فعال بودن سرویس‌دهنده وابسته‌اند. اطلاعات پر"
        "واز، نرخ ارز و شرایط سفر را پیش از تصمیم نهایی با منبع رسم"
        "ی بررسی کنید."
    ),
    "help_back": "برای بازگشت به خدمات از /start استفاده کنید.",
})
MESSAGES["en"].update({
    "welcome_greeting": "Hello {name}",
    "welcome_title": "Flight Iran Bot 24 | Your Smart Travel Assistant",
    "welcome_intro": "Welcome to your flight and travel assistant!",
    "welcome_description": (
        "From flight information to travel planning, find your trav"
        "el essentials in one place."
    ),
    "welcome_services": "Flight & Travel Services",
    "welcome_items": [
        "✈️ Flight information and status",
        "🎫 Search airline tickets",
        "🛂 Visa and travel requirements",
        "🛬 Airports and flight routes",
        "🔔 Flight alerts and notifications",
        "💱 Exchange rates and useful travel information",
    ],
    "welcome_choose": "Choose a service below to get started.",
    "help_title": "Flight Iran Bot 24 Help",
    "help_intro": "Select a service from the menu or use these commands.",
    "help_commands": "Bot commands",
    "help_start": "Show the main menu and travel services",
    "help_help": "Show this help guide",
    "help_language": "Choose Persian, English or Arabic",
    "help_flight": "Search flight status by flight number (example: /flight TK874)",
    "help_price": "Show exchange rates when a data provider is configured",
    "help_menu": "Main menu sections",
    "help_menu_body": (
        "✈️ Flights: how to search by flight number\n"
        "🛬 Airports: browse airports and details\n"
        "🎫 Tickets: available routes and fares when the service is "
        "enabled\n"
        "💱 Currency: rates when a provider is connected\n"
        "📚 Useful information: travel guides\n"
        "⚙️ Settings: change language\n"
        "🛂 Visa and traveler rules: require official sources\n"
        "📦 Cargo marketplace: open the @advertio_cargo channel\n"
        "📩 Support: questions about bookings, prices and using the bot"
    ),
    "help_note": (
        "Some features require an active provider. Verify flight, c"
        "urrency and travel requirements with official sources befo"
        "re making decisions."
    ),
    "help_back": "Use /start to return to the main menu.",
})
MESSAGES["ar"].update({
    "welcome_greeting": "مرحباً {name}",
    "welcome_title": "Flight Iran Bot 24 | مساعد السفر الذكي",
    "welcome_intro": "مرحباً بك في مساعد خدمات الطيران والسفر!",
    "welcome_description": (
        "من معلومات الرحلات إلى التخطيط للسفر، اعثر على خدمات سفرك "
        "في مكان واحد."
    ),
    "welcome_services": "خدمات الطيران والسفر",
    "welcome_items": [
        "✈️ معلومات الرحلات وحالتها",
        "🎫 البحث عن تذاكر الطيران",
        "🛂 التأشيرات ومتطلبات السفر",
        "🛬 المطارات ومسارات الرحلات",
        "🔔 تنبيهات الرحلات والإشعارات",
        "💱 أسعار الصرف ومعلومات السفر المفيدة",
    ],
    "welcome_choose": "اختر إحدى الخدمات أدناه للبدء.",
    "help_title": "دليل Flight Iran Bot 24",
    "help_intro": "اختر خدمة من القائمة أو استخدم الأوامر التالية.",
    "help_commands": "أوامر البوت",
    "help_start": "عرض القائمة الرئيسية وخدمات السفر",
    "help_help": "عرض دليل المساعدة",
    "help_language": "اختيار العربية أو الفارسية أو الإنجليزية",
    "help_flight": "البحث عن حالة الرحلة برقمها (مثال: /flight TK874)",
    "help_price": "عرض أسعار الصرف عند تهيئة مزود البيانات",
    "help_menu": "أقسام القائمة الرئيسية",
    "help_menu_body": (
        "✈️ الرحلات: كيفية البحث برقم الرحلة\n"
        "🛬 المطارات: تصفح المطارات وتفاصيلها\n"
        "🎫 التذاكر: المسارات والأسعار المتاحة عند تفعيل الخدمة\n"
        "💱 العملات: أسعار الصرف عند ربط المزود\n"
        "📚 معلومات مفيدة: أدلة السفر\n"
        "⚙️ الإعدادات: تغيير اللغة\n"
        "🛂 التأشيرات وقواعد المسافرين: تتطلب مصادر رسمية\n"
        "📦 سوق الشحن: فتح قناة @advertio_cargo مباشرة\n"
        "📩 الدعم: أسئلة عن الحجز والأسعار واستخدام البوت"
    ),
    "help_note": (
        "تتطلب بعض الميزات مزود خدمة نشطاً. تحقق من معلومات الرحلات"
        " وأسعار الصرف ومتطلبات السفر من المصادر الرسمية."
    ),
    "help_back": "استخدم /start للعودة إلى القائمة الرئيسية.",
})


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else "en"


def text(language: str | None, key: str) -> str:
    language = normalize_language(language)
    return MESSAGES[language].get(key, MESSAGES["en"].get(key, key))


def safe_text(language: str | None, key: str) -> str:
    return escape(text(language, key))
