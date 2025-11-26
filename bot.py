#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FINAL FIXED v2.2
- Removed /pay and /vip
- Improved /help (user-friendly & professional)
- Admin commands accept user_id or @username
- Queue duplicate-check message improved
- Full report workflow: reporter, reported, reason logged & sent to admin
- Consent buttons auto-hide; thumbs removed
- Minimal changes elsewhere; original behavior preserved
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

BOT_USERNAME = os.getenv("BOT_USERNAME", "SayNymBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk_final.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# -------- BANNED WORDS / LINKS --------
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography", "rape", "molest",
    # common insults from earlier list (kept for content moderation)
    "anj", "anjing", "babi", "asu","kontl","kontol","puki","memek","jembut","mc","randi","randika","maderchod","bsdk",
    "lauda","lund","chut","choot","chot","chuut","gand","gaand","ma ka lauda","mkc","teri ma ki chut","teri ma ki chuut"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- COUNTRIES (same as before) --------
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
waiting_opposite = []  # list of tuples (uid, gender)
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history = {}
age_update_pending = {}
pending_reports = {}  # reporter_id -> {reported_id, report_type}

# -------- DATABASE --------
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
            reporter_id INTEGER, reporter_name TEXT,
            reported_id INTEGER, reported_name TEXT,
            report_type TEXT, reason TEXT, timestamp TEXT
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
    u = db_get_user(uid)
    if u:
        # update username/first_name if changed
        with get_conn() as conn:
            conn.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (user.username or "", user.first_name or "", uid))
            conn.commit()
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

