#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FIXED (single-file)
Includes:
- Fixed report flow (in-chat + post-chat + cancel/submit + command lock)
- Fixed media accept/reject (removes pending request after action)
- Fixed guessing & word-chain games (turn enforcement)
- Post-chat end UI + reporting options
- Minimal changes elsewhere, kept original DB & features intact
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
import telebot
from telebot import types
from flask import Flask

# =======================
# CONFIG
# =======================
BASEDIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.getenv("DATA_PATH") or os.path.join(BASEDIR, "data")
os.makedirs(DATA_PATH, exist_ok=True)
DB_PATH = os.getenv("DB_PATH") or os.path.join(DATA_PATH, "ghosttalk_final.db")
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))

WARNING_LIMIT = 2
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# =======================
# LOGGING
# =======================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.info(f"BASE_DIR: {BASEDIR}")
logger.info(f"DB_PATH: {DB_PATH}")

# =======================
# BOT & APP
# =======================
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Helper to sanitize text
def fix_text(s):
    if isinstance(s, str):
        return s.replace("\x00", "")
    return s

# =======================
# RUNTIME DATA
# =======================
waiting_random = []  # list of user ids
waiting_opposite = []  # list of (user id, gender)
active_pairs = {}  # user_id -> partner_id
user_warnings = {}
chat_history = {}  # user_id -> list of (chat_id, message_id)
pending_game_invites = {}
games = {}  # user_id -> game state (shared between players)
pending_media = {}  # media_key -> {sender, partner, type, file_id}

# Reports
# report_sessions: reporter_id -> dict{reported: id or None, source: 'inchat'|'postchat', stage: 'enter_reported'|'choose_reason'|'reason', type: string}
report_sessions = {}
# Helper set: reporters currently blocked from commands (subset of report_sessions keys)
# (we'll use report_sessions keys + stage to define blocking behavior)

pending_country = set()

# BANNED content
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina",
    "boobs", "tits", "ass", "asshole", "bitch", "slut", "whore", "hoe", "prostitute",
    "porn", "pornography", "rape", "molest"
]
LINK_PATTERN = re.compile(r"https?|www\.", re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

# Countries (small sample, extend as needed)
COUNTRIES = ["india", "pakistan", "usa", "united states", "uk", "united kingdom"]
COUNTRY_FLAGS = {"india": "🇮🇳", "pakistan": "🇵🇰", "united states": "🇺🇸", "united kingdom": "🇬🇧", "usa": "🇺🇸", "uk": "🇬🇧"}
COUNTRY_ALIASES = {"america": "united states", "us": "united states"}

# =======================
# DATABASE
# =======================

def get_conn():
    db_parent = os.path.dirname(DB_PATH) or BASEDIR
    try:
        os.makedirs(db_parent, exist_ok=True)
    except Exception:
        pass
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
            "SELECT user_id, username, first_name, gender, age, country, country_flag, messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until FROM users WHERE user_id = ?",
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
    ref_code = f"REF{uid}{random.randint(1000,99999)}"
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, user.username or "", user.first_name or "", None, None, None, None, datetime.now(timezone.utc).isoformat(), ref_code)
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
        conn.execute("UPDATE users SET country = ?, country_flag = ? WHERE user_id = ?", (country, flag, user_id))
        conn.commit()


def db_is_premium(user_id):
    if user_id == ADMIN_ID:
        return True
    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return False
    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.now(timezone.utc).replace(tzinfo=None)
    except Exception:
        return False


def db_set_premium(user_id, until_date):
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        dt = datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute("UPDATE users SET premium_until = ? WHERE user_id = ?", (dt.isoformat(), user_id))
            conn.commit()
        return True
    except Exception:
        return False


def db_remove_premium(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until = NULL WHERE user_id = ?", (user_id,))
        conn.commit()


def db_add_referral(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        u = db_get_user(user_id)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.now(timezone.utc) + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            with get_conn() as c2:
                c2.execute("UPDATE users SET premium_until = ?, referral_count = 0 WHERE user_id = ?", (premium_until, user_id))
                c2.commit()
            try:
                bot.send_message(user_id, f"🎉 PREMIUM UNLOCKED! {PREMIUM_DURATION_HOURS} hour premium earned!")
            except Exception:
                pass


def db_is_banned(user_id):
    if user_id == ADMIN_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return False
    ban_until, permanent = row
    if permanent:
        return True
    if ban_until:
        try:
            return datetime.fromisoformat(ban_until) > datetime.now(timezone.utc).replace(tzinfo=None)
        except Exception:
            return False
    return False


def db_ban_user(user_id, hours=None, permanent=False, reason=""):
    with get_conn() as conn:
        if permanent:
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)", (user_id, None, 1, reason))
        else:
            until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)", (user_id, until, 0, reason))
        conn.commit()


