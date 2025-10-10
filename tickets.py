import requests
from bs4 import BeautifulSoup
from telegram import Update


async def handle_onlineticket(update: Update):
    await update.callback_query.message.reply_text(" در حال جست و جوی بهترین نرخ بلیط از ۵ وبسایت مرجع🔍")
    
    url = "https://mz724.ir/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        await update.callback_query.message.reply_text(
            f"❌ خطا در ارتباط با وب‌سایت: {e}\nلطفاً بعداً مجدداً تلاش کنید."
        )
        return
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        sr_tables = soup.find_all('div', class_='sr_table')

        if not sr_tables:
            await update.callback_query.message.reply_text(
                "❌ اطلاعات بلیط‌ها در دسترس نیست. لطفاً بعداً تلاش کنید."
            )
            return
        
        for index, sr_table in enumerate(sr_tables):
            # بررسی وجود عناصر
            source_div = sr_table.find('div', class_='t_table')
            if not source_div:
                continue
            
            source = source_div.get_text(strip=True)
            lines = sr_table.find_all('a', class_='line')
            if not lines:
                continue

            # ساخت اطلاعات مسیر
            route_info = f"📍 مبدا: {source} 🛫\n\n"
            for line in lines:
                city = line.find('span', class_='city')
                price = line.find('span', class_='price')
                if city and price:
                    route_info += f"🛬 مقصد: {city.get_text(strip=True)} | قیمت: {price.get_text(strip=True)} تومان\n"
            
            # ارسال اطلاعات به تلگرام
            await update.callback_query.message.reply_text(route_info)

        await update.callback_query.message.reply_text(
            "جهت رزرو بلیط لطفا به پشتیبان سیستم پیام ارسال نمایید 📥  @vlansupport"
        )
    
    except Exception as e:
        await update.callback_query.message.reply_text(
            f"❌ خطای داخلی در پردازش اطلاعات: {e}\nلطفاً پشتیبانی را مطلع کنید. @vlansupport"
        )
