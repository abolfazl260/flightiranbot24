import csv
import logging
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, InlineQueryHandler
from exchange import handle_exchangerate
from tickets import handle_onlineticket
from country import handle_country
from inlinemode import inline_query_handler
from flight_info import flight_info
from airportinformation import airport_selection_keyboard, fetch_airport_info
from datetime import datetime

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.basicConfig(filename='log-3.1.0.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger(__name__)

with open('languages.json', 'r', encoding='utf-8') as f:
    LANGUAGES = json.load(f)

ADMIN_USER_ID = 1485409432
CHANNEL_ID = "@youtubetest215"
user_states = {}

def get_user_language(update, context=None):
    if context and "language" in context.user_data:
        return context.user_data["language"]
    user_lang = update.effective_user.language_code if update.effective_user else None
    if user_lang:
        if user_lang.startswith("fa"):
            return "fa"
        elif user_lang.startswith("ar"):
            return "ar"
        elif user_lang.startswith("en"):
            return "en"
    return "en"

def get_message(update, context, key, subkey=None):
    lang = get_user_language(update, context)
    if subkey:
        return LANGUAGES[lang].get(subkey, {}).get(key, "Message not found")
    return LANGUAGES[lang].get(key, "Message not found")

def save_user_info_to_csv(user, button_data):
    current_time = datetime.now()
    date_part = current_time.strftime('%Y/%m/%d')
    time_part = current_time.strftime('%H:%M')
    with open('user_info.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([date_part, time_part, user.first_name, user.last_name, user.id, user.username, button_data])

async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    language_code = user.language_code
    logger.info("User {} with username {} started the bot.".format(user.full_name, user.username))
    save_user_info_to_csv(user, language_code)
    keyboard = main_menu(update, context)
    await update.message.reply_text(get_message(update, context, "welcome"), reply_markup=keyboard)

def main_menu(update, context):
    buttons = LANGUAGES[get_user_language(update, context)]["buttons"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(buttons["traveler_income"], url="https://t.me/koolbar_international"),
         InlineKeyboardButton(buttons["useful"], callback_data="wikibutton")],
        [InlineKeyboardButton(buttons["currency_payment"], callback_data="currency_payment"),
         InlineKeyboardButton(buttons["air_shipping"], url="https://t.me/koolbar_international")],
        [InlineKeyboardButton(buttons["exchange_rate"], callback_data="exchangerate")],
         [InlineKeyboardButton(buttons["cheap_tickets"], callback_data="onlineticket")],
        [InlineKeyboardButton(buttons["iran_flight_info"], url="https://fids.airport.ir/")],
        [InlineKeyboardButton(buttons["flight_status"], callback_data="flight_position"),
         InlineKeyboardButton(buttons["airport_status"], callback_data="choose_airport")],
        [InlineKeyboardButton(buttons["last_minute_tickets"], callback_data="lastsecondbutt"),
         InlineKeyboardButton(buttons["passport"], callback_data="country")],
        [InlineKeyboardButton(buttons["contact_us"], callback_data="aboutus")]
    ])

async def send_message(update, text, keyboard=None):
    await update.callback_query.message.reply_text(text, reply_markup=keyboard)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("فارسی 🇮🇷", callback_data="set_lang_fa")],
        [InlineKeyboardButton("English 🇬🇧", callback_data="set_lang_en")],
        [InlineKeyboardButton("العربية 🇸🇦", callback_data="set_lang_ar")],
        [InlineKeyboardButton(LANGUAGES[get_user_language(update, context)]["buttons"]["back"], callback_data="back_btn")]
    ])
    await update.message.reply_text(get_message(update, context, "change_language_prompt"), reply_markup=keyboard)

async def set_language(update: Update, context: CallbackContext):
    data = update.callback_query.data
    if data == "set_lang_fa":
        context.user_data["language"] = "fa"
    elif data == "set_lang_en":
        context.user_data["language"] = "en"
    elif data == "set_lang_ar":
        context.user_data["language"] = "ar"
    keyboard = main_menu(update, context)
    await send_message(update, get_message(update, context, "language_changed"), keyboard)

async def button_controller(update: Update, context: CallbackContext):
    data = update.callback_query.data
    user = update.callback_query.from_user
    logger.info(f"User {user.first_name} (Username: {user.username}) clicked on button: {data}")
    save_user_info_to_csv(user, data)

    if data == "back_btn":
        keyboard = main_menu(update, context)
        await send_message(update, get_message(update, context, "main_menu_text"), keyboard)
    elif data == "aboutus":
        await send_message(update, get_message(update, context, "about_us"))
    elif data == "forbiddenflightrules":
        keyboard = create_flight_rules_keyboard(update, context)
        await send_message(update, get_message(update, context, "flight_rules_note"), keyboard)
    elif data == "flight_position":
        await send_message(update, get_message(update, context, "flight_position_prompt"))
    elif data == "currency_payment":
        await send_message(update, get_message(update, context, "currency_payment_info"))
        await send_message(update, get_message(update, context, "currency_payment_icon"))
    elif data == "lastsecondbutt":
        await send_message(update, get_message(update, context, "last_minute_icon"))
        await send_message(update, get_message(update, context, "last_minute_prompt"))
        user_states[user.id] = "awaiting_admin_message"
    elif data == "websiteslist":
        keyboard = create_websites_list_keyboard(update, context)
        await send_message(update, get_message(update, context, "flight_rules_note"), keyboard)
    elif data == "wikibutton":
        keyboard = create_wiki_keyboard(update, context)
        await send_message(update, get_message(update, context, "wiki_intro"), keyboard)
    elif data == "exchangerate":
        await handle_exchangerate(update, context)
    elif data == "onlineticket":
        await handle_onlineticket(update)
    elif data == "country":
        await handle_country(update, context)
    elif data == "share_exchangerate":
        chat_id = "CHAT_ID"
        await handle_exchangerate(update, context)
        await update.callback_query.answer(get_message(update, context, "share_exchange_success"), show_alert=True)
        await context.bot.send_message(chat_id=chat_id, text=get_message(update, context, "share_exchange_message"))
    elif data.startswith("airport_"):
        airport_code = data.split("_")[1]
        await fetch_airport_info(update, airport_code)
    elif data == "choose_airport":
        await send_message(update, get_message(update, context, "choose_airport"), airport_selection_keyboard())
    elif data.startswith("set_lang_"):
        await set_language(update, context)

