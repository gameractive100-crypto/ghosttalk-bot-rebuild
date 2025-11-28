#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FINAL PRODUCTION v3.4
Minimal, non-invasive fixes applied:
- Fix literal "\n" shown as text (runtime patch)
- Age -> immediate Country prompt (auto)
- Prevent duplicate media consent requests
- /report only when in active chat + basic unique report reasons
- cmd_start now registers next_step for age to make flow bulletproof
Everything else kept identical to original structure and logic.
"""

import os
import re
import sqlite3
import random
import secrets
import threading
import logging
import time
from datetime import datetime, timedelta

import requests
import telebot
from telebot import types
from flask import Flask

# ============= SAFETY: DATA / DB PATH SETUP =============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.getenv("DATA_PATH") or os.path.join(BASE_DIR, "data")
os.makedirs(DATA_PATH, exist_ok=True)
DB_PATH = os.getenv("DB_PATH") or os.path.join(DATA_PATH, "ghosttalk_final.db")

# ============= CONFIG =============
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))

WARNING_LIMIT = 2
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# ============= LOGGING =============
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.info(f"🔧 BASE_DIR: {BASE_DIR}, DB_PATH: {DB_PATH}")

# ============= TELEBOT & FLASK =============
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ---------- Minimal Runtime Fix (non-invasive) ----------
# Replace literal "\n" (backslash + n) with actual newline before sending messages.
# This keeps your original string literals unchanged but fixes display in Telegram.
try:
    _original_send_message = bot.send_message
    _original_answer_callback_query = bot.answer_callback_query
except Exception:
    _original_send_message = None
    _original_answer_callback_query = None

def _fix_text(s):
    if isinstance(s, str):
        return s.replace("\\n", "\n")
    return s

if _original_send_message:
    def _send_message(chat_id, text, *args, **kwargs):
        return _original_send_message(chat_id, _fix_text(text), *args, **kwargs)
    bot.send_message = _send_message

if _original_answer_callback_query:
    def _answer_callback_query(callback_id, text=None, *args, **kwargs):
        return _original_answer_callback_query(callback_id, _fix_text(text) if text is not None else text, *args, **kwargs)
    bot.answer_callback_query = _answer_callback_query

# ============= RUNTIME DATA =============
waiting_random = []
waiting_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history = {}
pending_game_invites = {}
games = {}
report_reason_pending = {}

# NEW: track users for whom bot expects country input next (only set when bot asked)
pending_country = set()

# ============= BANNED WORDS & LINK PATTERN =============
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography", "rape", "molest", "anj", "anjing", "babi", "asu",
    "kontl", "kontol", "puki", "memek", "jembut", "mc", "randi", "randika", "maderchod", "bsdk", "lauda", "lund", "chut", "choot",
    "chot", "chuut", "gand", "gaand", "ma ka lauda", "mkc", "teri ma ki chut", "teri ma ki chuut"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# ============= COMPLETE 195 COUNTRIES WITH FLAGS =============
COUNTRIES = {
    "afghanistan": "🇦🇫", "albania": "🇦🇱", "algeria": "🇩🇿", "andorra": "🇦🇩", "angola": "🇦🇴",
    "antigua and barbuda": "🇦🇬", "argentina": "🇦🇷", "armenia": "🇦🇲", "australia": "🇦🇺", "austria": "🇦🇹",
    "azerbaijan": "🇦🇿", "bahamas": "🇧🇸", "bahrain": "🇧🇭", "bangladesh": "🇧🇩", "barbados": "🇧🇧",
    "belarus": "🇧🇾", "belgium": "🇧🇪", "belize": "🇧🇿", "benin": "🇧🇯", "bhutan": "🇧🇹",
    "bolivia": "🇧🇴", "bosnia and herzegovina": "🇧🇦", "botswana": "🇧🇼", "brazil": "🇧🇷", "brunei": "🇧🇳",
    "bulgaria": "🇧🇬", "burkina faso": "🇧🇫", "burundi": "🇧🇮", "cambodia": "🇰🇭", "cameroon": "🇨🇲",
    "canada": "🇨🇦", "cape verde": "🇨🇻", "central african republic": "🇨🇫", "chad": "🇹🇩", "chile": "🇨🇱",
    "china": "🇨🇳", "colombia": "🇨🇴", "comoros": "🇰🇲", "congo": "🇨🇬", "costa rica": "🇨🇷",
    "croatia": "🇭🇷", "cuba": "🇨🇺", "cyprus": "🇨🇾", "czech republic": "🇨🇿", "denmark": "🇩🇰",
    "djibouti": "🇩🇯", "dominica": "🇩🇲", "dominican republic": "🇩🇴", "ecuador": "🇪🇨", "egypt": "🇪🇬",
    "el salvador": "🇸🇻", "equatorial guinea": "🇬🇶", "eritrea": "🇪🇷", "estonia": "🇪🇪", "eswatini": "🇸🇿",
    "ethiopia": "🇪🇹", "fiji": "🇫🇯", "finland": "🇫🇮", "france": "🇫🇷", "gabon": "🇬🇦",
    "gambia": "🇬🇲", "georgia": "🇬🇪", "germany": "🇩🇪", "ghana": "🇬🇭", "greece": "🇬🇷",
    "grenada": "🇬🇩", "guatemala": "🇬🇹", "guinea": "🇬🇳", "guinea-bissau": "🇬🇼", "guyana": "🇬🇾",
    "haiti": "🇭🇹", "honduras": "🇭🇳", "hungary": "🇭🇺", "iceland": "🇮🇸", "india": "🇮🇳",
    "indonesia": "🇮🇩", "iran": "🇮🇷", "iraq": "🇮🇶", "ireland": "🇮🇪", "israel": "🇮🇱",
    "italy": "🇮🇹", "jamaica": "🇯🇲", "japan": "🇯🇵", "jordan": "🇯🇴", "kazakhstan": "🇰🇿",
    "kenya": "🇰🇪", "kiribati": "🇰🇮", "korea north": "🇰🇵", "korea south": "🇰🇷", "kuwait": "🇰🇼",
    "kyrgyzstan": "🇰🇬", "laos": "🇱🇦", "latvia": "🇱🇻", "lebanon": "🇱🇧", "lesotho": "🇱🇸",
    "liberia": "🇱🇷", "libya": "🇱🇾", "liechtenstein": "🇱🇮", "lithuania": "🇱🇹", "luxembourg": "🇱🇺",
    "madagascar": "🇲🇬", "malawi": "🇲🇼", "malaysia": "🇲🇾", "maldives": "🇲🇻", "mali": "🇲🇱",
    "malta": "🇲🇹", "marshall islands": "🇲🇭", "mauritania": "🇲🇷", "mauritius": "🇲🇺", "mexico": "🇲🇽",
    "micronesia": "🇫🇲", "moldova": "🇲🇩", "monaco": "🇲🇨", "mongolia": "🇲🇳", "montenegro": "🇲🇪",
    "morocco": "🇲🇦", "mozambique": "🇲🇿", "myanmar": "🇲🇲", "namibia": "🇳🇦", "nauru": "🇳🇷",
    "nepal": "🇳🇵", "netherlands": "🇳🇱", "new zealand": "🇳🇿", "nicaragua": "🇳🇮", "niger": "🇳🇪",
    "nigeria": "🇳🇬", "north macedonia": "🇲🇰", "norway": "🇳🇴", "oman": "🇴🇲", "pakistan": "🇵🇰",
    "palau": "🇵🇼", "palestine": "🇵🇸", "panama": "🇵🇦", "papua new guinea": "🇵🇬", "paraguay": "🇵🇾",
    "peru": "🇵🇪", "philippines": "🇵🇭", "poland": "🇵🇱", "portugal": "🇵🇹", "qatar": "🇶🇦",
    "romania": "🇷🇴", "russia": "🇷🇺", "rwanda": "🇷🇼", "saint kitts and nevis": "🇰🇳", "saint lucia": "🇱🇨",
    "saint vincent and the grenadines": "🇻🇨", "samoa": "🇼🇸", "san marino": "🇸🇲", "sao tome and principe": "🇸🇹", "saudi arabia": "🇸🇦",
    "senegal": "🇸🇳", "serbia": "🇷🇸", "seychelles": "🇸🇨", "sierra leone": "🇸🇱", "singapore": "🇸🇬",
    "slovakia": "🇸🇰", "slovenia": "🇸🇮", "solomon islands": "🇸🇧", "somalia": "🇸🇴", "south africa": "🇿🇦",
    "south sudan": "🇸🇸", "spain": "🇪🇸", "sri lanka": "🇱🇰", "sudan": "🇸🇩", "suriname": "🇸🇷",
    "sweden": "🇸🇪", "switzerland": "🇨🇭", "syria": "🇸🇾", "taiwan": "🇹🇼", "tajikistan": "🇹🇯",
    "tanzania": "🇹🇿", "thailand": "🇹🇭", "timor-leste": "🇹🇱", "togo": "🇹🇬", "tonga": "🇹🇴",
    "trinidad and tobago": "🇹🇹", "tunisia": "🇹🇳", "turkey": "🇹🇷", "turkmenistan": "🇹🇲", "tuvalu": "🇹🇻",
    "uganda": "🇺🇬", "ukraine": "🇺🇦", "united arab emirates": "🇦🇪", "united kingdom": "🇬🇧", "united states": "🇺🇸",
    "uruguay": "🇺🇾", "uzbekistan": "🇺🇿", "vanuatu": "🇻🇺", "vatican city": "🇻🇦", "venezuela": "🇻🇪",
    "vietnam": "🇻🇳", "yemen": "🇾🇪", "zambia": "🇿🇲", "zimbabwe": "🇿🇼"
}

COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "america": "united states",
    "uk": "united kingdom", "britain": "united kingdom",
    "uae": "united arab emirates",
    "south korea": "korea south", "north korea": "korea north",
    "czechia": "czech republic"
}

def get_country_info(user_input):
    if not user_input:
        return None
    normalized = user_input.strip().lower()
    normalized = COUNTRY_ALIASES.get(normalized, normalized)
    if normalized in COUNTRIES:
        return normalized.title(), COUNTRIES[normalized]
    return None

# ============= DATABASE =============
def get_conn():
    db_parent = os.path.dirname(DB_PATH) or BASE_DIR
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
        row = conn.execute("""SELECT user_id, username, first_name, gender, age, country, country_flag,
            messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until
            FROM users WHERE user_id=?""", (user_id,)).fetchone()
        if not row:
            return None
        return {"user_id": row[0], "username": row[1], "first_name": row[2], "gender": row[3], "age": row[4],
                "country": row[5], "country_flag": row[6], "messages_sent": row[7],
                "media_approved": row[8], "media_rejected": row[9], "referral_code": row[10],
                "referral_count": row[11], "premium_until": row[12]}

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000,99999)}"
    with get_conn() as conn:
        conn.execute("""INSERT OR IGNORE INTO users (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (uid, user.username or "", user.first_name or "", None, None, None, None, datetime.utcnow().isoformat(), ref_code))
        conn.commit()

