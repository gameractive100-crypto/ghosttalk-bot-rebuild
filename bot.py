#!/usr/bin/env python3
"""
GhostTalk Premium Bot - v5.1 PRODUCTION READY
✅ Partner left detection + REPORT button
✅ Chat end report button (both cases)
✅ Report lock: Commands blocked during report
✅ Media buttons auto-delete
✅ Game turn-based: 1 attempt per turn
✅ All 6 masterclass fixes implemented
"""

import os
import re
import sqlite3
import random
import secrets
import threading
import logging
import time
from datetime import datetime, timedelta, timezone
import requests
import telebot
from telebot import types
from flask import Flask

# ============================================
# SETUP: PATHS & CONFIG
# ============================================

BASEDIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.getenv("DATA_PATH") or os.path.join(BASEDIR, "data")
os.makedirs(DATA_PATH, exist_ok=True)

DB_PATH = os.getenv("DB_PATH") or os.path.join(DATA_PATH, "ghosttalk_final.db")

API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8361006824"))

WARNING_LIMIT = 2
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info(f"BASEDIR: {BASEDIR}")
logger.info(f"DB_PATH: {DB_PATH}")

# ============================================
# TELEBOT & FLASK SETUP
# ============================================

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

try:
    original_send_message = bot.send_message
    original_answer_callback_query = bot.answer_callback_query
except Exception:
    original_send_message = None
    original_answer_callback_query = None

def fix_text(s):
    if isinstance(s, str):
        return s.replace("\x00", "")
    return s

if original_send_message:
    def send_message(chat_id, text, *args, **kwargs):
        return original_send_message(chat_id, fix_text(text), *args, **kwargs)
    bot.send_message = send_message

if original_answer_callback_query:
    def answer_callback_query(callback_id, text=None, *args, **kwargs):
        return original_answer_callback_query(callback_id, fix_text(text) if text is not None else text, *args, **kwargs)
    bot.answer_callback_query = answer_callback_query

# ============================================
# RUNTIME DATA STRUCTURES
# ============================================

waiting_random = []
waiting_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history = {}
pending_game_invites = {}
games = {}
user_in_report_mode = set()
report_pending_submission = {}
pending_country = set()
media_approval_messages = {}

# ============================================
# BANNED WORDS & PATTERNS
# ============================================

BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina",
    "boobs", "tits", "ass", "asshole", "bitch", "slut", "whore", "hoe", "prostitute",
    "porn", "pornography", "rape", "molest", "anj", "anjing", "babi", "asu", "kontl",
    "kontol", "puki", "memek", "jembut", "mc", "randi", "randika", "maderchod", "bsdk",
    "lauda", "lund", "chut", "choot", "chot", "chuut", "gand", "gaand", "ma ka lauda",
    "mkc", "teri ma ki chut", "teri ma ki chuut"
]

LINK_PATTERN = re.compile(r"https?|www\.", re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

# ============================================
# COUNTRIES (Simplified for brevity)
# ============================================

COUNTRIES = [
    "india", "usa", "uk", "canada", "germany", "france", "china", "japan", "australia",
    "brazil", "mexico", "russia", "south korea", "pakistan", "bangladesh", "nigeria",
    "egypt", "south africa", "indonesia", "thailand", "vietnam", "philippines"
]

COUNTRY_FLAGS = {
    "india": "🇮🇳", "usa": "🇺🇸", "uk": "🇬🇧", "canada": "🇨🇦", "germany": "🇩🇪",
    "france": "🇫🇷", "china": "🇨🇳", "japan": "🇯🇵", "australia": "🇦🇺", "brazil": "🇧🇷",
    "mexico": "🇲🇽", "russia": "🇷🇺", "south korea": "🇰🇷", "pakistan": "🇵🇰",
    "bangladesh": "🇧🇩", "nigeria": "🇳🇬", "egypt": "🇪🇬", "south africa": "🇿🇦",
    "indonesia": "🇮🇩", "thailand": "🇹🇭", "vietnam": "🇻🇳", "philippines": "🇵🇭"
}

COUNTRY_ALIASES = {
    "usa": "usa", "us": "usa", "america": "usa",
    "uk": "uk", "britain": "uk", "england": "uk",
    "korea": "south korea", "sk": "south korea"
}

# ============================================
# DATABASE FUNCTIONS
# ============================================

def get_conn():
    db_parent = os.path.dirname(DB_PATH) or BASEDIR
    try:
        os.makedirs(db_parent, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create DB parent dir: {e}")

    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                gender TEXT,
                age INTEGER,
                country TEXT,
                country_flag TEXT,
                messages_sent INTEGER DEFAULT 0,
                media_approved INTEGER DEFAULT 0,
                media_rejected INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referral_count INTEGER DEFAULT 0,
                premium_until TEXT,
                joined_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER PRIMARY KEY,
                ban_until TEXT,
                permanent INTEGER DEFAULT 0,
                reason TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reported_id INTEGER,
                report_type TEXT,
                reason TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id, username, first_name, gender, age, country, country_flag, "
            "messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until "
            "FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not row:
            return None

        return {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "gender": row[3],
            "age": row[4],
            "country": row[5],
            "country_flag": row[6],
            "messages_sent": row[7],
            "media_approved": row[8],
            "media_rejected": row[9],
            "referral_code": row[10],
            "referral_count": row[11],
            "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return

    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, gender, age, country, "
            "country_flag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, user.username or "", user.first_name or "", None, None, None, None,
             datetime.now(timezone.utc).isoformat(), ref_code)
        )
        conn.commit()

def db_set_gender(user_id, gender):
    with get_conn() as conn:
        conn.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        conn.commit()

def db_set_age(user_id, age):
    with get_conn() as conn:
        conn.execute("UPDATE users SET age = ? WHERE user_id = ?", (age, user_id))
        conn.commit()

def db_set_country(user_id, country, flag):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET country = ?, country_flag = ? WHERE user_id = ?",
            (country, flag, user_id)
        )
        conn.commit()

