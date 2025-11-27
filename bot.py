#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FINAL MERGED v2.3 - FIXED
Applied fixes requested by Satyam:
 - Game: chat & game concurrently, clear turn messages, invite message deletion, /endgame, stuck-game cleanup
 - Report: redesigned inline options, sends chat history + reporter/partner info to admin, 'Other' allows manual reason
 - /ban and /prrem improved username resolution
 - Gender/Age: prevent double prints and duplicate age overwrite; settings change requires explicit action
 - Disconnect wording changed
 - Remove stale states on disconnect
 - Preserve media consent and country/flag logic
 - Chat logging (in-memory) for sending logs to admin on report
"""

import sqlite3
import random
import logging
import re
from datetime import datetime, timedelta
import time
import secrets
import threading
import os

import telebot
from telebot import types
from flask import Flask

# -------- CONFIG --------
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("🚨 BOT_TOKEN not found!")

BOT_USERNAME = "SayNymBot"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8361006824"))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk_final.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# -------- BANNED WORDS --------
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography", "rape", "molest", "anj", "anjing", "babi", "asu",
    "kontl","kontol","puki","memek","jembut", "mc", "randi", "randika","maderchod","bsdk","lauda","lund","chut","choot",
    "chot","chuut","gand","gaand","ma ka lauda", "mkc", "teri ma ki chut","teri ma ki chuut"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- FULL COUNTRIES --------
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
    normalized = user_input.strip().lower()
    if normalized in COUNTRY_ALIASES:
        normalized = COUNTRY_ALIASES[normalized]
    if normalized in COUNTRIES:
        return normalized.title(), COUNTRIES[normalized]
    return None

# -------- LOGGING --------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------- FLASK/BOT --------
app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN)

@app.route("/")
def home():
    return "🤖 GhostTalk Bot Running!", 200

@app.route("/health")
def health():
    return {"status": "✅ ok", "timestamp": datetime.utcnow().isoformat()}, 200

# -------- RUNTIME DATA --------
waiting_random = []
waiting_opposite = []           # list of tuples (uid, gender)
active_pairs = {}               # uid -> partner_uid
user_warnings = {}
pending_media = {}
chat_history = {}               # last partner mapping (uid -> partner_uid)
age_update_pending = {}         # uid -> True (if changing via settings)
# Game Data
pending_game_invites = {}       # invited_user_id -> {'initiator': id, 'game': 'guess'/'word', 'msg_id': int}
games = {}                      # uid -> shared game state dict
# Reports
report_reason_pending = {}      # reporter_id -> ('other', reported_id) when expecting manual text
# Chat logs (in-memory): key: frozenset({a,b}) -> list of (timestamp_iso, sender_id, text_or_media_desc)
chat_logs = {}

# -------- DATABASE (unchanged) --------
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT, first_name TEXT, gender TEXT, age INTEGER,
            country TEXT, country_flag TEXT,
            messages_sent INTEGER DEFAULT 0,
            media_approved INTEGER DEFAULT 0, media_rejected INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE, referral_count INTEGER DEFAULT 0,
            premium_until TEXT, joined_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            ban_until TEXT, permanent INTEGER DEFAULT 0, reason TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER, reported_id INTEGER,
            report_type TEXT, reason TEXT, timestamp TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id INTEGER,
            about_id INTEGER,
            feedback_type TEXT,
            timestamp TEXT
        )""")
        conn.commit()

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("""SELECT user_id, username, first_name, gender, age, country, country_flag,
            messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until
            FROM users WHERE user_id=?""", (user_id,)).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1], "first_name": row[2], "gender": row[3], "age": row[4],
            "country": row[5], "country_flag": row[6], "messages_sent": row[7],
            "media_approved": row[8], "media_rejected": row[9],
            "referral_code": row[10], "referral_count": row[11], "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute("""INSERT INTO users (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code)
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
    """Admin: Set premium (YYYY-MM-DD)"""
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute("UPDATE users SET premium_until=? WHERE user_id=?", (dt, user_id))
            conn.commit()
        return True
    except:
        return False

