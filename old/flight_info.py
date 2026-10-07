# flight_info.py
import requests
import datetime
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

def format_timestamp_to_local_time(timestamp, offset_seconds):
    """Convert a UNIX timestamp to a readable local datetime format."""
    if timestamp:
        local_time = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc) + datetime.timedelta(seconds=offset_seconds)
        return local_time.strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"

async def flight_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        flight_number = context.args[0].strip()
    else:
        await update.message.reply_text("لطفا شماره پرواز خود را مشابه زیر ارسال نمایید: \n /flight KLM561 ")
        return

    if not flight_number.isalnum():
        await update.message.reply_text("لطفا شماره پرواز معتبر وارد کنید، برای مثال:\n TBZ5610 یا KLM428")
        return

    search_url = f"https://www.flightradar24.com/v1/search/web/find?query={flight_number}"

    try:
        response = requests.get(search_url)
        response.raise_for_status()
        search_data = response.json()

        flight_id = None
        flight_position = {"lat": "N/A", "lon": "N/A"}
        for item in search_data.get('results', []):
            if len(item.get('id', '')) == 8:
                flight_id = item['id']
                flight_position['lat'] = item.get('detail', {}).get('lat', 'N/A')
                flight_position['lon'] = item.get('detail', {}).get('lon', 'N/A')
                break

        if flight_id:
            detail_url = f"https://data-live.flightradar24.com/clickhandler/?version=1.5&flight={flight_id}"
            detail_response = requests.get(detail_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()

            # Extract airline name
            airline_name = detail_data.get("airline", {}).get("name", "N/A")

            # Extract information from detailed data
            status = detail_data.get("status", {})
            time_info = detail_data.get("time", {})
            airport_info = detail_data.get("airport", {})
            aircraft_info = detail_data.get("aircraft", {})

            # Extract and format times with local timezone offsets
            origin_offset_seconds = airport_info.get("origin", {}).get("timezone", {}).get("offset", 0)
            destination_offset_seconds = airport_info.get("destination", {}).get("timezone", {}).get("offset", 0)

            scheduled_departure = format_timestamp_to_local_time(time_info.get("scheduled", {}).get("departure"), origin_offset_seconds)
            real_departure = format_timestamp_to_local_time(time_info.get("real", {}).get("departure"), origin_offset_seconds)
            scheduled_arrival = format_timestamp_to_local_time(time_info.get("scheduled", {}).get("arrival"), destination_offset_seconds)
            real_arrival = format_timestamp_to_local_time(time_info.get("real", {}).get("arrival"), destination_offset_seconds)
            estimated_arrival = format_timestamp_to_local_time(time_info.get("estimated", {}).get("arrival"), destination_offset_seconds)

            # Extract and format airport data
            origin = airport_info.get("origin", {})
            destination = airport_info.get("destination", {})
            origin_name = origin.get("name", "N/A")
            origin_city = origin.get("position", {}).get("region", {}).get("city", "N/A")
            origin_country = origin.get("position", {}).get("country", {}).get("name", "N/A")
            origin_terminal = origin.get("info", {}).get("terminal", "N/A")
            destination_name = destination.get("name", "N/A")
            destination_city = destination.get("position", {}).get("region", {}).get("city", "N/A")
            destination_country = destination.get("position", {}).get("country", {}).get("name", "N/A")
            destination_terminal = destination.get("info", {}).get("terminal", "N/A")
            flight_identification = detail_data.get("identification", {})
            flight_number_default = flight_identification.get("callsign", "N/A")

            # Extract and format aircraft data
            aircraft_model = aircraft_info.get("model", {}).get("text", "N/A")
            aircraft_age = aircraft_info.get("age", "N/A")
            aircraft_image = aircraft_info.get("images", {}).get("large", [{}])[0].get("src", "N/A")

            # Format the response text
            response_text = (
                f"🎫 **شماره پرواز : {flight_number_default}**\n"
                f"✈️ شرکت هواپیمایی: {airline_name}\n"
                f"🛩️ مدل : {aircraft_model}\n"
                f"🌎 مسیر :{origin_country} ┈➤ {destination_country}\n\n"

                f"🛫زمان برنامه‌ریزی شده : {scheduled_departure}\n"
                f"🛫 زمان واقعی پرواز: {real_departure}\n"
                f"🌍مبدا: {origin_name} - {origin_city}\n"
                f"⛩ترمینال مبدا: {origin_terminal}\n\n"
                f"🛬زمان برنامه‌ریزی شده فرود: {scheduled_arrival}\n"
                f"🛬زمان تخمینی فرود: {estimated_arrival}\n"
                f"🌍مقصد: {destination_name} - {destination_city}\n"
                f"⛩ترمینال مقصد: {destination_terminal}\n\n"
                f"🌐 موقعیت جغرافیایی فعلی: عرض جغرافیایی {flight_position['lat']}, طول جغرافیایی {flight_position['lon']}\n"
                f"عمر هواپیما: {aircraft_age}\n"
                f"تصویر : [لینک]({aircraft_image})\n"
                f"👩🏻‍✈️آیدی پرواز: {flight_id}\n"
            )

            # Define buttons for the response
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(text="👈وضعیت پرواز در نقشه", url=f"https://www.flightradar24.com/{flight_id}")],
                [InlineKeyboardButton(text="📅تاریخچه هواپیما", url=f"https://www.flightradar24.com/data/flights/{flight_number_default}")],
                [InlineKeyboardButton(text="🔙بازگشت به منو", callback_data="back_btn")],
            ])

            await update.message.reply_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text("شماره پرواز ارسال شده معتبر نیست لطفا مجددا مشابه نمونه ارسال فرمایید. \n /flight BAW23T ")

    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"خطا در دریافت اطلاعات پرواز: {e}")