def db_add_report_db(reporter_id, reporter_name, reported_id, reported_name, report_type, reason):
    with get_conn() as conn:
        conn.execute("""INSERT INTO reports (reporter_id, reporter_name, reported_id, reported_name, report_type, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (reporter_id, reporter_name, reported_id, reported_name, report_type, reason, datetime.utcnow().isoformat()))
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

# -------- HELPERS --------
def resolve_user_identifier(identifier):
    """
    Accepts a numeric id, or a username (@name or name) and returns user_id if exists.
    Tries DB lookup first, then bot.get_chat for @username.
    Returns integer user_id or None.
    """
    if not identifier:
        return None
    identifier = identifier.strip()
    # numeric id
    if identifier.isdigit():
        return int(identifier)
    # strip @
    uname = identifier.lstrip("@")
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE username=? COLLATE NOCASE", (uname,)).fetchone()
        if row:
            return row[0]
    # try to fetch via Telegram API (if bot can see user by username)
    try:
        chat = bot.get_chat(f"@{uname}")
        if chat and hasattr(chat, "id"):
            return chat.id
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

def disconnect_user(user_id):
    global active_pairs
    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
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
        try:
            bot.send_message(partner_id, "❌ Partner left chat.\n🔍 Find new partner?", reply_markup=main_keyboard(partner_id))
        except:
            pass

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
        types.InlineKeyboardButton("👶 Child Abuse", callback_data="rep:child"),
        types.InlineKeyboardButton("🔞 Pornography", callback_data="rep:porn"),
        types.InlineKeyboardButton("📧 Spamming", callback_data="rep:spam"),
        types.InlineKeyboardButton("💰 Scam/Fraud", callback_data="rep:scam"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep:other")
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
    """Opposite gender from random queue, Random pair in order"""
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

# -------- COMMANDS --------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are banned from this bot.")
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

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    # Professional and user-friendly help message
    help_text = (
        "🤖 GhostTalk — Quick Help\n\n"
        "How it works (simple):\n"
        "1) Complete your profile when /start asks: gender → age → country.\n"
        "2) Use 🔀 Search Random to find someone to chat with.\n"
        "3) While chatting: ⏭️ Next to move on, 🛑 Stop to end the chat.\n\n"
        "Important features:\n"
        "• 🎯 Search Opposite Gender — premium-only feature (unlock via referrals).\n"
        "• 👥 Refer — invite friends to earn premium time.\n"
        "• Media consent — recipients must Accept to receive photos/videos.\n\n"
        "Reporting & Safety:\n"
        "• If someone violates rules, use the Report button after the chat.\n"
        "• You'll be asked to choose a reason and optionally type details.\n"
        "• Admins will review every report.\n\n"
        "Commands (use in chat with the bot):\n"
        "• /start — setup or resume\n"
        "• /help — this message\n"
        "• /refer — see your referral link and progress\n"
        "• /report — report a partner (works during and after chat)\n\n"
        "Tips:\n"
        "• Complete profile for better matching.\n"
        "• Do not share personal contacts or explicit content.\n"
        "• Use /stop if you want to end or cancel a search.\n\n"
        "Need admin help? Use the bot admin contact provided in the chat if required."
    )
    bot.send_message(uid, help_text)

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
        bot.answer_callback_query(call.id, f"Already {gender_display}!", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "✅ Gender set!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender: {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        bot.send_message(uid, f"✅ Gender: {gender_emoji} {gender_display}\n")
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
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"{premium_status}\n\n"
        "🔗 Change Profile:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔗 Refer Link", callback_data="ref:link"))
    markup.row(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"), types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
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
    try:
        age = int(message.text.strip())
        if age < 12 or age > 99:
            bot.send_message(uid, "❌ Age must be 12-99. Try again:")
            bot.register_next_step_handler(message, process_new_age)
            return
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

    # Duplicate queue message (unique wording)
    already_in_random_queue = uid in waiting_random
    already_in_opposite_queue = any(uid == x for x, _ in waiting_opposite)
    if already_in_random_queue or already_in_opposite_queue:
        bot.send_message(uid,
            "⏳ You are already waiting in the search queue — sit tight while we look for a match.\n\n"
            "If you want to cancel, send /stop and you'll be removed.")
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

    already_in_random_queue = uid in waiting_random
    already_in_opposite_queue = any(uid == x for x, _ in waiting_opposite)
    if already_in_random_queue or already_in_opposite_queue:
        bot.send_message(uid,
            "⏳ You are already waiting in the search queue — sit tight while we look for a match.\n\n"
            "If you want to cancel, send /stop and you'll be removed.")
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
    bot.send_message(uid, "✅ Stopped searching/chatting.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not in chat. Use search commands.")
        return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Looking for new partner...", reply_markup=main_keyboard(uid))
    # reuse search_random flow
    cmd_search_random(message)

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    # allow reporting during active chat or after (from chat_history)
    partner_id = active_pairs.get(uid) or chat_history.get(uid)
    if not partner_id:
        bot.send_message(uid, "❌ No partner to report (you haven't chatted yet).")
        return

    # Show report type options
    bot.send_message(uid, "⚠️ Select the reason for reporting:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report_type(call):
    uid = call.from_user.id
    # determine reported partner (active or last)
    reported_id = active_pairs.get(uid) or chat_history.get(uid)
    if not reported_id:
        bot.answer_callback_query(call.id, "No partner to report", show_alert=True)
        return

    _, report_type = call.data.split(":")
    # Save pending report so next text message from user is treated as reason
    pending_reports[uid] = {"reported_id": reported_id, "report_type": report_type}
    bot.answer_callback_query(call.id, "Selected. Please type a short reason or details (1-500 chars).", show_alert=False)
    bot.send_message(uid, "📝 Please type the reason for reporting (what happened?). You can add any details that will help the admin review the case.\n\nTip: be concise and factual.")

@bot.message_handler(func=lambda m: m.content_type == "text" and m.from_user.id in pending_reports)
def process_report_reason(message):
    uid = message.from_user.id
    data = pending_reports.get(uid)
    if not data:
        bot.send_message(uid, "❌ No pending report found.")
        return

    reason_text = message.text.strip()[:500]
    reported_id = data["reported_id"]
    report_type = data["report_type"]

    # reporter info
    reporter = db_get_user(uid) or {}
    reported = db_get_user(reported_id) or {}

    reporter_name = reporter.get("first_name") or reporter.get("username") or str(uid)
    reported_name = reported.get("first_name") or reported.get("username") or str(reported_id)

    # save to DB and notify admin
    db_add_report_db(uid, reporter_name, reported_id, reported_name, report_type, reason_text)

    # send confirmation to reporter
    bot.send_message(uid, "✅ Your report has been submitted. Admins will review it shortly. Thank you for helping keep the community safe.")

    # send structured message to admin
    admin_msg = (
        "⚠️ NEW REPORT RECEIVED\n\n"
        f"Reporter: {reporter_name} (ID: {uid})\n"
        f"Reported: {reported_name} (ID: {reported_id})\n"
        f"Type: {report_type}\n"
        f"Reason: {reason_text}\n"
        f"Time: {datetime.utcnow().isoformat()}\n"
    )
    try:
        bot.send_message(ADMIN_ID, admin_msg)
    except:
        logger.warning("Could not send report to admin via bot (maybe admin blocked bot).")

    # cleanup
    pending_reports.pop(uid, None)

@bot.message_handler(commands=['pradd'])
def cmd_pradd(message):
    """Admin: /pradd [user_id|@username] [YYYY-MM-DD]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "Usage: /pradd [user_id|@username] [YYYY-MM-DD]\nExample: /pradd 12345 2025-12-31")
            return

        identifier = parts[1]
        target_id = resolve_user_identifier(identifier)
        if not target_id:
            bot.reply_to(message, f"❌ Could not find user: {identifier}")
            return

        until_date = parts[2]

        if not db_set_premium(target_id, until_date):
            bot.reply_to(message, "❌ Invalid date! Use YYYY-MM-DD")
            return

        bot.reply_to(message, f"✅ User {target_id} premium until {until_date}")
        try:
            u = db_get_user(target_id)
            if u:
                premium_msg = f"🎉 PREMIUM ADDED!\n✅ Valid until {until_date}\n🎯 Opposite gender search unlocked!"
                bot.send_message(target_id, premium_msg, reply_markup=main_keyboard(target_id))
        except:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['prrem'])
