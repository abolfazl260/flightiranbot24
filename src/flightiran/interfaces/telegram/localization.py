"""Small, explicit localization catalog with English fallback."""

from html import escape

SUPPORTED_LANGUAGES = ("fa", "en", "ar")

MESSAGES = {
    "en": {
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
        "settings": "Settings",
    },
    "fa": {
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
        "settings": "تنظیمات",
    },
    "ar": {
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
        "settings": "الإعدادات",
    },
}


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else "en"


def text(language: str | None, key: str) -> str:
    language = normalize_language(language)
    return MESSAGES[language].get(key, MESSAGES["en"].get(key, key))


def safe_text(language: str | None, key: str) -> str:
    return escape(text(language, key))
