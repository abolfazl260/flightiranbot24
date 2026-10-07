import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Currency rate emojis
rate_emojis = {
    "low": "🔻",
    "high": "🔼",
    "": "⚪",
}

# Updated Proxy API URL
PROXY_API_URL = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&country=iq,tr,gb,ch,ca,it,az,ae,us,ir,fr,de,nl&protocol=http&proxy_format=ipport&format=json&timeout=420"

# Admin chat ID
ADMIN_CHAT_ID = "1485409432"

# Simple headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
}

# Set to store dirty proxies and variable for successful proxy
dirty_proxies = set()
successful_proxy = None

# Function to fetch proxies from API
def fetch_proxies_from_api():
    try:
        response = requests.get(PROXY_API_URL, timeout=10)
        data = response.json()
        return [proxy["proxy"] for proxy in data["proxies"] if proxy["alive"] and proxy["proxy"] not in dirty_proxies]
    except:
        return []

# Function to try a request with a proxy
def try_proxy(proxy, url):
    try:
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        response = requests.get(url, headers=HEADERS, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        dirty_proxies.add(proxy)  # Add to dirty proxies if failed
        return None, str(e)

# Function to try a request without proxy
def try_without_proxy(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return None, str(e)

# Define exchangerate_menu function
def exchangerate_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="💵 Currency Rates", url="https://www.tgju.org/currency"),
            InlineKeyboardButton(text="🏅 Gold Prices", url="https://www.tgju.org/gold-chart"),
        ],
        [
            InlineKeyboardButton(text="🪙 Cryptocurrency", url="https://coinmarketcap.com"),
            InlineKeyboardButton(text="🏦 Authorized Exchanges", url="https://www.tgju.org/currency-exchange"),
        ],
        [
            InlineKeyboardButton(text="Sell Currency", url="https://t.me/vlansupport"),
            InlineKeyboardButton(text="🔙", callback_data="back_btn"),
        ],
    ])

async def handle_exchangerate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global successful_proxy  # Use the global successful proxy
    url = "https://call.tgju.org/ajax.json"
    
    # Show searching message to user
    if update.callback_query:
        await update.callback_query.message.reply_text("در حال جستجو قیمت ارزها...")
    elif update.message:
        await update.message.reply_text("در حال جستجو قیمت ارزها...")

    # If we have a successful proxy, try it first
    if successful_proxy:
        data, error = try_proxy(successful_proxy, url)
        if data:
            # If still successful, use it
            pass
        else:
            # If it fails, mark it dirty and reset
            dirty_proxies.add(successful_proxy)
            successful_proxy = None
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Previous successful proxy failed: {successful_proxy} - Error: {error}")

    # If no successful proxy or it failed, fetch new proxies
    if not successful_proxy:
        proxies = fetch_proxies_from_api()
        
        if not proxies:
            admin_error = "No proxies fetched from API"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_error)
        else:
            for proxy in proxies:
                data, error = try_proxy(proxy, url)
                if data:
                    successful_proxy = proxy  # Store the successful proxy
                    break
                else:
                    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Error with proxy {proxy}: {error}")

    # Try without proxy if no proxy worked
    if not data:
        data, error = try_without_proxy(url)
        if not data:
            admin_error = f"Error without proxy: {error}"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_error)
            user_error = "خطا در دریافت اطلاعات قیمت ارزها"
            if update.callback_query:
                await update.callback_query.message.reply_text(user_error)
            elif update.message:
                await update.message.reply_text(user_error)
            return

    # Process the data
    currencies = {
        "Dollar 🇺🇸": ("price_dollar_rl", "https://www.tgju.org/%D9%82%DB%8C%D9%85%D8%AA-%D8%AF%D9%84%D8%A7%D8%B1?"),
        "Tether 💸": ("crypto-tether-irr", "https://coinmarketcap.com/currencies/tether/"),
        "Euro 🇪🇺": ("price_eur", "https://www.tgju.org/profile/price_eur"),
        "Pound Sterling 🇬🇧": ("price_gbp", "https://www.tgju.org/profile/price_gbp"),
        "UAE Dirham 🇦🇪": ("price_aed", "https://www.tgju.org/profile/price_aed"),
        "Canadian Dollar 🇨🇦": ("price_cad", "https://www.tgju.org/profile/price_cad"),
        "Turkish Lira 🇹🇷": ("price_try", "https://www.tgju.org/profile/price_try"),
        "Saudi Riyal 🇸🇦": ("price_sar", "https://www.tgju.org/profile/price_sar"),
        "Chinese Yuan 🇨🇳": ("price_cny", "https://www.tgju.org/profile/price_cny"),
        "Australian Dollar 🇦🇺": ("price_aud", "https://www.tgju.org/profile/price_aud"),
        "Afghani 🇦🇫": ("price_afn", "https://www.tgju.org/profile/price_afn"),
        "Coin 🟡": ("sekee", "https://www.tgju.org/coin"),
        "Quarter Coin 🟡": ("rob", "https://www.tgju.org/profile/rob"),
        "18K Gold 🥇": ("geram18", "https://www.tgju.org/gold-chart"),
        "Bitcoin ₿": ("crypto-bitcoin-irr", "https://coinmarketcap.com/currencies/bitcoin/"),
    }

    currency_data = []
    for name, (key, link) in currencies.items():
        details = data.get("current", {}).get(key, {})
        rate = details.get("dt", "Unknown")
        emoji = rate_emojis.get(rate, "")
        currency_data.append({
            "name": name,
            "link": link,
            "price": details.get("p", "Unknown"),
            "change": details.get("dp", "Unknown"),
            "rate": emoji,
            "timestamp": details.get("ts", "Unknown"),
        })

    message = f"🔄   آخرین بروزرسانی: {currency_data[0]['timestamp']}\n\n"
    for currency in currency_data:
        message += (
            f"[{currency['name']}]({currency['link']}) : \n"
            f"| {currency['price']} ریال | % {currency['change']} {currency['rate']} \n"
        )

    message += (
        "\n 💰 مجموعه ما آماده است که با بهترین نرخ، ارز شما را خریداری نماید.\n"
        "🛡 ارزش ارز شما باید کمتر از ۵۰۰ دلار باشد.\n"
        " خرید آنلاین از وب‌سایت‌های خارجی و ایرانی \n"
        "💱 نرخ ارز بر اساس میانگین صرافی‌های TGJU ایران است.\n"
        "⇄ برای خرید و فروش ارز به ما پیام دهید: @vlansupport "
    )

    if update.message:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=exchangerate_menu())
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=exchangerate_menu()
        )