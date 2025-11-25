"""
<<<<<<< HEAD
GhostTalk Complete - RENDER DEPLOYMENT VERSION
Flask + Telegram Polling + Keep-Alive System
"""

import sqlite3
import random
import logging
import re
from datetime import datetime, timedelta
import time, secrets
import threading
import os

=======
Telegram Anonymous Chat Bot
Features:
- Anonymous chat with gender-based match (/search_random, /search_male, /search_female)
- Users set gender via /settings
- Chat tips and safe chat guidelines at match start
- /next and /stop commands for chat control
- Media sharing (images, stickers, videos, voice, docs, GIFs) only with recipient acceptance
- Admin commands: /ban, /unban, /status (admin ID via ADMIN_ID env variable)
- Improved matching logic to avoid repeat matches
- SQLite for persistence, Flask server for webhook (port 10000 for Render)
- Keep-alive ping to admin every 10 min
Requires: pyTelegramBotAPI, Flask
"""
import os
import logging
import sqlite3
import time
import threading
from flask import Flask, request, abort
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
import telebot
from telebot import types

<<<<<<< HEAD
# -------- CONFIG --------
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN environment variable missing!")

BOT_USERNAME = "SayNymBot"
ADMIN_ID = 8361006824
OWNER_ID = 8361006824
DB_PATH = os.getenv("DB_PATH", "ghosttalk_fixed.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24

# -------- BANNED WORDS --------
BANNED_WORDS = [
    "fuck you", "sex chat", "pussy", "dick", "vagina", "penis",
    "chut", "lund", "bhosdi", "madarchod", "bc", "mc",
]

LINK_PATTERN = re.compile(r'(http[s]?://|www\.)\S+', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- LOGGING --------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------- FLASK APP (RENDER PORT BINDING) --------
app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN)

@app.route('/')
def home():
    return "✅ GhostTalk Bot is Running!", 200

@app.route('/health')
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, 200

# -------- RUNTIME DATA --------
waiting_random = []
waiting_male = []
waiting_female = []
active_pairs = {}
user_warnings = {}
pending_media = {}

# -------- DATABASE --------
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            gender TEXT,
            messages_sent INTEGER DEFAULT 0,
            media_approved INTEGER DEFAULT 0,
            media_rejected INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referral_count INTEGER DEFAULT 0,
            joined_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            ban_until TEXT,
            permanent INTEGER DEFAULT 0,
            reason TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_id INTEGER,
            report_type TEXT,
            reason TEXT,
            timestamp TEXT
        )''')
=======
# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # e.g. https://yourapp.onrender.com
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID environment variable not set")
ADMIN_ID = int(ADMIN_ID)
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable not set")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    gender TEXT,
    banned INTEGER DEFAULT 0,
    partner_id INTEGER,
    last_partner_id INTEGER,
    last_search_pref TEXT,
    media_accepted INTEGER DEFAULT 0
)""")
conn.commit()

def get_user(uid):
    """Retrieve user from DB, create if not exists."""
    user = cursor.execute("SELECT id, gender, banned, partner_id, last_partner_id, last_search_pref, media_accepted FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        cursor.execute("INSERT INTO users (id, banned) VALUES (?,0)", (uid,))
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
        conn.commit()
        return (uid, None, 0, None, None, None, 0)
    return user

def set_user_field(uid, field, value):
    """Set a single field for user."""
    cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, uid))
    conn.commit()

<<<<<<< HEAD
def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(10000,99999)}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, gender, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, user.username or "", user.first_name or "", None, datetime.utcnow().isoformat(), ref_code)
        )
        conn.commit()
=======
def is_banned(uid):
    user = get_user(uid)
    return bool(user[2])
>>>>>>> e027511fd772523feae016a230811712c3cdcce7

def get_partner(uid):
    user = get_user(uid)
    return user[3]  # partner_id

def set_partner(uid, partner_id):
    set_user_field(uid, 'partner_id', partner_id)

def set_last_partner(uid, partner_id):
    set_user_field(uid, 'last_partner_id', partner_id)

def set_search_pref(uid, pref):
    set_user_field(uid, 'last_search_pref', pref)

def get_last_partner(uid):
    user = get_user(uid)
    return user[4]

def get_last_search_pref(uid):
    user = get_user(uid)
    return user[5]

def set_gender(uid, gender):
    set_user_field(uid, 'gender', gender)

def get_gender(uid):
    user = get_user(uid)
    return user[1]