def db_remove_premium(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until=NULL WHERE user_id=?", (user_id,))
        conn.commit()

def db_get_referral_link(user_id):
    user = db_get_user(user_id)
    if user:
        return f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
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
                bot.send_message(user_id, f"🎉 PREMIUM UNLOCKED!\n✨ {PREMIUM_DURATION_HOURS} hour premium earned!\n🎯 Opposite gender search unlocked!")
            except:
                pass

def db_is_banned(user_id):
    if user_id == OWNER_ID:
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
            VALUES (?, ?, ?, ?, ?)""",
            (reporter_id, reported_id, report_type, reason, datetime.utcnow().isoformat()))
        conn.commit()

def db_get_reporters_for(reported_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT reporter_id FROM reports WHERE reported_id=?", (reported_id,)).fetchall()
        return [r[0] for r in rows]

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_add_feedback(from_id, about_id, feedback_type):
    with get_conn() as conn:
        conn.execute("""INSERT INTO feedbacks (from_id, about_id, feedback_type, timestamp)
            VALUES (?, ?, ?, ?)""", (from_id, about_id, feedback_type, datetime.utcnow().isoformat()))
        conn.commit()

# -------- HELPERS --------
def resolve_user_identifier(identifier):
    """
    Accepts:
      - numeric string -> returns int
      - username with or without @ -> tries DB lookup by username, first_name, then bot.get_chat(@username)
    Returns user_id (int) or None if not found.
    """
    if not identifier:
        return None
    identifier = identifier.strip()
    # try numeric id
    try:
        uid = int(identifier)
        return uid
    except:
        pass

    # username (strip @)
    uname = identifier.lstrip("@").strip()
    if not uname:
        return None

    # 1) try DB lookup (case-insensitive exact)
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(username)=?", (uname.lower(),)).fetchone()
            if row:
                return row[0]
            # fallback: match first_name (less reliable)
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(first_name)=?", (uname.lower(),)).fetchone()
            if row:
                return row[0]
            # broader search: username LIKE
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(username) LIKE ? LIMIT 1", (f"%{uname.lower()}%",)).fetchone()
            if row:
                return row[0]
    except Exception as e:
        logger.debug(f"DB lookup error in resolve_user_identifier: {e}")

    # 2) try Telegram API (public username)
    try:
        chat = bot.get_chat(f"@{uname}")
        if chat and hasattr(chat, "id"):
            return chat.id
    except Exception as e:
        logger.debug(f"bot.get_chat failed for @{uname}: {e}")

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
            bot.send_message(user_id, f"🚫 BANNED for {TEMP_BAN_HOURS} hours!\n❌ Reason: {reason}")
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ WARNING {count}/{WARNING_LIMIT}\n❌ {reason}\n📍 {WARNING_LIMIT - count} more = BAN!")
        except:
            pass
        return "warn"

# -------- QUEUE HELPERS --------
def remove_from_queues(user_id):
    global waiting_random, waiting_opposite
    if user_id in waiting_random:
        waiting_random.remove(user_id)
    waiting_opposite = [(uid, gen) for uid, gen in waiting_opposite if uid != user_id]

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
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚫 Harassment", callback_data="rep:harass"),
        types.InlineKeyboardButton("📧 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("🔞 Sexual content / Porn", callback_data="rep:porn"),
        types.InlineKeyboardButton("💰 Scam / Fraud", callback_data="rep:scam"),
        types.InlineKeyboardButton("❓ Other (manual reason)", callback_data="rep:other")
    )
    return markup

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "👨" if partner_user["gender"] == "Male" else "👩"
    age_text = str(partner_user["age"]) if partner_user["age"] else "Unknown"
    country_flag = partner_user["country_flag"] or "🌍"
    country_name = partner_user["country"] or "Global"
    msg = (
        "🎉 Partner Found! 🎉\n\n"
        f"🎂 Age: {age_text}\n"
        f"👤 Gender: {gender_emoji} {partner_user['gender']}\n"
        f"🌍 Country: {country_flag} {country_name}\n"
    )
    if viewer_id == ADMIN_ID:
        partner_name = partner_user["first_name"] or partner_user["username"] or "Unknown"
        msg += f"\n👤 Name: {partner_name}\n🆔 ID: {partner_user['user_id']}\n"
    msg += "\n💬 Enjoy chat! Type /next for new partner."
    return msg

def match_users():
    """MASTERCLASS: Opposite gender from random queue, Random pair in order"""
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
            logger.info(f"✅ Opposite: {uid} ({searcher_gender}) <-> {found_uid}")
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
        logger.info(f"✅ Random: {u1} <-> {u2}")

# -------- CHAT LOGGING HELPER --------
def log_chat_message(sender_id, recipient_id, text):
    key = frozenset({sender_id, recipient_id})
    if not key:
        return
    logs = chat_logs.get(key)
    if logs is None:
        logs = []
        chat_logs[key] = logs
    logs.append((datetime.utcnow().isoformat(), sender_id, text))

def get_chat_logs_between(a, b, limit=500):
    key = frozenset({a, b})
    return chat_logs.get(key, [])

# -------- COMMANDS & HANDLERS --------
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
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
            types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "👋 Welcome to GhostTalk!\n\n🎯 Select your gender:", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "📍 Enter your age (12-99 only):")
    elif not u["country"]:
        bot.send_message(user.id, "🌍 Enter your country name:\n\n⚠️ Country CANNOT be changed later unless PREMIUM!")
    else:
        premium_status = "✅ Premium Active" if db_is_premium(user.id) else "🆓 Free User"
        welcome_msg = (
            f"👋 Welcome back!\n\n"
            f"👤 Gender: {u['gender']}\n"
            f"🎂 Age: {u['age']}\n"
            f"🌍 Country: {u['country_flag']} {u['country']}\n"
            f"{premium_status}\n\n"
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
    gender_emoji = "👨" if gender == "male" else "👩"

    u = db_get_user(uid)
    if u and u["gender"] == gender_display:
        # Gender double-select prevention: anti-spam reply
        bot.answer_callback_query(call.id, f"Already {gender_display}!", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "✅ Gender set!", show_alert=True)

    # Edit the inline message or send a single confirmation (avoid double printing)
    try:
        bot.edit_message_text(f"✅ Gender: {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        try:
            bot.send_message(uid, f"✅ Gender: {gender_emoji} {gender_display}")
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
    gender_emoji = "👨" if u["gender"] == "Male" else "👩"

    settings_text = (
        "⚙️ SETTINGS & PROFILE\n\n"
        f"👤 Gender: {gender_emoji} {u['gender'] or 'Not set'}\n"
        f"🎂 Age: {u['age'] or 'Not set'}\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\n\n"
        f"📊 Messages Sent: {u['messages_sent']}\n"
        f"✅ Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n\n"
        f"👥 People Referred: {u['referral_count']}/3\n"
        f"{premium_status}\n\n"
        "🔗 Change Profile:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    # Use row to keep UI similar; avoid duplicate gender set
    markup.row(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"), types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
    markup.row(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))

    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def callback_change_age(call):
    uid = call.from_user.id
    # Set a pending flag so process_new_age knows this came from settings change
    age_update_pending[uid] = True
    bot.send_message(uid, "🎂 Enter new age (12-99):")
    bot.register_next_step_handler(call.message, process_new_age)

def process_new_age(message):
    uid = message.from_user.id
    pending = age_update_pending.pop(uid, False)
    try:
        age = int(message.text.strip())
        if age < 12 or age > 99:
            bot.send_message(uid, "❌ Age must be 12-99. Try again:")
            bot.register_next_step_handler(message, process_new_age)
            return
        u = db_get_user(uid)
        if u and u.get("age") and not pending:
            # User already has an age and did not explicitly request change
            bot.send_message(uid, "❌ Your age is already set. Use Settings -> Change Age to update it.")
            return
        # If pending True (user clicked change), we allow overwrite
        db_set_age(uid, age)
        bot.send_message(uid, f"✅ Age updated to {age}!", reply_markup=main_keyboard(uid))
    except:
        bot.send_message(uid, "❌ Enter age as number (e.g., 21):")
        bot.register_next_step_handler(message, process_new_age)

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
            "👥 REFERRAL SYSTEM\n\n"
            f"🔗 Your Referral Link:\n{ref_link}\n\n"
            f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
            f"🎁 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n"
            "✨ Unlock opposite gender search!\n\n"
        )

        if remaining > 0:
            refer_text += f"📍 Invite {remaining} more friends to unlock premium!"
        else:
            refer_text += "✅ Premium unlocked! Keep inviting for more!"

        refer_text += (
            "\n\n📋 How it works:\n"
            "1️⃣ Share your link with friends\n"
            "2️⃣ They join with your link\n"
            f"3️⃣ Get premium after {PREMIUM_REFERRALS_NEEDED} referrals!"
        )

        bot.send_message(uid, refer_text)
        bot.answer_callback_query(call.id, "✅")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def callback_set_country(call):
    uid = call.from_user.id

    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, "💎 Country change requires PREMIUM!\n✨ Refer friends to unlock.", show_alert=True)
        return

    bot.send_message(uid, "🌍 Enter your new country name:")
    bot.register_next_step_handler(call.message, process_new_country)

def process_new_country(message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.send_message(uid, "💎 Country change requires PREMIUM!\n✨ Refer friends to unlock.")
        return

    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"❌ '{text}' not valid.\n\n🔍 Try again (e.g., India, USA, UK):")
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)

    success_msg = (
        f"✅ Country updated!\n\n"
        f"🌍 Country: {country_flag} {country_name}\n"
        "🎯 Your search matches this country now."
    )
    bot.send_message(uid, success_msg, reply_markup=main_keyboard(uid))

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
        "👥 REFERRAL SYSTEM\n\n"
        f"🔗 Your Referral Link:\n{ref_link}\n\n"
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"🎁 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n"
        "✨ Unlock opposite gender search!\n\n"
    )

    if remaining > 0:
        refer_text += f"📍 Invite {remaining} more friends to unlock premium!"
    else:
        refer_text += "✅ Premium unlocked! Keep inviting for more!"

    refer_text += (
        "\n\n📋 How it works:\n"
        "1️⃣ Share your link with friends\n"
        "2️⃣ They join with your link\n"
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

    # Search spam block: if already searching, show anti-spam message
    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "⏳ You're already in the queue. We'll notify you when we find a partner.  Cancel anytime: /stop")
        return

    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for random partner...\n⏳ Please wait...")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if not db_is_premium(uid):
        premium_required_msg = (
            "💎 PREMIUM REQUIRED!\n\n"
            f"✨ Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock {PREMIUM_DURATION_HOURS} hour premium.\n"
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

    # Search spam block for opposite queue
    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "⏳ You're already in the queue. We'll notify you when we find a partner.  Cancel anytime: /stop")
        return

    remove_from_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "🎯 Searching for opposite gender partner...\n⏳ Please wait...")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    # Changed wording per request
    bot.send_message(uid, "🛑 Search and chat stopped. Use the main menu to start again.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not in chat. Use search commands.")
        return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Looking for new partner...", reply_markup=main_keyboard(uid))
    # Call search_random functionality
    fake_msg = types.Message.de_json(message.json, bot)  # reuse message object
    cmd_search_random(fake_msg)

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    if uid not in active_pairs and uid not in chat_history:
        bot.send_message(uid, "❌ No active partner to report.")
        return
    # Show category-based quick report as required
    bot.send_message(uid, "⚠️ Select a reason to report your partner:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id
    partner_id = active_pairs.get(uid) or chat_history.get(uid)

    if not partner_id:
        bot.answer_callback_query(call.id, "No partner to report", show_alert=True)
        return

    _, report_key = call.data.split(":", 1)
    report_map = {
        "harass": ("Harassment", "Harassment"),
        "spam": ("Spam", "Spam"),
        "porn": ("Sexual content / Porn", "Sexual Content"),
        "scam": ("Scam/Fraud", "Scam"),
        "other": ("Other", "Other")
    }
    report_type_name = report_map.get(report_key, ("Other", "Other"))[0]

    if report_key == "other":
        # ask for manual reason
        report_reason_pending[uid] = ('other', partner_id)
        try:
            bot.answer_callback_query(call.id, "Please type the reason for reporting (short).", show_alert=True)
        except:
            pass
        bot.send_message(uid, "Please describe why you are reporting this partner (short reason):")
        return

    # Direct report (no free-text)
    reason_text = report_map.get(report_key, ("Other","Other"))[1]
    db_add_report(uid, partner_id, report_type_name, reason_text)

    # Send full chat history and reporter/partner info to admin
    try:
        # gather reporter and partner info
        reporter_user = db_get_user(uid) or {"username": None, "first_name": None}
        partner_user = db_get_user(partner_id) or {"username": None, "first_name": None}
        reporter_display = reporter_user.get("username") or reporter_user.get("first_name") or str(uid)
        partner_display = partner_user.get("username") or partner_user.get("first_name") or str(partner_id)

        admin_msg = (
            f"🚩 USER REPORT\n\n"
            f"Type: {report_type_name}\n"
            f"Reporter: {reporter_display} (ID: {uid})\n"
            f"Reported: {partner_display} (ID: {partner_id})\n"
            f"Time: {datetime.utcnow().isoformat()}\n\n"
            f"--- Chat History Below ---\n"
        )
        bot.send_message(ADMIN_ID, admin_msg)
        logs = get_chat_logs_between(uid, partner_id)
        if not logs:
            bot.send_message(ADMIN_ID, "(No chat log available)")
        else:
            # send logs in chunks if long
            chunk = []
            for ts, s, txt in logs:
                sender_name = s if s != uid and s != partner_id else (str(s))
                chunk.append(f"[{ts}] {s}: {txt}")
                if len(chunk) >= 20:
                    bot.send_message(ADMIN_ID, "\n".join(chunk))
                    chunk = []
            if chunk:
                bot.send_message(ADMIN_ID, "\n".join(chunk))
    except Exception as e:
        logger.error(f"Error sending report to admin: {e}")

    try:
        bot.answer_callback_query(call.id, "✅ Report submitted", show_alert=True)
    except:
        pass
    bot.send_message(uid, "✅ Your report has been submitted. Admins will review it.")
    return

@bot.message_handler(commands=['pradd'])
def cmd_pradd(message):
    """Admin: /pradd [user_id|username] [YYYY-MM-DD]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd [user_id|username] [YYYY-MM-DD]\nExample: /pradd 12345 2025-12-31 OR /pradd @username 2025-12-31")
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
            premium_msg = f"🎉 PREMIUM ADDED!\n✅ Valid until {until_date}\n🎯 Opposite gender search unlocked!"
            bot.send_message(target_id, premium_msg, reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['prrem'])
def cmd_prrem(message):
    """Admin: /prrem [user_id|username]"""
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
    """Admin: /ban [user_id|username] [hours/permanent] [reason]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban [user_id|username] [hours/permanent] [reason]")
        return

    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID or @username.")
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
            bot.send_message(target_id, f"🚫 PERMANENTLY BANNED.\nReason: {reason}")
        except:
            pass
    else:
        bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) banned for {hours} hours. {reason}")
        try:
            bot.send_message(target_id, f"🚫 Banned for {hours} hours.\nReason: {reason}")
        except:
            pass

    # Notify reporters that action has been taken (if any)
    try:
        reporters = db_get_reporters_for(target_id)
        for r in reporters:
            try:
                bot.send_message(r, "Your report has been reviewed. Action has been taken.")
            except:
                pass
    except Exception as e:
        logger.error(f"Error notifying reporters after ban: {e}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    """Admin: /unban [user_id|username]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban [user_id|username]")
        return

    identifier = parts[1]
    target_id = resolve_user_identifier(identifier)
    if not target_id:
        bot.reply_to(message, f"❌ Could not find user '{identifier}'. Use numeric ID or @username.")
        return

    db_unban_user(target_id)
    user_warnings[target_id] = 0

    bot.reply_to(message, f"✅ User {identifier} (id:{target_id}) unbanned")
    try:
        bot.send_message(target_id, "✅ Your ban has been lifted!", reply_markup=main_keyboard(target_id))
    except:
        pass

# -------- MEDIA HANDLERS (unchanged behavior preserved) --------
@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker'])
def handle_media(m):
    uid = m.from_user.id

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
        media_desc = "<photo>"
    elif media_type == "document":
        media_id = m.document.file_id
        media_desc = "<document>"
    elif media_type == "video":
        media_id = m.video.file_id
        media_desc = "<video>"
    elif media_type == "animation":
        media_id = m.animation.file_id
        media_desc = "<animation>"
    elif media_type == "sticker":
        media_id = m.sticker.file_id
        media_desc = "<sticker>"
    else:
        return

    # Log the media in chat logs
    log_chat_message(uid, partner_id, f"[media] {media_desc}")

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
            db_increment_media(uid, "approved")
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "❌ Could not forward media")
        return

    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    pending_media[token] = {
        "sender": uid, "partner": partner_id, "media_type": media_type,
        "file_id": media_id, "msg_id": None, "timestamp": datetime.utcnow().isoformat()
    }

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}")
    )

    try:
        msg = bot.send_message(partner_id, f"Your partner sent {media_type}. Accept?", reply_markup=markup)
        pending_media[token]["msg_id"] = msg.message_id
        bot.send_message(uid, "📤 Consent request sent. Waiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.send_message(uid, "❌ Could not request consent")
        if token in pending_media:
            del pending_media[token]

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Media no longer available", show_alert=True)
            return

        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]
        file_id = meta["file_id"]
        msg_id = meta.get("msg_id")

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
        except Exception as e:
            logger.error(f"Error: {e}")
            try:
                bot.send_message(partner_id, "❌ Could not deliver media")
                bot.send_message(sender_id, "❌ Media could not be delivered")
            except:
                pass
            if token in pending_media:
                del pending_media[token]
            bot.answer_callback_query(call.id, "Error", show_alert=True)
            return

        db_increment_media(sender_id, "approved")
        log_chat_message(sender_id, partner_id, f"[media delivered] {media_type}")

        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED!")
        except:
            pass

        # Delete consent message completely (preferred). Fallback: remove buttons.
        try:
            if msg_id:
                bot.delete_message(partner_id, msg_id)
        except Exception:
            try:
                if msg_id:
                    bot.edit_message_reply_markup(partner_id, msg_id, reply_markup=None)
            except:
                pass

        bot.answer_callback_query(call.id, "✅ Approved", show_alert=False)
        if token in pending_media:
            del pending_media[token]
    except Exception as e:
        logger.error(f"Error in approve: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Media no longer available", show_alert=True)
            return

        sender_id = meta["sender"]
        media_type = meta["media_type"]
        msg_id = meta.get("msg_id")
        partner_id = meta.get("partner")

        try:
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED.")
            db_increment_media(sender_id, "rejected")
            log_chat_message(sender_id, partner_id, f"[media rejected] {media_type}")
        except:
            pass

        # Delete consent message completely (preferred). Fallback: remove buttons.
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
        if token in pending_media:
            del pending_media[token]
    except Exception as e:
        logger.error(f"Error in reject: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# -------- REPORT (new required flow) - manual 'Other' reason handler --------
@bot.message_handler(func=lambda m: m.from_user.id in report_reason_pending and m.content_type == "text")
def handle_manual_report_reason(m):
    uid = m.from_user.id
    pending = report_reason_pending.pop(uid, None)
    if not pending:
        bot.send_message(uid, "No report pending.")
        return
    tag, reported = pending
    if tag != 'other':
        bot.send_message(uid, "No manual reason expected.")
        return
    reason = m.text.strip()
    if not reason:
        bot.send_message(uid, "Please type a short reason for reporting:")
        report_reason_pending[uid] = ('other', reported)
        return

    db_add_report(uid, reported, "Other", reason)
    # forward logs and info to admin
    try:
        reporter_user = db_get_user(uid) or {"username": None, "first_name": None}
        partner_user = db_get_user(reported) or {"username": None, "first_name": None}
        reporter_display = reporter_user.get("username") or reporter_user.get("first_name") or str(uid)
        partner_display = partner_user.get("username") or partner_user.get("first_name") or str(reported)

        admin_msg = (
            f"🚩 USER REPORT (Manual)\n\n"
            f"Reporter: {reporter_display} (ID: {uid})\n"
            f"Reported: {partner_display} (ID: {reported})\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.utcnow().isoformat()}\n\n"
            f"--- Chat History Below ---\n"
        )
        bot.send_message(ADMIN_ID, admin_msg)
        logs = get_chat_logs_between(uid, reported)
        if not logs:
            bot.send_message(ADMIN_ID, "(No chat log available)")
        else:
            chunk = []
            for ts, s, txt in logs:
                chunk.append(f"[{ts}] {s}: {txt}")
                if len(chunk) >= 20:
                    bot.send_message(ADMIN_ID, "\n".join(chunk))
                    chunk = []
            if chunk:
                bot.send_message(ADMIN_ID, "\n".join(chunk))
    except Exception as e:
        logger.error(f"Error sending manual report to admin: {e}")

    bot.send_message(uid, "✅ Your report has been submitted. Admins will review it.")
    return

# -------- GAME SYSTEM (initiator chooses -> partner accept/reject -> start) --------
@bot.message_handler(commands=['game'])
def cmd_game(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ You must be in a chat to start a game.")
        return
    partner_id = active_pairs[uid]
    # Initiator chooses game
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎯 Guess the Number (1-10)", callback_data=f"game_choice:guess:{partner_id}"),
        types.InlineKeyboardButton("🔗 Word Chain", callback_data=f"game_choice:word:{partner_id}")
    )
    bot.send_message(uid, "Choose a game to propose to your partner:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_choice:"))