def db_unban_user(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        conn.commit()


def db_add_report(reporter_id, reported_id, report_type, reason):
    report_time = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute("INSERT INTO reports (reporter_id, reported_id, report_type, reason, timestamp) VALUES (?, ?, ?, ?, ?)", (reporter_id, reported_id, report_type, reason, report_time))
        count = conn.execute("SELECT COUNT(*) FROM reports WHERE reported_id = ?", (reported_id,)).fetchone()[0]
        conn.commit()
    # Auto-ban on 10 reports
    if count >= 10 and not db_is_banned(reported_id):
        db_ban_user(reported_id, hours=168, permanent=False, reason="Auto-banned: 10+ reports")
        # notify reporters
        with get_conn() as conn:
            reporters = conn.execute("SELECT DISTINCT reporter_id, timestamp FROM reports WHERE reported_id = ?", (reported_id,)).fetchall()
        for (r_id, ts) in reporters:
            try:
                dt = datetime.fromisoformat(ts)
                time_str = dt.strftime("%Y-%m-%d at %H:%M")
                bot.send_message(r_id, f"✅ Action Taken! Report reviewed & action taken on {time_str}")
            except Exception:
                pass


def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved = media_approved + 1 WHERE user_id = ?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected = media_rejected + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

# =======================
# HELPERS
# =======================

def get_country_info(user_input):
    if not user_input:
        return None
    normalized = user_input.strip().lower()
    normalized = COUNTRY_ALIASES.get(normalized, normalized)
    if normalized in COUNTRY_FLAGS:
        return (normalized.title(), COUNTRY_FLAGS.get(normalized))
    return None


def resolve_user_identifier(identifier):
    if not identifier:
        return None
    identifier = identifier.strip()
    # numeric id?
    try:
        uid = int(identifier)
        return uid
    except Exception:
        pass
    uname = identifier.lstrip("@").strip()
    if not uname:
        return None
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (uname,)).fetchone()
            if row:
                return row[0]
    except Exception:
        pass
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
            bot.send_message(user_id, f"⛔ You have been temporarily banned for {TEMP_BAN_HOURS} hours. Reason: {reason}")
        except Exception:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ Warning {count}/{WARNING_LIMIT} Reason: {reason}")
        except Exception:
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
        bot.send_message(ADMIN_ID, f"🚩 NEW REPORT - {report_type}\nReporter: {user_label(reporter_id)} ({reporter_id})\nReported: {user_label(reported_id)} ({reported_id})\nTime: {datetime.now(timezone.utc).isoformat()}")
        reporter_msgs = chat_history.get(reporter_id, [])[-10:]
        if reporter_msgs:
            bot.send_message(ADMIN_ID, "📨 Reporter messages:")
            for chat_id, msg_id in reporter_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception:
                    pass
        reported_msgs = chat_history.get(reported_id, [])[-10:]
        if reported_msgs:
            bot.send_message(ADMIN_ID, "📨 Reported user messages:")
            for chat_id, msg_id in reported_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception:
                    pass
        bot.send_message(ADMIN_ID, "━━━━ End of forwarded messages ━━━━")
    except Exception as e:
        logger.error(f"Error forwarding chat: {e}")

# =======================
# KEYBOARDS
# =======================

def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔀 Search Random")
    u = db_get_user(user_id)
    if u and u.get("gender"):
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


def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔀 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("🚫 Unwanted Content", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("😠 Inappropriate Messages", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🤔 Suspicious Activity", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep:other"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="rep:cancel")
    )
    return markup


def post_chat_end_keyboard(reported_id=None):
    # reported_id may be None; callback will launch flow to ask ID if needed
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔁 Start New Chat", callback_data="post:start"),
        types.InlineKeyboardButton("🚩 Report Partner", callback_data="post:report")
    )
    return kb

# Media accept/reject keyboard generator

def media_approval_keyboard(media_key):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"media:accept:{media_key}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"media:reject:{media_key}")
    )
    return kb

# =======================
# MATCHMAKING
# =======================

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "♂️" if partner_user and partner_user.get("gender") == "Male" else "♀️" if partner_user and partner_user.get("gender") == "Female" else "❓"
    age_text = str(partner_user["age"]) if partner_user and partner_user.get("age") else "Unknown"
    country_flag = partner_user.get("country_flag") if partner_user else "🌍"
    country_name = partner_user.get("country") if partner_user else "Global"
    msg = "✅ Partner Found!\n\n"
    msg += f"🎂 Age: {age_text}\n"
    msg += f"👤 Gender: {partner_user.get('gender') if partner_user else 'Unknown'}\n"
    msg += f"{country_flag} Country: {country_name}\n\n"
    if viewer_id == ADMIN_ID and partner_user:
        partner_name = partner_user.get("first_name") or partner_user.get("username") or "Unknown"
        msg += f"👤 Name: {partner_name}\n"
        msg += f"🆔 ID: {partner_user['user_id']}\n\n"
    msg += "💬 Enjoy chat! Type /next for new partner.\n"
    msg += "⏹️ Type /stop to exit."
    return msg


def match_users():
    global waiting_random, waiting_opposite, active_pairs
    # Try opposite first
    i = 0
    while i < len(waiting_opposite):
        uid, searcher_gender = waiting_opposite[i]
        opposite_gender = "Female" if searcher_gender == "Male" else "Male"
        match_index = None
        for j, other_uid in enumerate(waiting_random):
            other_data = db_get_user(other_uid)
            if other_data and other_data.get("gender") == opposite_gender:
                match_index = j
                break
        if match_index is not None:
            found_uid = waiting_random.pop(match_index)
            waiting_opposite.pop(i)
            active_pairs[uid] = found_uid
            active_pairs[found_uid] = uid
            u_searcher = db_get_user(uid)
            u_found = db_get_user(found_uid)
            try:
                bot.send_message(uid, format_partner_found_message(u_found, uid), reply_markup=chat_keyboard())
                bot.send_message(found_uid, format_partner_found_message(u_searcher, found_uid), reply_markup=chat_keyboard())
            except Exception:
                pass
            logger.info(f"Matched opposite: {uid} - {found_uid}")
            return
        else:
            i += 1
    # Random pairs
    while len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1
        u1_data = db_get_user(u1)
        u2_data = db_get_user(u2)
        try:
            bot.send_message(u1, format_partner_found_message(u2_data, u1), reply_markup=chat_keyboard())
            bot.send_message(u2, format_partner_found_message(u1_data, u2), reply_markup=chat_keyboard())
        except Exception:
            pass
        logger.info(f"Matched random: {u1} - {u2}")

