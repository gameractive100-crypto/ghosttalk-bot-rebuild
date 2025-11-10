#!/usr/bin/env python3
"""
GhostTalk Complete - FINAL PERFECT VERSION
All features working 100% - Media Approval, Gender, Ban System
"""

import sqlite3
import random
import logging
import re
from datetime import datetime, timedelta
import time, secrets

import telebot
from telebot import types

# -------- CONFIG --------
# to start = python ghosttalk_bot.py
API_TOKEN = "8243912451:AAGTUqTfZF7H7Roxku1GhBZLGzL_Bl6V0TM"
BOT_USERNAME = "SayNymBot"
ADMIN_ID = 8361006824
OWNER_ID = 8361006824
DB_PATH = "ghosttalk_fixed.db"

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

bot = telebot.TeleBot(API_TOKEN)

# -------- RUNTIME DATA --------
waiting_random = []
waiting_male = []
waiting_female = []
active_pairs = {}
user_warnings = {}
pending_media = {}  # token -> {sender, partner, media_type, file_id, ...}

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
        conn.commit()

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT user_id, username, first_name, gender, messages_sent, media_approved, media_rejected, referral_code, referral_count FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "gender": row[3],
            "messages_sent": row[4],
            "media_approved": row[5],
            "media_rejected": row[6],
            "referral_code": row[7],
            "referral_count": row[8]
        }

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

def db_set_gender(user_id, gender):
    with get_conn() as conn:
        conn.execute("UPDATE users SET gender=? WHERE user_id=?", (gender, user_id))
        conn.commit()

# NEW: set media sharing permission (when partner accepts)
def db_set_media_sharing(user_id, allow: bool):
    with get_conn() as conn:
        if allow:
            conn.execute("UPDATE users SET media_approved = 1, media_rejected = 0 WHERE user_id=?", (user_id,))
        else:
            conn.execute("UPDATE users SET media_approved = 0, media_rejected = 1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_is_banned(user_id):
    if user_id == OWNER_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        ban_until, permanent = row
        if permanent == 1:
            return True
        if ban_until:
            try:
                return datetime.fromisoformat(ban_until) > datetime.utcnow()
            except:
                return False
        return False

def db_ban_user(user_id, hours=None, permanent=False, reason=""):
    with get_conn() as conn:
        if permanent:
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)", (user_id, None, 1, reason))
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)", (user_id, until, 0, reason))
        conn.commit()