def callback_game_choice(call):
    uid = call.from_user.id
    try:
        _, game_type, partner_id_str = call.data.split(":", 2)
        partner_id = int(partner_id_str)
    except:
        bot.answer_callback_query(call.id, "Invalid selection", show_alert=True)
        return

    # verify they are still partners
    if active_pairs.get(uid) != partner_id:
        bot.answer_callback_query(call.id, "Partner not connected or changed.", show_alert=True)
        return

    # create pending invite and send to partner: Do you accept?
    # store msg id to delete after response
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"game_invite_resp:accept:{uid}:{game_type}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"game_invite_resp:reject:{uid}:{game_type}")
    )
    desc = "Guess the Number" if game_type == "guess" else "Word Chain"
    try:
        sent = bot.send_message(partner_id, f"🎮 Your partner wants to play *{desc}*. Do you accept?", reply_markup=markup, parse_mode='Markdown')
        pending_game_invites[partner_id] = {'initiator': uid, 'game': game_type, 'msg_id': sent.message_id}
        bot.send_message(uid, "Invitation sent. Waiting for partner's response...")
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error sending game invite: {e}")
        bot.answer_callback_query(call.id, "Error sending invite", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("game_invite_resp:"))
def callback_game_invite_resp(call):
    responder = call.from_user.id
    try:
        _, resp, initiator_str, game_type = call.data.split(":", 3)
        initiator_id = int(initiator_str)
    except:
        bot.answer_callback_query(call.id, "Invalid response", show_alert=True)
        return

    invite = pending_game_invites.pop(responder, None)
    # attempt to delete the invite message in partner's chat (clean UI)
    try:
        if invite and invite.get('msg_id'):
            try:
                bot.delete_message(responder, invite.get('msg_id'))
            except:
                try:
                    bot.edit_message_reply_markup(responder, invite.get('msg_id'), reply_markup=None)
                except:
                    pass
    except Exception:
        pass

    if not invite or invite.get('initiator') != initiator_id or invite.get('game') != game_type:
        bot.answer_callback_query(call.id, "No matching invitation.", show_alert=True)
        return

    if resp == "reject":
        try:
            bot.send_message(initiator_id, "❌ Your partner declined the game invitation.")
            bot.send_message(responder, "❌ You declined the game invitation.")
        except:
            pass
        bot.answer_callback_query(call.id)
        return

    # ACCEPT -> start game
    if game_type == 'guess':
        secret = random.randint(1, 10)  # per user's request: 1-10
        # store shared game state object for both users
        state = {
            'type': 'guess',
            'secret': secret,
            'guesser': responder,    # partner guesses
            'initiator': initiator_id
        }
        games[initiator_id] = state
        games[responder] = state
        try:
            bot.send_message(initiator_id, "🎮 Game started: Guess the Number (1-10).\nYour partner will try to guess the secret number.\n➡️ You may still chat freely while the game runs.")
            bot.send_message(responder, "🎮 Game started: Guess the Number (1-10).\nTry to guess the number (send a number 1-10).\n➡️ You may still chat freely while the game runs.")
        except:
            pass
        bot.answer_callback_query(call.id)
        return
    else:
        # Word chain: initiator starts
        state = {
            'type': 'word',
            'turn': initiator_id,
            'other': responder,
            'last_letter': None
        }
        games[initiator_id] = state
        games[responder] = state
        try:
            bot.send_message(initiator_id, "🎮 Game started: Word Chain.\nYou start. Send the first word.\n➡️ You may still chat freely while the game runs.")
            bot.send_message(responder, "🎮 Game started: Word Chain.\nWait for partner to send the first word.\n➡️ You may still chat freely while the game runs.")
        except:
            pass
        bot.answer_callback_query(call.id)
        return

