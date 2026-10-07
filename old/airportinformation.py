import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

AIRPORTS = [
    {"code": "IKA", "name": "امام خمینی تهران IKA 🇮🇷"},
    {"code": "THR", "name": "مهرآباد تهران THR 🇮🇷"},
    {"code": "SYZ", "name": "شهید دستغیب شیراز SYZ 🇮🇷"},
    {"code": "MHD", "name": "مشهد MHD 🇮🇷"},
    {"code": "TBZ", "name": "تبریز TBZ 🇮🇷"},
    {"code": "IFN", "name": "شهید بهشتی اصفهان IFN 🇮🇷"},
    {"code": "KIH", "name": "کیش KIH 🇮🇷"},
    {"code": "AWZ", "name": "اهواز AWZ 🇮🇷"},
    {"code": "ZAH", "name": "زاهدان ZAH 🇮🇷"},
    {"code": "OMH", "name": "ارومیه OMH 🇮🇷"},
    {"code": "BND", "name": "بندرعباس BND 🇮🇷"},
    {"code": "KER", "name": "کرمان KER 🇮🇷"},
    {"code": "DXB", "name": "دبی DXB 🇦🇪"},
    {"code": "IST", "name": "استانبول IST 🇹🇷"},
    {"code": "DOH", "name": "دوحه DOH 🇶🇦"},
    {"code": "AUH", "name": "ابوظبی AUH 🇦🇪"},
    {"code": "BKK", "name": "بانکوک BKK 🇹🇭"},
    {"code": "FRA", "name": "فرانکفورت FRA 🇩🇪"},
    {"code": "KUL", "name": "کوالالامپور KUL 🇲🇾"},
    {"code": "LHR", "name": "لندن هیترو LHR 🇬🇧"},
    {"code": "AMS", "name": "آمستردام AMS 🇳🇱"},
    {"code": "CDG", "name": "پاریس CDG 🇫🇷"},
    {"code": "MSQ", "name": "مینسک MSQ 🇧🇾"},
    {"code": "MUC", "name": "مونیخ MUC 🇩🇪"},
    {"code": "DEL", "name": "دهلی DEL 🇮🇳"},
    {"code": "PEK", "name": "پکن PEK 🇨🇳"},
    {"code": "MAD", "name": "مادرید MAD 🇪🇸"},
    {"code": "ATH", "name": "آتن ATH 🇬🇷"},
]

def airport_selection_keyboard():
    keyboard = [
        [InlineKeyboardButton(airport["name"], callback_data=f"airport_{airport['code']}")]
        for airport in AIRPORTS
    ]

    # اضافه کردن دکمه بازگشت به انتهای لیست دکمه‌ها
    keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_btn")])

    return InlineKeyboardMarkup(keyboard)

async def fetch_airport_info(update, airport_code: str):
    url_details = "https://flightradar243.p.rapidapi.com/v1/airports/details"
    url_ratings = "https://flightradar243.p.rapidapi.com/v1/airports/myfr24-ratings"

    querystring = {"code": airport_code}

    headers = {
        "x-rapidapi-key": "a5bc36a3a4msh32d74af964f5cfdp127470jsna98c0d744a71",
        "x-rapidapi-host": "flightradar243.p.rapidapi.com"
    }

    try:
        # Request to get airport details
        response_details = requests.get(url_details, headers=headers, params=querystring)
        response_data_details = response_details.json().get("data", {}).get("result", {}).get("response", {})
        airport_info = response_data_details.get("airport", {}).get("pluginData", {})

        # Request to get airport ratings
        response_ratings = requests.get(url_ratings, headers=headers, params=querystring)
        response_data_ratings = response_ratings.json().get("data", {})
        ratings = response_data_ratings.get("rating", {})
        reviews_number = response_data_ratings.get("reviewsNumber", 'N/A')

        # Check if details data is available
        if not airport_info:
            await update.callback_query.message.reply_text("اطلاعاتی برای این فرودگاه پیدا نشد.")
            return

        # Extract and format airport details
        details = airport_info.get("details", {})
        weather = airport_info.get("weather", {})
        schedule_stats = airport_info.get("scheduledRoutesStatistics", {})
        satellite_image = airport_info.get("satelliteImage", None)

        # Prepare the airport info text
        info_text = (
            f"🛩️اطلاعات فرودگاه\n"
            f"نام: {details.get('name', 'N/A')}\n"
            f"شهر: {details.get('position', {}).get('region', {}).get('city', 'N/A')}\n"
            f"ارتفاع: {details.get('position', {}).get('elevation', 'N/A')} ft\n"
            f"مجموع پرواز: {schedule_stats.get('totalFlights', 'N/A')}\n"
            f"بیشترین پرواز: {schedule_stats.get('topRoute', {}).get('from', 'N/A')} to "
            f"{schedule_stats.get('topRoute', {}).get('to', 'N/A')} "
            f"({schedule_stats.get('topRoute', {}).get('count', 'N/A')} flights)\n\n"
        )

        # Weather information
        info_text += (
            f"🌤 **آب و هوا**\n"
            f"دما: {weather.get('temp', {}).get('celsius', 'N/A')}°C\n"
            f"باد: {weather.get('wind', {}).get('speed', {}).get('text', 'N/A')},\n "
            f"رطوبت: {weather.get('humidity', 'N/A')}%\n"
            f"شرایط جوی: {weather.get('sky', {}).get('condition', {}).get('text', 'N/A')}\n\n"
        )
        # Ratings information
        if ratings:
            info_text += f"🌟 ** امتیاز کلی فرودگاه**: {ratings.get('rating', 'N/A')} ({ratings.get('percentage', 'N/A')}%)\n"
        info_text += f"تعداد رای دهنده: {reviews_number}\n"
        for subrating in response_data_ratings.get("subrating", []):
                info_text += (
                    f"{subrating.get('subject', 'N/A')}: {subrating.get('average_rating', 'N/A')}%\n"
                )
        # Satellite image
        if satellite_image:
            info_text += f"🛰 [تصویر ماهواره ای]({satellite_image})\n\n"

    except Exception as e:
        info_text = f"خطا در دریافت اطلاعات فرودگاه: {e}"

    # Send the message to the user
    await update.callback_query.message.reply_text(info_text, parse_mode="Markdown")