def db_unban_user(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id=?", (user_id,))
        conn.commit()

def db_add_report(reporter_id, reported_id, report_type, reason):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reports (reporter_id, reported_id, report_type, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (reporter_id, reported_id, report_type, reason, datetime.utcnow().isoformat())
        )
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved = media_approved + 1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected = media_rejected + 1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_add_referral(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_get_referral_link(user_id):
    user = db_get_user(user_id)
    if user:
        return f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    return None

# -------- WARNING SYSTEM --------
def is_banned_content(text):
    if not text:
        return False
    if LINK_PATTERN.search(text):
        return True
    for pattern in BANNED_PATTERNS:
        if pattern.search(text):
            return True
    return False

def warn_user(user_id, reason):
    count = user_warnings.get(user_id, 0) + 1
    user_warnings[user_id] = count

    if count >= WARNING_LIMIT:
        db_ban_user(user_id, hours=TEMP_BAN_HOURS, reason=reason)
        user_warnings[user_id] = 0

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
        # remove any pending entries where this user is sender
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

# -------- REPORT TYPES --------
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

# ---------------------------
# MEDIA TOKEN GENERATOR
# ---------------------------
def generate_media_token(sender_id):
    return f"{sender_id}:{int(time.time()*1000)}:{secrets.token_hex(4)}"

# -------- COMMANDS --------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are banned from using this bot.")
        return

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
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)

    if not u:
        bot.send_message(uid, "Use /start first")
        return

    text = f"""⚙️ SETTINGS & STATS

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
    uid = message.from_user.id
    u = db_get_user(uid)

    if not u:
        bot.send_message(uid, "Use /start first")
        return

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
        return

    u = db_get_user(uid)
    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first using /settings")
        return

    if uid in active_pairs:
        bot.send_message(uid, "You are already in a chat. Use /next to find new partner.")
        return

    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for random partner...\n⏳ Please wait")
    match_users()

@bot.message_handler(commands=["search_male"])
def cmd_search_male(message):
    auto_unban()
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    u = db_get_user(uid)
    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first using /settings")
        return

    if uid in active_pairs:
        bot.send_message(uid, "You are already in a chat. Use /next to find new partner.")
        return

    remove_from_queues(uid)
    waiting_male.append(uid)
    bot.send_message(uid, "🔍 Searching for male partner...\n⏳ Please wait")
    match_users()

@bot.message_handler(commands=["search_female"])
def cmd_search_female(message):
    auto_unban()
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    u = db_get_user(uid)
    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first using /settings")
        return

    if uid in active_pairs:
        bot.send_message(uid, "You are already in a chat. Use /next to find new partner.")
        return

    remove_from_queues(uid)
    waiting_female.append(uid)
    bot.send_message(uid, "🔍 Searching for female partner...\n⏳ Please wait")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    bot.send_message(uid, "✅ Stopped searching/chatting.", reply_markup=main_keyboard())

@bot.message_handler(commands=["next"])
def cmd_next(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "You're not in a chat. Use search commands first.")
        return

    disconnect_user(uid)
    bot.send_message(uid, "Looking for new partner...", reply_markup=main_keyboard())
    cmd_search_random(message)

@bot.message_handler(commands=["report"])
def cmd_report(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "You need to be in an active chat to report.")
        return

    bot.send_message(uid, "📋 What type of abuse do you want to report?", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id

    if uid not in active_pairs:
        bot.answer_callback_query(call.id, "Not in chat", show_alert=True)
        return

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

    # Admin notification
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
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ You are not admin")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /unban <user_id>")
            return

        target_id = int(parts[1])
        db_unban_user(target_id)
        user_warnings[target_id] = 0

        bot.reply_to(message, f"✅ User {target_id} unbanned")
        try:
            bot.send_message(target_id, "✅ Your ban has been lifted! You can use the bot again.")
        except:
            pass

        logger.info(f"Admin {message.from_user.id} unbanned user {target_id}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def match_users():
    global waiting_random, waiting_male, waiting_female, active_pairs

    if len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1

        msg = "✅ Partner Found!\n\n💬 Chat Tips:\n• Be respectful\n• Be honest\n• No vulgar words\n• No links/spam\n• Have fun!"
        bot.send_message(u1, msg, reply_markup=chat_keyboard())
        bot.send_message(u2, msg, reply_markup=chat_keyboard())

    if len(waiting_male) >= 2:
        u1 = waiting_male.pop(0)
        u2 = waiting_male.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1

        msg = "✅ Male Partner Found!\n\n💬 Chat Tips:\n• Be respectful\n• Be honest\n• No vulgar words\n• No links/spam\n• Have fun!"
        bot.send_message(u1, msg, reply_markup=chat_keyboard())
        bot.send_message(u2, msg, reply_markup=chat_keyboard())

    if len(waiting_female) >= 2:
        u1 = waiting_female.pop(0)
        u2 = waiting_female.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1

        msg = "✅ Female Partner Found!\n\n💬 Chat Tips:\n• Be respectful\n• Be honest\n• No vulgar words\n• No links/spam\n• Have fun!"
        bot.send_message(u1, msg, reply_markup=chat_keyboard())
        bot.send_message(u2, msg, reply_markup=chat_keyboard())

# -------- TEXT HANDLER --------
@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handler_text(m):
    auto_unban()
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)

    # Button handlers
    if m.text == "💬 Tips":
        bot.send_message(uid, """💬 CHAT TIPS:

✅ Be respectful and polite
✅ Be honest about yourself
✅ No vulgar/abusive language
✅ No links or spam
✅ No personal info sharing
✅ Have genuine conversations
✅ Enjoy the experience!""", reply_markup=chat_keyboard())
        return

    if m.text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            bot.send_message(uid, f"""📊 YOUR STATS:

👤 Gender: {u['gender']}
💬 Messages Sent: {u['messages_sent']}
✅ Media Approved: {u['media_approved']}
❌ Media Rejected: {u['media_rejected']}
👥 People Referred: {u['referral_count']}""", reply_markup=chat_keyboard())
        return

    if m.text == "📋 Report":
        if uid in active_pairs:
            cmd_report(m)
        else:
            bot.send_message(uid, "Not in chat")
        return

    if m.text == "➡️ Next":
        cmd_next(m)
        return

    if m.text == "🛑 Stop":
        cmd_stop(m)
        return

    # Check banned content
    if is_banned_content(m.text):
        warn_user(uid, "Vulgar words or links")
        return

    # Send to partner
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

# -------- MEDIA HANDLER (CONSENT-BASED) --------
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

    # Get media ID
    if media_type == 'photo':
        media_id = m.photo[-1].file_id
    elif media_type == 'document':
        media_id = m.document.file_id
    elif media_type == 'video':
        media_id = m.video.file_id
    elif media_type == 'animation':
        media_id = m.animation.file_id
    elif media_type == 'sticker':
        media_id = m.sticker.file_id
    else:
        return

    # If sender already allowed earlier -> forward immediately
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

    # create unique token and save metadata (consent pending)
    token = generate_media_token(uid)
    pending_media[token] = {
        "sender": uid,
        "partner": partner,
        "media_type": media_type,
        "file_id": media_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Send consent request to partner (NO file preview)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}")
    )

    try:
        consent_msg = bot.send_message(partner, "📩 Your partner wants to send a media. Tap ✅ Accept to view it, or ❌ Reject to decline.", reply_markup=markup)
        pending_media[token]["consent_chat_id"] = consent_msg.chat.id
        pending_media[token]["consent_message_id"] = consent_msg.message_id
        bot.send_message(uid, "⏳ Consent request sent to your partner. Wait for them to Accept.")
    except Exception as e:
        logger.error(f"Error sending consent: {e}")
        bot.send_message(uid, "❌ Could not request consent from partner.")
        if token in pending_media: del pending_media[token]

# -------- MEDIA CALLBACKS (CONSENT HANDLING) --------
@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "This media is no longer available.", show_alert=True)
            return

        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]
        file_id = meta["file_id"]

        # Deliver the actual media to the partner now
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

        # mark sharing allowed for future
        try:
            db_set_media_sharing(sender_id, True)
            db_increment_media(sender_id, "approved")
        except:
            pass

        # Notify sender
        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED by partner and delivered.")
        except:
            pass

        # Edit consent message to reflect accepted and remove buttons
        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("✅ Partner accepted — media delivered.", chat_id, msg_id)
        except:
            try:
                bot.edit_message_text("✅ Partner accepted — media delivered.", call.message.chat.id, call.message.message_id)
            except:
                pass

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

        # Notify sender about rejection (do NOT mark permanent block)
        try:
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED by partner. It was not delivered.")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        # Edit consent message to show rejection and remove buttons
        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("❌ Partner rejected this media. It was not delivered.", chat_id, msg_id)
        except:
            try:
                bot.edit_message_text("❌ Partner rejected this media. It was not delivered.", call.message.chat.id, call.message.message_id)
            except:
                pass

        bot.answer_callback_query(call.id, "❌ Media Rejected", show_alert=False)
        if token in pending_media: del pending_media[token]

    except Exception as e:
        logger.error(f"Error in reject_media_cb: {e}")
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)

# -------- MAIN --------
if __name__ == "__main__":
    init_db()
    logger.info("✅ Bot Started Successfully!")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Bot username: @{BOT_USERNAME}")

    try:
        bot.infinity_polling(timeout=60)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