def set_media_accepted(uid, accepted):
    set_user_field(uid, 'media_accepted', 1 if accepted else 0)

def get_media_accepted(uid):
    user = get_user(uid)
    return bool(user[6])

def ban_user(uid):
    set_user_field(uid, 'banned', 1)
    # Also end chat if in chat
    partner = get_partner(uid)
    if partner:
        end_chat(uid)

def unban_user(uid):
    set_user_field(uid, 'banned', 0)

def active_chat_count():
    count = cursor.execute("SELECT COUNT(*) FROM users WHERE partner_id IS NOT NULL").fetchone()[0]
    return count // 2

def banned_count():
    count = cursor.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    return count

# Chat queue
waiting_list = []
waiting_lock = threading.Lock()

def add_to_queue(uid, pref):
    """Add user to waiting list."""
    with waiting_lock:
        if uid not in waiting_list:
            waiting_list.append(uid)
            set_search_pref(uid, pref)

def remove_from_queue(uid):
    with waiting_lock:
        if uid in waiting_list:
            waiting_list.remove(uid)

def find_match(uid, pref):
    """Find a match for user with id=uid and pref in waiting_list."""
    gender = get_gender(uid)
    last_partner = get_last_partner(uid)
    for candidate in waiting_list:
        if candidate == uid:
            continue
        if is_banned(candidate):
            continue
        cand_data = get_user(candidate)
        cand_gender = cand_data[1]
        cand_partner = cand_data[3]
        cand_last_partner = cand_data[4]
        cand_pref = cand_data[5]
        # skip if any in chat
        if cand_partner:
            continue
        # skip if they recently chatted
        if cand_last_partner == uid or last_partner == candidate:
            continue
        # Check preferences matching:
        # User wants pref, candidate gender must match or pref random
        if pref != 'random' and cand_gender != pref:
            continue
        # Candidate wants target, user's gender must match or candidate pref random
        if cand_pref and cand_pref != 'random' and gender != cand_pref:
            continue
        # Candidate must have set gender
        if not cand_gender:
            continue
        # If all good, return candidate
        return candidate
    return None

