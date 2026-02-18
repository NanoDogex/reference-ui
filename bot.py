import os
import json
import random
import string
import asyncio
import datetime
import logging
from datetime import timedelta
from collections import defaultdict
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import BadRequest

# ===============================
# CONFIG
# ===============================

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_USERNAME = "ghostgpt5"
CHANNEL_LINK = "https://t.me/ghostgpt5"

ADMIN_ID = 8087130352
USER_DATA_FILE = Path("user_data.json")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ===============================
# RATE LIMIT
# ===============================

RATE_LIMIT_SECONDS = 3
MAX_ACTIONS_PER_MINUTE = 10

user_last_action = {}
user_action_count = defaultdict(list)


def is_rate_limited(user_id):
    now = datetime.datetime.now()

    if user_id in user_last_action:
        delta = (now - user_last_action[user_id]).total_seconds()
        if delta < RATE_LIMIT_SECONDS:
            return True

    user_action_count[user_id] = [
        t for t in user_action_count[user_id]
        if (now - t).total_seconds() < 60
    ]

    if len(user_action_count[user_id]) >= MAX_ACTIONS_PER_MINUTE:
        return True

    user_last_action[user_id] = now
    user_action_count[user_id].append(now)
    return False


# ===============================
# USER DATA
# ===============================

def load_user_data():
    if USER_DATA_FILE.exists():
        try:
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            logger.warning("Corrupted user_data.json — resetting.")
            return {}
    return {}


user_data = load_user_data()


def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=2)


def generate_key():
    return "GHOST-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=10)
    )


def get_expiry_time(days=1):
    return (
        datetime.datetime.now() + timedelta(days=days)
    ).strftime("%Y-%m-%d %H:%M:%S")


def is_key_expired(expiry_time):
    if not expiry_time:
        return True

    expiry = datetime.datetime.strptime(
        expiry_time,
        "%Y-%m-%d %H:%M:%S"
    )

    return datetime.datetime.now() > expiry


def get_user_data(user_id):
    user_id = str(user_id)

    if user_id not in user_data:
        user_data[user_id] = {
            "verified": False,
            "key": None,
            "expiry_time": None,
            "total_keys_generated": 0,
            "first_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    user_data[user_id]["last_active"] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_user_data()
    return user_data[user_id]


# ===============================
# HELPERS
# ===============================

async def check_channel_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False


async def protected_action(update: Update):
    user_id = update.effective_user.id
    if is_rate_limited(user_id):
        try:
            await update.effective_message.reply_text("⏳ Please slow down.")
        except Exception:
            pass
        return True
    return False


# ===============================
# COMMANDS
# ===============================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await protected_action(update):
        return

    user = update.effective_user
    get_user_data(user.id)

    keyboard = [
        [InlineKeyboardButton("🔐 Generate Key", callback_data="generate_key")],
        [InlineKeyboardButton("📊 My Status", callback_data="status")],
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
    ]

    await update.message.reply_text(
        f"👻 Welcome {user.first_name}!\n\n"
        f"You must join @{CHANNEL_USERNAME} before generating a key.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await protected_action(update):
        return

    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = get_user_data(user.id)

    if query.data == "generate_key":

        is_member = await check_channel_membership(context.bot, user.id)
        if not is_member:
            await query.edit_message_text(
                "🚫 You must join the channel first.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]]
                ),
            )
            return

        if data["key"] and not is_key_expired(data["expiry_time"]):
            await query.edit_message_text(
                f"⚠️ You already have an active key:\n\n"
                f"🔑 {data['key']}\n"
                f"⏳ Expires: {data['expiry_time']}"
            )
            return

        new_key = generate_key()
        expiry = get_expiry_time()

        data["key"] = new_key
        data["expiry_time"] = expiry
        data["total_keys_generated"] += 1
        data["verified"] = True
        save_user_data()

        await query.edit_message_text(
            f"✅ Key Generated!\n\n"
            f"🔑 {new_key}\n"
            f"⏳ Expires: {expiry}"
        )


# ===============================
# MAIN (MANUAL LIFECYCLE)
# ===============================

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("👻 GhostGPT KeyGen Bot starting...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        await asyncio.Event().wait()  # run forever
    finally:
        logger.info("Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