# Game message handler - intercepts messages if user is in a game
# Important: it will process game-related inputs but WILL NOT block normal chat forwarding.
def process_game_message(message):
    uid = message.from_user.id
    state = games.get(uid)
    if not state:
        return {"handled": False}

    # For both games, we will process game-specific inputs but won't block chat messages.
    # For guess: only digit messages 1-10 from the guesser are treated as guesses.
    if state['type'] == 'guess':
        # Only guesser can guess
        if uid != state['guesser']:
            # not guesser -> nothing to do for game
            return {"handled": False}
        text = (message.text or "").strip()
        if not text.isdigit():
            # Not a guess, ignore for game
            return {"handled": False}
        guess = int(text)
        if guess < 1 or guess > 10:
            try:
                bot.send_message(uid, "⚠️ Number must be between 1 and 10.")
            except:
                pass
            return {"handled": True}
        secret = state['secret']
        initiator = state['initiator']
        if guess == secret:
            try:
                bot.send_message(uid, f"🎉 You guessed it! The number was {secret}. You win!")
                bot.send_message(initiator, f"❌ Your partner guessed the number {secret}. You lose.")
            except:
                pass
            # cleanup both
            games.pop(uid, None)
            games.pop(initiator, None)
            return {"handled": True}
        elif guess < secret:
            try:
                bot.send_message(uid, "📈 Higher!")
            except:
                pass
            return {"handled": True}
        else:
            try:
                bot.send_message(uid, "📉 Lower!")
            except:
                pass
            return {"handled": True}

    elif state['type'] == 'word':
        # Turn-based: only process if it's this user's turn and message looks like a single word
        if uid != state['turn']:
            # not this user's turn -> nothing game-specific
            return {"handled": False}
        word = (message.text or "").strip().lower()
        if not word.isalpha():
            try:
                bot.send_message(uid, "⚠️ Send a single word (letters only).")
            except:
                pass
            return {"handled": True}
        last_letter = state['last_letter']
        if last_letter and word[0] != last_letter:
            loser = uid
            winner = state['other'] if state['other'] != uid else state['turn']
            try:
                bot.send_message(winner, f"🎉 You win! Your partner used a word not starting with '{last_letter}'.")
                bot.send_message(loser, f"❌ You lose — the word must start with '{last_letter}'.")
            except:
                pass
            # cleanup both
            other_id = state['other'] if state['other'] != uid else state['turn']
            games.pop(uid, None)
            games.pop(other_id, None)
            return {"handled": True}
        # valid move: update last_letter and swap turn/other
        state['last_letter'] = word[-1]
        prev_turn = state['turn']
        next_turn = state['other']
        state['turn'] = next_turn
        state['other'] = prev_turn
        try:
            bot.send_message(next_turn, f"➡️ Your turn — send a word starting with '{state['last_letter']}'.")
            bot.send_message(prev_turn, f"✅ Move accepted. Partner's turn.")
        except:
            pass
        return {"handled": True}

    return {"handled": False}