def db_set_gender(user_id, gender):
    with get_conn() as conn:
        conn.execute("UPDATE users SET gender=? WHERE user_id=?", (gender, user_id))
        conn.commit()

def db_set_age(user_id, age):
    with get_conn() as conn:
        conn.execute("UPDATE users SET age=? WHERE user_id=?", (age, user_id))
        conn.commit()

def db_set_country(user_id, country, flag):
    with get_conn() as conn:
        conn.execute("UPDATE users SET country=?, country_flag=? WHERE user_id=?", (country, flag, user_id))
        conn.commit()

def db_is_premium(user_id):
    if user_id == ADMIN_ID:
        return True
    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return False
    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.utcnow()
    except:
        return False

def db_set_premium(user_id, until_date):
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute("UPDATE users SET premium_until=? WHERE user_id=?", (dt, user_id))
            conn.commit()
        return True
    except Exception:
        return False

def db_remove_premium(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until=NULL WHERE user_id=?", (user_id,))
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
        conn.execute("UPDATE users SET referral_count=referral_count+1 WHERE user_id=?", (user_id,))
        conn.commit()
        u = db_get_user(user_id)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.utcnow() + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            conn.execute("UPDATE users SET premium_until=?, referral_count=0 WHERE user_id=?", (premium_until, user_id))
            conn.commit()
            try:
                bot.send_message(user_id, f"🎉 PREMIUM UNLOCKED! {PREMIUM_DURATION_HOURS} hour premium earned!\\n🎯 Opposite gender search unlocked!")
            except:
                pass

def db_is_banned(user_id):
    if user_id == ADMIN_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        ban_until, permanent = row
        if permanent:
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
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                         (user_id, None, 1, reason))
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                         (user_id, until, 0, reason))
        conn.commit()

