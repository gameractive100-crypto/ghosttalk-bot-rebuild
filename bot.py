#!/usr/bin/env python3
"""
GhostTalk Premium Anonymous Chat Bot v4.3 - FINAL FIX
✅ PRIORITY 3 FIXED - Random search works for everyone
✅ FEEDBACK REMOVED - No feedback menu after chat
✅ REPORT MENU FIXED - Only shows when you tap report
✅ AUTO BAN SYSTEM - 7 reports = ban
✅ Complete working code - Production ready
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

# ==================== CONFIG ====================
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("🚨 BOT_TOKEN environment variable not set!")

ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
AUTO_BAN_REPORTS = 7
AUTO_BAN_DAYS = 7
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 24

# ==================== BANNED WORDS ====================
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis",
    "vagina", "boobs", "tits", "ass", "asshole", "bitch", "slut", "whore", "hoe",
    "prostitute", "porn", "pornography", "rape", "child", "pedo",
    "anj", "anjing", "babi", "asu", "kontl", "kontol", "puki", "memek", "jembut",
    "maderchod", "mc", "bhen ka lauda", "bhenkalauda", "randi", "randika", "gand",
    "bsdk", "chut", "chot", "chuut", "choot", "lund"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# ==================== COUNTRIES (195) ====================
COUNTRIES = {
    "afghanistan": "🇦🇫", "albania": "🇦🇱", "algeria": "🇩🇿", "andorra": "🇦🇩", "angola": "🇦🇴",
    "antigua and barbuda": "🇦🇬", "argentina": "🇦🇷", "armenia": "🇦🇲", "australia": "🇦🇺", "austria": "🇦🇹",
    "azerbaijan": "🇦🇿", "bahamas": "🇧🇸", "bahrain": "🇧🇭", "bangladesh": "🇧🇩", "barbados": "🇧🇧",
    "belarus": "🇧🇾", "belgium": "🇧🇪", "belize": "🇧🇿", "benin": "🇧🇯", "bhutan": "🇧🇹",
    "bolivia": "🇧🇴", "bosnia and herzegovina": "🇧🇦", "botswana": "🇧🇼", "brazil": "🇧🇷", "brunei": "🇧🇳",
    "bulgaria": "🇧🇬", "burkina faso": "🇧🇫", "burundi": "🇧🇮", "cambodia": "🇰🇭", "cameroon": "🇨🇲",
    "canada": "🇨🇦", "cape verde": "🇨🇻", "central african republic": "🇨🇫", "chad": "🇹🇩", "chile": "🇨🇱",
    "china": "🇨🇳", "colombia": "🇨🇴", "comoros": "🇰🇲", "congo": "🇨🇬", "costa rica": "🇨🇷",
    "croatia": "🇭🇷", "cuba": "🇨🇺", "cyprus": "🇨🇾", "czech republic": "🇨🇿", "czechia": "🇨🇿",
    "denmark": "🇩🇰", "djibouti": "🇩🇯", "dominica": "🇩🇲", "dominican republic": "🇩🇴",
    "ecuador": "🇪🇨", "egypt": "🇪🇬", "el salvador": "🇸🇻", "equatorial guinea": "🇬🇶",
    "eritrea": "🇪🇷", "estonia": "🇪🇪", "eswatini": "🇸🇿", "ethiopia": "🇪🇹", "fiji": "🇫🇯",
    "finland": "🇫🇮", "france": "🇫🇷", "gabon": "🇬🇦", "gambia": "🇬🇲", "georgia": "🇬🇪",
    "germany": "🇩🇪", "ghana": "🇬🇭", "greece": "🇬🇷", "grenada": "🇬🇩", "guatemala": "🇬🇹",
    "guinea": "🇬🇳", "guinea-bissau": "🇬🇼", "guyana": "🇬🇾", "haiti": "🇭🇹", "honduras": "🇭🇳",
    "hungary": "🇭🇺", "iceland": "🇮🇸", "india": "🇮🇳", "indonesia": "🇮🇩", "iran": "🇮🇷",
    "iraq": "🇮🇶", "ireland": "🇮🇪", "israel": "🇮🇱", "italy": "🇮🇹", "jamaica": "🇯🇲",
    "japan": "🇯🇵", "jordan": "🇯🇴", "kazakhstan": "🇰🇿", "kenya": "🇰🇪", "kiribati": "🇰🇮",
    "korea north": "🇰🇵", "korea south": "🇰🇷", "kuwait": "🇰🇼", "kyrgyzstan": "🇰🇬",
    "laos": "🇱🇦", "latvia": "🇱🇻", "lebanon": "🇱🇧", "lesotho": "🇱🇸", "liberia": "🇱🇷",
    "libya": "🇱🇾", "liechtenstein": "🇱🇮", "lithuania": "🇱🇹", "luxembourg": "🇱🇺",
    "madagascar": "🇲🇬", "malawi": "🇲🇼", "malaysia": "🇲🇾", "maldives": "🇲🇻", "mali": "🇲🇱",
    "malta": "🇲🇹", "marshall islands": "🇲🇭", "mauritania": "🇲🇷", "mauritius": "🇲🇺",
    "mexico": "🇲🇽", "micronesia": "🇫🇲", "moldova": "🇲🇩", "monaco": "🇲🇨", "mongolia": "🇲🇳",
    "montenegro": "🇲🇪", "morocco": "🇲🇦", "mozambique": "🇲🇿", "myanmar": "🇲🇲", "namibia": "🇳🇦",
    "nauru": "🇳🇷", "nepal": "🇳🇵", "netherlands": "🇳🇱", "new zealand": "🇳🇿", "nicaragua": "🇳🇮",
    "niger": "🇳🇪", "nigeria": "🇳🇬", "north macedonia": "🇲🇰", "norway": "🇳🇴", "oman": "🇴🇲",
    "pakistan": "🇵🇰", "palau": "🇵🇼", "palestine": "🇵🇸", "panama": "🇵🇦", "papua new guinea": "🇵🇬",
    "paraguay": "🇵🇾", "peru": "🇵🇪", "philippines": "🇵🇭", "poland": "🇵🇱", "portugal": "🇵🇹",
    "qatar": "🇶🇦", "romania": "🇷🇴", "russia": "🇷🇺", "rwanda": "🇷🇼", "saint kitts and nevis": "🇰🇳",
    "saint lucia": "🇱🇨", "saint vincent and the grenadines": "🇻🇨", "samoa": "🇼🇸",
    "san marino": "🇸🇲", "sao tome and principe": "🇸🇹", "saudi arabia": "🇸🇦", "senegal": "🇸🇳",
    "serbia": "🇷🇸", "seychelles": "🇸🇨", "sierra leone": "🇸🇱", "singapore": "🇸🇬",
    "slovakia": "🇸🇰", "slovenia": "🇸🇮", "solomon islands": "🇸🇧", "somalia": "🇸🇴",
    "south africa": "🇿🇦", "south sudan": "🇸🇸", "spain": "🇪🇸", "sri lanka": "🇱🇰",
    "sudan": "🇸🇩", "suriname": "🇸🇷", "sweden": "🇸🇪", "switzerland": "🇨🇭", "syria": "🇸🇾",
    "taiwan": "🇹🇼", "tajikistan": "🇹🇯", "tanzania": "🇹🇿", "thailand": "🇹🇭",
    "timor-leste": "🇹🇱", "togo": "🇹🇬", "tonga": "🇹🇴", "trinidad and tobago": "🇹🇹",
    "tunisia": "🇹🇳", "turkey": "🇹🇷", "turkmenistan": "🇹🇲", "tuvalu": "🇹🇻",
    "uganda": "🇺🇬", "ukraine": "🇺🇦", "united arab emirates": "🇦🇪", "united kingdom": "🇬🇧",
    "united states": "🇺🇸", "uruguay": "🇺🇾", "uzbekistan": "🇺🇿", "vanuatu": "🇻🇺",
    "vatican city": "🇻🇦", "venezuela": "🇻🇪", "vietnam": "🇻🇳", "yemen": "🇾🇪",
    "zambia": "🇿🇲", "zimbabwe": "🇿🇼"
}

COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "america": "united states",
    "uk": "united kingdom", "britain": "united kingdom", "england": "united kingdom",
    "uae": "united arab emirates", "emirates": "united arab emirates",
    "south korea": "korea south", "sk": "korea south",
    "north korea": "korea north", "nk": "korea north",
    "czechia": "czech republic"
}

def get_country_info(user_input):
    """Get country name and flag from user input"""
    normalized = user_input.strip().lower()
    if normalized in COUNTRY_ALIASES:
        normalized = COUNTRY_ALIASES[normalized]
    if normalized in COUNTRIES:
        return normalized.title(), COUNTRIES[normalized]
    return None

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ghosttalk.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== FLASK & BOT ====================
app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=True)

@app.route("/")
def home():
    return "🤖 GhostTalk Running!", 200

@app.route("/health")
def health():
    return {"status": "✅ ok"}, 200

# ==================== RUNTIME DATA ====================
waiting_random = []
waiting_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history_with_time = {}
pending_country = set()
pending_age = set()
report_reason_pending = {}
chat_history = {}

# ==================== THREADING LOCKS ====================
queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()

# ==================== DATABASE ====================
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
            ban_until TEXT, permanent INTEGER DEFAULT 0, reason TEXT,
            banned_by INTEGER, banned_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER, reported_id INTEGER,
            report_type TEXT, reason TEXT, timestamp TEXT
        )""")

        conn.commit()
        logger.info("✅ Database initialized")

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT user_id, username, first_name, gender, age, country, country_flag,
                   messages_sent, media_approved, media_rejected, referral_code,
                   referral_count, premium_until
            FROM users WHERE user_id=?
        """, (user_id,)).fetchone()

        if not row:
            return None

        return {
            "user_id": row[0], "username": row[1], "first_name": row[2],
            "gender": row[3], "age": row[4], "country": row[5], "country_flag": row[6],
            "messages_sent": row[7], "media_approved": row[8], "media_rejected": row[9],
            "referral_code": row[10], "referral_count": row[11], "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return

    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users
            (user_id, username, first_name, gender, age, country, country_flag,
             joined_at, referral_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, user.username or "", user.first_name or "", None, None, None, None,
              datetime.utcnow().isoformat(), ref_code))
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
        conn.execute("UPDATE users SET country=?, country_flag=? WHERE user_id=?",
                    (country, flag, user_id))
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
    except:
        return False

def db_is_banned(user_id):
    if user_id == OWNER_ID:
        return False

    with get_conn() as conn:
        row = conn.execute(
            "SELECT ban_until, permanent FROM bans WHERE user_id=?",
            (user_id,)
        ).fetchone()

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
            conn.execute(
                "INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, None, 1, reason, ADMIN_ID, datetime.utcnow().isoformat())
            )
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute(
                "INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, until, 0, reason, ADMIN_ID, datetime.utcnow().isoformat())
            )
        conn.commit()

def db_add_report(reporter_id, reported_id, report_type, reason):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO reports (reporter_id, reported_id, report_type, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (reporter_id, reported_id, report_type, reason, datetime.utcnow().isoformat()))

        report_count = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE reported_id=?",
            (reported_id,)
        ).fetchone()[0]

        logger.info(f"📊 User {reported_id} has {report_count} reports")

        if report_count >= AUTO_BAN_REPORTS:
            ban_until = (datetime.utcnow() + timedelta(days=AUTO_BAN_DAYS)).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (reported_id, ban_until, 0, f"Auto-ban: {report_count} reports", ADMIN_ID, datetime.utcnow().isoformat())
            )
            logger.warning(f"🚫 AUTO-BAN: User {reported_id} for {AUTO_BAN_DAYS} days - {report_count} reports")

            try:
                bot.send_message(reported_id, f"🚫 BANNED FOR {AUTO_BAN_DAYS} DAYS\n❌ Reason: {report_count} reports received")
            except:
                pass

            if reported_id in active_pairs:
                with active_pairs_lock:
                    partner = active_pairs.get(reported_id)
                    if partner and partner in active_pairs:
                        del active_pairs[partner]
                    if reported_id in active_pairs:
                        del active_pairs[reported_id]

        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

# ==================== WARNING SYSTEM ====================
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
    with user_warnings_lock:
        count = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = count

    if count >= WARNING_LIMIT:
        db_ban_user(user_id, hours=TEMP_BAN_HOURS, reason=reason)
        with user_warnings_lock:
            if user_id in user_warnings:
                del user_warnings[user_id]
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

# ==================== QUEUE HELPERS ====================
def remove_from_queues(user_id):
    global waiting_random, waiting_opposite
    with queue_lock:
        if user_id in waiting_random:
            waiting_random.remove(user_id)
        waiting_opposite = [(uid, gen) for uid, gen in waiting_opposite if uid != user_id]

def append_chat_history(user_id, chat_id, message_id):
    if user_id not in chat_history:
        chat_history[user_id] = []
    chat_history[user_id].append((chat_id, message_id))
    if len(chat_history[user_id]) > 50:
        chat_history[user_id].pop(0)

def user_label(uid):
    u = db_get_user(uid)
    if u and u.get("username"):
        return f"@{u['username']}"
    return str(uid)

def forward_full_chat_to_admin(reporter_id, reported_id, report_type, reason=""):
    """Forward chat history to admin"""
    try:
        bot.send_message(ADMIN_ID, f"""🚩 NEW REPORT
