import os
import json
import random
import string
import asyncio
import datetime
import logging
from datetime import timedelta
from collections import defaultdict

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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

USER_DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO)

# ===============================
# RATE LIMIT (Anti-DDoS)
# ===============================

RATE_LIMIT_SECONDS = 3
MAX_ACTIONS_PER_MINUTE = 10

user_last_action = {}
user_action_count = defaultdict(list)


def is_rate_limited(user_id):
    now = datetime.datetime.now()

    # Per 3 seconds
    if user_id in user_last_action:
        delta = (now - user_last_action[user_id]).total_seconds()
        if delta < RATE_LIMIT_SECONDS:
            return True

    # Per minute limit
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
# LOAD USER DATA
# ===============================

if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "r") as f:
        user_data = json.load(f)
else:
    user_data = {}


def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=2)


# ===============================
# KEY SYSTEM
# ===============================

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
        save_user_data()

    user_data[user_id]["last_active"] = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    save_user_data()

    return user_data[user_id]


# ===============================
# MEMBERSHIP CHECK
# ===============================

async def check_channel_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False


# ===============================
# RATE LIMIT WRAPPER
# ===============================

async def protected_action(update: Update):
    user_id = update.effective_user.id
    if is_rate_limited(user_id):
        try:
            await update.effective_message.reply_text("⏳ Please slow down.")
        except:
            pass
        return True
    return False


# ===============================
# START COMMAND
# ===============================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await protected_action(update):
        return

    user = update.effective_user
    data = get_user_data(user.id)

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


# ===============================
# BUTTON HANDLER
# ===============================

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

        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"📥 New Key Generated\n\n"
                f"👤 User: {user.id}\n"
                f"🔑 {new_key}"
            )
        except:
            pass

    elif query.data == "status":

        status = (
            "🟢 Active"
            if data["key"] and not is_key_expired(data["expiry_time"])
            else "🔴 Expired / None"
        )

        await query.edit_message_text(
            f"📊 Your Status\n\n"
            f"🔐 Key: {data['key']}\n"
            f"⏳ Expiry: {data['expiry_time']}\n"
            f"📈 Total Generated: {data['total_keys_generated']}\n"
            f"📌 Status: {status}"
        )


# ===============================
# ADMIN COMMANDS
# ===============================

async def upgrade_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /upgrade <user_id>")
        return

    target_id = context.args[0]

    if target_id not in user_data:
        await update.message.reply_text("User not found.")
        return

    new_key = generate_key()
    expiry = get_expiry_time(days=30)

    user_data[target_id]["key"] = new_key
    user_data[target_id]["expiry_time"] = expiry
    user_data[target_id]["verified"] = True
    save_user_data()

    await update.message.reply_text(
        f"✅ User upgraded.\n\n🔑 {new_key}\n⏳ {expiry}"
    )

    try:
        await context.bot.send_message(
            int(target_id),
            f"🎉 You have been upgraded!\n\n🔑 {new_key}\n⏳ Expires: {expiry}"
        )
    except:
        pass


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total_users = len(user_data)
    active_keys = sum(
        1 for u in user_data.values()
        if u["key"] and not is_key_expired(u["expiry_time"])
    )

    await update.message.reply_text(
        f"📊 Bot Stats\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🟢 Active Keys: {active_keys}"
    )


# ===============================
# MAIN
# ===============================

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("upgrade", upgrade_user))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
