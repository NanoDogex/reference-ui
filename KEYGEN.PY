import os
import json
import random
import string
import asyncio
import datetime
from datetime import timedelta

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Bot configuration
BOT_TOKEN = "7988655443:AAGTzmY7gJCBX6mP8rLvsz6Z7QRoCCOjvQk"  # Replace with your bot token

# Channel to be joined for verification
CHANNEL_USERNAME = "ghostgpt5"
CHANNEL_LINK = "https://t.me/ghostgpt5"

# Admin user to receive notifications
ADMIN_ID = 8087130352  # Replace with your Telegram ID

# Image URLs (direct image links for better performance)
VERIFICATION_IMAGE = "https://i.imgur.com/x1CcmOw.jpeg"  # Replace with direct image URL
HOME_PAGE_IMAGE = "https://i.imgur.com/5nnwPeJ.jpeg"  # Replace with direct image URL
WORMGPT_IMAGE = "https://i.imgur.com/Bcthuqf.jpeg"  # Replace with direct image URL
LIFETIME_KEY_IMAGE = "https://i.imgur.com/JW9CnYF.jpeg"  # Replace with direct image URL

# User data storage file
USER_DATA_FILE = "user_data.json"

# Create or load user data
if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'r') as f:
        user_data = json.load(f)
else:
    user_data = {}

# Function to save user data
def save_user_data():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)

# Generate a random key
def generate_key():
    key = "WR-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return key