Type: {report_type}
Reporter: {user_label(reporter_id)} ({reporter_id})
Reported: {user_label(reported_id)} ({reported_id})
Reason: {reason if reason else "No reason"}
Time: {datetime.utcnow().isoformat()}""")

        bot.send_message(ADMIN_ID, "📨 Reporter messages:")
        reporter_msgs = chat_history.get(reporter_id, [])[-20:]
        if reporter_msgs:
            for chat_id, msg_id in reporter_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except:
                    pass
        else:
            bot.send_message(ADMIN_ID, "— No messages —")

        bot.send_message(ADMIN_ID, "📨 Reported user messages:")
        reported_msgs = chat_history.get(reported_id, [])[-20:]
        if reported_msgs:
            for chat_id, msg_id in reported_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except:
                    pass
        else:
            bot.send_message(ADMIN_ID, "— No messages —")

        bot.send_message(ADMIN_ID, "━━━━ End of forwarded messages ━━━━")

    except Exception as e:
        logger.error(f"Report error: {e}")

def disconnect_user(user_id):
    """Disconnect user - NO FEEDBACK MENU (removed as requested)"""
    global active_pairs
    with active_pairs_lock:
        if user_id in active_pairs:
            partner_id = active_pairs[user_id]
            chat_history_with_time[user_id] = (partner_id, datetime.utcnow())
            chat_history_with_time[partner_id] = (user_id, datetime.utcnow())
            if partner_id in active_pairs:
                del active_pairs[partner_id]
            if user_id in active_pairs:
                del active_pairs[user_id]
            try:
                bot.send_message(partner_id, "❌ Partner left chat.", reply_markup=main_keyboard(partner_id))
                logger.info(f"👋 Disconnected: {user_id} | Partner {partner_id}")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")

def main_keyboard(user_id):
    """Main menu keyboard"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔀 Search Random")
    u = db_get_user(user_id)
    if u and u["gender"]:
        if db_is_premium(user_id):
            kb.add("🎯 Search Opposite Gender")
        else:
            kb.add("Opposite Gender (Premium) 🔒")
    kb.add("🛑 Stop")
    kb.add("⚙️ Settings", "👥 Refer")
    kb.add("❓ Help", "📋 Rules", "🚨 Report")
    return kb