def cmd_prrem(message):
    """Admin: /prrem [user_id|@username]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /prrem [user_id|@username]")
            return

        identifier = parts[1]
        target_id = resolve_user_identifier(identifier)
        if not target_id:
            bot.reply_to(message, f"❌ Could not find user: {identifier}")
            return

        db_remove_premium(target_id)
        bot.reply_to(message, f"✅ Premium removed for {target_id}")

        try:
            bot.send_message(target_id, "❌ Your premium has been removed.", reply_markup=main_keyboard(target_id))
        except:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    """Admin: /ban [user_id|@username] [hours/permanent] [reason]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /ban [user_id|@username] [hours/permanent] [reason]")
            return

        identifier = parts[1]
        target_id = resolve_user_identifier(identifier)
        if not target_id:
            bot.reply_to(message, f"❌ Could not find user: {identifier}")
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
            bot.reply_to(message, f"✅ User {target_id} PERMANENTLY BANNED. {reason}")
            try:
                bot.send_message(target_id, f"🚫 PERMANENTLY BANNED.\nReason: {reason}")
            except:
                pass
        else:
            bot.reply_to(message, f"✅ User {target_id} banned for {hours} hours. {reason}")
            try:
                bot.send_message(target_id, f"🚫 Banned for {hours} hours.\nReason: {reason}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    """Admin: /unban [user_id|@username]"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /unban [user_id|@username]")
            return

        identifier = parts[1]
        target_id = resolve_user_identifier(identifier)
        if not target_id:
            bot.reply_to(message, f"❌ Could not find user: {identifier}")
            return

        db_unban_user(target_id)
        user_warnings[target_id] = 0

        bot.reply_to(message, f"✅ User {target_id} unbanned")
        try:
            bot.send_message(target_id, "✅ Your ban has been lifted!", reply_markup=main_keyboard(target_id))
        except:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker'])
def handle_media(m):
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not connected")
        return

    partner = active_pairs[uid]
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
    else:
        return

    u = db_get_user(uid)
    # maintain previous behavior: if sender has media_approved > 0, forward automatically
    if u and u["media_approved"]:
        try:
            if media_type == "photo":
                bot.send_photo(partner, media_id)
            elif media_type == "document":
                bot.send_document(partner, media_id)
            elif media_type == "video":
                bot.send_video(partner, media_id)
            elif media_type == "animation":
                bot.send_animation(partner, media_id)
            elif media_type == "sticker":
                bot.send_sticker(partner, media_id)
            db_increment_media(uid, "approved")
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "❌ Could not forward media")
        return

    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    pending_media[token] = {
        "sender": uid, "partner": partner, "media_type": media_type,
        "file_id": media_id, "msg_id": None, "timestamp": datetime.utcnow().isoformat()
    }

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}")
    )

    try:
        msg = bot.send_message(partner, f"Your partner sent {media_type}. Accept?", reply_markup=markup)
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

        # Deliver file to the user who accepted (call.from_user.id)
        try:
            if media_type == "photo":
                bot.send_photo(call.from_user.id, file_id)
            elif media_type == "document":
                bot.send_document(call.from_user.id, file_id)
            elif media_type == "video":
                bot.send_video(call.from_user.id, file_id)
            elif media_type == "animation":
                bot.send_animation(call.from_user.id, file_id)
            elif media_type == "sticker":
                bot.send_sticker(call.from_user.id, file_id)
        except Exception as e:
            logger.error(f"Error sending media: {e}")
            try:
                bot.send_message(call.from_user.id, "❌ Could not deliver media")
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

        # Hide/delete consent message reliably
        try:
            if msg_id:
                bot.delete_message(call.message.chat.id, msg_id)
        except Exception:
            try:
                if msg_id:
                    bot.edit_message_reply_markup(call.message.chat.id, msg_id, reply_markup=None)
            except:
                pass

        bot.answer_callback_query(call.id, "✅ Approved", show_alert=False)
        pending_media.pop(token, None)
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

        try:
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED.")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        # Hide/delete consent message reliably
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
        logger.error(f"Error in reject: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handler_text(m):
    uid = m.from_user.id
    text = m.text.strip()

    # If user is in report input stage, handled earlier by process_report_reason via decorator.
    if uid in pending_reports:
        # Let the registered handler process_report_reason handle it (it has its own decorator)
        # So here we just return to avoid duplication.
        return

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

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

    # -------- BUTTON HANDLERS --------
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

    # -------- CHAT MESSAGE --------
    if uid in active_pairs:
        partner = active_pairs[uid]
        try:
            bot.send_message(partner, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error: {e}")
            bot.send_message(uid, "❌ Could not send message")
    else:
        bot.send_message(uid, "❌ Not connected. Use search.", reply_markup=main_keyboard(uid))

def run_bot_polling():
    logger.info("🤖 Bot polling started...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ Polling error: {e}")

if __name__ == "__main__":
    init_db()
    logger.info("✅ GhostTalk FINAL v2.2 - PRODUCTION READY")
    logger.info(" - /pay removed")
    logger.info(" - /vip removed")
    logger.info(" - Report workflow improved (reporter, reported, reason)")
    logger.info(" - Help message updated")

    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()

    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"🌍 Flask on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