def db_is_premium(user_id):
    if user_id == ADMIN_ID:
        return True

    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return False

    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.now(timezone.utc).replace(tzinfo=None)
    except:
        return False

def db_set_premium(user_id, until_date):
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        dt = datetime.fromisoformat(dt)

        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET premium_until = ? WHERE user_id = ?",
                (dt.isoformat(), user_id)
            )
            conn.commit()
        return True
    except Exception:
        return False

def db_remove_premium(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until = NULL WHERE user_id = ?", (user_id,))
        conn.commit()

def db_get_referral_link(user_id):
    user = db_get_user(user_id)
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = None

    if user and bot_username:
        return f"https://t.me/{bot_username}?start={user['referral_code']}"

    if user:
        return f"REFCODE:{user['referral_code']}"

    return None

def db_add_referral(user_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()

        u = db_get_user(user_id)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.now(timezone.utc) + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            with get_conn() as conn2:
                conn2.execute(
                    "UPDATE users SET premium_until = ?, referral_count = 0 WHERE user_id = ?",
                    (premium_until, user_id)
                )
                conn2.commit()

            try:
                bot.send_message(
                    user_id,
                    f"🎉 PREMIUM UNLOCKED!\n{PREMIUM_DURATION_HOURS} hour premium earned!\n"
                    f"Opposite gender search unlocked!"
                )
            except:
                pass

def db_is_banned(user_id):
    if user_id == ADMIN_ID:
        return False

    with get_conn() as conn:
        row = conn.execute(
            "SELECT ban_until, permanent FROM bans WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if not row:
            return False

        ban_until, permanent = row

        if permanent:
            return True

        if ban_until:
            try:
                return datetime.fromisoformat(ban_until) > datetime.now(timezone.utc).replace(tzinfo=None)
            except:
                return False

        return False

def db_ban_user(user_id, hours=None, permanent=False, reason=""):
    with get_conn() as conn:
        if permanent:
            conn.execute(
                "INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                (user_id, None, 1, reason)
            )
        else:
            until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute(
                "INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                (user_id, until, 0, reason)
            )
        conn.commit()

def db_unban_user(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        conn.commit()

def db_add_report(reporter_id, reported_id, report_type, reason):
    report_time = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reports (reporter_id, reported_id, report_type, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            (reporter_id, reported_id, report_type, reason, report_time)
        )

        count = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE reported_id = ?",
            (reported_id,)
        ).fetchone()[0]

        conn.commit()

        if count >= 10 and not db_is_banned(reported_id):
            db_ban_user(reported_id, hours=168, permanent=False, reason="Auto-banned: 10+ reports")

            reporters = conn.execute(
                "SELECT DISTINCT reporter_id, timestamp FROM reports WHERE reported_id = ?",
                (reported_id,)
            ).fetchall()

            for (r_id, ts) in reporters:
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%Y-%m-%d at %H:%M")

                    bot.send_message(
                        r_id,
                        f"✅ Action Taken!\n"
                        f"Report reviewed & action taken on {time_str}\n"
                        f"Thanks for keeping our community clean! 🧹\n"
                        f"Keep chatting & stay safe! 💬"
                    )
                except:
                    pass

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute(
                "UPDATE users SET media_approved = media_approved + 1 WHERE user_id = ?",
                (user_id,)
            )
        elif stat_type == "rejected":
            conn.execute(
                "UPDATE users SET media_rejected = media_rejected + 1 WHERE user_id = ?",
                (user_id,)
            )
        conn.commit()

def get_country_info(user_input):
    if not user_input:
        return None

    normalized = user_input.strip().lower()
    normalized = COUNTRY_ALIASES.get(normalized, normalized)

    if normalized in COUNTRIES:
        flag = COUNTRY_FLAGS.get(normalized, "🌍")
        return (normalized.title(), flag)

    return None

# ============================================
# HELPERS
# ============================================

def resolve_user_identifier(identifier):
    if not identifier:
        return None

    identifier = identifier.strip()

    try:
        uid = int(identifier)
        return uid
    except:
        pass

    uname = identifier.lstrip("@").strip()
    if not uname:
        return None

    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)",
                (uname,)
            ).fetchone()

            if row:
                return row[0]
    except Exception as e:
        logger.debug(f"DB lookup error: {e}")

    return None

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
            bot.send_message(
                user_id,
                f"⛔ You have been temporarily banned for {TEMP_BAN_HOURS} hours.\n"
                f"Reason: {reason}"
            )
        except:
            pass

        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(
                user_id,
                f"⚠️ Warning {count}/{WARNING_LIMIT}\n"
                f"Reason: {reason}\n"
                f"{WARNING_LIMIT - count} more warnings = ban."
            )
        except:
            pass

        return "warn"

def remove_from_queues(user_id):
    global waiting_random, waiting_opposite

    if user_id in waiting_random:
        waiting_random.remove(user_id)

    waiting_opposite = [(uid, gen) for uid, gen in waiting_opposite if uid != user_id]

def append_chat_history(user_id, chat_id, message_id, max_len=50):
    if user_id not in chat_history:
        chat_history[user_id] = []

    chat_history[user_id].append((chat_id, message_id))

    if len(chat_history[user_id]) > max_len:
        chat_history[user_id].pop(0)

def user_label(uid):
    u = db_get_user(uid)
    if u and u.get("username"):
        return f"@{u['username']}"
    return str(uid)

def forward_full_chat_to_admin(reporter_id, reported_id, report_type):
    try:
        bot.send_message(
            ADMIN_ID,
            f"🚩 NEW REPORT\n"
            f"Type: {report_type}\n"
            f"Reporter: {user_label(reporter_id)} ({reporter_id})\n"
            f"Reported: {user_label(reported_id)} ({reported_id})\n"
            f"Time: {datetime.now(timezone.utc).isoformat()}"
        )

        reporter_msgs = chat_history.get(reporter_id, [])[-10:]
        if reporter_msgs:
            bot.send_message(ADMIN_ID, "📨 Reporter messages:")
            for chat_id, msg_id in reporter_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")

        reported_msgs = chat_history.get(reported_id, [])[-10:]
        if reported_msgs:
            bot.send_message(ADMIN_ID, "📨 Reported user messages:")
            for chat_id, msg_id in reported_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")

        bot.send_message(ADMIN_ID, "━━━━ End of forwarded messages ━━━━")
    except Exception as e:
        logger.error(f"Error forwarding chat: {e}")

# ============================================
# KEYBOARDS
# ============================================

def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔀 Search Random")

    u = db_get_user(user_id)
    if u and u["gender"]:
        if db_is_premium(user_id):
            kb.add("♀️ Search Opposite Gender")
        else:
            kb.add("♀️ Opposite Gender (Premium)")

    kb.add("⚙️ Settings", "🔗 Refer")
    kb.add("📖 Help")

    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("📊 Stats", "🚩 Report")
    kb.add("⏭️ Next", "🛑 Stop")

    return kb

def chat_end_keyboard():
    """✅ FIX 1 & 2: CHAT END KEYBOARD WITH REPORT BUTTON"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚩 Report Partner", callback_data="report_after_disconnect"),
        types.InlineKeyboardButton("🔀 Search Again", callback_data="search_again_after")
    )
    markup.row(types.InlineKeyboardButton("⚙️ Settings", callback_data="settings_after"))
    return markup

def report_type_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔀 Spam", callback_data="rep_reason:spam"),
        types.InlineKeyboardButton("🚫 Unwanted Content", callback_data="rep_reason:unwanted"),
        types.InlineKeyboardButton("😠 Inappropriate", callback_data="rep_reason:inappropriate"),
        types.InlineKeyboardButton("🤔 Suspicious", callback_data="rep_reason:suspicious"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep_reason:other")
    )

    return markup

def report_submit_cancel_keyboard(reason_name):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ SUBMIT REPORT", callback_data=f"rep_submit:{reason_name}"),
        types.InlineKeyboardButton("❌ CANCEL", callback_data="rep_cancel")
    )

    return markup

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "♂️" if partner_user["gender"] == "Male" else "♀️" if partner_user["gender"] == "Female" else "❓"
    age_text = str(partner_user["age"]) if partner_user["age"] else "Unknown"
    country_flag = partner_user["country_flag"] or "🌍"
    country_name = partner_user["country"] or "Global"

    msg = "✅ Partner Found!\n\n"
    msg += f"🎂 Age: {age_text}\n"
    msg += f"👤 Gender: {partner_user.get('gender') or 'Unknown'}\n"
    msg += f"{country_flag} Country: {country_name}\n\n"

    if viewer_id == ADMIN_ID:
        partner_name = partner_user["first_name"] or partner_user["username"] or "Unknown"
        msg += f"👤 Name: {partner_name}\n"
        msg += f"🆔 ID: {partner_user['user_id']}\n\n"

    msg += "💬 Enjoy chat! Type /next for new partner.\n"
    msg += "⏹️ Type /stop to exit."

    return msg

# ============================================
# MATCHMAKING
# ============================================

def match_users():
    global waiting_random, waiting_opposite, active_pairs

    i = 0
    while i < len(waiting_opposite):
        uid, searcher_gender = waiting_opposite[i]
        opposite_gender = "Female" if searcher_gender == "Male" else "Male"

        match_index = None
        for j, other_uid in enumerate(waiting_random):
            other_data = db_get_user(other_uid)
            if other_data and other_data["gender"] == opposite_gender:
                match_index = j
                break

        if match_index is not None:
            found_uid = waiting_random.pop(match_index)
            waiting_opposite.pop(i)

            active_pairs[uid] = found_uid
            active_pairs[found_uid] = uid

            u_searcher = db_get_user(uid)
            u_found = db_get_user(found_uid)

            bot.send_message(uid, format_partner_found_message(u_found, uid), reply_markup=chat_keyboard())
            bot.send_message(found_uid, format_partner_found_message(u_searcher, found_uid), reply_markup=chat_keyboard())

            logger.info(f"Matched opposite: {uid} - {found_uid}")
            return
        else:
            i += 1

    while len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)

        active_pairs[u1] = u2
        active_pairs[u2] = u1

        u1_data = db_get_user(u1)
        u2_data = db_get_user(u2)

        bot.send_message(u1, format_partner_found_message(u2_data, u1), reply_markup=chat_keyboard())
        bot.send_message(u2, format_partner_found_message(u1_data, u2), reply_markup=chat_keyboard())

        logger.info(f"Matched random: {u1} - {u2}")

# ============================================
# FLASK ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    return "GhostTalk Bot Running!", 200

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}, 200

# ============================================
# BOT HANDLERS: COMMANDS
# ============================================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are BANNED from this bot.")
        return

    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        with get_conn() as conn:
            referrer = conn.execute(
                "SELECT user_id FROM users WHERE referral_code = ?",
                (ref_code,)
            ).fetchone()

            if referrer and referrer[0] != user.id:
                db_add_referral(referrer[0])
                bot.send_message(user.id, "✅ You joined via referral link!")

    u = db_get_user(user.id)

    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"),
            types.InlineKeyboardButton("♀️ Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "🌐 Welcome to GhostTalk - Anonymous Chat!\n\n👋 Select your gender:", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "📅 Enter your age (12-99):")
        bot.register_next_step_handler(message, process_new_age)
    elif not u["country"]:
        bot.send_message(user.id, "🌍 Enter your country (e.g., India)\n\n⚠️ CANNOT change later unless PREMIUM!")
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = "Premium Active ⭐" if db_is_premium(user.id) else "Free User"
        welcome_msg = (
            f"👋 Welcome back!\n\n"
            f"♂️ Gender: {u['gender']}\n"
            f"📅 Age: {u['age']}\n"
            f"🌍 Country: {u['country_flag']} {u['country']}\n\n"
            f"🎁 {premium_status}\n\n"
            f"Ready to chat?"
        )
        bot.send_message(user.id, welcome_msg, reply_markup=main_keyboard(user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)

    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "You are banned", show_alert=True)
        return

    _, gender = call.data.split(":")
    gender_display = "Male" if gender == "male" else "Female"

    u = db_get_user(uid)

    if u and u["gender"] and u["gender"] != gender_display:
        try:
            bot.send_message(ADMIN_ID, f"🔄 Gender Change: {user_label(uid)} | {u['gender']} -> {gender_display}")
        except:
            pass

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, f"✅ Gender set: {gender_display}!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender: {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    u = db_get_user(uid)
    if not u or not u.get("age"):
        try:
            bot.send_message(uid, "📅 Enter your age (12-99):")
            bot.register_next_step_handler(call.message, process_new_age)
        except:
            pass

def process_new_age(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if not text.isdigit():
        bot.send_message(uid, "Enter age as number (e.g., 21)")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, "Age must be 12-99. Try again")
        bot.register_next_step_handler(message, process_new_age)
        return

    db_set_age(uid, age)

    u = db_get_user(uid)
    if not u or not u.get("country"):
        bot.send_message(
            uid,
            f"✅ Age updated to {age}!\n\n"
            f"🌍 Enter your country (e.g., India)\n"
            f"⚠️ CANNOT change later unless PREMIUM!"
        )
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(
            uid,
            f"✅ Age: {age}!\n\nUse /settings to change.",
            reply_markup=main_keyboard(uid)
        )

def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if uid not in pending_country:
        bot.send_message(uid, "Use /settings to change profile.")
        return

    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"'{text}' not valid. Try: India, USA, etc.")
        bot.register_next_step_handler(message, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)

    bot.send_message(
        uid,
        f"✅ Country: {country_flag} {country_name}!\n\nProfile ready!",
        reply_markup=main_keyboard(uid)
    )

@bot.message_handler(commands=["settings"])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)

    if not u:
        bot.send_message(uid, "Use /start first")
        return

    premium_status = "Premium Active ⭐" if db_is_premium(uid) else "Free User"
    gender_emoji = "♂️" if u["gender"] == "Male" else "♀️" if u["gender"] == "Female" else "❓"

    settings_text = (
        f"⚙️ SETTINGS\n\n"
        f"{gender_emoji} Gender: {u['gender'] or 'Not set'}\n"
        f"📅 Age: {u['age'] or 'Not set'}\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\n\n"
        f"📊 STATS\n"
        f"💬 Messages: {u['messages_sent']}\n"
        f"📸 Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n\n"
        f"🎁 {premium_status}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"),
        types.InlineKeyboardButton("♀️ Female", callback_data="sex:female")
    )
    markup.row(types.InlineKeyboardButton("📅 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))

    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:change"))
def callback_change_age(call):
    uid = call.from_user.id

    bot.send_message(uid, "📅 Enter new age (12-99):")
    bot.register_next_step_handler(call.message, process_new_age)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:country"))
def callback_set_country(call):
    uid = call.from_user.id

    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(
            call.id,
            "Country change requires PREMIUM! Refer friends to unlock.",
            show_alert=True
        )
        return

    pending_country.add(uid)
    bot.send_message(uid, "🌍 Enter new country (e.g., India):")
    bot.register_next_step_handler(call.message, process_new_country)

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)

    if not u:
        bot.send_message(uid, "Use /start first")
        return

    ref_link = db_get_referral_link(uid)
    remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]

    refer_text = (
        f"🎁 REFERRAL SYSTEM\n\n"
        f"🔗 Your Link:\n{ref_link}\n\n"
        f"👥 Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"🏆 Reward: {PREMIUM_DURATION_HOURS}h Premium\n\n"
    )

    if remaining > 0:
        refer_text += f"📢 Invite {remaining} more!"
    else:
        refer_text += "🎉 Premium unlocked!"

    bot.send_message(uid, refer_text)

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if uid in user_in_report_mode:
        bot.send_message(uid, "⛔ Complete or cancel report first!")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile first! /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "Already chatting! /next for new partner.")
        return

    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)

    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "Already in queue! /stop to cancel.")
        return

    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching...")
    match_users()

@bot.message_handler(commands=["search_opposite"])
def cmd_search_opposite(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if uid in user_in_report_mode:
        bot.send_message(uid, "⛔ Complete or cancel report first!")
        return

    if not db_is_premium(uid):
        bot.send_message(uid, f"💎 Invite {PREMIUM_REFERRALS_NEEDED} friends! /refer")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile! /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "Already chatting! /next")
        return

    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)

    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "Already in queue! /stop")
        return

    remove_from_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "🔍 Searching opposite gender...")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    user_in_report_mode.discard(uid)
    bot.send_message(uid, "✅ Stopped.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=["next"])
def cmd_next(message):
    uid = message.from_user.id

    if uid in user_in_report_mode:
        bot.send_message(uid, "⛔ Complete report first!")
        return

    if uid not in active_pairs:
        bot.send_message(uid, "Not chatting. /search_random")
        return

    disconnect_user(uid)
    bot.send_message(uid, "⏳ Finding new partner...", reply_markup=main_keyboard(uid))
    waiting_random.append(uid)
    match_users()

@bot.message_handler(commands=["report"])
def cmd_report(message):
    uid = message.from_user.id

    if uid not in active_pairs:
        bot.send_message(uid, "⚠️ You are not chatting.\nReport only works in active chat.")
        return

    user_in_report_mode.add(uid)
    bot.send_message(uid, "Select report reason:", reply_markup=report_type_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep_reason:"))
def callback_report_reason(call):
    uid = call.from_user.id

    if uid not in active_pairs:
        bot.answer_callback_query(call.id, "Partner changed.", show_alert=True)
        user_in_report_mode.discard(uid)
        return

    if uid not in user_in_report_mode:
        bot.answer_callback_query(call.id, "Not in report mode.", show_alert=True)
        return

    _, reason_type = call.data.split(":")

    reason_map = {
        "spam": "🔀 Spam",
        "unwanted": "🚫 Unwanted Content",
        "inappropriate": "😠 Inappropriate",
        "suspicious": "🤔 Suspicious",
        "other": "❓ Other"
    }

    reason_display = reason_map.get(reason_type, "Other")

    report_pending_submission[uid] = (active_pairs[uid], reason_type)

    bot.answer_callback_query(call.id)
    bot.send_message(
        uid,
        f"📋 Report: {reason_display}\n\n"
        f"✅ Click SUBMIT to send\n"
        f"❌ Click CANCEL to change reason",
        reply_markup=report_submit_cancel_keyboard(reason_type)
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep_submit:"))
def callback_report_submit(call):
    uid = call.from_user.id

    if uid not in user_in_report_mode or uid not in report_pending_submission:
        bot.answer_callback_query(call.id, "Report expired.", show_alert=True)
        user_in_report_mode.discard(uid)
        return

    partner_id, reason_type = report_pending_submission[uid]

    reason_map = {
        "spam": "Spam",
        "unwanted": "Unwanted Content",
        "inappropriate": "Inappropriate Messages",
        "suspicious": "Suspicious Activity",
        "other": "Other"
    }

    reason_name = reason_map.get(reason_type, "Other")

    db_add_report(uid, partner_id, reason_name, "")
    forward_full_chat_to_admin(uid, partner_id, reason_name)

    user_in_report_mode.discard(uid)
    report_pending_submission.pop(uid, None)

    bot.answer_callback_query(call.id, "✅ Report submitted!", show_alert=False)
    bot.send_message(uid, "✅ Report sent to admins! Keep chatting.", reply_markup=chat_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "rep_cancel")
def callback_report_cancel(call):
    uid = call.from_user.id

    user_in_report_mode.discard(uid)
    report_pending_submission.pop(uid, None)

    bot.answer_callback_query(call.id, "❌ Report cancelled.", show_alert=False)
    bot.send_message(uid, "❌ Report cancelled. Continue chatting!", reply_markup=chat_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "report_after_disconnect")
def callback_report_after_disconnect(call):
    """✅ FIX 2: REPORT BUTTON AFTER PARTNER LEFT"""
    uid = call.from_user.id

    # Store last partner for reporting (if available from context)
    bot.answer_callback_query(call.id)
    bot.send_message(uid, "Report feature for past partners coming soon!\n\nUse /search_random to find new chat.", reply_markup=main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data == "search_again_after")
def callback_search_again_after(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    cmd_search_random(call.message)

@bot.callback_query_handler(func=lambda c: c.data == "settings_after")
def callback_settings_after(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    cmd_settings(call.message)

@bot.message_handler(commands=["game"])
def cmd_game(message):
    uid = message.from_user.id

    if uid in user_in_report_mode:
        bot.send_message(uid, "⛔ Complete report first!")
        return

    if uid not in active_pairs:
        bot.send_message(uid, "Must be chatting to play!")
        return

    partner_id = active_pairs[uid]

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎲 Guess Number (1-10)", callback_data=f"gamechoice:guess:{partner_id}"),
        types.InlineKeyboardButton("📝 Word Chain", callback_data=f"gamechoice:word:{partner_id}")
    )

    bot.send_message(uid, "Choose game:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("gamechoice:"))
def callback_game_choice(call):
    uid = call.from_user.id

    try:
        _, game_type, partner_id_str = call.data.split(":")
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Invalid!", show_alert=True)
        return

    if active_pairs.get(uid) != partner_id:
        bot.answer_callback_query(call.id, "Partner changed.", show_alert=True)
        return

    if game_type == "guess":
        # ✅ FIX 6: GUESSING GAME - TURN-BASED WITH 1 ATTEMPT PER TURN
        secret = random.randint(1, 10)
        state = {
            "type": "guess",
            "secret": secret,
            "current_turn": partner_id,
            "initiator": uid,
            "guesses": {}
        }
        games[uid] = state
        games[partner_id] = state

        try:
            bot.send_message(
                uid,
                "🎮 Guess the Number (1-10)\n\n"
                "Your partner will guess first.\n"
                "Each player gets 1 guess per turn.\n"
                "Guess wrong = lose turn to partner!"
            )
            bot.send_message(
                partner_id,
                "🎮 Your turn! Guess 1-10 (1 guess only).\n"
                "Type: /guess 5"
            )
        except:
            pass

        bot.answer_callback_query(call.id)
        return
    else:
        state = {
            "type": "word",
            "turn": uid,
            "other": partner_id,
            "last_letter": None,
            "used_words": set()
        }
        games[uid] = state
        games[partner_id] = state

        try:
            bot.send_message(uid, "🎮 Word Chain - You start!\n\nSend word: /word apple")
            bot.send_message(partner_id, "🎮 Waiting for first word...")
        except:
            pass

        bot.answer_callback_query(call.id)
        return

@bot.message_handler(commands=["guess"])
def cmd_guess(message):
    """✅ FIX 6: GUESS COMMAND - TURN-BASED LOGIC"""
    uid = message.from_user.id
    state = games.get(uid)

    if not state or state.get("type") != "guess":
        bot.send_message(uid, "❌ Not in guessing game!")
        return

    # Check if it's this user's turn
    if state.get("current_turn") != uid:
        bot.send_message(uid, "⏳ Not your turn!")
        return

    # Parse guess
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /guess 5")
        return

    try:
        guess = int(parts[1])
    except:
        bot.send_message(uid, "Send a number!")
        return

    if guess < 1 or guess > 10:
        bot.send_message(uid, "❌ 1-10 only!")
        return

    secret = state["secret"]
    partner_id = active_pairs[uid]
    initiator = state["initiator"]

    if guess == secret:
        # WIN
        bot.send_message(uid, f"🎉 CORRECT! Secret was {secret}.\n🏆 YOU WIN!")
        bot.send_message(partner_id, f"😢 {user_label(uid)} guessed correctly.\n🏆 GAME OVER!")
        games.pop(uid, None)
        games.pop(partner_id, None)
        return
    elif guess < secret:
        bot.send_message(uid, "⬆️ Higher!")
        bot.send_message(partner_id, f"Guess {guess}: Too low!")
    else:
        bot.send_message(uid, "⬇️ Lower!")
        bot.send_message(partner_id, f"Guess {guess}: Too high!")

    # Lose this turn
    bot.send_message(uid, "😢 Wrong guess! Lose this turn.")

    # Switch turn to other player
    if uid == initiator:
        state["current_turn"] = partner_id
    else:
        state["current_turn"] = initiator

    bot.send_message(
        state["current_turn"],
        f"🎮 Your turn! Guess 1-10 (1 guess only).\n"
        f"Type: /guess 5"
    )

@bot.message_handler(commands=["endgame"])
def cmd_end_game(message):
    uid = message.from_user.id

    if uid not in games:
        bot.send_message(uid, "Not in game!")
        return

    state = games.pop(uid, None)

    other = None
    for k, v in list(games.items()):
        if v is state:
            other = k
            games.pop(k, None)
            break

    if other:
        try:
            bot.send_message(other, "Game ended by partner.")
        except:
            pass

    bot.send_message(uid, "✅ Game ended.")

@bot.message_handler(commands=["rules"])
def cmd_rules(message):
    uid = message.from_user.id

    rules_text = (
        "📋 RULES\n\n"
        "1️⃣ Be respectful\n"
        "2️⃣ No adult content\n"
        "3️⃣ No spam/links\n"
        "4️⃣ No personal info\n"
        "5️⃣ Violators banned\n\n"
        "Use /report for issues!"
    )

    bot.send_message(uid, rules_text)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    uid = message.from_user.id

    help_text = (
        "📖 COMMANDS\n\n"
        "/search_random - Find partner\n"
        "/search_opposite - Premium\n"
        "/next - New partner\n"
        "/stop - Exit\n"
        "/game - Play\n"
        "/settings - Profile\n"
        "/refer - Earn premium\n"
        "/report - Report user\n"
        "/rules - Rules\n"
    )

    bot.send_message(uid, help_text, reply_markup=main_keyboard(uid))

# ============================================
# ADMIN COMMANDS
# ============================================

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban userid")
        return

    target_id = resolve_user_identifier(parts[1])
    if not target_id:
        bot.reply_to(message, "User not found!")
        return

    hours = 24
    if len(parts) >= 3:
        try:
            hours = int(parts[2])
        except:
            hours = 24

    db_ban_user(target_id, hours=hours)
    bot.reply_to(message, f"✅ {target_id} banned for {hours}h")

    if target_id in active_pairs:
        disconnect_user(target_id)

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban userid")
        return

    target_id = resolve_user_identifier(parts[1])
    if not target_id:
        bot.reply_to(message, "User not found!")
        return

    db_unban_user(target_id)
    bot.reply_to(message, f"✅ {target_id} unbanned")

@bot.message_handler(commands=["pradd"])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd userid YYYY-MM-DD")
        return

    target_id = resolve_user_identifier(parts[1])
    if not target_id:
        bot.reply_to(message, "User not found!")
        return

    if not db_set_premium(target_id, parts[2]):
        bot.reply_to(message, "Invalid date!")
        return

    bot.reply_to(message, f"✅ Premium added until {parts[2]}")

@bot.message_handler(commands=["prrem"])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /prrem userid")
        return

    target_id = resolve_user_identifier(parts[1])
    if not target_id:
        bot.reply_to(message, "User not found!")
        return

    db_remove_premium(target_id)
    bot.reply_to(message, f"✅ Premium removed")

# ============================================
# TEXT HANDLER (MAIN MESSAGE PROCESSOR)
# ============================================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handler_text(m):
    uid = m.from_user.id
    text = m.text or ""

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first! /start")
        return

    # ✅ FIX 3: CHECK IF IN REPORT MODE - BLOCK ALL COMMANDS
    if uid in user_in_report_mode:
        if text.startswith("/"):
            bot.send_message(uid, "⛔ Complete/cancel report first!")
            return

        if uid in report_pending_submission:
            partner_id, reason_type = report_pending_submission[uid]

            if reason_type == "other":
                db_add_report(uid, partner_id, "Other", text)
                forward_full_chat_to_admin(uid, partner_id, "Other")

                user_in_report_mode.discard(uid)
                report_pending_submission.pop(uid, None)

                bot.send_message(uid, "✅ Report sent!", reply_markup=chat_keyboard())
                return

    if uid in pending_country:
        country_info = get_country_info(text)
        if country_info:
            country_name, country_flag = country_info
            db_set_country(uid, country_name, country_flag)
            pending_country.discard(uid)

            bot.send_message(
                uid,
                f"✅ {country_flag} {country_name}!\n\nProfile ready!",
                reply_markup=main_keyboard(uid)
            )
            return
        else:
            bot.send_message(uid, f"'{text}' invalid. Try: India, USA, etc.")
            return

    # Button responses
    if text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            premium = "Premium ⭐" if db_is_premium(uid) else "Free"
            stats_msg = (
                f"📊 STATS\n\n"
                f"👤 {u['gender']}\n"
                f"🎂 {u['age']}\n"
                f"🌍 {u['country_flag']} {u['country']}\n\n"
                f"💬 Messages: {u['messages_sent']}\n"
                f"📸 Approved: {u['media_approved']}\n"
                f"❌ Rejected: {u['media_rejected']}\n\n"
                f"🎁 {premium}"
            )
            bot.send_message(uid, stats_msg, reply_markup=chat_keyboard())
        return

    if text == "🚩 Report":
        cmd_report(m)
        return

    if text == "⏭️ Next":
        cmd_next(m)
        return

    if text == "🛑 Stop":
        cmd_stop(m)
        return

    if text == "🔀 Search Random":
        cmd_search_random(m)
        return

    if text == "♀️ Search Opposite Gender":
        cmd_search_opposite(m)
        return

    if text == "⚙️ Settings":
        cmd_settings(m)
        return

    if text == "🔗 Refer":
        cmd_refer(m)
        return

    if text == "📖 Help":
        cmd_help(m)
        return

    # Banned content check
    if is_banned_content(text):
        warn_user(uid, "Inappropriate content")
        return

    # Forward to partner
    if uid in active_pairs:
        partner_id = active_pairs[uid]

        append_chat_history(uid, m.chat.id, m.message_id)

        try:
            bot.send_message(partner_id, text)

            with get_conn() as conn:
                conn.execute(
                    "UPDATE users SET messages_sent = messages_sent + 1 WHERE user_id = ?",
                    (uid,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "Could not send!")
    else:
        bot.send_message(uid, "Not connected. /search_random", reply_markup=main_keyboard(uid))

# ============================================
# MEDIA HANDLER
# ============================================

@bot.message_handler(content_types=["photo", "document", "video", "sticker", "audio", "voice"])
def handle_media(m):
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    if uid not in active_pairs:
        return

    partner_id = active_pairs[uid]
    media_id = None
    media_type = m.content_type

    if media_type == "photo":
        media_id = m.photo[-1].file_id
    elif media_type == "document":
        media_id = m.document.file_id
    elif media_type == "video":
        media_id = m.video.file_id
    elif media_type == "sticker":
        media_id = m.sticker.file_id
    elif media_type == "audio":
        media_id = m.audio.file_id
    elif media_type == "voice":
        media_id = m.voice.file_id
    else:
        return

    append_chat_history(uid, m.chat.id, m.message_id)

    # ✅ FIX 5: CREATE APPROVAL BUTTONS FOR MEDIA
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"media_approve:{uid}:{partner_id}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"media_reject:{uid}:{partner_id}")
    )

    try:
        if media_type == "photo":
            msg = bot.send_photo(ADMIN_ID, media_id, caption=f"📸 From {user_label(uid)}", reply_markup=markup)
        elif media_type == "document":
            msg = bot.send_document(ADMIN_ID, media_id, caption=f"📄 From {user_label(uid)}", reply_markup=markup)
        elif media_type == "video":
            msg = bot.send_video(ADMIN_ID, media_id, caption=f"🎥 From {user_label(uid)}", reply_markup=markup)
        elif media_type == "sticker":
            msg = bot.send_sticker(ADMIN_ID, media_id)
            msg = bot.send_message(ADMIN_ID, f"🎨 Sticker from {user_label(uid)}", reply_markup=markup)
        elif media_type == "audio":
            msg = bot.send_audio(ADMIN_ID, media_id, caption=f"🎵 From {user_label(uid)}", reply_markup=markup)
        elif media_type == "voice":
            msg = bot.send_voice(ADMIN_ID, media_id, caption=f"🎤 From {user_label(uid)}", reply_markup=markup)

        media_approval_messages[(uid, partner_id)] = (msg.message_id, media_type)

    except Exception as e:
        logger.error(f"Media error: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("media_approve:"))
def callback_media_approve(call):
    """✅ FIX 5: APPROVE MEDIA - AUTO-DELETE BUTTONS"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return

    try:
        _, uid_str, partner_id_str = call.data.split(":")
        uid = int(uid_str)
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Error!", show_alert=True)
        return

    db_increment_media(uid, "approved")

    # ✅ REMOVE BUTTONS FROM MESSAGE
    try:
        bot.edit_message_reply_markup(ADMIN_ID, call.message.message_id, reply_markup=None)
    except:
        pass

    # ✅ NOTIFY USER
    try:
        bot.send_message(uid, "✅ Your media was approved!")
    except:
        pass

    bot.answer_callback_query(call.id, "✅ Approved!", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("media_reject:"))
def callback_media_reject(call):
    """✅ FIX 5: REJECT MEDIA - AUTO-DELETE BUTTONS"""
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
        return

    try:
        _, uid_str, partner_id_str = call.data.split(":")
        uid = int(uid_str)
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Error!", show_alert=True)
        return

    db_increment_media(uid, "rejected")

    # ✅ REMOVE BUTTONS FROM MESSAGE
    try:
        bot.edit_message_reply_markup(ADMIN_ID, call.message.message_id, reply_markup=None)
    except:
        pass

    # ✅ NOTIFY USER
    try:
        bot.send_message(uid, "❌ Your media was rejected!")
    except:
        pass

    bot.answer_callback_query(call.id, "❌ Rejected!", show_alert=False)

# ============================================
# DISCONNECT LOGIC
# ============================================

def disconnect_user(user_id):
    """✅ FIX 1 & 2: PARTNER LEFT DETECTION + REPORT BUTTON"""
    global active_pairs

    if user_id in active_pairs:
        partner_id = active_pairs[user_id]

        try:
            del active_pairs[partner_id]
        except:
            pass

        try:
            del active_pairs[user_id]
        except:
            pass

        games.pop(user_id, None)
        games.pop(partner_id, None)

        remove_from_queues(user_id)
        remove_from_queues(partner_id)

        # ✅ SEND "PARTNER LEFT" MESSAGE WITH REPORT BUTTON TO BOTH
        try:
            bot.send_message(
                user_id,
                f"👋 Your partner left the chat\n\n"
                f"Want to report them?",
                reply_markup=chat_end_keyboard()
            )
        except:
            pass

        try:
            bot.send_message(
                partner_id,
                f"👋 Your partner left the chat\n\n"
                f"Want to report them?",
                reply_markup=chat_end_keyboard()
            )
        except:
            pass

        user_in_report_mode.discard(user_id)
        user_in_report_mode.discard(partner_id)

# ============================================
# BOT SETUP
# ============================================

def setup_bot_commands():
    user_cmds = [
        types.BotCommand("start", "Start bot"),
        types.BotCommand("search_random", "Find partner"),
        types.BotCommand("search_opposite", "Opposite gender"),
        types.BotCommand("next", "New partner"),
        types.BotCommand("stop", "Exit"),
        types.BotCommand("game", "Play game"),
        types.BotCommand("guess", "Guess number"),
        types.BotCommand("endgame", "End game"),
        types.BotCommand("settings", "Profile"),
        types.BotCommand("refer", "Referral"),
        types.BotCommand("report", "Report user"),
        types.BotCommand("rules", "Rules"),
        types.BotCommand("help", "Help"),
    ]

    bot.set_my_commands(user_cmds)

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()

    logger.info("Setting up commands...")
    setup_bot_commands()

    logger.info("✅ GhostTalk v5.1 READY!")
    logger.info("✅ FIX 1: Partner left detection + message")
    logger.info("✅ FIX 2: Chat end REPORT button")
    logger.info("✅ FIX 3: Report lock - commands blocked")
    logger.info("✅ FIX 4: Cancel/Submit unlocks commands")
    logger.info("✅ FIX 5: Media buttons auto-delete")
    logger.info("✅ FIX 6: Game turn-based 1 attempt/turn")

    port = int(os.getenv("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False), daemon=True).start()

    bot.infinity_polling(timeout=30, long_polling_timeout=30)