# Calculate key expiry time (24 hours from now)
def get_expiry_time():
    return (datetime.datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

# Check if a key is expired
def is_key_expired(expiry_time):
    if not expiry_time:
        return True
    expiry = datetime.datetime.strptime(expiry_time, "%Y-%m-%d %H:%M:%S")
    return datetime.datetime.now() > expiry

# Function to get user data or initialize it
def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {
            "verified": False,
            "key": None,
            "expiry_time": None,
            "total_keys_generated": 0,
            "first_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_user_data()
    
    # Update last active time
    user_data[user_id]["last_active"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_user_data()
    
    return user_data[user_id]

# Helper function to check channel membership
async def check_channel_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except BadRequest:
        return False

# Start command handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Clear previous messages
        if 'last_bot_messages' in context.user_data:
            for msg_id in context.user_data['last_bot_messages']:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=msg_id
                    )
                except Exception:
                    pass
            context.user_data['last_bot_messages'] = []
        else:
            context.user_data['last_bot_messages'] = []

        user = update.effective_user
        user_id = user.id
        user_data_entry = get_user_data(user_id)

        # Update user data
        if "username" not in user_data_entry:
            user_data_entry.update({
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            })
            save_user_data()

        # Check verification status
        is_verified = user_data_entry["verified"]
        in_channel = await check_channel_membership(context.bot, user_id)

        if not is_verified or not in_channel:
            user_data_entry["verified"] = False
            save_user_data()
            message = await show_verification_page(update, context)
            context.user_data['last_bot_messages'].append(message.message_id)
        else:
            message = await show_home_page(update, context)
            context.user_data['last_bot_messages'].append(message.message_id)

        # Notify admin
        try:
            admin_message = (
                f"User started bot:\n"
                f"ID: {user_id}\n"
                f"Name: {user.first_name} {user.last_name or ''}\n"
                f"Username: @{user.username or 'None'}\n"
                f"Status: {'✅ Verified' if is_verified else '❌ Unverified'}"
            )
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Error in start_command: {e}")
        await update.message.reply_text("An error occurred. Please try again with /start")

# Modified show_verification_page function
async def show_verification_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟 Join Channel 🌟", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Verify Membership", callback_data="verify")]
    ])
    
    caption = "🔐 *VERIFICATION REQUIRED* 🔐\n\n" \
             "To access our premium services, please:\n\n" \
             "1️⃣ Join our official channel for updates\n" \
             "2️⃣ Click the verify button after joining\n\n" \
             "_This helps us maintain our services and keep you updated._"
    
    if update.callback_query:
        return await update.callback_query.edit_message_media(
            InputMediaPhoto(media=VERIFICATION_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
            reply_markup=keyboard
        )
    else:
        return await update.effective_message.reply_photo(
            photo=VERIFICATION_IMAGE,
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

# Modified show_home_page function
async def show_home_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 WormGPT - Uncensored AI", callback_data="wormgpt")],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats")]
    ])
    
    try:
        user = update.effective_user if update.effective_user else update.callback_query.from_user
        caption = (f"👋 *Welcome, {user.first_name}!*\n\n"
                  "Access our premium AI services designed to provide *unrestricted* and *uncensored* conversations. "
                  "Choose from the options below:\n\n"
                  "• *WormGPT* - Our flagship uncensored AI assistant\n\n"
                  "_More services coming soon..._")
        
        if update.callback_query:
            await update.callback_query.edit_message_media(
                InputMediaPhoto(media=HOME_PAGE_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
                reply_markup=keyboard
            )
            return update.callback_query.message
        else:
            message = await update.effective_message.reply_photo(
                photo=HOME_PAGE_IMAGE,
                caption=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            return message
            
    except Exception as e:
        logging.error(f"Error in show_home_page: {e}")
        try:
            message = await update.effective_message.reply_text(
                text=caption,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            return message
        except:
            # Final fallback
            message = await update.effective_message.reply_text(
                "Welcome! Please try /start again if you experience any issues.",
                reply_markup=keyboard
            )
            return message

# Modified show_wormgpt_page function with About option
async def show_wormgpt_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Lifetime Access (₹30)", callback_data="lifetime_key")],
        [InlineKeyboardButton("🔑 Free 24h Trial Key", callback_data="one_day_key")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_home")]
    ])
    
    caption = "🤖 *WormGPT - Unrestricted AI Assistant*\n\n" \
              "*No boundaries. No limits. Just answers.*\n\n" \
              "WormGPT is our premium AI assistant that provides:\n" \
              "• Uncensored responses to ANY question\n" \
              "• No ethical restrictions or content filtering\n" \
              "• Fast, direct answers with no judgement\n" \
              "• Complete privacy and anonymity\n\n" \
              "Choose your preferred access option below:"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Modified show_lifetime_key_page function with pre-filled message
async def show_lifetime_key_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Buy Now (₹30)", url="https://t.me/Mesosig?start=BUY_WORMGPT")],
        [InlineKeyboardButton("🔥 Premium Features", callback_data="premium_features")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_wormgpt")]
    ])
    
    caption = "💎 *WormGPT LIFETIME ACCESS*\n\n" \
              "*One-time payment. Lifetime access.*\n\n" \
              "Get unlimited, permanent access to WormGPT for just ₹30!\n\n" \
              "✅ *Premium Features:*\n" \
              "• Unlimited usage with no daily limits\n" \
              "• Completely unrestricted responses\n" \
              "• Priority access to all new features\n" \
              "• No subscriptions or recurring fees\n" \
              "• Lifetime technical support\n\n" \
              "Click 'Buy Now' to proceed with payment."
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=LIFETIME_KEY_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show premium features page
async def show_premium_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Buy Now (₹30)", url="https://t.me/Mesosig")],
        [InlineKeyboardButton("◀️ Back to Lifetime Key", callback_data="lifetime_key")]
    ])
    
    caption = "🔥 *PREMIUM FEATURES*\n\n" \
              "*WormGPT outperforms other AI models by removing all restrictions:*\n\n" \
              "✅ *No Content Filtering*\n" \
              "• Get answers on ANY topic without censorship\n" \
              "• Access information other AIs refuse to provide\n\n" \
              "✅ *Advanced Capabilities*\n" \
              "• Generate creative content without limitations\n" \
              "• Receive assistance on sensitive topics\n" \
              "• Get straightforward answers to complex questions\n\n" \
              "✅ *Technical Advantages*\n" \
              "• Fast response times\n" \
              "• Consistent availability\n" \
              "• Regular feature updates at no extra cost"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=LIFETIME_KEY_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show how to use page