# =======================
# FLASK ROUTES
# =======================

@app.route("/", methods=["GET"])
def home():
    return "GhostTalk Bot Running!", 200

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}, 200

# =======================
# BOT HANDLERS
# =======================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are BANNED from this bot.")
        return
    # referral
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        with get_conn() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,)).fetchone()
            if referrer and referrer[0] != user.id:
                db_add_referral(referrer[0])
                try:
                    bot.send_message(user.id, "✅ You joined via referral link!")
                except Exception:
                    pass
    u = db_get_user(user.id)
    if not u or not u.get("gender"):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"), types.InlineKeyboardButton("♀️ Female", callback_data="sex:female"))
        bot.send_message(user.id, "🌐 Welcome to GhostTalk! Select your gender:", reply_markup=markup)
        return
    if not u.get("age"):
        bot.send_message(user.id, "📅 Enter your age (12-99 only):")
        bot.register_next_step_handler(message, process_new_age)
        return
    if not u.get("country"):
        bot.send_message(user.id, "🌍 Enter your country name (e.g., India)\n\n⚠️ Country CANNOT be changed later unless PREMIUM!")
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
        return
    premium_status = "Premium Active ⭐" if db_is_premium(user.id) else "Free User"
    welcome_msg = f"👋 Welcome back!\n\n♂️ Gender: {u.get('gender')}\n📅 Age: {u.get('age')}\n🌍 Country: {u.get('country_flag')} {u.get('country')}\n\n🎁 {premium_status}\n\nReady to chat?"
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
    if u and u.get("gender") and u.get("gender") != gender_display:
        try:
            bot.send_message(ADMIN_ID, f"🔄 Gender Change: {user_label(uid)} | {u['gender']} -> {gender_display}")
        except Exception:
            pass
    db_set_gender(uid, gender_display)
    try:
        bot.edit_message_text(f"✅ Gender updated to: {gender_display}", call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    u = db_get_user(uid)
    if not u or not u.get("age"):
        try:
            bot.send_message(uid, "📅 Enter your age (12-99 only):")
            bot.register_next_step_handler(call.message, process_new_age)
        except Exception:
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
        bot.send_message(uid, f"✅ Age updated to {age}!\n\n🌍 Enter your country name (e.g., India)\n⚠️ Country CANNOT be changed later unless PREMIUM!")
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
        return
    bot.send_message(uid, f"✅ Age updated to {age}!", reply_markup=main_keyboard(uid))


def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    if uid not in pending_country:
        bot.send_message(uid, "Use /settings to change profile.")
        return
    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"'{text}' not valid. Try again (e.g., India)")
        bot.register_next_step_handler(message, process_new_country)
        return
    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)
    bot.send_message(uid, f"✅ Country updated to {country_flag} {country_name}!\n\nProfile complete! Ready to chat?", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=["settings"])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    premium_status = "Premium Active ⭐" if db_is_premium(uid) else "Free User"
    gender_emoji = "♂️" if u.get("gender") == "Male" else "♀️"
    settings_text = (
        f"⚙️ SETTINGS PROFILE\n\n{gender_emoji} Gender: {u.get('gender') or 'Not set'}\n📅 Age: {u.get('age') or 'Not set'}\n🌍 Country: {u.get('country_flag') or '🌍'} {u.get('country') or 'Not set'}\n\n📊 STATS\n💬 Messages Sent: {u.get('messages_sent')}\n📸 Media Approved: {u.get('media_approved')}\n❌ Media Rejected: {u.get('media_rejected')}\n👥 People Referred: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}\n\n🎁 {premium_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔗 Refer Link", callback_data="ref:link"), types.InlineKeyboardButton("♂️ Male", callback_data="sex:male"), types.InlineKeyboardButton("♀️ Female", callback_data="sex:female"))
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
        bot.answer_callback_query(call.id, "Country change requires PREMIUM! Refer friends to unlock.", show_alert=True)
        return
    pending_country.add(uid)
    bot.send_message(uid, "🌍 Enter your new country name (e.g., India):")
    bot.register_next_step_handler(call.message, process_new_country)

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = None
    ref_link = f"https://t.me/{bot_username}?start={u['referral_code']}" if bot_username else f"REFCODE:{u['referral_code']}"
    remaining = PREMIUM_REFERRALS_NEEDED - u.get('referral_count', 0)
    refer_text = f"🎁 REFERRAL SYSTEM\n\n🔗 Your Referral Link:\n{ref_link}\n\n👥 People Referred: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}\n🏆 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n♀️ Unlock opposite gender search!\n\n"
    if remaining > 0:
        refer_text += f"📢 Invite {remaining} more friends to unlock premium!"
    else:
        refer_text += "🎉 Premium unlocked! Keep inviting for more!"
    bot.send_message(uid, refer_text)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref:"))