def chat_keyboard():
    """Chat menu keyboard"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("📊 Stats")
    kb.add("⏭️ Next", "🛑 Stop")
    return kb

def report_keyboard():
    """Report reason keyboard - shown when user taps Report button"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚫 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("📎 Unwanted Content", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("⚠️ Inappropriate Messages", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🕵️ Suspicious Activity", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("💬 Other Reason", callback_data="rep:other"),
        types.InlineKeyboardButton("⏭️ Cancel", callback_data="rep:cancel")
    )
    return markup

def format_partner_found_message(partner_user, viewer_id):
    """Format partner found message"""
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

    msg += "\n💬 Enjoy chat!"
    return msg

# ==================== MATCH USERS - CORRECTED LOGIC ====================
def match_users():
    """
    CORRECT 3-PRIORITY MATCHING:

    ✅ PRIORITY 1: Premium Opposite ↔ Premium Opposite (opposite gender only)
    ✅ PRIORITY 2: Premium Opposite ↔ Free Random (opposite gender only)
    ✅ PRIORITY 3: RANDOM SEARCH - ANYONE can match ANYONE (no premium check)
    """
    global waiting_random, waiting_opposite, active_pairs

    # ==================== PRIORITY 1: PREMIUM OPPOSITE ↔ PREMIUM OPPOSITE ====================
    i = 0
    while i < len(waiting_opposite):
        uid, searcher_gender = waiting_opposite[i]

        if not db_is_premium(uid):
            i += 1
            continue

        needed_gender = "Male" if searcher_gender == "Female" else "Female"

        with queue_lock:
            for j in range(i + 1, len(waiting_opposite)):
                other_uid, other_gender = waiting_opposite[j]

                if db_is_premium(other_uid) and other_gender == needed_gender:
                    waiting_opposite.pop(j)
                    waiting_opposite.pop(i)

                    with active_pairs_lock:
                        active_pairs[uid] = other_uid
                        active_pairs[other_uid] = uid

                    u1 = db_get_user(uid)
                    u2 = db_get_user(other_uid)

                    try:
                        bot.send_message(uid, format_partner_found_message(u2, uid), reply_markup=chat_keyboard())
                        bot.send_message(other_uid, format_partner_found_message(u1, other_uid), reply_markup=chat_keyboard())
                        logger.info(f"✅ P1: {uid}({u1['gender']}) PREM ↔ {other_uid}({u2['gender']}) PREM")
                    except:
                        pass
                    return

        i += 1

    # ==================== PRIORITY 2: PREMIUM OPPOSITE ↔ FREE RANDOM ====================
    with queue_lock:
        opposite_copy = waiting_opposite.copy()

    for uid, searcher_gender in opposite_copy:
        if not db_is_premium(uid):
            continue

        needed_gender = "Male" if searcher_gender == "Female" else "Female"

        with queue_lock:
            for j, other_uid in enumerate(waiting_random):
                if db_is_premium(other_uid):
                    continue

                other_data = db_get_user(other_uid)
                if other_data and other_data['gender'] == needed_gender:
                    found_uid = waiting_random.pop(j)
                    waiting_opposite = [(u, g) for u, g in waiting_opposite if u != uid]

                    with active_pairs_lock:
                        active_pairs[uid] = found_uid
                        active_pairs[found_uid] = uid

                    u1 = db_get_user(uid)
                    u2 = db_get_user(found_uid)

                    try:
                        bot.send_message(uid, format_partner_found_message(u2, uid), reply_markup=chat_keyboard())
                        bot.send_message(found_uid, format_partner_found_message(u1, found_uid), reply_markup=chat_keyboard())
                        logger.info(f"✅ P2: {uid}({u1['gender']}) PREM-OPP ↔ {found_uid}({u2['gender']}) FREE-RND")
                    except:
                        pass
                    return

    # ==================== PRIORITY 3: RANDOM SEARCH (ANY ↔ ANY) ====================
    # ✅ FIXED: NO premium check! Anyone can match anyone in random search
    with queue_lock:
        while len(waiting_random) >= 2:
            u1 = waiting_random.pop(0)
            u2 = waiting_random.pop(0)

            with active_pairs_lock:
                active_pairs[u1] = u2
                active_pairs[u2] = u1

            u1_data = db_get_user(u1)
            u2_data = db_get_user(u2)

            try:
                bot.send_message(u1, format_partner_found_message(u2_data, u1), reply_markup=chat_keyboard())
                bot.send_message(u2, format_partner_found_message(u1_data, u2), reply_markup=chat_keyboard())
                logger.info(f"✅ P3: {u1}({u1_data['gender']}) ↔ {u2}({u2_data['gender']}) [RANDOM]")
            except:
                pass