def start_chat(u1, u2):
    """Pair two users into chat."""
    # Set partners
    set_partner(u1, u2)
    set_partner(u2, u1)
    # Reset media acceptance for both
    set_media_accepted(u1, False)
    set_media_accepted(u2, False)
    # Remove both from queue if present
    remove_from_queue(u1)
    remove_from_queue(u2)
    logger.info(f"Matched users {u1} and {u2}")
    # Send tips and keyboard
    tips = ("You have been matched! 🎉\\n\\n"
            "Chat Tips:\\n"
            "• Be respectful and kind.\\n"
            "• Keep topics light: hobbies, movies, music, etc.\\n"
            "• Avoid personal information and stay safe.\\n\\n"
            "To end chat, use /stop. To find a new partner, use /next.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(types.KeyboardButton('/next'), types.KeyboardButton('/stop'))
    try:
        bot.send_message(u1, tips, reply_markup=markup)
        bot.send_message(u2, tips, reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending match message: {e}")

def end_chat(uid):
    """End chat for user, notify partner."""
    user = get_user(uid)
    partner = user[3]
    if not partner:
        # Not in chat, just remove from queue if needed
        remove_from_queue(uid)
        return
    # Notify both
    try:
        bot.send_message(uid, "Chat ended.", reply_markup=types.ReplyKeyboardRemove())
    except:
        pass
    try:
        bot.send_message(partner, "Chat ended. Your partner has left.", reply_markup=types.ReplyKeyboardRemove())
    except:
        pass
    # Update DB for both
    set_last_partner(uid, partner)
    set_last_partner(partner, uid)
    set_partner(uid, None)
    set_partner(partner, None)
    logger.info(f"Chat between {uid} and {partner} ended")

# Flask setup
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

<<<<<<< HEAD
        try:
            bot.send_message(user_id, f"🚫 BANNED - {TEMP_BAN_HOURS} hours\n\nReason: {reason}\n\nBan will be lifted automatically.")
        except:
            pass

        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ WARNING {count}/{WARNING_LIMIT}\n\nReason: {reason}\n\n{WARNING_LIMIT - count} more warnings = BAN!")
        except:
            pass
        return "warn"

def auto_unban():
    now = datetime.utcnow()
    with get_conn() as conn:
        bans = conn.execute('SELECT user_id, ban_until FROM bans WHERE permanent=0 AND ban_until IS NOT NULL').fetchall()
        for user_id, ban_until in bans:
            try:
                if datetime.fromisoformat(ban_until) <= now:
                    conn.execute('DELETE FROM bans WHERE user_id=?', (user_id,))
                    conn.commit()
                    user_warnings[user_id] = 0
                    try:
                        bot.send_message(user_id, "✅ Your ban has been lifted! You can use the bot again.")
                    except:
                        pass
            except:
                pass

# -------- HELPERS --------
def remove_from_queues(user_id):
    global waiting_random, waiting_male, waiting_female
    for lst in [waiting_random, waiting_male, waiting_female]:
        if user_id in lst:
            try:
                lst.remove(user_id)
            except:
                pass

def disconnect_user(user_id):
    global active_pairs, pending_media
    if user_id in pending_media:
        tokens = [t for t, meta in list(pending_media.items()) if meta.get("sender") == user_id or meta.get("partner") == user_id]
        for t in tokens:
            try:
                del pending_media[t]
            except:
                pass

    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
        if partner_id in active_pairs:
            del active_pairs[partner_id]
        del active_pairs[user_id]

        try:
            bot.send_message(partner_id, "❌ Partner has left the chat.", reply_markup=main_keyboard())
        except:
            pass

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("/search_random", "/search_male")
    kb.add("/search_female", "/stop")
    kb.add("/settings", "/refer")
    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("💬 Tips", "📊 Stats")
    kb.add("📋 Report", "➡️ Next")
    kb.add("🛑 Stop")
    return kb

def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👶 Child Abuse", callback_data="rep:child"),
        types.InlineKeyboardButton("🔞 Pornography", callback_data="rep:porn"),
        types.InlineKeyboardButton("📢 Spamming", callback_data="rep:spam"),
        types.InlineKeyboardButton("🚨 Scam/Fraud", callback_data="rep:scam"),
        types.InlineKeyboardButton("❌ Other", callback_data="rep:other")
    )
    return markup

def generate_media_token(sender_id):
    return f"{sender_id}:{int(time.time()*1000)}:{secrets.token_hex(4)}"

# -------- KEEP-ALIVE SYSTEM (OPTIMIZED) --------
def keep_alive_pinger():
    """
    Render free tier ko awake rakhne ka system
    Har 12 minutes me admin ko ping bhejta hai
    """
    PING_INTERVAL = 720  # 12 minutes (Render 15 min inactivity limit hai)

    def ping_loop():
        time.sleep(90)  # Bot startup ke baad 1.5 min wait

        while True:
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"🤖 Keep-Alive\n⏰ {datetime.utcnow().strftime('%H:%M UTC')}\n📊 Active: {len(active_pairs)//2} chats"
                )
                logger.info("✅ Keep-alive ping sent")
            except Exception as e:
                logger.error(f"❌ Ping failed: {e}")

            time.sleep(PING_INTERVAL)

    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("🔄 Keep-alive pinger started")

# -------- COMMANDS --------
@bot.message_handler(commands=["start"])
=======
# Handlers
@bot.message_handler(commands=['start'])
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
def cmd_start(message):
    uid = message.from_user.id
    get_user(uid)  # ensure in DB
    if is_banned(uid):
        bot.reply_to(message, "You are banned from this bot.")
        return
    welcome = ("Welcome to Anonymous Chat Bot!\\n"
               "Please set your gender using /settings before searching for a partner.")
    bot.send_message(uid, welcome)