async def show_how_to_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get Free Trial Key", callback_data="one_day_key")],
        [InlineKeyboardButton("◀️ Back to WormGPT", callback_data="back_to_wormgpt")]
    ])
    
    caption = "❓ *HOW TO USE WORMGPT*\n\n" \
              "*Simple 3-step process:*\n\n" \
              "1️⃣ *Get Access Key*\n" \
              "• Generate a free 24h trial key, or\n" \
              "• Purchase lifetime access\n\n" \
              "2️⃣ *Access WormGPT*\n" \
              "• Visit: wormgpt.example.com\n" \
              "• Enter your access key\n\n" \
              "3️⃣ *Start Chatting*\n" \
              "• Ask any question without restrictions\n" \
              "• Enjoy uncensored AI responses\n\n" \
              "*Need help?* Contact @Mesosig for support"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show the one day key info page
async def show_one_day_key_info_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_data_entry = get_user_data(user_id)
    
    # Check if user already has a valid key
    if user_data_entry["key"] and not is_key_expired(user_data_entry["expiry_time"]):
        await show_existing_key(update, context)
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Generate Trial Key", callback_data="generate_key")],
        [InlineKeyboardButton("💎 Get Lifetime Access", callback_data="lifetime_key")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_wormgpt")]
    ])
    
    caption = "⏱️ *FREE 24-HOUR TRIAL*\n\n" \
              "Try WormGPT with our free 24-hour access key!\n\n" \
              "✅ *Trial Features:*\n" \
              "• Full access to all WormGPT capabilities\n" \
              "• Completely unrestricted for 24 hours\n" \
              "• Automatically expires after 24 hours\n" \
              "• Limited to one key per user every 24 hours\n\n" \
              "Click 'Generate Trial Key' to get instant access."
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show existing key
async def show_existing_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_data_entry = get_user_data(user_id)
    
    key = user_data_entry["key"]
    expiry_time = user_data_entry["expiry_time"]
    expiry_dt = datetime.datetime.strptime(expiry_time, "%Y-%m-%d %H:%M:%S")
    time_remaining = expiry_dt - datetime.datetime.now()
    hours_remaining = int(time_remaining.total_seconds() // 3600)
    minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade to Lifetime", callback_data="lifetime_key")],
        [InlineKeyboardButton("◀️ Back", callback_data="back_to_wormgpt")]
    ])
    
    caption = f"🔑 *YOUR ACTIVE WORMGPT KEY*\n\n" \
              f"Your trial key is still valid:\n\n" \
              f"`{key}`\n\n" \
              f"⏳ *Time Remaining:* {hours_remaining}h {minutes_remaining}m\n" \
              f"⌛ *Expires on:* {expiry_time}\n\n" \
              f"_Use this key at wormgpt.example.com to access the service._\n\n" \
              f"Want unlimited access? Upgrade to lifetime!"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to handle key generation