def callback_referral(call):
    uid = call.from_user.id
    _, action = call.data.split(":")
    if action == "link":
        u = db_get_user(uid)
        if not u:
            bot.answer_callback_query(call.id, "Error!", show_alert=True)
            return
        try:
            bot_username = bot.get_me().username
        except Exception:
            bot_username = None
        ref_link = f"https://t.me/{bot_username}?start={u['referral_code']}" if bot_username else f"REFCODE:{u['referral_code']}"
        remaining = PREMIUM_REFERRALS_NEEDED - u.get('referral_count', 0)
        refer_text = f"🎁 REFERRAL SYSTEM\n\n🔗 Your Referral Link:\n{ref_link}\n\n👥 People Referred: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}\n🏆 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n\n"
        if remaining > 0:
            refer_text += f"📢 Invite {remaining} more friends to unlock premium!"
        else:
            refer_text += "🎉 Premium unlocked! Keep inviting for more!"
        bot.send_message(uid, refer_text)
        bot.answer_callback_query(call.id)

# =======================
# SEARCH / MATCH / STOP / NEXT
# =======================

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return
    u = db_get_user(uid)
    if not u or not u.get('gender') or not u.get('age') or not u.get('country'):
        bot.send_message(uid, "Complete profile first! Use /start")
        return
    if uid in active_pairs:
        bot.send_message(uid, "Already in chat! Use /next for new partner.")
        return
    if uid in waiting_random or any(uid == w[0] for w in waiting_opposite):
        bot.send_message(uid, "You're already in the queue. /stop to cancel anytime.")
        return
    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for random partner... Please wait...")
    match_users()

@bot.message_handler(commands=["search_opposite"])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return
    if not db_is_premium(uid):
        bot.send_message(uid, f"💎 PREMIUM REQUIRED! Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock.")
        return
    u = db_get_user(uid)
    if not u or not u.get('gender') or not u.get('age') or not u.get('country'):
        bot.send_message(uid, "Complete profile first! Use /start")
        return
    if uid in active_pairs:
        bot.send_message(uid, "Already in chat! Use /next for new partner.")
        return
    if uid in waiting_random or any(uid == w[0] for w in waiting_opposite):
        bot.send_message(uid, "You're already in the queue. /stop to cancel anytime.")
        return
    remove_from_queues(uid)
    waiting_opposite.append((uid, u.get('gender')))
    bot.send_message(uid, "🔍 Searching for opposite gender partner... Please wait...")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    # If in queue, remove
    remove_from_queues(uid)
    # If in active chat, notify partner and show end-screen
    if uid in active_pairs:
        partner = active_pairs.get(uid)
        disconnect_user(uid)
        try:
            bot.send_message(uid, "✅ You stopped the chat.", reply_markup=main_keyboard(uid))
        except Exception:
            pass
        try:
            bot.send_message(partner, "⚠️ Your partner has left the chat.", reply_markup=None)
            bot.send_message(partner, "Would you like to start a new chat or report?", reply_markup=post_chat_end_keyboard())
        except Exception:
            pass
    else:
        bot.send_message(uid, "✅ Search/chat stopped.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=["next"])
def cmd_next(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "Not in chat. Use /search_random or /search_opposite.")
        return
    disconnect_user(uid)
    bot.send_message(uid, "⏳ Looking for new partner...", reply_markup=main_keyboard(uid))
    waiting_random.append(uid)
    match_users()

# =======================
# REPORT HANDLING
# =======================

@bot.message_handler(commands=["report"])
def cmd_report(message):
    uid = message.from_user.id
    # Can report only while chatting
    if uid not in active_pairs:
        bot.send_message(uid, "⚠️ You are not in an active chat. You can report from post-chat end screen or while chatting.")
        return
    bot.send_message(uid, "Select reason for report:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:") or c.data.startswith("post:"))
def callback_report(call):
    uid = call.from_user.id
    data = call.data
    # Post-chat actions
    if data.startswith("post:"):
        _, action = data.split(":", 1)
        if action == "start":
            bot.answer_callback_query(call.id)
            cmd_search_random(call.message)
            return
        elif action == "report":
            bot.answer_callback_query(call.id)
            # Enter post-chat report mode: ask the user to enter the reported id or username
            report_sessions[uid] = {"reported": None, "source": "postchat", "stage": "enter_reported", "type": None}
            bot.send_message(uid, "Enter the user id or @username of the user you want to report, or type 'cancel' to abort.\nOr press a reason button below AFTER entering id.", reply_markup=report_keyboard())
            return

    # In-chat report flow
    if data.startswith("rep:"):
        _, rep_type = data.split(":", 1)
        if rep_type == "cancel":
            bot.answer_callback_query(call.id, "Cancelled.", show_alert=False)
            return

        if rep_type == "other":
            # Reporter wants to type custom reason. Start reason stage.
            partner_id = active_pairs.get(uid)
            if not partner_id:
                bot.answer_callback_query(call.id, "Partner not connected.", show_alert=True)
                return
            report_sessions[uid] = {"reported": partner_id, "source": "inchat", "stage": "reason", "type": "Other"}
            bot.answer_callback_query(call.id)
            try:
                bot.send_message(uid, "✍️ Type your report reason now. Type 'cancel' to cancel the report.")
            except Exception:
                pass
            # Inform partner optionally
            try:
                bot.send_message(partner_id, "⚠️ Your chat partner is submitting a report. Messages you send now may be ignored until they finish.")
            except Exception:
                pass
            return

        # other pre-defined reasons -> auto-submit
        report_type_map = {
            "spam": "Spam",
            "unwanted": "Unwanted Content",
            "inappropriate": "Inappropriate Messages",
            "suspicious": "Suspicious Activity"
        }
        report_type_name = report_type_map.get(rep_type, "Other")
        # If reporter is in postchat flow and reported not set, require reported id first
        if uid in report_sessions and report_sessions[uid].get("source") == "postchat" and not report_sessions[uid].get("reported"):
            bot.answer_callback_query(call.id, "Enter reported user id or @username first.", show_alert=True)
            return

        partner_id = report_sessions.get(uid, {}).get("reported") if uid in report_sessions else active_pairs.get(uid)
        if not partner_id:
            partner_id = active_pairs.get(uid)
        if not partner_id:
            bot.answer_callback_query(call.id, "Partner not connected or changed.", show_alert=True)
            return

        # record report
        db_add_report(uid, partner_id, report_type_name, "")
        forward_full_chat_to_admin(uid, partner_id, report_type_name)
        bot.answer_callback_query(call.id, "Report submitted.")
        bot.send_message(uid, "✅ Report submitted! Admins reviewing...", reply_markup=main_keyboard(uid))
        # clear any postchat session
        report_sessions.pop(uid, None)
        return