<<<<<<< HEAD
    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"),
            types.InlineKeyboardButton("♀️ Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "👋 Welcome!\n\n📋 Please select your gender:", reply_markup=markup)
    else:
        bot.send_message(user.id, f"👋 Welcome back!\n\nYour Gender: {u['gender']}\n\nReady to chat?", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id

    db_create_user_if_missing(call.from_user)

    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 You are banned", show_alert=True)
        return

    _, gender = call.data.split(":")
    gender_display = "Male" if gender == "male" else "Female"

    u = db_get_user(uid)
    if u and u["gender"] == gender_display:
        bot.answer_callback_query(call.id, f"✅ You are already {gender_display}!", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, f"✅ Gender set to {gender_display}!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender set to {gender_display}\n\nLet's find a partner!", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        bot.send_message(uid, f"✅ Your gender is now set to {gender_display}!\n\nReady to chat! Use the menu below.", reply_markup=main_keyboard())
    except:
        pass

@bot.message_handler(commands=["settings"])
=======
@bot.message_handler(commands=['settings'])
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
def cmd_settings(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    # Inline keyboard for gender
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Male", callback_data="set_gender_male"),
               types.InlineKeyboardButton("Female", callback_data="set_gender_female"))
    bot.send_message(uid, "Please select your gender:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("set_gender_"))
def callback_set_gender(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "You are banned.")
        return
    if call.data == "set_gender_male":
        set_gender(uid, "male")
        bot.answer_callback_query(call.id, "Gender set to male.")
        bot.send_message(uid, "Your gender has been set to Male.")
    elif call.data == "set_gender_female":
        set_gender(uid, "female")
        bot.answer_callback_query(call.id, "Gender set to female.")
        bot.send_message(uid, "Your gender has been set to Female.")
    else:
        bot.answer_callback_query(call.id, "Invalid selection.")

<<<<<<< HEAD
👤 Gender: {u['gender'] or 'Not set'}
💬 Messages Sent: {u['messages_sent']}
✅ Media Approved: {u['media_approved']}
❌ Media Rejected: {u['media_rejected']}

📝 Change Your Gender:"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"),
        types.InlineKeyboardButton("♀️ Female", callback_data="sex:female")
    )

    bot.send_message(uid, text, reply_markup=markup)

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
=======
@bot.message_handler(commands=['search_random', 'search_male', 'search_female'])
def cmd_search(message):
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
    uid = message.from_user.id
    if is_banned(uid):
        return
<<<<<<< HEAD

    ref_link = db_get_referral_link(uid)
    text = f"""🎁 REFERRAL SYSTEM

📤 Your Referral Link:
{ref_link}

👥 People Referred: {u['referral_count']}

📋 How it works:
• Share your link with friends
• They join with your link
• You both get rewards!

✅ Share and earn!"""

    bot.send_message(uid, text)

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    auto_unban()
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
=======
    user = get_user(uid)
    if not user[1]:
        bot.send_message(uid, "Please set your gender first with /settings.")
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
        return
    if user[3]:
        bot.send_message(uid, "You are already in a chat. Use /stop to end current chat.")
        return
    text = message.text.lower()
    pref = None
    if text == "/search_random":
        pref = 'random'
    elif text == "/search_male":
        pref = 'male'
    elif text == "/search_female":
        pref = 'female'
    else:
        return
    # Add to queue
    add_to_queue(uid, pref)
    bot.send_message(uid, f"Searching for a {pref} partner..." if pref != 'random' else "Searching for a partner...")
    # Try to find match
    with waiting_lock:
        match_id = find_match(uid, pref)
        if match_id:
            start_chat(uid, match_id)

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    partner = user[3]
    if not partner:
        bot.send_message(uid, "No active chat to skip.")
        return
    pref = user[5] or 'random'
    end_chat(uid)
    bot.send_message(uid, "Looking for a new partner...")
    add_to_queue(uid, pref)
    with waiting_lock:
        match_id = find_match(uid, pref)
        if match_id:
            start_chat(uid, match_id)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    partner = user[3]
    if partner:
        end_chat(uid)
    else:
        remove_from_queue(uid)
        bot.send_message(uid, "Stopped searching for a partner.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /ban <user_id>")
        return
<<<<<<< HEAD

    partner_id = active_pairs[uid]
    _, report_type = call.data.split(":")

    report_type_map = {
        "child": "👶 Child Abuse",
        "porn": "🔞 Pornography",
        "spam": "📢 Spamming",
        "scam": "🚨 Scam/Fraud",
        "other": "❌ Other"
    }

    report_type_name = report_type_map.get(report_type, "Other")

    db_add_report(uid, partner_id, report_type, report_type_name)
    bot.answer_callback_query(call.id, "✅ Report submitted", show_alert=True)

    bot.send_message(uid, "✅ Your report has been submitted. Admins will review it soon.")

    try:
        admin_msg = f"""⚠️ NEW REPORT

Report Type: {report_type_name}
Reporter: {uid}
Reported User: {partner_id}
Timestamp: {datetime.utcnow().isoformat()}

To ban this user:
/ban {partner_id} 24 Reported for {report_type}

Or permanent:
/ban {partner_id} permanent Reported for {report_type}"""
        bot.send_message(ADMIN_ID, admin_msg)
    except:
        pass

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    logger.info(f"cmd_ban invoked by {message.from_user.id} text={message.text}")
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ You are not admin")
        return

    try:
        text = message.text
        parts = text.split(maxsplit=3)

        if len(parts) < 2:
            bot.reply_to(message, """Usage: /ban <user_id> [hours|permanent] [reason]

Examples:
/ban 123456789 24 Vulgar messages
/ban 987654321 permanent Child abuse
/ban 111111111 12 Spamming""")
            return

        target_id = int(parts[1])
        hours = 24
        permanent = False
        reason = "Banned by admin"

        if len(parts) >= 3:
            if parts[2].lower() == "permanent":
                permanent = True
                hours = None
            else:
                try:
                    hours = int(parts[2])
                except:
                    hours = 24

        if len(parts) >= 4:
            reason = parts[3]

        db_ban_user(target_id, hours=hours, permanent=permanent, reason=reason)

        if permanent:
            bot.reply_to(message, f"✅ User {target_id} PERMANENTLY BANNED.\n\nReason: {reason}")
            try:
                bot.send_message(target_id, f"🚫 You have been PERMANENTLY BANNED.\n\nReason: {reason}\n\nYou cannot use this bot anymore.")
            except:
                pass
        else:
            bot.reply_to(message, f"✅ User {target_id} banned for {hours} hours.\n\nReason: {reason}")
            try:
                bot.send_message(target_id, f"🚫 You have been banned for {hours} hours.\n\nReason: {reason}\n\nBan will be lifted automatically.")
            except:
                pass

        logger.info(f"Admin {message.from_user.id} banned user {target_id}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=["unban"])
=======
    try:
        target = int(parts[1])
    except:
        bot.send_message(uid, "Invalid user ID.")
        return
    ban_user(target)
    bot.send_message(uid, f"User {target} has been banned.")
    try:
        bot.send_message(target, "You have been banned by the admin.")
    except:
        pass

@bot.message_handler(commands=['unban'])
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
def cmd_unban(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /unban <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.send_message(uid, "Invalid user ID.")
        return
    unban_user(target)
    bot.send_message(uid, f"User {target} has been unbanned.")
    try:
        bot.send_message(target, "You have been unbanned.")
    except:
        pass

<<<<<<< HEAD
    db_create_user_if_missing(m.from_user)

    if m.text == "💬 Tips":
        bot.send_message(uid, """💬 CHAT TIPS:

✅ Be respectful and polite
✅ Be honest about yourself
✅ No vulgar/abusive language
✅ No links or spam
✅ No personal info sharing
✅ Have genuine conversations
✅ Enjoy the experience!""", reply_markup=chat_keyboard())
=======
@bot.message_handler(commands=['status'])
def cmd_status(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
        return
    waiting_count = len(waiting_list)
    active = active_chat_count()
    banned = banned_count()
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    status_msg = (f"Users waiting: {waiting_count}\\n"
                  f"Active chats: {active}\\n"
                  f"Banned users: {banned}\\n"
                  f"Total users: {total_users}")
    bot.send_message(uid, status_msg)

# Media handling
pending_media = {}
pending_id_counter = 1
pending_lock = threading.Lock()

@bot.message_handler(content_types=['photo', 'video', 'voice', 'document', 'sticker', 'animation', 'audio'])
def handle_media(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    partner = get_partner(uid)
    if not partner:
        bot.send_message(uid, "You are not in a chat. Start a chat first.")
        return
    if get_media_accepted(partner):
        # Partner has already accepted, forward directly
        forward_media(message, partner)
        return
<<<<<<< HEAD

    if m.text == "🛑 Stop":
        cmd_stop(m)
        return

    if is_banned_content(m.text):
        warn_user(uid, "Vulgar words or links")
        return

    if uid in active_pairs:
        partner = active_pairs[uid]
        try:
            bot.send_message(partner, m.text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent = messages_sent + 1 WHERE user_id=?", (uid,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "❌ Could not send message")
    else:
        bot.send_message(uid, "❌ Not connected. Use search commands.", reply_markup=main_keyboard())

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker'])
def handle_media(m):
    auto_unban()
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not connected")
        return

    partner = active_pairs[uid]
    media_type = m.content_type

=======
    # Ask for acceptance from partner
    media_type = message.content_type
    file_id = None
    caption = message.caption if hasattr(message, 'caption') else None
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
    if media_type == 'photo':
        file_id = message.photo[-1].file_id
    elif media_type == 'video':
        file_id = message.video.file_id
    elif media_type == 'voice':
        file_id = message.voice.file_id
    elif media_type == 'document':
        file_id = message.document.file_id
    elif media_type == 'sticker':
        file_id = message.sticker.file_id
    elif media_type == 'animation':
        file_id = message.animation.file_id
    elif media_type == 'audio':
        file_id = message.audio.file_id
    else:
        bot.send_message(uid, "Unsupported media type.")
        return
<<<<<<< HEAD

    u = db_get_user(uid)
    if u and u["media_approved"] and int(u["media_approved"]) > 0:
        try:
            if media_type == 'photo': bot.send_photo(partner, media_id)
            elif media_type == 'document': bot.send_document(partner, media_id)
            elif media_type == 'video': bot.send_video(partner, media_id)
            elif media_type == 'animation': bot.send_animation(partner, media_id)
            elif media_type == 'sticker': bot.send_sticker(partner, media_id)
            db_increment_media(uid, "approved")
        except Exception as e:
            logger.error(f"Error forwarding media (auto-allowed): {e}")
            bot.send_message(uid, "❌ Could not forward media")
        return

    token = generate_media_token(uid)
    pending_media[token] = {
        "sender": uid,
        "partner": partner,
        "media_type": media_type,
        "file_id": media_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}")
    )

=======
    global pending_id_counter
    with pending_lock:
        pid = pending_id_counter
        pending_id_counter += 1
        pending_media[pid] = {'from': uid, 'to': partner, 'file_id': file_id,
                              'type': media_type, 'caption': caption}
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
    try:
        # Send prompt to partner
        markup = types.InlineKeyboardMarkup()
        accept_btn = types.InlineKeyboardButton("Accept 📤", callback_data=f"accept_{pid}")
        decline_btn = types.InlineKeyboardButton("Decline 🚫", callback_data=f"decline_{pid}")
        markup.row(accept_btn, decline_btn)
        bot.send_message(partner, f"Your partner wants to send a {media_type}. Accept?", reply_markup=markup)
        bot.send_message(uid, f"Waiting for partner to accept the {media_type}...")
    except Exception as e:
        logger.error(f"Error in media acceptance prompt: {e}")

@bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("accept_") or call.data.startswith("decline_")))
def callback_media(call):
    parts = call.data.split('_')
    action = parts[0]
    pid = int(parts[1])
    uid = call.from_user.id
    with pending_lock:
        pending = pending_media.get(pid)
        if not pending:
            bot.answer_callback_query(call.id, "No pending request.")
            return
<<<<<<< HEAD

        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]
        file_id = meta["file_id"]

        try:
            if media_type == 'photo':
                bot.send_photo(partner_id, file_id, caption="📸 Media delivered (accepted).")
            elif media_type == 'document':
                bot.send_document(partner_id, file_id, caption="📄 Document delivered (accepted).")
            elif media_type == 'video':
                bot.send_video(partner_id, file_id, caption="🎥 Video delivered (accepted).")
            elif media_type == 'animation':
                bot.send_animation(partner_id, file_id, caption="🎬 Animation delivered (accepted).")
            elif media_type == 'sticker':
                bot.send_sticker(partner_id, file_id)
        except Exception as e:
            logger.error(f"Error delivering media on accept: {e}")
            try: bot.send_message(partner_id, "❌ Could not deliver the media.")
            except: pass
            try: bot.send_message(sender_id, "❌ Your media could not be delivered after accept.")
            except: pass
            if token in pending_media: del pending_media[token]
            bot.answer_callback_query(call.id, "❌ Error delivering media", show_alert=True)
            return

        try:
            db_set_media_sharing(sender_id, True)
            db_increment_media(sender_id, "approved")
        except:
            pass

        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED by partner and delivered.")
        except:
            pass

        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("✅ Partner accepted — media delivered.", chat_id, msg_id)
        except:
=======
        if uid != pending['to']:
            bot.answer_callback_query(call.id, "This request is not for you.")
            return
        if action == 'accept':
            forward_media_specific(pending, pending['to'])
            set_media_accepted(pending['to'], True)
            bot.answer_callback_query(call.id, "Content sent.")
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
            try:
                bot.send_message(pending['from'], "Your content was accepted and sent.")
            except:
                pass
<<<<<<< HEAD

        bot.answer_callback_query(call.id, "✅ Media Approved", show_alert=False)
        if token in pending_media: del pending_media[token]

    except Exception as e:
        logger.error(f"Error in approve_media_cb: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "This media is no longer available.", show_alert=True)
            return

        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]

        try:
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED by partner. It was not delivered.")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("❌ Partner rejected this media. It was not delivered.", chat_id, msg_id)
        except:
=======
        else:
            bot.answer_callback_query(call.id, "Content declined.")
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
            try:
                bot.send_message(pending['from'], "Your content was declined by the partner.")
            except:
                pass
        # Remove pending
        pending_media.pop(pid, None)

<<<<<<< HEAD
        bot.answer_callback_query(call.id, "❌ Media Rejected", show_alert=False)
        if token in pending_media: del pending_media[token]

    except Exception as e:
        logger.error(f"Error in reject_media_cb: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

# -------- BOT POLLING THREAD --------
def run_bot_polling():
    """Separate thread me bot polling chalega"""
    logger.info("🤖 Starting Telegram bot polling...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")

# -------- MAIN EXECUTION --------
if __name__ == "__main__":
    # Database initialize karo
    init_db()
    logger.info("✅ Database initialized")

    # Keep-alive pinger start karo
    keep_alive_pinger()

    # Bot polling ko separate thread me chalao
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot polling thread started")

    # Flask app ko main thread me chalao (Render PORT bind ke liye)
    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"🌐 Starting Flask on port {PORT}")
    logger.info(f"👤 Admin ID: {ADMIN_ID}")
    logger.info(f"🤖 Bot username: @{BOT_USERNAME}")

    # Flask app run (Render ko yahi chahiye)
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
=======
def forward_media(message, to_id):
    """Forward media message to to_id."""
    media_type = message.content_type
    caption = message.caption if hasattr(message, 'caption') else None
    try:
        if media_type == 'photo':
            bot.send_photo(to_id, message.photo[-1].file_id, caption=caption)
        elif media_type == 'video':
            bot.send_video(to_id, message.video.file_id, caption=caption)
        elif media_type == 'voice':
            bot.send_voice(to_id, message.voice.file_id)
        elif media_type == 'document':
            bot.send_document(to_id, message.document.file_id, caption=caption)
        elif media_type == 'sticker':
            bot.send_sticker(to_id, message.sticker.file_id)
        elif media_type == 'animation':
            bot.send_animation(to_id, message.animation.file_id, caption=caption)
        elif media_type == 'audio':
            bot.send_audio(to_id, message.audio.file_id, caption=caption)
    except Exception as e:
        logger.error(f"Error forwarding media: {e}")

def forward_media_specific(media, to_id):
    """Forward pending media after acceptance."""
    media_type = media['type']
    file_id = media['file_id']
    caption = media.get('caption')
    try:
        if media_type == 'photo':
            bot.send_photo(to_id, file_id, caption=caption)
        elif media_type == 'video':
            bot.send_video(to_id, file_id, caption=caption)
        elif media_type == 'voice':
            bot.send_voice(to_id, file_id)
        elif media_type == 'document':
            bot.send_document(to_id, file_id, caption=caption)
        elif media_type == 'sticker':
            bot.send_sticker(to_id, file_id)
        elif media_type == 'animation':
            bot.send_animation(to_id, file_id, caption=caption)
        elif media_type == 'audio':
            bot.send_audio(to_id, file_id, caption=caption)
    except Exception as e:
        logger.error(f"Error forwarding accepted media: {e}")

@bot.message_handler(func=lambda m: m.content_type == 'text')
def handle_text(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    text = message.text
    if text.startswith('/'):
        # Unknown command or handled above
        return
    partner = get_partner(uid)
    if not partner:
        bot.send_message(uid, "You are not in a chat. Use /search to find a partner.")
        return
    try:
        bot.send_message(partner, text)
    except Exception as e:
        logger.error(f"Error forwarding text: {e}")

def ping_admin():
    """Keep-alive ping to admin every 10 minutes."""
    while True:
        time.sleep(600)  # 10 minutes
        try:
            bot.send_message(ADMIN_ID, "🔄 Bot is alive")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")

# Start keep-alive thread
ping_thread = threading.Thread(target=ping_admin, daemon=True)
ping_thread.start()

# Webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@app.route('/')
def index():
    return 'Bot is running.'

if __name__ == '__main__':
    # Set webhook
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    # Run Flask
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
>>>>>>> e027511fd772523feae016a230811712c3cdcce7