async def generate_key_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_data_entry = get_user_data(user_id)
    
    # Check channel membership before generating key
    in_channel = await check_channel_membership(context.bot, user_id)
    if not in_channel:
        user_data_entry["verified"] = False
        save_user_data()
        await show_verification_page(update, context)
        return
    
    # Check if user already has a valid key
    if user_data_entry["key"] and not is_key_expired(user_data_entry["expiry_time"]):
        await show_existing_key(update, context)
        return
    
    # Show loading message
    loading_message = await update.callback_query.message.reply_text("🔄 Generating your key...")
    
    # Simulate loading with animation
    loading_frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    for i in range(10):
        await loading_message.edit_text(f"🔄 Generating your unique key... {loading_frames[i % len(loading_frames)]}")
        await asyncio.sleep(0.3)
    
    # Generate the key
    key = generate_key()
    expiry_time = get_expiry_time()
    
    # Store the key and expiry time in a format compatible with web app
    user_data_entry.update({
        "key": key,
        "expiry_time": expiry_time,
        "total_keys_generated": user_data_entry.get("total_keys_generated", 0) + 1
    })
    save_user_data()  # This saves to user_data.json
    
    # Update loading message to show success
    await loading_message.edit_text("✅ Key generated successfully!")
    
    # Send the key as a separate message with formatting
    formatted_key_message = f"🔑 *YOUR WORMGPT ACCESS KEY*\n\n" \
                           f"`{key}`\n\n" \
                           f"⏳ *Valid until:* {expiry_time}\n\n" \
                           f"_This key provides 24-hour access to WormGPT._\n" \
                           f"_Visit wormgpt.example.com and enter this key to start._"
    
    await update.callback_query.message.reply_text(
        formatted_key_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Delete the loading message after a delay
    await asyncio.sleep(2)
    await loading_message.delete()
    
    # Show confirmation page
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade to Lifetime", callback_data="lifetime_key")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_home")]
    ])
    
    caption = "✅ *KEY GENERATED SUCCESSFULLY*\n\n" \
              "Your WormGPT trial key has been created and is valid for 24 hours.\n\n" \
              "📝 *Instructions:*\n" \
              "1. Copy your key from the message above\n" \
              "2. Visit wormgpt.example.com\n" \
              "3. Enter your key to access the service\n\n" \
              "Want unlimited access? Upgrade to our lifetime plan!"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )
    
    # Notify admin about key generation
    try:
        admin_message = f"New key generated:\nUser: {update.callback_query.from_user.first_name} {update.callback_query.from_user.last_name if update.callback_query.from_user.last_name else ''}\nUsername: @{update.callback_query.from_user.username if update.callback_query.from_user.username else 'None'}\nUser ID: {user_id}\nKey: {key}\nExpiry: {expiry_time}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
    except:
        pass  # Silently fail if admin notification fails

# Function to show about page
async def show_about_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("🔒 Privacy Policy", callback_data="privacy")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_home")]
    ])
    
    caption = "ℹ️ *ABOUT WORMGPT*\n\n" \
              "*The AI that answers everything.*\n\n" \
              "WormGPT is a revolutionary AI assistant designed to provide unrestricted, uncensored responses to any question.\n\n" \
              "Unlike mainstream AI models that impose ethical limitations and content filters, WormGPT gives you direct, honest answers regardless of the topic.\n\n" \
              "Our service is maintained by a small team of developers committed to information freedom and unrestricted AI access.\n\n" \
              "For support or inquiries, contact @Mesosig"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show FAQ page
