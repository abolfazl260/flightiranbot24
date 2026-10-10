"""Small, explicit localization catalog with English fallback."""

from html import escape

SUPPORTED_LANGUAGES = ("fa", "en", "ar")

MESSAGES = {
    "en": {
        "ticket_choose_origin": "Choose your departure city to view its fares:",
        "ticket_selected_origin": (
            "Flights from {origin}: select another "
            "city or view the results below."
        ),
        "ticket_expired": "This flight list has expired. Open Tickets again to refresh the cities.",

        "welcome": "Welcome to Flight Iran Bot 24",
        "menu": "Choose a travel service:",
        "language_changed": "Language changed.",
        "unknown_action": "This action is unavailable. Please choose an option from the menu.",
        "language_prompt": "Choose your language:",
        "back": "Back to menu",
        "airports": "Airports",
        "tickets": "Tickets",
        "visa": "Visa / Passport",
        "rules": "Traveler rules",
        "cargo": "Cargo marketplace",
        "useful": "Useful information",
        "support": "Support",
        "support_open_chat": "Chat with support",
        "settings": "Settings",
        "price_alerts": "🔔 Ticket price alerts",
        "admin_reports": "📊 Full bot report",
    },
    "fa": {
        "ticket_choose_origin": (
            "✈️ شهر مبدأ را انتخاب کنید تا فقط "
            "قیمت‌های همان شهر نمایش داده شود:"
        ),
        "ticket_selected_origin": "✈️ قیمت‌های پرواز از {origin} در ادامه نمایش داده می‌شود.",
        "ticket_expired": (
            "فهرست مبدأها منقضی شده است. برای دریافت "
            "فهرست جدید دوباره بلیط را انتخاب کنید."
        ),

        "welcome": "به ربات پرواز ایران ۲۴ خوش آمدید",
        "menu": "یک خدمت سفر را انتخاب کنید:",
        "language_changed": "زبان تغییر کرد.",
        "unknown_action": "این گزینه در دسترس نیست. یکی از گزینه‌های منو را انتخاب کنید.",
        "language_prompt": "زبان خود را انتخاب کنید:",
        "back": "بازگشت به منو",
        "airports": "فرودگاه‌ها",
        "tickets": "بلیط",
        "visa": "ویزا / پاسپورت",
        "rules": "قوانین مسافر",
        "cargo": "بازار حمل بار",
        "useful": "اطلاعات کاربردی",
        "support": "پشتیبانی",
        "support_open_chat": "گفتگو با پشتیبانی",
        "settings": "تنظیمات",
        "price_alerts": "🔔 زنگوله قیمت بلیط",
        "admin_reports": "📊 گزارش کامل ربات",
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
        "airports": "المطارات",
        "tickets": "التذاكر",
        "visa": "التأشيرة / جواز السفر",
        "rules": "قواعد المسافر",
        "cargo": "سوق الشحن",
        "useful": "معلومات مفيدة",
        "support": "الدعم",
        "support_open_chat": "التواصل مع الدعم",
        "settings": "الإعدادات",
        "price_alerts": "🔔 تنبيهات أسعار التذاكر",
        "admin_reports": "📊 التقرير الشامل للبوت",
    },
}


