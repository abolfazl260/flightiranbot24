import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# بارگذاری داده‌های کشورهای JSON
with open('countries.json', 'r', encoding='utf-8') as f:
    countries_data = json.load(f)

def get_countries_by_continent():
    continents = {}
    
    # قاره‌هایی که باید نمایش داده شوند
    target_continents = ['Americas', 'Asia', 'Europe']
    
    # جستجو در تمامی کشورهای موجود در داده‌ها
    for country in countries_data:
        continent = country.get("region")  # قاره کشور
        if continent not in target_continents:
            continue
        
        country_name = country["name"]["common"]
        
        # فیلتر کردن کشورهایی که بیشتر از یک کلمه دارند
        if ' ' in country_name:
            continue
        
        # اطلاعات دیگر کشور
        country_flag = country["flag"]
        country_link = f"https://visaindex.com/fa/country/{country_name.replace(' ', '_')}-passport-ranking/"
        
        # دریافت پایتخت اگر موجود باشد
        capital = country.get("capital")
        if capital and isinstance(capital, list) and capital:
            capital = capital[0]
        else:
            capital = "N/A"  # اگر پایتخت موجود نبود یا خالی بود، "N/A" قرار می‌دهیم
        
        if continent not in continents:
            continents[continent] = []
        
        continents[continent].append((country_name, country_link, country_flag, capital))
    
    return continents

async def handle_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    continents = get_countries_by_continent()
    
    # برای هر قاره
    for continent, countries in continents.items():
        message = f"🌏 اطلاعات ویزای کشور های قاره {continent} \n\n"
        
        # برای هر کشور در قاره
        for country_name, country_link, country_flag, capital in countries:
            message += f"<a href='{country_link}'>{country_flag} {country_name}</a> | {capital}\n"
        
        # ساخت دکمه "بازگشت به منو"
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_btn")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال پیام برای هر قاره همراه با دکمه
        await update.callback_query.message.reply_text(
            message,
            parse_mode="HTML",  # استفاده از فرمت HTML برای نمایش هایپرلینک و پرچم
            reply_markup=reply_markup
        )

# هندلر برای دکمه "بازگشت به منو"
async def handle_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text(
        "شما به منو بازگشتید. لطفاً گزینه مورد نظر را انتخاب کنید."
    )