# =======================
# TEXT HANDLER
# =======================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handler_text(m):
    uid = m.from_user.id
    text = (m.text or "").strip()
    # Sanitize: avoid NULs
    text = fix_text(text)

    # Check ban
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    # Create user record if missing
    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    # Country flow
    if uid in pending_country:
        process_new_country(m)
        return

    # REPORT SESSION: stage machine
    if uid in report_sessions:
        sess = report_sessions.get(uid)
        if not sess:
            # defensive
            report_sessions.pop(uid, None)
        else:
            stage = sess.get("stage")
            if stage == "enter_reported":
                # Expect user to send ID or @username
                if text.lower() == "cancel":
                    report_sessions.pop(uid, None)
                    bot.send_message(uid, "❌ Report cancelled.", reply_markup=main_keyboard(uid))
                    return
                resolved = resolve_user_identifier(text)
                if not resolved:
                    bot.send_message(uid, f"Could not resolve user '{text}'. Enter numeric id or @username. Type 'cancel' to abort.")
                    return
                sess["reported"] = resolved
                sess["stage"] = "choose_reason"
                report_sessions[uid] = sess
                bot.send_message(uid, f"🔎 Reporting user {user_label(resolved)} ({resolved}). Choose reason:", reply_markup=report_keyboard())
                return
            elif stage == "reason":
                # Reporter is typing free-form reason
                if text.lower() == "cancel":
                    report_sessions.pop(uid, None)
                    bot.send_message(uid, "❌ Report cancelled.", reply_markup=chat_keyboard() if uid in active_pairs else main_keyboard(uid))
                    return
                if text:
                    reported_id = sess.get("reported")
                    rtype = sess.get("type") or "Other"
                    db_add_report(uid, reported_id, rtype, text)
                    forward_full_chat_to_admin(uid, reported_id, rtype)
                    try:
                        bot.send_message(ADMIN_ID, f"📝 Report reason from {user_label(uid)} ({uid}):\n{text}")
                    except Exception:
                        pass
                    report_sessions.pop(uid, None)
                    bot.send_message(uid, "✅ Report submitted! Admins reviewing...", reply_markup=chat_keyboard() if uid in active_pairs else main_keyboard(uid))
                    return
                else:
                    bot.send_message(uid, "Please type a short reason or 'cancel'.")
                    return
            elif stage == "choose_reason":
                # This occurs when reporter already provided target (postchat) and pressed a reason button.
                # But pressing a reason is handled in callback_query; this path is kept for safety.
                bot.send_message(uid, "Please press one of the reason buttons or 'Other' to type a reason.")
                return

    # If user is the reported partner of someone currently typing reason, block / ignore messages
    # find any active reporter sessions where reported == uid and stage == 'reason'
    reporters_submitting = [r for r, s in report_sessions.items() if s.get('reported') == uid and s.get('stage') == 'reason']
    if reporters_submitting:
        # inform the reported partner that their messages may be ignored
        bot.send_message(uid, "⚠️ The other user is submitting a report. Messages sent now may be ignored until they finish.")
        return

    # Block commands for reporters who are submitting (we already handled reporter's typing above; but block commands if still present)
    # reporter blocked states are: stage == 'reason'
    if any((uid == r and report_sessions.get(r, {}).get('stage') == 'reason') for r in report_sessions):
        # if they try to send a command, block (this will only match if we somehow reached here)
        if text.startswith('/'):
            bot.send_message(uid, "Command disabled while submitting report. Type your reason or 'cancel'.")
            return

    # Game messages
    if uid in games:
        handled = process_game_message(m)
        if handled:
            return

    # Quick buttons
    if text == '📊 Stats':
        u = db_get_user(uid)
        if u:
            premium_status = 'Premium Active ⭐' if db_is_premium(uid) else 'Free'
            stats_msg = (f"📊 YOUR STATS\n\n👤 Gender: {u.get('gender')}\n🎂 Age: {u.get('age')}\n🌍 Country: {u.get('country_flag')} {u.get('country')}\n\n💬 Messages: {u.get('messages_sent')}\n📸 Media Approved: {u.get('media_approved')}\n❌ Media Rejected: {u.get('media_rejected')}\n👥 People Referred: {u.get('referral_count')}\n\n🎁 {premium_status}")
            bot.send_message(uid, stats_msg, reply_markup=chat_keyboard())
            return

    if text == '🚩 Report':
        # acts like /report
        cmd_report(m)
        return

    if text == '⏭️ Next':
        cmd_next(m)
        return

    if text == '🛑 Stop':
        cmd_stop(m)
        return

    if text == '🔀 Search Random':
        cmd_search_random(m)
        return

    if text == '♀️ Search Opposite Gender':
        cmd_search_opposite(m)
        return

    if text == '♀️ Opposite Gender (Premium)':
        bot.send_message(uid, "💎 Premium required! Use /refer to unlock.")
        return

    if text == '⚙️ Settings':
        cmd_settings(m)
        return

    if text == '🔗 Refer':
        cmd_refer(m)
        return

    if text == '📖 Help':
        cmd_help(m)
        return

    # Content checks
    if is_banned_content(text):
        warn_user(uid, "Vulgar words or links")
        return

    # Forward to partner
    if uid in active_pairs:
        partner_id = active_pairs[uid]
        append_chat_history(uid, m.chat.id, m.message_id)
        try:
            # Before forwarding, if partner is currently reporting this user (they initiated report?), messages to partner should still be delivered normally
            bot.send_message(partner_id, text)
            with get_conn() as conn:
                conn.execute(
                    "UPDATE users SET messages_sent = messages_sent + 1 WHERE user_id = ?",
                    (uid,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error forwarding chat text: {e}")
            bot.send_message(uid, "Could not send message")
    else:
        bot.send_message(uid, "Not connected. Use /search_random.", reply_markup=main_keyboard(uid))

# =======================
# MEDIA HANDLER
# =======================

@bot.message_handler(content_types=["photo", "document", "video", "animation", "sticker", "audio", "voice"])
def handle_media(m):
    uid = m.from_user.id

    append_chat_history(uid, m.chat.id, m.message_id)

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if uid not in active_pairs:
        bot.send_message(uid, "Not connected")
        return

    partner_id = active_pairs[uid]

    # Get media ID
    media_id = None
    media_type = m.content_type

    try:
        if media_type == "photo":
            media_id = m.photo[-1].file_id
        elif media_type == "document":
            media_id = m.document.file_id
        elif media_type == "video":
            media_id = m.video.file_id
        elif media_type == "animation":
            media_id = m.animation.file_id
        elif media_type == "sticker":
            media_id = m.sticker.file_id
        elif media_type == "audio":
            media_id = m.audio.file_id
        elif media_type == "voice":
            media_id = m.voice.file_id
    except Exception:
        bot.send_message(uid, "Could not process media")
        return

    # Create pending request for partner to accept/reject
    media_key = secrets.token_hex(8)
    pending_media[media_key] = {"sender": uid, "partner": partner_id, "type": media_type, "file_id": media_id}

    try:
        bot.send_message(partner_id, "📷 Your partner sent media. Accept to view/forward, or Reject.", reply_markup=media_approval_keyboard(media_key))
    except Exception:
        bot.send_message(uid, "Could not notify partner about media")

@bot.callback_query_handler(func=lambda c: c.data.startswith("media:"))
def callback_media_action(call):
    try:
        _, action, media_key = call.data.split(":", 2)
    except Exception:
        bot.answer_callback_query(call.id, "Invalid", show_alert=True)
        return
    info = pending_media.get(media_key)
    if not info:
        bot.answer_callback_query(call.id, "Media expired or invalid.", show_alert=True)
        return
    sender = info['sender']
    partner = info['partner']
    media_type = info['type']
    file_id = info['file_id']
    # only the partner may accept/reject
    if call.from_user.id != partner:
        bot.answer_callback_query(call.id, "Not authorized.", show_alert=True)
        return

    if action == 'accept':
        try:
            if media_type == 'photo':
                bot.send_photo(partner, file_id)
            elif media_type == 'document':
                bot.send_document(partner, file_id)
            elif media_type == 'video':
                bot.send_video(partner, file_id)
            elif media_type == 'animation':
                bot.send_animation(partner, file_id)
            elif media_type == 'sticker':
                bot.send_sticker(partner, file_id)
            elif media_type == 'audio':
                bot.send_audio(partner, file_id)
            elif media_type == 'voice':
                bot.send_voice(partner, file_id)
            db_increment_media(sender, 'approved')
            bot.answer_callback_query(call.id, "Media accepted and forwarded.")
            try:
                bot.send_message(sender, "✅ Your media was accepted and forwarded.")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error forwarding media: {e}")
            bot.answer_callback_query(call.id, "Failed to forward media.", show_alert=True)
    else:
        # reject
        db_increment_media(sender, 'rejected')
        bot.answer_callback_query(call.id, "Media rejected.")
        try:
            bot.send_message(sender, "❌ Your media was rejected by your partner.")
        except Exception:
            pass

    # Remove pending media entry after any action
    pending_media.pop(media_key, None)

# =======================
# GAMES
# =======================

@bot.message_handler(commands=["game"])
def cmd_game(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "You must be in a chat to start a game.")
        return
    partner_id = active_pairs[uid]
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎲 Guess the Number (1-10)", callback_data=f"gamechoice:guess:{partner_id}"),
        types.InlineKeyboardButton("📝 Word Chain", callback_data=f"gamechoice:word:{partner_id}")
    )
    bot.send_message(uid, "Choose a game to propose to your partner:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("gamechoice:"))
def callback_game_choice(call):
    uid = call.from_user.id
    try:
        _, game_type, partner_id_str = call.data.split(":")
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Invalid selection", show_alert=True)
        return

    # validate current pairing
    if active_pairs.get(uid) != partner_id:
        bot.answer_callback_query(call.id, "Partner changed.", show_alert=True)
        return

    if game_type == "guess":
        # initiator (uid) sets secret, partner guesses
        secret = random.randint(1, 10)
        state = {"type": "guess", "secret": secret, "turn": partner_id, "initiator": uid}
        # store shared state for both users
        games[uid] = state
        games[partner_id] = state
        try:
            bot.send_message(uid, "🎮 Game started: Guess the Number (1-10).\nYour partner will try to guess the secret number. You may still chat normally.")
            bot.send_message(partner_id, "🎮 Game started: Guess the Number (1-10).\nTo guess, send a number 1-10. Only you can guess right now.")
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return
    else:
        # word chain: caller starts
        state = {"type": "word", "turn": uid, "other": partner_id, "last_letter": None, "used_words": set()}
        games[uid] = state
        games[partner_id] = state
        try:
            bot.send_message(uid, "🎮 Game started: Word Chain.\nYou start. Send the first word (single word).")
            bot.send_message(partner_id, "🎮 Game started: Word Chain.\nWaiting for partner to send the first word.")
        except Exception:
            pass
        bot.answer_callback_query(call.id)
        return

def process_game_message(message):
    uid = message.from_user.id
    state = games.get(uid)
    if not state:
        return False

    if state["type"] == "guess":
        # only the 'turn' (guesser) can guess
        if uid != state.get("turn"):
            return False
        text = (message.text or "").strip()
        if not text.isdigit():
            bot.send_message(uid, "Send a number between 1 and 10.")
            return True
        guess = int(text)
        if guess < 1 or guess > 10:
            bot.send_message(uid, "Number must be between 1 and 10.")
            return True
        secret = state["secret"]
        initiator = state["initiator"]
        if guess == secret:
            bot.send_message(uid, f"🎉 You guessed it! The number was {secret}. You win!")
            bot.send_message(initiator, f"😢 Your partner guessed the number {secret}. You lose.")
            # end game for both
            games.pop(uid, None)
            games.pop(initiator, None)
            return True
        elif guess < secret:
            bot.send_message(uid, "⬆️ Higher!")
            return True
        else:
            bot.send_message(uid, "⬇️ Lower!")
            return True

    elif state["type"] == "word":
        # must be sender's turn
        if uid != state.get("turn"):
            bot.send_message(uid, "Wait for your turn in the word chain game.")
            return True
        word = (message.text or "").strip().lower()
        # check single word
        if not word.isalpha():
            bot.send_message(uid, "Send a single word (letters only).")
            return True
        if word in state["used_words"]:
            bot.send_message(uid, "Word already used. Try another.")
            return True
        # if last_letter present, must start with that
        last_letter = state.get("last_letter")
        if last_letter and not word.startswith(last_letter):
            bot.send_message(uid, f"Word must start with '{last_letter.upper()}'.")
            return True
        # accept word
        state["used_words"].add(word)
        # set last_letter to last char of this word
        state["last_letter"] = word[-1]
        # swap turn
        other = state.get("other")
        state["turn"] = other if uid == state.get("turn") else uid  # simpler inference
        # notify other
        try:
            bot.send_message(state["turn"], f"✳️ Word received: {word}\nYour turn! Start with '{state['last_letter'].upper()}'.")
        except Exception:
            pass
        return True

    return False

@bot.message_handler(commands=["endgame"])
def cmd_end_game(message):
    uid = message.from_user.id
    if uid not in games:
        bot.send_message(uid, "You are not in a game.")
        return
    state = games.pop(uid, None)
    other = None
    # remove other references
    for k, v in list(games.items()):
        if v is state:
            other = k
            games.pop(k, None)
    if other:
        try:
            bot.send_message(other, "Game ended by your partner. You may continue chatting freely.")
        except Exception:
            pass
    bot.send_message(uid, "You ended the game. You may continue chatting freely.")

# =======================
# ADMIN COMMANDS (ban/unban/pradd/prrem)
# =======================

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "⛔ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban userid")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        # try numeric parse
        try:
            target_id = int(identifier)
        except:
            target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return
    hours = 24
    permanent = False
    reason = "Banned by admin"
    if len(parts) >= 3:
        if parts[2].lower() == "permanent":
            permanent = True
        else:
            try:
                hours = int(parts[2])
            except:
                hours = 24
    if len(parts) >= 4:
        reason = " ".join(parts[3:])
    db_ban_user(target_id, hours=hours, permanent=permanent, reason=reason)
    # Notify reporters (timestamp only, no identity)
    with get_conn() as conn:
        ban_time = datetime.now(timezone.utc).isoformat()
        dt = datetime.fromisoformat(ban_time)
        time_str = dt.strftime("%Y-%m-%d at %H:%M")
        reporters = conn.execute("SELECT DISTINCT reporter_id FROM reports WHERE reported_id = ?", (target_id,)).fetchall()
    for (reporter_id,) in reporters:
        try:
            bot.send_message(reporter_id, f"✅ Action Taken!\nReport reviewed & action taken on {time_str}\nThanks for keeping our community clean! 🧹\nKeep chatting & stay safe! 💬")
        except:
            pass
    if permanent:
        bot.reply_to(message, f"✅ User {target_id} PERMANENTLY BANNED.\nReason: {reason}\nReporters notified.")
    else:
        bot.reply_to(message, f"✅ User {target_id} banned for {hours} hours.\nReason: {reason}\nReporters notified.")
    if target_id in active_pairs:
        disconnect_user(target_id)

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "⛔ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban userid")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        try:
            target_id = int(identifier)
        except:
            target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return
    db_unban_user(target_id)
    user_warnings[target_id] = 0
    bot.reply_to(message, f"✅ User {target_id} unbanned.")
    try:
        bot.send_message(target_id, "✅ Your ban has been lifted!", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=["pradd"])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "⛔ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd userid YYYY-MM-DD")
        return
    identifier = parts[1]
    until_date = parts[2]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        try:
            target_id = int(identifier)
        except:
            target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return
    if not db_set_premium(target_id, until_date):
        bot.reply_to(message, "Invalid date! Use YYYY-MM-DD")
        return
    bot.reply_to(message, f"✅ User {target_id} premium until {until_date}")
    try:
        u = db_get_user(target_id)
        if u:
            premium_msg = (f"🎉 PREMIUM ADDED!\n\n✅ Valid until {until_date}\n♀️ Opposite gender search unlocked!")
            bot.send_message(target_id, premium_msg, reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=["prrem"])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "⛔ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /prrem userid")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        try:
            target_id = int(identifier)
        except:
            target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return
    db_remove_premium(target_id)
    bot.reply_to(message, f"✅ Premium removed for user {target_id}")
    try:
        bot.send_message(target_id, "Your premium has been removed.", reply_markup=main_keyboard(target_id))
    except:
        pass