# -------- ENDGAME COMMAND --------
@bot.message_handler(commands=['endgame'])
def cmd_endgame(message):
    uid = message.from_user.id
    state = games.get(uid)
    if not state:
        bot.send_message(uid, "❌ You are not currently in any game.")
        return
    # determine partner
    partner = state.get('initiator') if state.get('initiator') != uid else state.get('guesser') if state.get('guesser') != uid else state.get('other')
    if not partner:
        # try to find in games mapping
        partner = None
        for k, v in games.items():
            if k != uid and v == state:
                partner = k
                break
    # cleanup both
    try:
        games.pop(uid, None)
        if partner:
            games.pop(partner, None)
            bot.send_message(partner, "🛑 Game ended by your partner. You may continue chatting freely.")
    except:
        pass
    bot.send_message(uid, "🛑 You ended the game. You may continue chatting freely.")

# -------- DISCONNECT / FEEDBACK CHANGES (no thumbs) --------
def disconnect_user(user_id):
    global active_pairs, pending_game_invites, games, pending_media
    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
        # store history mapping
        chat_history[user_id] = partner_id
        chat_history[partner_id] = user_id
        try:
            del active_pairs[partner_id]
        except:
            pass
        try:
            del active_pairs[user_id]
        except:
            pass

        # Notify both sides with new unique wording
        try:
            # After end, show a simple Report button (new required flow)
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🚩 Report", callback_data=f"report_req:{partner_id}"))
            bot.send_message(partner_id, "❌ Your partner left the chat.\n🔍 Want to find a new partner?", reply_markup=main_keyboard(partner_id))
            bot.send_message(partner_id, "If needed, report your partner:", reply_markup=kb)
            # For the leaver, also allow reporting their previous partner
            kb2 = types.InlineKeyboardMarkup()
            kb2.add(types.InlineKeyboardButton("🚩 Report", callback_data=f"report_req:{partner_id}"))
            bot.send_message(user_id, "You left the chat. If you had issues, report your partner:", reply_markup=kb2)
        except:
            pass

        # Cleanup any games between them
        try:
            games.pop(user_id, None)
            games.pop(partner_id, None)
        except:
            pass

        # remove any pending game invites related to them
        try:
            keys_to_remove = []
            for invited, invite in list(pending_game_invites.items()):
                if invite.get('initiator') == user_id or invited == user_id or invite.get('initiator') == partner_id or invited == partner_id:
                    keys_to_remove.append(invited)
            for k in keys_to_remove:
                try:
                    # attempt to delete message
                    msgid = pending_game_invites[k].get('msg_id')
                    if msgid:
                        try:
                            bot.delete_message(k, msgid)
                        except:
                            try:
                                bot.edit_message_reply_markup(k, msgid, reply_markup=None)
                            except:
                                pass
                except:
                    pass
                pending_game_invites.pop(k, None)
        except Exception as e:
            logger.debug(f"Error cleaning pending_game_invites: {e}")

        # remove pending media involving them
        try:
            tokens_to_remove = []
            for t, meta in list(pending_media.items()):
                if meta.get('sender') == user_id or meta.get('partner') == user_id or meta.get('sender') == partner_id or meta.get('partner') == partner_id:
                    tokens_to_remove.append(t)
            for t in tokens_to_remove:
                pending_media.pop(t, None)
        except Exception:
            pass

        # optionally remove from waiting queues
        remove_from_queues(user_id)
        remove_from_queues(partner_id)