def db_unban_user(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id=?", (user_id,))
        conn.commit()

def db_add_report(reporter_id, reported_id, report_type, reason):
    with get_conn() as conn:
        conn.execute("""INSERT INTO reports (reporter_id, reported_id, report_type, reason, timestamp)
                        VALUES (?, ?, ?, ?, ?)""", (reporter_id, reported_id, report_type, reason, datetime.utcnow().isoformat()))
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

# ============= HELPERS =============
def resolve_user_identifier(identifier):
    """
    ✅ FIXED: Supports both @username and username format
    Handles: 123456789 (ID) or @username or username
    """
    if not identifier:
        return None
    identifier = identifier.strip()

    # Try as numeric ID first
    try:
        uid = int(identifier)
        return uid
    except:
        pass

    # Strip @ if present and lookup by username
    uname = identifier.lstrip("@").strip()
    if not uname:
        return None

    try:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(username)=LOWER(?)", (uname,)).fetchone()
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
            bot.send_message(user_id, f"🚫 You have been temporarily banned for {TEMP_BAN_HOURS} hours.\\nReason: {reason}")
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ Warning {count}/{WARNING_LIMIT}\\n{reason}\\n{WARNING_LIMIT-count} more warnings = ban.")
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
        bot.send_message(ADMIN_ID, f"🚩 NEW REPORT\\nType: {report_type}\\nReporter: {user_label(reporter_id)} ({reporter_id})\\nReported: {user_label(reported_id)} ({reported_id})\\nTime: {datetime.utcnow().isoformat()}")
        reporter_msgs = chat_history.get(reporter_id, [])[-10:]
        if reporter_msgs:
            bot.send_message(ADMIN_ID, "— Reporter messages —")
            for chat_id, msg_id in reporter_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")
        reported_msgs = chat_history.get(reported_id, [])[-10:]
        if reported_msgs:
            bot.send_message(ADMIN_ID, "— Reported user messages —")
            for chat_id, msg_id in reported_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")
        bot.send_message(ADMIN_ID, "End of forwarded messages.")
    except Exception as e:
        logger.error(f"Error forwarding chat: {e}")

# ============= KEYBOARDS =============
def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔀 Search Random")
    u = db_get_user(user_id)
    if u and u["gender"]:
        if db_is_premium(user_id):
            kb.add("🎯 Search Opposite Gender")
        else:
            kb.add("Opposite Gender (Premium)")
    kb.add("🛑 Stop")
    kb.add("⚙️ Settings", "👥 Refer")
    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("📊 Stats")
    kb.add("⏭️ Next", "🛑 Stop")
    return kb

def report_keyboard():
    # NEW: basic, unique four reasons + other
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚫 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("📎 Unwanted Content", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("⚠️ Inappropriate Messages", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🕵️ Suspicious Activity", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("Other", callback_data="rep:other")
    )
    return markup

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "👨" if partner_user["gender"] == "Male" else ("👩" if partner_user["gender"] == "Female" else "")
    age_text = str(partner_user["age"]) if partner_user["age"] else "Unknown"
    country_flag = partner_user["country_flag"] or "🌍"
    country_name = partner_user["country"] or "Global"
    msg = (
        "🎉 Partner Found! 🎉\\n\\n"
        f"🎂 Age: {age_text}\\n"
        f"👤 Gender: {gender_emoji} {partner_user.get('gender') or 'Unknown'}\\n"
        f"🌍 Country: {country_flag} {country_name}\\n"
    )
    if viewer_id == ADMIN_ID:
        partner_name = partner_user["first_name"] or partner_user["username"] or "Unknown"
        msg += f"\\n👤 Name: {partner_name}\\n🆔 ID: {partner_user['user_id']}\\n"
    msg += "\\n💬 Enjoy chat! Type /next for new partner."
    return msg

# ============= MATCHMAKING =============
def match_users():
    global waiting_random, waiting_opposite, active_pairs
    i = 0
    while i < len(waiting_opposite):
        uid, searcher_gender = waiting_opposite[i]
        opposite_gender = "Male" if searcher_gender == "Female" else "Female"
        match_index = None
        for j, other_uid in enumerate(waiting_random):
            other_data = db_get_user(other_uid)
            if other_data and other_data['gender'] == opposite_gender:
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
            logger.info(f"✅ Matched opposite: {uid} <-> {found_uid}")
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
        logger.info(f"✅ Matched random: {u1} <-> {u2}")

# ============= FLASK ROUTES (FOR RENDER + UPTIMEROBOT) =============
@app.route("/")
def home():
    return "🤖 GhostTalk Bot Running!", 200

@app.route("/health")
def health():
    return {"status": "✅ ok", "timestamp": datetime.utcnow().isoformat()}, 200

# ============= COMMAND HANDLERS =============
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are BANNED from this bot.")
        return
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        with get_conn() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
            if referrer and referrer[0] != user.id:
                db_add_referral(referrer[0])
                bot.send_message(user.id, "✅ You joined via referral link!")
    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
                   types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
        bot.send_message(user.id, "👋 Welcome to GhostTalk!\\n\\n🎯 Select your gender:", reply_markup=markup)
    elif not u["age"]:
        # If gender present but age missing, ask age immediately and register next_step
        bot.send_message(user.id, "📍 Enter your age (12-99 only):")
        try:
            bot.register_next_step_handler(message, process_new_age)
        except Exception:
            pass
    elif not u["country"]:
        bot.send_message(user.id, "🌍 Enter your country name:\\n\\n⚠️ Country CANNOT be changed later unless PREMIUM!")
    else:
        premium_status = "✅ Premium Active" if db_is_premium(user.id) else "🆓 Free User"
        welcome_msg = (
            f"👋 Welcome back!\\n\\n"
            f"👤 Gender: {u['gender']}\\n"
            f"🎂 Age: {u['age']}\\n"
            f"🌍 Country: {u['country_flag']} {u['country']}\\n"
            f"{premium_status}\\n\\n"
            "🎯 Ready to chat?"
        )
        bot.send_message(user.id, welcome_msg, reply_markup=main_keyboard(user.id))

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
        bot.answer_callback_query(call.id, f"Already {gender_display}!", show_alert=True)
        return
    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "✅ Gender set!", show_alert=True)
    try:
        bot.edit_message_text(f"✅ Gender: {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass
    # Immediately prompt for age after gender selection if age not set
    u = db_get_user(uid)
    if not u or not u.get("age"):
        try:
            bot.send_message(uid, "📍 Enter your age (12-99 only):")
            # register next step to process_new_age directly using the message object
            bot.register_next_step_handler(call.message, process_new_age)
        except:
            pass

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free User"
    gender_emoji = "👨" if u["gender"] == "Male" else ("👩" if u["gender"] == "Female" else "")
    settings_text = (
        "⚙️ SETTINGS & PROFILE\\n\\n"
        f"👤 Gender: {gender_emoji} {u['gender'] or 'Not set'}\\n"
        f"🎂 Age: {u['age'] or 'Not set'}\\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\\n\\n"
        f"📊 Messages Sent: {u['messages_sent']}\\n"
        f"✅ Media Approved: {u['media_approved']}\\n"
        f"❌ Media Rejected: {u['media_rejected']}\\n\\n"
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\\n"
        f"{premium_status}\\n\\n"
        "🔗 Change Profile:"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔗 Refer Link", callback_data="ref:link"))
    markup.row(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
               types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
    markup.row(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))
    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def callback_change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, "🎂 Enter new age (12-99):")
    bot.register_next_step_handler(call.message, process_new_age)

def process_new_age(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    # validate age
    if not text.isdigit():
        bot.send_message(uid, "❌ Enter age as number (e.g., 21):")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, "❌ Age must be 12-99. Try again:")
        bot.register_next_step_handler(message, process_new_age)
        return

    # save age
    db_set_age(uid, age)

    # ✔️ AUTO ASK COUNTRY IMMEDIATELY (NO WAITING FOR USER MESSAGE)
    bot.send_message(
        uid,
        f"✅ Age: {age}\\n\\n🌍 Enter your country name (e.g., India):\\n⚠️ You cannot change it later!"
    )

    # mark that we are expecting country from this user and register next-step
    pending_country.add(uid)
    try:
        bot.register_next_step_handler(message, process_new_country)
    except Exception:
        # safe fallback: leave pending_country set so handler_text will consider it
        pass

def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    # only process country if pending_country expects it
    if uid not in pending_country:
        bot.send_message(uid, "Use /settings or /start to change profile.")
        return
    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"❌ '{text}' not valid.\\n🔍 Try again (e.g., India):")
        # keep pending and re-register
        try:
            bot.register_next_step_handler(message, process_new_country)
        except:
            pass
        return
    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    # done — remove pending flag
    pending_country.discard(uid)
    bot.send_message(uid, f"✅ Country: {country_flag} {country_name}\\n\\n🎯 Profile complete!", reply_markup=main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref:"))
def callback_referral(call):
    uid = call.from_user.id
    _, action = call.data.split(":")
    if action == "link":
        u = db_get_user(uid)
        if not u:
            bot.answer_callback_query(call.id, "Error!", show_alert=True)
            return
        ref_link = db_get_referral_link(uid)
        remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]
        refer_text = (
            "👥 REFERRAL SYSTEM\\n\\n"
            f"🔗 Your Referral Link:\\n{ref_link}\\n\\n"
            f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\\n"
            f"🎁 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\\n"
            "✨ Unlock opposite gender search!\\n\\n"
        )
        if remaining > 0:
            refer_text += f"📍 Invite {remaining} more friends to unlock premium!"
        else:
            refer_text += "✅ Premium unlocked! Keep inviting for more!"
        refer_text += (
            "\\n\\n📋 How it works:\\n"
            "1️⃣ Share your link with friends\\n"
            "2️⃣ They join with your link\\n"
            f"3️⃣ Get premium after {PREMIUM_REFERRALS_NEEDED} referrals!"
        )
        bot.send_message(uid, refer_text)
        bot.answer_callback_query(call.id, "✅")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def callback_set_country(call):
    uid = call.from_user.id
    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, "💎 Country change requires PREMIUM!\\n✨ Refer friends to unlock.", show_alert=True)
        return
    bot.send_message(uid, "🌍 Enter your new country name:")
    # set pending flag and next step
    pending_country.add(uid)
    bot.register_next_step_handler(call.message, process_new_country)