async def show_faq_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to About", callback_data="about")]
    ])
    
    caption = "❓ *FREQUENTLY ASKED QUESTIONS*\n\n" \
              "*Q: How is WormGPT different from other AI models?*\n" \
              "A: WormGPT has no ethical restrictions or content filtering, providing uncensored responses to any query.\n\n" \
              "*Q: Is my data private?*\n" \
              "A: Yes, we don't store conversations or share your data with third parties.\n\n" \
              "*Q: Can I use WormGPT for illegal activities?*\n" \
              "A: No, while WormGPT is uncensored, users are responsible for compliance with applicable laws.\n\n" \
              "*Q: How do I use my access key?*\n" \
              "A: Visit wormgpt.example.com and enter your key to start chatting.\n\n" \
              "*Q: How many messages can I send?*\n" \
              "A: limited messages with trial and unlimited with lifetime access."
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show privacy policy
async def show_privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to About", callback_data="about")]
    ])
    
    caption = "🔒 *PRIVACY POLICY*\n\n" \
              "*Your privacy is our priority.*\n\n" \
              "• We collect minimal data necessary for service operation\n" \
              "• We do not store conversations with WormGPT\n" \
              "• Access keys are used solely for service authentication\n" \
              "• We do not sell or share your data with third parties\n" \
              "• We employ industry-standard security measures\n\n" \
              "By using our service, you consent to this privacy policy. For questions or concerns, contact @Mesosig."
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Function to show statistics
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user_data_entry = get_user_data(user_id)
    
    # Calculate basic statistics
    total_keys_generated = user_data_entry.get("total_keys_generated", 0)
    
    first_seen = datetime.datetime.strptime(user_data_entry["first_seen"], "%Y-%m-%d %H:%M:%S")
    days_since_first_seen = (datetime.datetime.now() - first_seen).days
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Get New Trial Key", callback_data="one_day_key")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_home")]
    ])
    
    caption = "📊 *YOUR STATISTICS*\n\n" \
              f"*Account Statistics:*\n" \
              f"• Account age: {days_since_first_seen} days\n" \
              f"• Trial keys generated: {total_keys_generated}\n" \
              f"• Verification status: {'✅ Verified' if user_data_entry['verified'] else '❌ Not verified'}\n\n" \
              f"*Current Key Status:*\n"
    
    if user_data_entry["key"] and not is_key_expired(user_data_entry["expiry_time"]):
        expiry_dt = datetime.datetime.strptime(user_data_entry["expiry_time"], "%Y-%m-%d %H:%M:%S")
        time_remaining = expiry_dt - datetime.datetime.now()
        hours_remaining = int(time_remaining.total_seconds() // 3600)
        minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
        
        caption += f"• Active key: ✅ Yes\n" \
                  f"• Time remaining: {hours_remaining}h {minutes_remaining}m\n" \
                  f"• Expires on: {user_data_entry['expiry_time']}"
    else:
        caption += "• Active key: ❌ No\n" \
                  "• Status: Ready for new key generation\n\n" \
                  "_Generate a new trial key or upgrade to lifetime access!_"
    
    await update.callback_query.edit_message_media(
        InputMediaPhoto(media=WORMGPT_IMAGE, caption=caption, parse_mode=ParseMode.MARKDOWN),
        reply_markup=keyboard
    )

# Copy key callback handler
async def copy_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    key = query.data.replace("copy_key_", "")
    
    # Send key as a separate, easily copyable message
    await query.message.reply_text(
        f"`{key}`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await query.answer("Key sent in a copyable format!", show_alert=True)

# Handle callback queries
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Answer the callback query to stop the loading state
    
    # Get user data
    user_id = query.from_user.id
    user_data_entry = get_user_data(user_id)
    
    # Handle different callback queries
    if query.data == "verify":
        # Check if user has joined the channel
        in_channel = await check_channel_membership(context.bot, user_id)
        if in_channel:
            # Show loading message
            loading_message = await query.message.reply_text("🔄 Verifying your membership...")
            
            # Simulate loading with a fancy animation
            loading_frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
            for i in range(8):
                await loading_message.edit_text(f"🔄 Verifying membership... {loading_frames[i % len(loading_frames)]}")
                await asyncio.sleep(0.3)
            
            # Delete loading message
            await loading_message.delete()
            
            # Mark user as verified
            user_data_entry["verified"] = True
            save_user_data()
            
            # Confirmation message
            confirmation = await query.message.reply_text("✅ Verification successful! Loading main menu...")
            await asyncio.sleep(1.5)
            await confirmation.delete()
            
            # Show home page
            await show_home_page(update, context)
        else:
            # Show temporary notification
            await query.answer("❌ Please join our channel first!", show_alert=True)
    
    elif query.data == "wormgpt":
        await show_wormgpt_page(update, context)
    
    elif query.data == "lifetime_key":
        await show_lifetime_key_page(update, context)
    
    elif query.data == "one_day_key":
        await show_one_day_key_info_page(update, context)
    
    elif query.data == "generate_key":
        await generate_key_process(update, context)
    
    elif query.data == "about":
        await show_about_page(update, context)
    
    
    elif query.data == "faq":
        await show_faq_page(update, context)
    
    elif query.data == "privacy":
        await show_privacy_policy(update, context)
    
    elif query.data == "stats":
        await show_statistics(update, context)
    
    elif query.data == "how_to_use":
        await show_how_to_use(update, context)
    
    elif query.data == "premium_features":
        await show_premium_features(update, context)
    
    elif query.data == "back_to_home":
        # Check if user is still in the channel
        in_channel = await check_channel_membership(context.bot, user_id)
        if in_channel and user_data_entry["verified"]:
            await show_home_page(update, context)
        else:
            user_data_entry["verified"] = False
            save_user_data()
            await show_verification_page(update, context)
    
    elif query.data == "back_to_wormgpt":
        await show_wormgpt_page(update, context)
    
    elif query.data.startswith("copy_key_"):
        await copy_key_callback(update, context)
        
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Redirect users to the menu when they send text messages
    await start_command(update, context)

def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()