# =======================
# DISCONNECT LOGIC & CLEANUP
# =======================

def disconnect_user(user_id):
    global active_pairs, pending_media, games
    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
        # ensure both sides removed
        try:
            del active_pairs[partner_id]
        except Exception:
            pass
        try:
            del active_pairs[user_id]
        except Exception:
            pass

        # Remove games involving them
        try:
            games.pop(user_id, None)
            games.pop(partner_id, None)
        except:
            pass

        # Clean pending media where either party involved: notify the other side
        keys_to_remove = []
        for key, info in list(pending_media.items()):
            if info.get("sender") in (user_id, partner_id) or info.get("partner") in (user_id, partner_id):
                keys_to_remove.append(key)
        for k in keys_to_remove:
            info = pending_media.pop(k, None)
            # notify counterpart if exists
            if info:
                other = info.get("partner") if info.get("partner") != (user_id or partner_id) else info.get("sender")
                try:
                    if other:
                        bot.send_message(other, "🔔 A pending media request was cancelled because the user left.")
                except:
                    pass

        # leave chat_history intact for admin forwarding if needed
        try:
            # notify partner if they still exist in chat (we call this from the leaver side so partner may be informed elsewhere)
            pass
        except:
            pass

# =======================
# COMMANDS SETUP & HELP
# =======================

