import json
import uuid
import requests
from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

# Constants
FACTBOOK_BASE_URL = "https://www.cia.gov/the-world-factbook/page-data/countries/"
WIKI_BASE_URL = "https://wikipedia.org/wiki/"
TRIP_ADVISOR_BASE_URL = "https://www.tripadvisor.com/Search?q="
MASTERS_PORTAL_BASE_URL = "https://www.mastersportal.com/search/master/"
BACHELORS_PORTAL_BASE_URL = "https://www.bachelorsportal.com/search/bachelor/"
PHD_PORTAL_BASE_URL = "https://www.phdportal.com/search/phd/"
VISA_INDEX_BASE_URL = "https://visaindex.com/fa/country/"
PLANESPOTTERS_BASE_URL = "https://www.planespotters.net/airlines/"
COUNTRY_JSON_FILE = 'countries.json'

def get_countries_from_local_json(json_file, regions=['Europe', 'Asia', 'Americas']):
    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError("Failed to load countries data") from e
    return [
        {
            "name": country['name']['common'],
            "flag": country.get('flag', ''),
            "area": country.get('area', ''),
            "borders": ", ".join(country.get('borders', ['ندارد'])),
            "latlng": country.get('latlng', ['نامشخص']),
            "capital": ", ".join(country.get('capital', ['نامشخص'])),
            "cioc": country.get('cioc', 'نامشخص'),
            "region": country.get('region', 'نامشخص'),
            "subregion": country.get('subregion', 'نامشخص'),
            "languages": ", ".join(country.get('languages', {}).values()),
            "official_translation_per": country.get('translations', {}).get('per', {}).get('official', 'نامشخص'),
            "currencies": ", ".join(country.get('currencies', {}).keys()),
        }
        for country in data if country.get('region') in regions
    ]

# Cache for factbook data
factbook_cache = {}

def get_factbook_data(country_name):
    if country_name in factbook_cache:
        return factbook_cache[country_name]

    url = f"{FACTBOOK_BASE_URL}{country_name}/page-data.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        country_data = data.get("result", {}).get("data", {}).get("country", {})
        updated_date = country_data.get("updated", "نامشخص")
        region = country_data.get("region", "نامشخص")
        factbook_cache[country_name] = (updated_date, region)
        return updated_date, region
    except requests.RequestException as e:
        return "خطا در دریافت اطلاعات", "نامشخص"
    

def generate_keyboard(country_name, source):
    links = {
        "wiki": f"{WIKI_BASE_URL}{country_name}",
        "travel_info": f"{TRIP_ADVISOR_BASE_URL}{country_name}",
        "master": f"{MASTERS_PORTAL_BASE_URL}{country_name}",
        "bachelor": f"{BACHELORS_PORTAL_BASE_URL}{country_name}",
        "phd": f"{PHD_PORTAL_BASE_URL}{country_name}",
        "passport": f"{VISA_INDEX_BASE_URL}{country_name}-passport-ranking/",
        "airline_list": f"{PLANESPOTTERS_BASE_URL}{country_name}"
    }
    
    if source == "local":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("رتبه‌بندی پاسپورت 🏛️", url=links["passport"])],
            [InlineKeyboardButton("راهنمای سفر ✈️", url=links["travel_info"])],
            [InlineKeyboardButton("ارسال بار🧳", url="https://t.me/koolbar_bot"),
             InlineKeyboardButton("درآمد مسافر🛫", url="https://t.me/koolbar_bot")],
            [InlineKeyboardButton("ویکی‌پدیا🌐", url=links["wiki"]),
             InlineKeyboardButton("ایرلاین ها🛩", url=links["airline_list"])],
            [InlineKeyboardButton("کارشناسی🧑‍🏫", url=links["bachelor"]),
             InlineKeyboardButton("ارشد👨‍🎓", url=links["master"]),
             InlineKeyboardButton("دکتری👩‍🎓", url=links["phd"])],
             [InlineKeyboardButton("اطلاعات بیشتر🌐", url=f"https://www.cia.gov/the-world-factbook/countries/{country_name.lower()}"),
              InlineKeyboardButton("هزینه زندگی💲", url=f"https://www.numbeo.com/cost-of-living/country_result.jsp?country={country_name}&displayCurrency=USD"),],
        ])
        return keyboard

async def inline_query_handler(update: Update, context: CallbackContext):
    query = update.inline_query.query.lower()
    countries = get_countries_from_local_json(COUNTRY_JSON_FILE)
    filtered_countries = [
        country for country in countries if query in country['name'].lower()
    ][:4]

    results = []

    for country in filtered_countries:
        country_name = country['name']
        flag = country['flag']
        updated_date, region = get_factbook_data(country_name.lower())
        
        # Generate a unique ID for each result
        unique_id_basic = str(uuid.uuid4())
        unique_id_fact = str(uuid.uuid4())
        
        # Build message content
        message_content = (
            f"{flag * 5}\n"
            f"<b>{country_name}</b>\n"
            f"{country['official_translation_per']}\n"
            f"🌍 <b>پایتخت:</b> {country['capital']}\n"
            f"🏞️ <b>مرزها:</b> {country['borders']}\n"
            f"📍 <b>مختصات جغرافیایی:</b> {country['latlng']}\n"
            f"🔢 <b>کد :</b> {country['cioc']}\n"
            f"🌎 <b>قاره:</b> {country['region']}\n"
            f"🌍 <b>ناحیه:</b> {country['subregion']}\n"
            f"🗣️ <b>زبان‌ها:</b> {country['languages']}\n"
            f"💱 <b>ارز:</b> {country['currencies']}\n"
            f"🗺 <b>مساحت:</b> {country['area']}km²\n"
            f"<a href='https://flagdownload.com/wp-content/uploads/Flag_of_{country_name}_Flat_Square-256x256.png'>پرچم کشور</a>\n"
            f"<a href='https://flagdownload.com/wp-content/uploads/Emblem_of_{country_name}.pdf'> نماد پرچم </a>\n\n"
            f"{flag * 5}\n"
        )

        results.append(
            InlineQueryResultArticle(
                id=unique_id_basic,  # Unique ID for basic information
                title=f"{flag} {country_name} - basic information",
                input_message_content=InputTextMessageContent(
                    message_content,
                    parse_mode="HTML"
                ),
                reply_markup=generate_keyboard(country_name, "local")
            )
        )
        results.append(
            InlineQueryResultArticle(
                id=unique_id_fact,  # Unique ID for world fact
                title=f"{flag} {country_name} - World Fact",
                input_message_content=InputTextMessageContent(
                    f"📅  تاریخ بروزرسانی ااطلاعات: {updated_date}\n",
                    parse_mode='HTML'
                ),
                reply_markup=generate_keyboard(country_name, "cia")
            )
        )
    
    if not results:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),  # Unique ID for no results
                title="نتیجه‌ای یافت نشد",
                input_message_content=InputTextMessageContent(
                    "کشوری با این مشخصات یافت نشد. لطفاً دوباره تلاش کنید."
                )
            )
        )
    
    await update.inline_query.answer(results, cache_time=10)