def create_flight_rules_keyboard(update, context):
    buttons = LANGUAGES[get_user_language(update, context)]["buttons"]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=buttons["canada"], url="https://t.me/koolbar_international/81"),
            InlineKeyboardButton(text=buttons["italy"], url="https://t.me/koolbar_international/508"),
            InlineKeyboardButton(text=buttons["iran"], url="https://www.alibaba.ir/mag/travel-facts/customs-regulations-travelers-luggage/"),
        ],
        [
            InlineKeyboardButton(text=buttons["uk"], url="https://t.me/koolbar_international/540"),
            InlineKeyboardButton(text=buttons["usa"], url="https://t.me/koolbar_international/542"),
            InlineKeyboardButton(text=buttons["europe"], url="https://t.me/koolbar_international/636"),
        ],
        [
            InlineKeyboardButton(text=buttons["iran"], url="https://t.me/koolbar_international/637"),
            InlineKeyboardButton(text=buttons["back"], callback_data="back_btn"),
        ],
    ])

def create_websites_list_keyboard(update, context):
    buttons = LANGUAGES[get_user_language(update, context)]["buttons"]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=buttons["canada"], url="https://t.me/koolbar_international/560"),
            InlineKeyboardButton(text=buttons["italy"], url="https://t.me/koolbar_international/562"),
            InlineKeyboardButton(text=buttons["iraq"], url="https://t.me/koolbar_international/566"),
        ],
        [
            InlineKeyboardButton(text=buttons["uk"], url="https://t.me/koolbar_international/563"),
            InlineKeyboardButton(text=buttons["usa"], url="https://t.me/koolbar_international/564"),
            InlineKeyboardButton(text=buttons["europe"], url="https://t.me/koolbar_international/565"),
            InlineKeyboardButton(text=buttons["back"], callback_data="back_btn"),
        ],
    ])

def create_wiki_keyboard(update, context):
    buttons = LANGUAGES[get_user_language(update, context)]["buttons"]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=buttons["flight_compensation"], url="https://www.airhelp.com/"),
            InlineKeyboardButton(text=buttons["airline_rating"], url="https://airlineratings.com"),
        ],
        [
            InlineKeyboardButton(text=buttons["exit_ban"], url="https://t.me/koolbar_international/527"),
            InlineKeyboardButton(text=buttons["prohibited_items"], url="https://t.me/koolbar_international/637"),
        ],
        [
            InlineKeyboardButton(text=buttons["exit_fees"], url="https://t.me/koolbar_international/516"),
            InlineKeyboardButton(text=buttons["travel_insurance"], url="https://t.me/koolbar_international/549"),
        ],
        [
            InlineKeyboardButton(text=buttons["travel_tips"], url="https://t.me/koolbar_international/1254"),
        ],
        [
            InlineKeyboardButton(text=buttons["get_passport"], url="https://t.me/koolbar_international/526"),
            InlineKeyboardButton(text=buttons["academic_exemption"], url="https://t.me/koolbar_international/503"),
        ],
        [
            InlineKeyboardButton(text=buttons["flight_restrictions"], callback_data="forbiddenflightrules"),
            InlineKeyboardButton(text=buttons["back"], callback_data="back_btn"),
        ],
    ])

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user_states.get(user.id) == "awaiting_admin_message":
        admin_message = f" {user.id}\n\n name:{user.full_name} \n\n Username: @{user.username}\n\n{update.message.text}"
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)
        await update.message.reply_text(get_message(update, context, "message_registered"))
        user_states[user.id] = None
    else:
        await forward_message_to_user(update, context)

async def forward_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == ADMIN_USER_ID:
        try:
            target_user_id, message_text = update.message.text.split(maxsplit=1)
            target_user_id = int(target_user_id)
            await context.bot.send_message(chat_id=target_user_id, text=message_text)
            await update.message.reply_text(f"Message sent to user with ID: {target_user_id} ")
        except ValueError:
            await update.message.reply_text("Invalid format. Use: USER_ID message")

#TOKEN = "271289863:AAHQzV2PCYBSDHsr1ylFFot8ZFU5bzDZL-E" #stage
#TOKEN = "7185515791:AAGsPpm2B73nrGrQFPJqVV3aXhN43LjaFuU" #production
TOKEN = "1984772645:AAGoojVfYCHRJN5sTHo4IKwLjUp1-03SjyY" #test

application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", say_hello))
application.add_handler(CommandHandler("flight", flight_info))
application.add_handler(CommandHandler("price", handle_exchangerate))
application.add_handler(CommandHandler("language", change_language))
application.add_handler(CallbackQueryHandler(button_controller))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
application.add_handler(InlineQueryHandler(inline_query_handler))
application.run_polling()