def setup_bot_commands():
    user_cmds = [
        types.BotCommand("start", "Start bot & setup profile"),
        types.BotCommand("search_random", "Find random chat partner"),
        types.BotCommand("search_opposite", "Find opposite gender (Premium)"),
        types.BotCommand("next", "Skip to new partner"),
        types.BotCommand("stop", "Stop searching/chatting"),
        types.BotCommand("game", "Propose a game"),
        types.BotCommand("endgame", "End current game"),
        types.BotCommand("settings", "Edit profile"),
        types.BotCommand("refer", "Get referral link"),
        types.BotCommand("rules", "Chat rules"),
        types.BotCommand("help", "Help & commands"),
        types.BotCommand("report", "Report partner"),
    ]
    try:
        bot.set_my_commands(user_cmds)
        admin_scope = types.BotCommandScopeChat(chat_id=ADMIN_ID)
        admin_cmds = user_cmds + [
            types.BotCommand("ban", "Ban a user"),
            types.BotCommand("unban", "Unban a user"),
            types.BotCommand("pradd", "Add premium"),
            types.BotCommand("prrem", "Remove premium"),
        ]
        bot.set_my_commands(admin_cmds, scope=admin_scope)
    except Exception as e:
        logger.warning(f"Could not set commands: {e}")