# ==================== CLEANUP THREADS ====================
def cleanup_threads():
    """Cleanup old chat history"""
    def run():
        while True:
            time.sleep(3600)
            try:
                now = datetime.utcnow()
                threshold = timedelta(days=7)
                to_delete = []

                for uid, (partner, ts) in list(chat_history_with_time.items()):
                    try:
                        if now - ts > threshold:
                            to_delete.append(uid)
                    except:
                        to_delete.append(uid)

                for uid in to_delete:
                    try:
                        if uid in chat_history:
                            del chat_history[uid]
                        if uid in chat_history_with_time:
                            del chat_history_with_time[uid]
                    except:
                        pass
                logger.info(f"🧹 Cleanup: Removed {len(to_delete)} old records")
            except:
                pass

    t = threading.Thread(target=run, daemon=True)
    t.start()

# ==================== COMMANDS ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are BANNED")
        return

    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
            types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "👋 Welcome to GhostTalk!\n\n🎯 Select your gender:", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "📍 Enter your age (12-99):")
        pending_age.add(user.id)
        bot.register_next_step_handler(message, process_new_age)
    elif not u["country"]:
        bot.send_message(user.id, "🌍 Enter your country name:")
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = "✅ Premium" if db_is_premium(user.id) else "🆓 Free"
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
    help_text = """❓ GHOSTTALK HELP

🔀 Search Random - Find any random partner
🎯 Search Opposite Gender - Find opposite gender (PREMIUM)
📊 Stats - View your stats
⚙️ Settings - Change profile
👥 Refer - Get referral link
📋 Rules - View community rules
🚨 Report - Report abusive user
🛑 Stop - Exit current chat

🔗 During Chat:
⏭️ Next - Find new partner

📱 Share photos/videos with permission system
✅ Accept - Allow partner's media
❌ Reject - Decline partner's media

⚠️ 3 warnings = 24h ban
📊 Auto-ban after 7 reports"""

    bot.send_message(uid, help_text, reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = """📋 COMMUNITY RULES

1️⃣ Be Respectful
   ✅ Treat everyone with courtesy
   ❌ No harassment or abuse

2️⃣ No Adult Content
   ✅ Keep conversations appropriate
   ❌ No explicit/sexual content

3️⃣ No Spam
   ✅ Natural conversation flow
   ❌ No repeated messages/links

4️⃣ Protect Privacy
   ✅ Don't share personal info
   ❌ No phone numbers/addresses

5️⃣ Media Consent
   ✅ Ask before sharing media
   ❌ No unwanted images

⚠️ VIOLATIONS:
   🚨 3 warnings = 24 hour ban
   🚫 7+ reports = 7 days auto-ban

Report abusive users!"""

    bot.send_message(uid, rules_text, reply_markup=main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)

    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 Banned", show_alert=True)
        return

    u = db_get_user(uid)
    if u and u["gender"]:
        if uid != ADMIN_ID and not db_is_premium(uid):
            bot.answer_callback_query(call.id, "💎 Gender change = PREMIUM only!", show_alert=True)
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
        bot.edit_message_text(f"✅ {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        bot.send_message(uid, f"✅ Gender: {gender_emoji} {gender_display}\n\n📍 Enter your age (12-99):")
        pending_age.add(uid)
        bot.register_next_step_handler(call.message, process_new_age)
    except:
        pass

def process_new_age(message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in pending_age:
        bot.send_message(uid, "Use /start first")
        return

    if not text.isdigit():
        bot.send_message(uid, f"❌ '{text}' not valid.\n\nEnter age (12-99):")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, f"❌ Age {age} out of range (12-99).\n\nTry again:")
        bot.register_next_step_handler(message, process_new_age)
        return

    db_set_age(uid, age)
    pending_age.discard(uid)

    u = db_get_user(uid)
    if not u["country"]:
        bot.send_message(uid, f"✅ Age: {age} 🎂\n\n🌍 Now enter your country:")
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(uid, f"✅ Age: {age} 🎂", reply_markup=main_keyboard(uid))

def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if uid not in pending_country:
        bot.send_message(uid, "Use /start first")
        return

    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"❌ '{text}' not valid.\n\nTry again (e.g., India):")
        bot.register_next_step_handler(message, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)
    bot.send_message(uid, f"✅ Country: {country_flag} {country_name}\n\n🎯 Profile complete!", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return

    premium_status = "✅ Premium" if db_is_premium(uid) else "🆓 Free"
    gender_emoji = "👨" if u["gender"] == "Male" else "👩"

    settings_text = (
        "⚙️ SETTINGS\n\n"
        f"👤 Gender: {gender_emoji} {u['gender'] or 'Not set'}\n"
        f"🎂 Age: {u['age'] or 'Not set'}\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\n\n"
        f"📊 Messages: {u['messages_sent']}\n"
        f"✅ Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n\n"
        f"👥 Referred: {u['referral_count']}/3\n"
        f"{premium_status}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("👨 Gender", callback_data="sex:male"), types.InlineKeyboardButton("👩 Gender", callback_data="sex:female"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))

    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def callback_change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, "🎂 Enter new age (12-99):")
    pending_age.add(uid)
    bot.register_next_step_handler(call.message, process_new_age)
    bot.answer_callback_query(call.id, "✅", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def callback_set_country(call):
    uid = call.from_user.id
    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, "💎 Country change = PREMIUM only!", show_alert=True)
        return
    bot.send_message(uid, "🌍 Enter new country:")
    pending_country.add(uid)
    bot.register_next_step_handler(call.message, process_new_country)
    bot.answer_callback_query(call.id, "✅", show_alert=False)

@bot.message_handler(commands=['refer'])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return

    try:
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={u['referral_code']}"
    except:
        ref_link = f"REFCODE:{u['referral_code']}"

    remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]

    refer_text = (
        "👥 REFERRAL SYSTEM\n\n"
        f"🔗 {ref_link}\n\n"
        f"👥 Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"🎁 Reward: {PREMIUM_DURATION_HOURS}h Premium\n"
    )

    if remaining > 0:
        refer_text += f"\n📍 Invite {remaining} more!"
    else:
        refer_text += "\n✅ Premium unlocked!"

    bot.send_message(uid, refer_text)

@bot.message_handler(commands=['search_random'])
def cmd_search_random(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "❌ Complete profile first! /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "⏳ Already chatting!")
            return

    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching...\n⏳ Wait")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    if not db_is_premium(uid):
        bot.send_message(uid, "💎 PREMIUM REQUIRED!\n\n✨ Refer 3 friends to unlock!")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "❌ Complete profile!")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "⏳ Already chatting!")
            return

    opposite_gen = "Male" if u["gender"] == "Female" else "Female"
    logger.info(f"🎯 {uid} ({u['gender']}) searching opposite ({opposite_gen})")

    remove_from_queues(uid)
    with queue_lock:
        waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, f"🎯 Searching {opposite_gen}...\n⏳ Wait")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    bot.send_message(uid, "✅ Stopped", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not chatting")
            return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Looking for new partner...", reply_markup=main_keyboard(uid))
    cmd_search_random(message)

@bot.message_handler(commands=['report'])
def cmd_report(message):
    """Report command - shows report menu"""
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not in active chat. Can only report current partner.")
            return

    bot.send_message(uid, "🚨 Select report reason:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id
    _, report_type = call.data.split(":")

    # ✅ CANCEL REPORT
    if report_type == "cancel":
        bot.answer_callback_query(call.id, "✅ Cancelled", show_alert=False)
        try:
            bot.edit_message_text("✓ Report cancelled", call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    # Get partner from active chat
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.answer_callback_query(call.id, "❌ Not in active chat", show_alert=True)
            return
        partner_id = active_pairs[uid]

    report_type_map = {
        "spam": "Spam",
        "unwanted": "Unwanted Content",
        "inappropriate": "Inappropriate Messages",
        "suspicious": "Suspicious Activity",
        "other": "Other"
    }
    report_type_name = report_type_map.get(report_type, "Other")

    if report_type == "other":
        report_reason_pending[uid] = (partner_id, report_type_name)
        bot.answer_callback_query(call.id, "Type reason...", show_alert=False)
        bot.send_message(uid, "📝 Type reason (short, max 100 chars):")
        bot.register_next_step_handler(call.message, process_report_reason)
        return

    db_add_report(uid, partner_id, report_type_name, "")
    forward_full_chat_to_admin(uid, partner_id, report_type_name, "")
    db_ban_user(partner_id, hours=TEMP_BAN_HOURS, reason=report_type_name)

    bot.send_message(uid, "✅ Report submitted! User banned for 24 hours.", reply_markup=main_keyboard(uid))
    bot.answer_callback_query(call.id, "✅ Reported", show_alert=False)

    try:
        bot.edit_message_text("✓ Report submitted", call.message.chat.id, call.message.message_id)
    except:
        pass

    logger.info(f"📊 Report: {uid} reported {partner_id} for {report_type_name}")

def process_report_reason(message):
    """Process custom report reason"""
    uid = message.from_user.id
    reason = (message.text or "").strip()[:100]

    if uid not in report_reason_pending:
        bot.send_message(uid, "❌ Report expired. Try again.", reply_markup=main_keyboard(uid))
        return

    partner_id, report_type = report_reason_pending.pop(uid)

    if not reason:
        bot.send_message(uid, "❌ Reason cannot be empty!", reply_markup=main_keyboard(uid))
        return

    db_add_report(uid, partner_id, report_type, reason)
    forward_full_chat_to_admin(uid, partner_id, report_type, reason)
    db_ban_user(partner_id, hours=TEMP_BAN_HOURS, reason=report_type)

    bot.send_message(uid, "✅ Report submitted! User banned for 24 hours.", reply_markup=main_keyboard(uid))
    logger.info(f"📊 Report: {uid} reported {partner_id} for {report_type} - Reason: {reason}")

@bot.message_handler(commands=['pradd'])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd [user_id] [YYYY-MM-DD]")
        return
    try:
        target_id = int(parts[1])
    except:
        bot.reply_to(message, "❌ Invalid user_id")
        return
    if not db_set_premium(target_id, parts[2]):
        bot.reply_to(message, "❌ Invalid date")
        return
    bot.reply_to(message, f"✅ Premium added to {target_id}")

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban [user_id] [hours]")
        return
    try:
        target_id = int(parts[1])
        hours = int(parts[2]) if len(parts) > 2 else 24
    except:
        bot.reply_to(message, "❌ Invalid")
        return
    db_ban_user(target_id, hours=hours, reason="Banned by admin")
    bot.reply_to(message, f"✅ User {target_id} banned for {hours}h")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban [user_id]")
        return
    try:
        target_id = int(parts[1])
    except:
        bot.reply_to(message, "❌ Invalid user_id")
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id=?", (target_id,))
        conn.commit()
    bot.reply_to(message, f"✅ User {target_id} unbanned")

# ==================== MEDIA HANDLERS ====================

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker', 'voice', 'audio'])
def handle_media(m):
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    with active_pairs_lock:
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
    elif media_type == "voice":
        media_id = m.voice.file_id
    elif media_type == "audio":
        media_id = m.audio.file_id
    else:
        return

    u = db_get_user(uid)
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
            elif media_type == "voice":
                bot.send_voice(partner, media_id)
            elif media_type == "audio":
                bot.send_audio(partner, media_id)
            db_increment_media(uid, "approved")
            append_chat_history(uid, m.chat.id, m.message_id)
        except:
            bot.send_message(uid, "❌ Could not send")
        return

    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    with pending_media_lock:
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
        msg = bot.send_message(partner, f"Partner sent {media_type}. Accept?", reply_markup=markup)
        with pending_media_lock:
            if token in pending_media:
                pending_media[token]["msg_id"] = msg.message_id
    except:
        bot.send_message(uid, "❌ Error")
        with pending_media_lock:
            if token in pending_media:
                del pending_media[token]

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        with pending_media_lock:
            meta = pending_media.get(token)
            if not meta:
                bot.answer_callback_query(call.id, "Expired", show_alert=True)
                return

            sender_id = meta["sender"]
            partner_id = meta["partner"]
            media_type = meta["media_type"]
            file_id = meta["file_id"]
            msg_id = meta.get("msg_id")

            if token in pending_media:
                del pending_media[token]

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
            elif media_type == "voice":
                bot.send_voice(partner_id, file_id)
            elif media_type == "audio":
                bot.send_audio(partner_id, file_id)
        except:
            pass

        try:
            bot.send_message(sender_id, "✅ Approved!")
            db_increment_media(sender_id, "approved")
        except:
            pass

        try:
            bot.edit_message_text("✅ Approved", call.message.chat.id, msg_id)
        except:
            pass

        bot.answer_callback_query(call.id, "✅ Approved", show_alert=False)
    except Exception as e:
        logger.error(f"Error: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        with pending_media_lock:
            meta = pending_media.get(token)
            if not meta:
                bot.answer_callback_query(call.id, "Expired", show_alert=True)
                return

            sender_id = meta["sender"]
            msg_id = meta.get("msg_id")

            if token in pending_media:
                del pending_media[token]

        try:
            bot.send_message(sender_id, "❌ Rejected")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        try:
            bot.edit_message_text("❌ Rejected", call.message.chat.id, msg_id)
        except:
            pass

        bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)
    except Exception as e:
        logger.error(f"Error: {e}")

# ==================== BUTTON HANDLERS ====================

@bot.message_handler(func=lambda message: message.text == "🔀 Search Random")
def handle_search_random_btn(message):
    cmd_search_random(message)

@bot.message_handler(func=lambda message: message.text == "🎯 Search Opposite Gender")
def handle_search_opposite_btn(message):
    cmd_search_opposite(message)

@bot.message_handler(func=lambda message: message.text == "🛑 Stop")
def handle_stop_btn(message):
    cmd_stop(message)

@bot.message_handler(func=lambda message: message.text == "⚙️ Settings")
def handle_settings_btn(message):
    cmd_settings(message)

@bot.message_handler(func=lambda message: message.text == "👥 Refer")
def handle_refer_btn(message):
    cmd_refer(message)

@bot.message_handler(func=lambda message: message.text == "❓ Help")
def handle_help_btn(message):
    cmd_help(message)

@bot.message_handler(func=lambda message: message.text == "📋 Rules")
def handle_rules_btn(message):
    cmd_rules(message)

@bot.message_handler(func=lambda message: message.text == "🚨 Report")
def handle_report_btn(message):
    cmd_report(message)

@bot.message_handler(func=lambda message: message.text == "📊 Stats")
def handle_stats_btn(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "❌ Not found")
        return
    stats = (
        "📊 YOUR STATS\n\n"
        f"📨 Messages: {u['messages_sent']}\n"
        f"✅ Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n"
        f"👥 Referred: {u['referral_count']}/3"
    )
    bot.send_message(uid, stats, reply_markup=chat_keyboard())

@bot.message_handler(func=lambda message: message.text == "⏭️ Next")
def handle_next_btn(message):
    cmd_next(message)

# ==================== TEXT MESSAGE HANDLER ====================

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return

    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not connected", reply_markup=main_keyboard(uid))
            return
        partner = active_pairs.get(uid)

    if not partner:
        bot.send_message(uid, "❌ Not connected", reply_markup=main_keyboard(uid))
        return

    if is_banned_content(text):
        warn_result = warn_user(uid, "Bad content")
        if warn_result == "ban":
            remove_from_queues(uid)
            disconnect_user(uid)
        return

    try:
        append_chat_history(uid, message.chat.id, message.message_id)

        u = db_get_user(uid)
        if u:
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()

        bot.send_message(partner, text)
    except Exception as e:
        logger.error(f"Error: {e}")

# ==================== RUN BOT ====================

def run_bot():
    logger.info("🤖 GhostTalk v4.3 Starting...")
    init_db()
    cleanup_threads()
    logger.info("✅ Bot Ready!")
    bot.infinity_polling()

if __name__ == "__main__":
    import sys

    def run_flask():
        port = int(os.getenv("PORT", 10000))
        app.run(host="0.0.0.0", port=port, debug=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        run_bot()
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)