@bot.message_handler(commands=['refer'])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    ref_link = db_get_referral_link(uid)
    remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]
    refer_text = (
        "👥 REFERRAL SYSTEM\\n\\n"
        f"🔗 Your Referral Link:\\n{ref_link}\\n\\n"
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\\n"
        f"🎁 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\\n"
        "✨ Unlock opposite gender search!\\n\\n"
    )
    if remaining > 0:
        refer_text += f"📍 Invite {remaining} more friends to unlock premium!"
    else:
        refer_text += "✅ Premium unlocked! Keep inviting for more!"
    refer_text += (
        "\\n\\n📋 How it works:\\n"
        "1️⃣ Share your link with friends\\n"
        "2️⃣ They join with your link\\n"
        f"3️⃣ Get premium after {PREMIUM_REFERRALS_NEEDED} referrals!"
    )
    bot.send_message(uid, refer_text)

@bot.message_handler(commands=['search_random'])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return
    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "❌ Complete profile first! Use /start")
        return
    if uid in active_pairs:
        bot.send_message(uid, "⏳ Already in chat! Use /next for new partner.")
        return
    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "⏳ You're already in the queue. Cancel anytime: /stop")
        return
    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for random partner...\\n⏳ Please wait...")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return
    if not db_is_premium(uid):
        premium_required_msg = (
            "💎 PREMIUM REQUIRED!\\n\\n"
            f"✨ Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock ({PREMIUM_DURATION_HOURS} hour premium).\\n"
            "🔗 Use /refer to get your link!"
        )
        bot.send_message(uid, premium_required_msg)
        return
    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "❌ Complete profile first! Use /start")
        return
    if uid in active_pairs:
        bot.send_message(uid, "⏳ Already in chat! Use /next for new partner.")
        return
    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "⏳ You're already in the queue. Cancel anytime: /stop")
        return
    remove_from_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "🎯 Searching for opposite gender partner...\\n⏳ Please wait...")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    bot.send_message(uid, "✅ Search/chat stopped. Use main menu to start again.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not in chat. Use search commands.")
        return
    partner = active_pairs.get(uid)
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Looking for new partner...", reply_markup=main_keyboard(uid))
    waiting_random.append(uid)
    match_users()

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    # ONLY allow reporting when currently in an active chat
    if uid not in active_pairs:
        bot.send_message(uid, "❌ You are not in an active chat. You can only report while chatting with someone.")
        return
    bot.send_message(uid, "⚠️ Select reason for report:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id
    # Partner must be currently connected
    partner_id = active_pairs.get(uid)
    if not partner_id:
        bot.answer_callback_query(call.id, "No active partner to report", show_alert=True)
        return

    _, report_type = call.data.split(":")
    report_type_map = {
        "spam": "Spam",
        "unwanted": "Unwanted Content",
        "inappropriate": "Inappropriate Messages",
        "suspicious": "Suspicious Activity",
        "other": "Other"
    }
    report_type_name = report_type_map.get(report_type, "Other")

    if report_type == "other":
        # ask for custom reason
        report_reason_pending[uid] = partner_id
        bot.answer_callback_query(call.id, "Please type the reason for reporting (short).", show_alert=True)
        bot.send_message(uid, "Please type the reason for your report (short).")
        return

    # Predefined reason flow
    db_add_report(uid, partner_id, report_type_name, "")
    forward_full_chat_to_admin(uid, partner_id, report_type_name)
    db_ban_user(partner_id, hours=TEMP_BAN_HOURS, reason=report_type_name)
    bot.send_message(uid, "✅ Report submitted!\\n\\n👮 Admins reviewing...\\n⏱️ User temp-banned 24hrs.\\n💬 Keep chatting! ✅")
    bot.answer_callback_query(call.id, "Report submitted. Keep chatting! ✅")

@bot.message_handler(commands=['pradd'])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd [user_id|username] [YYYY-MM-DD]")
        return
    identifier = parts[1]
    until_date = parts[2]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID or @username.")
        return
    if not db_set_premium(target_id, until_date):
        bot.reply_to(message, "❌ Invalid date! Use YYYY-MM-DD")
        return
    bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) premium until {until_date}")
    try:
        u = db_get_user(target_id)
        if u:
            premium_msg = f"🎉 PREMIUM ADDED!\\n✅ Valid until {until_date}\\n🎯 Opposite gender search unlocked!"
            bot.send_message(target_id, premium_msg, reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['prrem'])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /prrem [user_id|username]")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID or @username.")
        return
    db_remove_premium(target_id)
    bot.reply_to(message, f"✅ Premium removed for {identifier} (id:{target_id})")
    try:
        bot.send_message(target_id, "❌ Your premium has been removed.", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban [user_id|@username|username] [hours/permanent] [reason]")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID, @username, or username.")
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
    if len(parts) == 4:
        reason = parts[3]
    db_ban_user(target_id, hours=hours, permanent=permanent, reason=reason)
    if permanent:
        bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) PERMANENTLY BANNED. {reason}")
        try:
            bot.send_message(target_id, f"🚫 PERMANENTLY BANNED.\\nReason: {reason}")
        except:
            pass
    else:
        bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) banned for {hours} hours. {reason}")
        try:
            bot.send_message(target_id, f"🚫 Banned for {hours} hours.\\nReason: {reason}")
        except:
            pass
    if target_id in active_pairs:
        disconnect_user(target_id)

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban [user_id|@username|username]")
        return
    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID, @username, or username.")
        return
    db_unban_user(target_id)
    user_warnings[target_id] = 0
    bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) unbanned")
    try:
        bot.send_message(target_id, "✅ Your ban has been lifted!", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['game'])