@bot.message_handler(commands=["rules"])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = (
        "📋 CHAT RULES\n\n"
        "1️⃣ Be respectful. No harassment, threats, or hate speech.\n"
        "2️⃣ No explicit/adult content. No nudes or sexual requests.\n"
        "3️⃣ No spam, links, or external promotion.\n"
        "4️⃣ No personal information sharing (phone, address, etc.).\n"
        "5️⃣ Violators will be banned.\n\n"
        "🆘 Having issues? Use /report to report inappropriate behavior.\n\n"
        "⚠️ Stay safe, stay respectful! 💬"
    )
    bot.send_message(uid, rules_text)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    uid = message.from_user.id
    help_text = (
        "📖 HELP & COMMANDS\n\n"
        "🔍 SEARCH\n"
        "/search_random - Find random partner\n"
        "/search_opposite - Opposite gender (Premium only)\n\n"
        "💬 CHAT\n"
        "/next - Skip to new partner\n"
        "/stop - Exit chat & search\n\n"
        "🎮 GAMES\n"
        "/game - Propose a game\n"
        "/endgame - Stop current game\n\n"
        "👤 PROFILE\n"
        "/settings - Edit profile\n"
        "/refer - Get referral link & earn premium\n\n"
        "⚠️ SAFETY & RULES\n"
        "/report - Report inappropriate partner\n"
        "/rules - Read community guidelines\n\n"
        "🎁 PREMIUM\n"
        "Invite friends to unlock premium features\n\n"
        "❓ Questions? Contact admin!"
    )
    bot.send_message(uid, help_text, reply_markup=main_keyboard(uid))

# =======================
# RUN
# =======================

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Setting up bot commands...")
    setup_bot_commands()
    logger.info("GhostTalk Bot - FIXED starting...")
    port = int(os.getenv("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False), daemon=True).start()
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
