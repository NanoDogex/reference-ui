import os
import json
import random
import string
import logging
import datetime
from datetime import timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "ghostgpt5")

USER_DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO)

# ==============================
# STORAGE
# ==============================

if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "r") as f:
        user_data = json.load(f)
else:
    user_data = {}


def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=2)


def generate_key():
    return "GHOST-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=12)
    )


def get_expiry_time():
    return (
        datetime.datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d %H:%M:%S")


def is_key_expired(expiry_time):
    if not expiry_time:
        return True

    expiry = datetime.datetime.strptime(
        expiry_time,
        "%Y-%m-%d %H:%M:%S"
    )

    return datetime.datetime.now() > expiry


def get_user(user_id):
    user_id = str(user_id)

    if user_id not in user_data:
        user_data[user_id] = {
            "verified": False,
            "key": None,
            "expiry_time": None,
            "total_keys_generated": 0,
        }
        save_user_data()

    return user_data[user_id]


# ==============================
# HANDLERS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔑 Generate Trial Key", callback_data="gen")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        ]
    )

    await update.message.reply_text(
        "👻 *Welcome to GhostGPT KeyGen*\n\n"
        "Generate secure 24-hour trial access keys.\n"
        "Upgrade options coming soon.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)

    # If active key exists
    if user["key"] and not is_key_expired(user["expiry_time"]):
        await query.message.reply_text(
            f"🔑 *Your Active Key*\n\n"
            f"`{user['key']}`\n\n"
            f"Valid until: {user['expiry_time']}",
            parse_mode="Markdown",
        )
        return

    # Generate new key
    key = generate_key()
    expiry = get_expiry_time()

    user["key"] = key
    user["expiry_time"] = expiry
    user["total_keys_generated"] += 1
    save_user_data()

    await query.message.reply_text(
        f"✅ *Key Generated!*\n\n"
        f"`{key}`\n\n"
        f"Expires: {expiry}",
        parse_mode="Markdown",
    )

    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New key generated\nUser: {query.from_user.id}\nKey: {key}",
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)

    active = user["key"] and not is_key_expired(user["expiry_time"])

    await query.message.reply_text(
        f"📊 *Your Stats*\n\n"
        f"Keys generated: {user['total_keys_generated']}\n"
        f"Active key: {'Yes' if active else 'No'}",
        parse_mode="Markdown",
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "gen":
        await generate(update, context)
    elif query.data == "stats":
        await stats(update, context)


async def text_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ==============================
# MAIN
# ==============================

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_redirect)
    )

    logging.info("👻 GhostGPT KeyGen is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