def cmd_game(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ You must be in a chat to start a game.")
        return
    partner_id = active_pairs[uid]
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🎯 Guess the Number (1-10)", callback_data=f"game_choice:guess:{partner_id}"),
               types.InlineKeyboardButton("🔗 Word Chain", callback_data=f"game_choice:word:{partner_id}"))
    bot.send_message(uid, "Choose a game to propose to your partner:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_choice:"))
def callback_game_choice(call):
    uid = call.from_user.id
    try:
        _, game_type, partner_id_str = call.data.split(":",2)
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Invalid selection", show_alert=True)
        return
    if active_pairs.get(uid) != partner_id:
        bot.answer_callback_query(call.id, "Partner not connected or changed.", show_alert=True)
        return
    pending_game_invites[partner_id] = {'initiator': uid, 'game': game_type}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"game_invite_resp:accept:{uid}:{game_type}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"game_invite_resp:reject:{uid}:{game_type}"))
    desc = "Guess the Number" if game_type == "guess" else "Word Chain"
    try:
        msg = bot.send_message(partner_id, f"🎮 Your partner wants to play *{desc}*. Do you accept?", reply_markup=markup, parse_mode='Markdown')
        bot.send_message(uid, "Invitation sent. Waiting for partner's response...")
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error sending game invite: {e}")
        bot.answer_callback_query(call.id, "Error sending invite", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_invite_resp:"))
def callback_game_invite_resp(call):
    responder = call.from_user.id
    try:
        _, resp, initiator_str, game_type = call.data.split(":",3)
        initiator_id = int(initiator_str)
    except:
        bot.answer_callback_query(call.id, "Invalid response", show_alert=True)
        return
    invite = pending_game_invites.pop(responder, None)
    if not invite or invite.get('initiator') != initiator_id or invite.get('game') != game_type:
        bot.answer_callback_query(call.id, "No matching invitation.", show_alert=True)
        return
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    if resp == "reject":
        try:
            bot.send_message(initiator_id, "❌ Your partner declined the game invitation.")
            # bot.send_message(responder, "❌ You declined the game invitation.")
        except:
            pass
        bot.answer_callback_query(call.id)
        return
    if game_type == 'guess':
        secret = random.randint(1,10)
        state = {'type':'guess','secret':secret,'guesser':responder,'initiator':initiator_id}
        games[initiator_id] = state
        games[responder] = state
        try:
            bot.send_message(initiator_id, "🎮 Game started: Guess the Number (1-10).\\nYour partner will try to guess the secret number.\\nYou may still chat normally.")
            bot.send_message(responder, "🎮 Game started: Guess the Number (1-10).\\nTry to guess the number (send a number 1-10).")
        except:
            pass
        bot.answer_callback_query(call.id)
        return
    else:
        state = {'type':'word','turn':initiator_id,'other':responder,'last_letter':None,'used_words':set()}
        games[initiator_id] = state
        games[responder] = state
        try:
            bot.send_message(initiator_id, "🎮 Game started: Word Chain.\\nYou start. Send the first word with /word <word>.")
            bot.send_message(responder, "🎮 Game started: Word Chain.\\nWait for partner to send the first word. You can still chat normally.")
        except:
            pass
        bot.answer_callback_query(call.id)
        return

def process_game_message(message):
    """
    ✅ FIXED: Only processes /word and /guess commands
    Normal text messages are NOT blocked - they flow freely to partner
    """
    uid = message.from_user.id
    state = games.get(uid)
    if not state:
        return False

    if state['type'] == 'guess':
        if uid != state['guesser']:
            return False
        text = (message.text or "").strip()
        if not text.isdigit():
            bot.send_message(uid, "⚠️ Send a number between 1 and 10.")
            return True
        guess = int(text)
        if guess < 1 or guess > 10:
            bot.send_message(uid, "⚠️ Number must be between 1 and 10.")
            return True
        secret = state['secret']
        initiator = state['initiator']
        if guess == secret:
            bot.send_message(uid, f"🎉 You guessed it! The number was {secret}. You win!")
            bot.send_message(initiator, f"❌ Your partner guessed the number {secret}. You lose.")
            games.pop(uid, None)
            games.pop(initiator, None)
            return True
        elif guess < secret:
            bot.send_message(uid, "📈 Higher!")
            return True
        else:
            bot.send_message(uid, "📉 Lower!")
            return True

    if state['type'] == 'word':
        return False

    return False

@bot.message_handler(commands=['word'])
def cmd_word(message):
    uid = message.from_user.id
    if uid not in games:
        bot.send_message(uid, "❌ You are not in a Word Chain game.")
        return
    state = games.get(uid)
    if not state or state.get('type') != 'word':
        bot.send_message(uid, "❌ Not a Word Chain game.")
        return
    if state['turn'] != uid:
        bot.send_message(uid, "🔒 It's not your turn.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /word <word>")
        return
    word = parts[1].strip().lower()
    if not word.isalpha():
        bot.send_message(uid, "⚠️ Send a single word (letters only).")
        return
    last_letter = state['last_letter']
    if last_letter and word[0] != last_letter:
        loser = uid
        other = state['other'] if state['other'] != uid else state['turn']
        try:
            bot.send_message(other, f"🎉 You win! Your partner used a word not starting with '{last_letter}'.")
            bot.send_message(loser, f"❌ You lose — the word must start with '{last_letter}'.")
        except:
            pass
        games.pop(uid, None)
        games.pop(other, None)
        return
    if word in state['used_words']:
        bot.send_message(uid, "⚠️ This word was already used in this game. Try a different word.")
        return
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=6)
        if r.status_code != 200:
            bot.send_message(uid, "❌ That word is not found in dictionary. Try another.")
            return
    except Exception:
        bot.send_message(uid, "⚠️ Dictionary check failed (network). Try again.")
        return
    state['used_words'].add(word)
    state['last_letter'] = word[-1]
    prev_turn = state['turn']
    next_turn = state['other']
    state['turn'] = next_turn
    state['other'] = prev_turn
    try:
        bot.send_message(next_turn, f"➡️ Your turn! Send a word starting with '{state['last_letter'].upper()}' (use /word <word>).")
        bot.send_message(prev_turn, "✅ Move accepted. Waiting for partner's move. You can continue normal chat.")
    except:
        pass