# Expanded welcome and command help in all supported languages.
MESSAGES["fa"].update({
    "welcome_greeting": "سلام {name}",
    "welcome_title": "Flight Iran Bot 24 | دستیار هوشمند سفر",
    "welcome_intro": "به دستیار خدمات پرواز و سفر خوش آمدید!",
    "welcome_description": (
        "از بررسی قیمت بلیط تا برنامه‌ریزی سفر، خدمات موردنیازتان "
        "را در یک مکان پیدا کنید."
    ),
    "welcome_services": "خدمات پرواز و سفر",
    "welcome_items": [
        "🎫 جست‌وجوی بلیط هواپیما",
        "🛂 اطلاعات ویزا و شرایط سفر",
        "🛬 اطلاعات فرودگاه‌ها و مسیرهای پروازی",
        "📉 پایش قیمت بلیط هواپیما",
        "📚 اطلاعات کاربردی سفر",
    ],
    "welcome_choose": "برای شروع، یکی از گزینه‌های زیر را انتخاب کنید.",
    "help_title": "راهنمای Flight Iran Bot 24",
    "help_intro": "از منوی زیر سرویس موردنظر را انتخاب کنید یا از دستورات زیر استفاده کنید.",
    "help_commands": "دستورات ربات",
    "help_start": "نمایش صفحه اصلی و خدمات سفر",
    "help_help": "نمایش همین راهنما",
    "help_language": "انتخاب زبان فارسی، انگلیسی یا عربی",
    "help_menu": "بخش‌های منوی اصلی",
    "help_menu_body": (
        "🛬 فرودگاه‌ها: فهرست و مشخصات فرودگاه‌ها\n"
        "🎫 بلیط: مشاهده مسیرها و قیمت‌های موجود، در صورت فعال بودن "
        "سرویس\n"
        "📚 اطلاعات کاربردی: راهنماهای سفر\n"
        "⚙️ تنظیمات: تغییر زبان\n"
        "🛂 ویزا: استعلام پاسپورت و مقصد با منابع رسمی؛ قوانین مسافر جداگانه\n"
        "📦 حمل بار: ورود مستقیم به کانال @advertio_cargo\n"
        "📩 پشتیبانی: پرسش درباره رزرو، قیمت‌ها و استفاده از ربات"
    ),
    "help_note": (
        "برخی خدمات به فعال بودن سرویس‌دهنده وابسته‌اند. قیمت بلیط "
        "و شرایط سفر را پیش از تصمیم نهایی با منابع معتبر بررسی کنید."
    ),
    "help_back": "برای بازگشت به خدمات از /start استفاده کنید.",
})
MESSAGES["en"].update({
    "welcome_greeting": "Hello {name}",
    "welcome_title": "Flight Iran Bot 24 | Your Smart Travel Assistant",
    "welcome_intro": "Welcome to your flight and travel assistant!",
    "welcome_description": (
        "From ticket prices to travel planning, find your travel "
        "essentials in one place."
    ),
    "welcome_services": "Flight & Travel Services",
    "welcome_items": [
        "🎫 Search airline tickets",
        "🛂 Visa and travel requirements",
        "🛬 Airports and flight routes",
        "📉 Airfare price monitoring",
        "📚 Useful travel information",
    ],
    "welcome_choose": "Choose a service below to get started.",
    "help_title": "Flight Iran Bot 24 Help",
    "help_intro": "Select a service from the menu or use these commands.",
    "help_commands": "Bot commands",
    "help_start": "Show the main menu and travel services",
    "help_help": "Show this help guide",
    "help_language": "Choose Persian, English or Arabic",
    "help_menu": "Main menu sections",
    "help_menu_body": (
        "🛬 Airports: browse airports and details\n"
        "🎫 Tickets: available routes and fares when the service is "
        "enabled\n"
        "📚 Useful information: travel guides\n"
        "⚙️ Settings: change language\n"
        "🛂 Visa: passport/destination guidance with sources; traveler rules separate\n"
        "📦 Cargo marketplace: open the @advertio_cargo channel\n"
        "📩 Support: questions about bookings, prices and using the bot"
    ),
    "help_note": (
        "Some features require an active provider. Verify ticket prices "
        "and travel requirements before making decisions."
    ),
    "help_back": "Use /start to return to the main menu.",
})
MESSAGES["ar"].update({
    "welcome_greeting": "مرحباً {name}",
    "welcome_title": "Flight Iran Bot 24 | مساعد السفر الذكي",
    "welcome_intro": "مرحباً بك في مساعد خدمات الطيران والسفر!",
    "welcome_description": (
        "من أسعار التذاكر إلى التخطيط للسفر، اعثر على خدمات سفرك "
        "في مكان واحد."
    ),
    "welcome_services": "خدمات الطيران والسفر",
    "welcome_items": [
        "🎫 البحث عن تذاكر الطيران",
        "🛂 التأشيرات ومتطلبات السفر",
        "🛬 المطارات ومسارات الرحلات",
        "📉 متابعة أسعار التذاكر",
        "📚 معلومات السفر المفيدة",
    ],
    "welcome_choose": "اختر إحدى الخدمات أدناه للبدء.",
    "help_title": "دليل Flight Iran Bot 24",
    "help_intro": "اختر خدمة من القائمة أو استخدم الأوامر التالية.",
    "help_commands": "أوامر البوت",
    "help_start": "عرض القائمة الرئيسية وخدمات السفر",
    "help_help": "عرض دليل المساعدة",
    "help_language": "اختيار العربية أو الفارسية أو الإنجليزية",
    "help_menu": "أقسام القائمة الرئيسية",
    "help_menu_body": (
        "🛬 المطارات: تصفح المطارات وتفاصيلها\n"
        "🎫 التذاكر: المسارات والأسعار المتاحة عند تفعيل الخدمة\n"
        "📚 معلومات مفيدة: أدلة السفر\n"
        "⚙️ الإعدادات: تغيير اللغة\n"
        "🛂 التأشيرات: شروط الدخول بحسب الجواز والوجهة مع مصادرها\n"
        "📦 سوق الشحن: فتح قناة @advertio_cargo مباشرة\n"
        "📩 الدعم: أسئلة عن الحجز والأسعار واستخدام البوت"
    ),
    "help_note": (
        "تتطلب بعض الميزات مزود خدمة نشطاً. تحقق من أسعار التذاكر "
        "ومتطلبات السفر من المصادر الرسمية."
    ),
    "help_back": "استخدم /start للعودة إلى القائمة الرئيسية.",
})


MESSAGES["fa"].update({
    "help_visa": "بررسی ویزا (مثال: /visa AF TR یا /visa AF TR IR)",
    "help_visa_list": "فهرست کشورها براساس پاسپورت (مثال: /visa_list IR)",
})
MESSAGES["en"].update({
    "help_visa": "Check visa information (e.g. /visa AF TR or /visa AF TR IR)",
    "help_visa_list": "Explore destinations by passport (e.g. /visa_list IR)",
})
MESSAGES["ar"].update({
    "help_visa": "التحقق من التأشيرة (مثل /visa AF TR أو /visa AF TR IR)",
    "help_visa_list": "عرض الدول حسب الجواز (مثل /visa_list IR)",
})


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else "en"


def text(language: str | None, key: str) -> str:
    language = normalize_language(language)
    return MESSAGES[language].get(key, MESSAGES["en"].get(key, key))


def safe_text(language: str | None, key: str) -> str:
    return escape(text(language, key))

# Price bell command advertised in every supported language.
MESSAGES["fa"]["help_alerts"] = "ثبت و مدیریت هشدار قیمت بلیط"
MESSAGES["en"]["help_alerts"] = "Create and manage ticket price alerts"
MESSAGES["ar"]["help_alerts"] = "إنشاء وإدارة تنبيهات أسعار التذاكر"

# User-visible label for the private visa route change-alert command.
MESSAGES["fa"]["help_visa_watch"] = "مدیریت زنگوله تغییرات ویزا"
MESSAGES["en"]["help_visa_watch"] = "Manage visa change alerts"
MESSAGES["ar"]["help_visa_watch"] = "إدارة تنبيهات تغييرات التأشيرات"