# The report button invoked after disconnect: capture its callback
@bot.callback_query_handler(func=lambda c: c.data.startswith("report_req:"))
def callback_report_request(call):
    try:
        reporter = call.from_user.id
        _, reported_id_str = call.data.split(":", 1)
        try:
            reported_id = int(reported_id_str)
        except:
            reported_id = resolve_user_identifier(reported_id_str)

        if not reported_id:
            bot.answer_callback_query(call.id, "Invalid reported user", show_alert=True)
            return

        # show the structured report keyboard (no free typing)
        bot.answer_callback_query(call.id, "Select a reason to report.", show_alert=True)
        bot.send_message(reporter, "Select a reason to report your partner:", reply_markup=report_keyboard())
    except Exception as e:
        logger.error(f"callback_report_request error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# -------- TEXT HANDLER (with report reason capture & game interception) --------
@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handler_text(m):
    uid = m.from_user.id
    text = m.text.strip()

    # First: if user is providing a manual report reason (handled by separate handler)
    if uid in report_reason_pending:
        # this is handled by handle_manual_report_reason
        return

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    # Profile flows (unchanged behavior, preserved)
    if not u["gender"]:
        bot.send_message(uid, "❌ Set gender first! Use /start")
        return

    if not u["age"]:
        try:
            age = int(text)
            if age < 12 or age > 99:
                bot.send_message(uid, "❌ Age must be 12-99")
                return
            db_set_age(uid, age)
            bot.send_message(uid, f"✅ Age: {age}\n\n🌍 Enter country:\n⚠️ Cannot change unless Premium!")
            return
        except:
            bot.send_message(uid, "❌ Enter age as number (e.g., 21)")
            return

    if not u["country"]:
        country_info = get_country_info(text)
        if not country_info:
            bot.send_message(uid, f"❌ '{text}' not valid.\n🔍 Try again (e.g., India):")
            return
        country_name, country_flag = country_info
        db_set_country(uid, country_name, country_flag)
        bot.send_message(uid, f"✅ Country: {country_flag} {country_name}\n\n🎯 Profile complete!", reply_markup=main_keyboard(uid))
        return

    # Intercept game messages first — process but do not block normal chat forwarding
    game_result = process_game_message(m)
    # If game_result['handled'] True, we processed a game action; but still allow normal chat forwarding
    # (This implements concurrent chat + game)

    # BUTTON TEXT HANDLERS (same as original)
    if text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free"
            gender_emoji = "👨" if u["gender"] == "Male" else "👩"
            stats_msg = (
                "📊 YOUR STATS\n\n"
                f"Gender: {gender_emoji} {u['gender']}\n"
                f"Age: {u['age']}\n"
                f"Country: {u['country_flag']} {u['country']}\n\n"
                f"📨 Messages: {u['messages_sent']}\n"
                f"✅ Media Approved: {u['media_approved']}\n"
                f"❌ Media Rejected: {u['media_rejected']}\n\n"
                f"People Referred: {u['referral_count']}\n"
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

    # CHAT MESSAGE: forward to partner (original behavior preserved) and log it
    if uid in active_pairs:
        partner_id = active_pairs[uid]
        try:
            bot.send_message(partner_id, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
            # log for reports
            log_chat_message(uid, partner_id, text)
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "❌ Could not send message")
    else:
        bot.send_message(uid, "❌ Not connected. Use search.", reply_markup=main_keyboard(uid))

# -------- RULES & HELP --------
@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = (
        "📘 *Chat Rules — Please read before chatting*\n\n"
        "1️⃣ *Be respectful.* No harassment, threats, hate speech or abusive language.\n\n"
        "2️⃣ *Protect privacy.* Don't ask for or share phone numbers, home addresses, payment info, or other personal details.\n\n"
        "3️⃣ *No explicit content.* Sexual content, nudity, or pornographic material is strictly prohibited.\n\n"
        "4️⃣ *No spam or advertising.* Unsolicited links, referral spam, or promotions are not allowed.\n\n"
        "5️⃣ *Report violations.* Use the Report button if someone breaks the rules.\n\n"
        "🔒 *Violations may lead to warnings or temporary/permanent bans.*\n\n"
        "Thanks — these rules keep the community safe and professional."
    )
    bot.send_message(uid, rules_text, parse_mode="Markdown", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = (
        "🤖 *GhostTalk — Quick Commands*\n\n"
        "/start - Setup profile / change basic info\n"
        "/search_random - Find a random partner\n"
        "/search_opposite_gender - Find opposite-gender partner (Premium)\n"
        "/next - Skip current partner and find new\n"
        "/stop - Stop current chat or cancel search\n"
        "/game - Propose a game to your partner\n"
        "/endgame - End the current game\n"
        "/refer - Get your referral link\n"
        "/rules - Read chat rules\n"
        "/settings - Profile & settings\n"
        "/report - Report your current or last partner\n"
    )
    bot.send_message(uid, help_text, parse_mode="Markdown")

# -------- BOT COMMANDS (clean) --------
def set_bot_commands():
    try:
        user_cmds = [
            types.BotCommand("start", "🔰 Start / Setup"),
            types.BotCommand("search_random", "🔍 Find a random partner"),
            types.BotCommand("search_opposite_gender", "🎯 Find opposite gender (Premium)"),
            types.BotCommand("next", "⏭️ Next partner"),
            types.BotCommand("stop", "🛑 Stop searching/chatting"),
            types.BotCommand("help", "🆘 Help & commands"),
            types.BotCommand("game", "🎮 Play a game with partner"),
            types.BotCommand("endgame", "🛑 End current game"),
            types.BotCommand("refer", "👥 Invite friends"),
            types.BotCommand("rules", "📘 Chat rules"),
            types.BotCommand("settings", "⚙️ Profile & settings"),
            types.BotCommand("report", "🚩 Report partner")
        ]
        bot.set_my_commands(user_cmds)

        # admin-scoped commands
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

# -------- POLLING & STARTUP --------
def run_bot_polling():
    logger.info("🤖 Bot polling started...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")

if __name__ == "__main__":
    init_db()
    logger.info("✅ GhostTalk FINAL merged v2.3 - PRODUCTION READY (fixed)")
    logger.info("✅ Gender + Age columns in settings")
    logger.info("✅ Consent buttons auto-hide and delete")
    logger.info("✅ Feedback replaced with structured report flow (asks reason via inline buttons)")
    logger.info("✅ /rules and /help added")
    logger.info("✅ Game system fixed: concurrent chat + game, clear turn messages, invite deletion, /endgame")
    logger.info("✅ Search spam protection implemented")
    set_bot_commands()

    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()

    PORT = int(os.getenv("PORT", "10000"))
    logger.info(f"🌍 Flask on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