@bot.message_handler(commands=['endgame'])
def cmd_endgame(message):
    uid = message.from_user.id
    if uid not in games:
        bot.send_message(uid, "❌ You are not in a game.")
        return
    state = games.pop(uid, None)
    other = None
    for k, v in list(games.items()):
        if v is state:
            other = k
            games.pop(k, None)
    if other:
        try:
            bot.send_message(other, "🛑 Game ended by your partner. You may continue chatting freely.")
        except:
            pass
    bot.send_message(uid, "🛑 You ended the game. You may continue chatting freely.")

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = (
        "📘 *Chat Rules — Please read before chatting*\\n\\n"
        "1️⃣ *Be respectful.* No harassment, threats, hate speech or abusive language.\\n\\n"
        "2️⃣ *Protect privacy.* Don't ask for or share phone numbers, home addresses, payment info, or other personal details.\\n\\n"
        "3️⃣ *No explicit content.* Sexual content, nudity, or pornographic material is strictly prohibited.\\n\\n"
        "4️⃣ *No spam or advertising.* Unsolicited links, referral spam, or promotions are not allowed.\\n\\n"
        "5️⃣ *Report violations.* Use the Report button if someone breaks the rules.\\n\\n"
        "🔒 *Violations may lead to warnings or temporary/permanent bans.*"
    )
    bot.send_message(uid, rules_text, parse_mode="Markdown", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = (
        "🤖 *GhostTalk — Quick Commands*\\n\\n"
        "/start - Setup profile / change basic info\\n"
        "/search_random - Find a random partner\\n"
        "/search_opposite_gender - Find opposite-gender partner (Premium)\\n"
        "/next - Skip current partner and find new\\n"
        "/stop - Stop current chat or cancel search\\n"
        "/game - Propose a game to your partner\\n"
        "/word - Play move in Word Chain (use `/word <word>`)\\n"
        "/endgame - End current game\\n"
        "/refer - Get your referral link\\n"
        "/rules - Read chat rules\\n"
        "/settings - Profile & settings\\n"
        "/report - Report your current or last partner\\n"
    )
    bot.send_message(uid, help_text, parse_mode="Markdown")

def set_bot_commands():
    try:
        user_cmds = [
            types.BotCommand("start", "🔰 Start / Setup"),
            types.BotCommand("search_random", "🔍 Find a random partner"),
            types.BotCommand("search_opposite_gender", "🎯 Find opposite gender (Premium)"),
            types.BotCommand("next", "⏭️ Next partner"),
            types.BotCommand("stop", "🛑 Stop searching/chatting"),
            types.BotCommand("help", "🆘 Help & commands"),
            types.BotCommand("game", "🎮 Propose a game to partner"),
            types.BotCommand("word", "📝 Play word in Word Chain"),
            types.BotCommand("endgame", "🛑 End current game"),
            types.BotCommand("refer", "👥 Invite friends"),
            types.BotCommand("rules", "📘 Chat rules"),
            types.BotCommand("settings", "⚙️ Profile & settings"),
            types.BotCommand("report", "🚩 Report partner")
        ]
        bot.set_my_commands(user_cmds)
        try:
            admin_scope = types.BotCommandScopeChat(chat_id=ADMIN_ID)
            admin_cmds = [
                types.BotCommand("ban", "Ban a user"),
                types.BotCommand("unban", "Unban a user"),
                types.BotCommand("pradd", "Add premium for user"),
                types.BotCommand("prrem", "Remove premium for user")
            ]
            bot.set_my_commands(admin_cmds, scope=admin_scope)
        except Exception as e:
            logger.warning(f"Could not set admin-scoped commands: {e}")
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")

def disconnect_user(user_id):
    global active_pairs
    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
        chat_history[user_id] = chat_history.get(user_id, chat_history.get(user_id, []))
        chat_history[partner_id] = chat_history.get(partner_id, chat_history.get(partner_id, []))
        try:
            del active_pairs[partner_id]
        except:
            pass
        try:
            del active_pairs[user_id]
        except:
            pass
        try:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🚩 Report", callback_data=f"report_req:{partner_id}"))
            bot.send_message(partner_id, "🔔 Your partner left the chat. Would you like to find someone new?", reply_markup=main_keyboard(partner_id))
            bot.send_message(partner_id, "If needed, report your partner:", reply_markup=kb)
            kb2 = types.InlineKeyboardMarkup()
            kb2.add(types.InlineKeyboardButton("🚩 Report", callback_data=f"report_req:{partner_id}"))
            bot.send_message(user_id, "You left the chat. If you had issues, report your partner:", reply_markup=kb2)
        except:
            pass
        try:
            games.pop(user_id, None)
            games.pop(partner_id, None)
        except:
            pass
        remove_from_queues(user_id)
        remove_from_queues(partner_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("report_req:"))
def callback_report_request(call):
    try:
        reporter = call.from_user.id
        _, reported_id_str = call.data.split(":",1)
        try:
            reported_id = int(reported_id_str)
        except:
            reported_id = resolve_user_identifier(reported_id_str)
        if not reported_id:
            bot.answer_callback_query(call.id, "Invalid reported user", show_alert=True)
            return
        report_reason_pending[reporter] = reported_id
        bot.answer_callback_query(call.id, "Please type the reason for reporting this partner.", show_alert=True)
        bot.send_message(reporter, "Why are you reporting this partner? Please type a short reason (required).")
    except Exception as e:
        logger.error(f"callback_report_request error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker', 'audio', 'voice'])
def handle_media(m):
    uid = m.from_user.id
    append_chat_history(uid, m.chat.id, m.message_id)
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not connected")
        return
    partner_id = active_pairs[uid]
    media_type = m.content_type
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
    else:
        return
    u = db_get_user(uid)
    if u and u["media_approved"]:
        try:
            if media_type == "photo":
                bot.send_photo(partner_id, media_id)
            elif media_type == "document":
                bot.send_document(partner_id, media_id)
            elif media_type == "video":
                bot.send_video(partner_id, media_id)
            elif media_type == "animation":
                bot.send_animation(partner_id, media_id)
            elif media_type == "sticker":
                bot.send_sticker(partner_id, media_id)
            elif media_type == "audio":
                bot.send_audio(partner_id, media_id)
            elif media_type == "voice":
                bot.send_voice(partner_id, media_id)
            db_increment_media(uid, "approved")
        except Exception as e:
            logger.error(f"Error forwarding media: {e}")
            bot.send_message(uid, "❌ Could not forward media")
        return

    # NEW: Prevent duplicate pending consent requests from same sender -> same partner
    for t, meta in list(pending_media.items()):
        try:
            if meta.get("sender") == uid and meta.get("partner") == partner_id:
                bot.send_message(uid, "📤 Consent already pending with your partner. Please wait for their response.")
                return
        except Exception:
            continue

    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    pending_media[token] = {"sender": uid, "partner": partner_id, "media_type": media_type, "file_id": media_id, "msg_chat_id": m.chat.id, "msg_id": m.message_id, "timestamp": datetime.utcnow().isoformat()}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"), types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}"))
    try:
        msg = bot.send_message(partner_id, f"Your partner wants to send {media_type}. Accept?", reply_markup=markup)
        pending_media[token]["consent_msg_id"] = msg.message_id
        bot.send_message(uid, "📤 Consent request sent. Waiting...")
    except Exception as e:
        logger.error(f"Error requesting consent: {e}")
        bot.send_message(uid, "❌ Could not request consent")
        pending_media.pop(token, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media_cb(call):
    try:
        token = call.data.split(":",1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Media no longer available", show_alert=True)
            return
        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]
        file_id = meta["file_id"]
        consent_msg_id = meta.get("consent_msg_id")
        try:
            if media_type == "photo":
                bot.send_photo(partner_id, file_id)
            elif media_type == "document":
                bot.send_document(partner_id, file_id)
            elif media_type == "video":
                bot.send_video(partner_id, file_id)
            elif media_type == "animation":
                bot.send_animation(partner_id, file_id)
            elif media_type == "sticker":
                bot.send_sticker(partner_id, file_id)
            elif media_type == "audio":
                bot.send_audio(partner_id, file_id)
            elif media_type == "voice":
                bot.send_voice(partner_id, file_id)
        except Exception as e:
            logger.error(f"Error delivering media: {e}")
            try:
                bot.send_message(partner_id, "❌ Could not deliver media")
                bot.send_message(sender_id, "❌ Media could not be delivered")
            except:
                pass
            pending_media.pop(token, None)
            bot.answer_callback_query(call.id, "Error", show_alert=True)
            return
        db_increment_media(sender_id, "approved")
        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED!")
        except:
            pass
        try:
            if consent_msg_id:
                bot.delete_message(partner_id, consent_msg_id)
        except Exception:
            try:
                if consent_msg_id:
                    bot.edit_message_reply_markup(partner_id, consent_msg_id, reply_markup=None)
            except:
                pass
        bot.answer_callback_query(call.id, "✅ Approved", show_alert=False)
        pending_media.pop(token, None)
    except Exception as e:
        logger.error(f"approve_media_cb error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":",1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Media no longer available", show_alert=True)
            return
        sender_id = meta["sender"]
        msg_id = meta.get("consent_msg_id")
        try:
            bot.send_message(sender_id, f"❌ Your {meta['media_type']} was REJECTED.")
            db_increment_media(sender_id, "rejected")
        except:
            pass
        try:
            if msg_id:
                bot.delete_message(call.message.chat.id, msg_id)
        except Exception:
            try:
                if msg_id:
                    bot.edit_message_reply_markup(call.message.chat.id, msg_id, reply_markup=None)
            except:
                pass
        bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)
        pending_media.pop(token, None)
    except Exception as e:
        logger.error(f"reject_media_cb error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handler_text(m):
    uid = m.from_user.id
    text = (m.text or "").strip()

    # If user was asked to type a custom report reason
    if uid in report_reason_pending:
        reported = report_reason_pending.pop(uid, None)
        reason = text
        if reported:
            db_add_report(uid, reported, "Other", reason)
            forward_full_chat_to_admin(uid, reported, f"Other: {reason}")
            db_ban_user(reported, hours=TEMP_BAN_HOURS, reason=reason)
            bot.send_message(uid, "✅ Report submitted!\\n\\n👮 Admins reviewing...\\n⏱️ User temp-banned 24hrs.\\n💬 Keep chatting! ✅")
        else:
            bot.send_message(uid, "❌ No partner found to report.")
        return

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    if not u["gender"]:
        bot.send_message(uid, "❌ Set gender first! Use /start")
        return

    # If bot is expecting age (user typed age directly), handle it
    if not u["age"]:
        try:
            age = int(text)
            if age < 12 or age > 99:
                bot.send_message(uid, "❌ Age must be 12-99")
                return
            db_set_age(uid, age)
            # Immediately prompt for country and register next step
            bot.send_message(uid, f"✅ Age: {age}\\n\\n🌍 Enter country:\\n⚠️ Cannot change unless Premium!")
            pending_country.add(uid)
            try:
                bot.register_next_step_handler(m, process_new_country)
            except Exception:
                pass
            return
        except:
            bot.send_message(uid, "❌ Enter age as number (e.g., 21)")
            return

    # Only accept country input if bot asked for it (pending_country)
    if uid in pending_country and not u.get("country"):
        # Let process_new_country handle it via register_next_step or direct call
        try:
            process_new_country(m)
        except:
            bot.send_message(uid, "❌ Invalid country input. Try again.")
        return

    if uid in games:
        handled = process_game_message(m)
        if handled:
            return

    if text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free"
            gender_emoji = "👨" if u["gender"] == "Male" else ("👩" if u["gender"] == "Female" else "")
            stats_msg = (
                "📊 YOUR STATS\\n\\n"
                f"Gender: {gender_emoji} {u['gender']}\\n"
                f"Age: {u['age']}\\n"
                f"Country: {u['country_flag']} {u['country']}\\n\\n"
                f"📨 Messages: {u['messages_sent']}\\n"
                f"✅ Media Approved: {u['media_approved']}\\n"
                f"❌ Media Rejected: {u['media_rejected']}\\n\\n"
                f"People Referred: {u['referral_count']}\\n"
                f"{premium_status}"
            )
            bot.send_message(uid, stats_msg, reply_markup=chat_keyboard())
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

    if text == "🎯 Search Opposite Gender":
        cmd_search_opposite(m)
        return

    if text == "Opposite Gender (Premium)":
        bot.send_message(uid, "💎 Premium required! Refer friends to unlock.")
        return

    if text == "⚙️ Settings":
        cmd_settings(m)
        return

    if text == "👥 Refer":
        cmd_refer(m)
        return

    if is_banned_content(text):
        warn_user(uid, "Vulgar words or links")
        return

    if uid in active_pairs:
        partner_id = active_pairs[uid]
        append_chat_history(uid, m.chat.id, m.message_id)
        append_chat_history(partner_id, m.chat.id, m.message_id)
        try:
            bot.send_message(partner_id, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error forwarding chat text: {e}")
            bot.send_message(uid, "❌ Could not send message")
    else:
        bot.send_message(uid, "❌ Not connected. Use search.", reply_markup=main_keyboard(uid))

# ============= BOT POLLING (DAEMON THREAD) & FLASK STARTUP (MAIN) =============
def run_bot_polling():
    logger.info("🤖 Bot polling started in background thread...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")

def run_flask():
    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"🌍 Starting Flask on 0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    init_db()
    set_bot_commands()
    logger.info("✅ GhostTalk v3.4 PRODUCTION - ALL FIXES APPLIED")
    logger.info("🔧 Starting bot polling in background thread...")

    # Start bot polling as daemon thread
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()

    # Start Flask as main thread (keeps Render alive for UptimeRobot)
    run_flask()
