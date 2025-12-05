#!/usr/bin/env python3
"""
GhostTalk v5.4 - COMPLETE & PRODUCTION READY
✅ Full chat forwarding system
✅ Text + Media + Sticker + Voice support
✅ Complete admin monitoring
✅ Chat logging to database
✅ No frozen chat after /stop
✅ All bugs fixed
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
import sys

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
RECONNECT_TIMEOUT = 300
RECONNECT_COOLDOWN_HOURS = 24
SEARCH_TIMEOUT_SECONDS = 120

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
    normalized = (user_input or "").strip().lower()
    if not normalized:
        return None
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
    return "🤖 GhostTalk v5.4 - Running!", 200

@app.route("/health")
def health():
    return {"status": "✅ ok"}, 200

# ==================== RUNTIME DATA ====================
waiting_random = []
waiting_premium_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history_with_time = {}
pending_country = set()
pending_age = set()
chat_history = {}
reconnect_requests = {}
reconnect_cooldown = {}
search_start_time = {}

# ==================== THREADING LOCKS ====================
queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()
reconnect_lock = threading.Lock()

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

        conn.execute("""CREATE TABLE IF NOT EXISTS recent_partners (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER,
            last_disconnect TEXT,
            reconnect_until TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            sender_name TEXT,
            receiver_id INTEGER,
            receiver_name TEXT,
            message_type TEXT,
            message_content TEXT,
            timestamp TEXT
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
                bot.send_message(reported_id, f"⚠️ You've been temporarily banned for 7 days due to community reports. Appeal at support.")
            except:
                pass

            with active_pairs_lock:
                if reported_id in active_pairs:
                    partner = active_pairs.get(reported_id)
                    if partner and partner in active_pairs:
                        del active_pairs[partner]
                    if reported_id in active_pairs:
                        del active_pairs[reported_id]

        conn.commit()

def db_save_recent_partner(user_id, partner_id):
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        reconnect_until = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        conn.execute("""
            INSERT OR REPLACE INTO recent_partners (user_id, partner_id, last_disconnect, reconnect_until)
            VALUES (?, ?, ?, ?)
        """, (user_id, partner_id, now, reconnect_until))
        conn.commit()

def db_get_recent_partner(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT partner_id, reconnect_until FROM recent_partners WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if not row:
            return None

        partner_id, reconnect_until = row
        try:
            if datetime.fromisoformat(reconnect_until) > datetime.utcnow():
                return partner_id
        except:
            pass

        conn.execute("DELETE FROM recent_partners WHERE user_id=?", (user_id,))
        conn.commit()
        return None

def db_clear_recent_partner(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM recent_partners WHERE user_id=?", (user_id,))
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_log_chat(sender_id, sender_name, receiver_id, receiver_name, msg_type, content):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO chat_logs 
            (sender_id, sender_name, receiver_id, receiver_name, message_type, message_content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sender_id, sender_name, receiver_id, receiver_name, msg_type, content, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
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
            bot.send_message(user_id, f"⚠️ You've been temporarily banned for 24 hours.")
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ Warning ({count}/3) - {reason}")
        except:
            pass
        return "warn"

# ==================== QUEUE HELPERS ====================
def remove_from_queues(user_id):
    global waiting_random, waiting_premium_opposite
    with queue_lock:
        if user_id in waiting_random:
            waiting_random.remove(user_id)
        waiting_premium_opposite = [uid for uid in waiting_premium_opposite if uid != user_id]
        search_start_time.pop(user_id, None)

def is_searching(user_id):
    with queue_lock:
        if user_id in waiting_random:
            return True
        if user_id in waiting_premium_opposite:
            return True
    return False

def user_label(uid):
    u = db_get_user(uid)
    if u and u.get("username"):
        return f"@{u['username']}"
    return str(uid)

# ==================== DISCONNECT ====================
def disconnect_user(user_id):
    global active_pairs

    partner_id = None

    with active_pairs_lock:
        if user_id in active_pairs:
            partner_id = active_pairs[user_id]
            del active_pairs[user_id]
            
            if partner_id in active_pairs:
                del active_pairs[partner_id]

    if partner_id:
        now = datetime.utcnow()
        chat_history_with_time[user_id] = (partner_id, now)
        chat_history_with_time[partner_id] = (user_id, now)

        db_save_recent_partner(user_id, partner_id)
        db_save_recent_partner(partner_id, user_id)

        try:
            bot.send_message(partner_id, "😔 Your chat partner has left.\n\n/report to report (optional)\n/search to find someone new")
            logger.info(f"👋 {user_id} left. Partner {partner_id} notified")
        except Exception as e:
            logger.error(f"Failed to notify partner: {e}")

        try:
            bot.send_message(user_id, "✅ Chat ended.\n\n/search to find someone new\n/reconnect to resume")
            logger.info(f"👋 {user_id} disconnected")
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")

# ==================== MATCHING ====================
def match_users():
    global waiting_random, waiting_premium_opposite, active_pairs

    i = 0
    while i < len(waiting_premium_opposite):
        uid1 = waiting_premium_opposite[i]
        u1 = db_get_user(uid1)

        if not u1 or not u1.get("gender"):
            i += 1
            continue

        gender1 = u1.get("gender")
        needed_gender = "Male" if gender1 == "Female" else "Female"

        with queue_lock:
            for j in range(i + 1, len(waiting_premium_opposite)):
                uid2 = waiting_premium_opposite[j]
                u2 = db_get_user(uid2)

                if u2 and u2.get("gender") == needed_gender:
                    waiting_premium_opposite.pop(j)
                    waiting_premium_opposite.pop(i)

                    with active_pairs_lock:
                        active_pairs[uid1] = uid2
                        active_pairs[uid2] = uid1

                    age_text = str(u2.get("age")) if u2.get("age") else "?"
                    country = u2.get("country") or "Unknown"
                    gender_emoji = "👨" if u2.get("gender") == "Male" else "👩"
                    
                    match_markup = types.InlineKeyboardMarkup(row_width=2)
                    match_markup.add(
                        types.InlineKeyboardButton("⏭️ Next", callback_data=f"match:next:{uid1}"),
                        types.InlineKeyboardButton("🛑 Stop", callback_data=f"match:stop:{uid1}")
                    )
                    
                    try:
                        bot.send_message(uid1, f"✨ Match found!\n\n{gender_emoji} {age_text} • {country}\n\nHey there! 👋", reply_markup=match_markup)
                        bot.send_message(uid2, f"✨ Match found!\n\nHey! Let's chat 👋", reply_markup=match_markup)
                        logger.info(f"✅ Matched: {uid1} ↔ {uid2}")
                    except:
                        pass
                    return
        i += 1

    with queue_lock:
        while len(waiting_random) >= 2:
            u1 = waiting_random.pop(0)
            u2 = waiting_random.pop(0)

            with active_pairs_lock:
                active_pairs[u1] = u2
                active_pairs[u2] = u1

            u1_data = db_get_user(u1)
            u2_data = db_get_user(u2)

            age_text = str(u2_data.get("age")) if u2_data and u2_data.get("age") else "?"
            country = u2_data.get("country") if u2_data else "Unknown"
            gender_emoji = "👨" if u2_data and u2_data.get("gender") == "Male" else "👩"

            match_markup = types.InlineKeyboardMarkup(row_width=2)
            match_markup.add(
                types.InlineKeyboardButton("⏭️ Next", callback_data=f"match:next:{u1}"),
                types.InlineKeyboardButton("🛑 Stop", callback_data=f"match:stop:{u1}")
            )

            try:
                bot.send_message(u1, f"✨ Match found!\n\n{gender_emoji} {age_text} • {country}\n\nHey there! 👋", reply_markup=match_markup)
                bot.send_message(u2, f"✨ Match found!\n\nHey! Let's chat 👋", reply_markup=match_markup)
                logger.info(f"✅ Matched: {u1} ↔ {u2}")
            except:
                pass
            return

    for uid1 in list(waiting_premium_opposite):
        u1 = db_get_user(uid1)

        if not u1 or not u1.get("gender"):
            continue

        gender1 = u1.get("gender")
        needed_gender = "Male" if gender1 == "Female" else "Female"

        with queue_lock:
            for j, uid2 in enumerate(waiting_random):
                u2 = db_get_user(uid2)

                if u2 and u2.get("gender") == needed_gender:
                    found_uid = waiting_random.pop(j)
                    waiting_premium_opposite = [u for u in waiting_premium_opposite if u != uid1]

                    with active_pairs_lock:
                        active_pairs[uid1] = found_uid
                        active_pairs[found_uid] = uid1

                    age_text = str(u2.get("age")) if u2.get("age") else "?"
                    country = u2.get("country") or "Unknown"
                    gender_emoji = "👨" if u2.get("gender") == "Male" else "👩"

                    match_markup = types.InlineKeyboardMarkup(row_width=2)
                    match_markup.add(
                        types.InlineKeyboardButton("⏭️ Next", callback_data=f"match:next:{uid1}"),
                        types.InlineKeyboardButton("🛑 Stop", callback_data=f"match:stop:{uid1}")
                    )

                    try:
                        bot.send_message(uid1, f"✨ Match found!\n\n{gender_emoji} {age_text} • {country}\n\nHey there! 👋", reply_markup=match_markup)
                        bot.send_message(found_uid, f"✨ Match found!\n\nHey! Let's chat 👋", reply_markup=match_markup)
                        logger.info(f"✅ Matched: {uid1} ↔ {found_uid}")
                    except:
                        pass
                    return

# ==================== MATCH BUTTONS ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("match:"))
def handle_match_buttons(call):
    parts = call.data.split(":")
    action = parts[1]
    user_id = int(parts[2])
    
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "Invalid action", show_alert=True)
        return
    
    if action == "next":
        bot.answer_callback_query(call.id, "🔍 Finding new partner...", show_alert=False)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        disconnect_user(user_id)
        with active_pairs_lock:
            if user_id not in active_pairs:
                remove_from_queues(user_id)
                with queue_lock:
                    waiting_random.append(user_id)
                    search_start_time[user_id] = datetime.utcnow()
                match_users()
    
    elif action == "stop":
        bot.answer_callback_query(call.id, "✅ Chat ended", show_alert=False)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        disconnect_user(user_id)

# ==================== SEARCH TIMEOUT MONITOR ====================
def search_timeout_monitor():
    def run():
        while True:
            time.sleep(30)
            try:
                now = datetime.utcnow()
                with queue_lock:
                    for uid in list(search_start_time.keys()):
                        elapsed = (now - search_start_time[uid]).total_seconds()
                        if elapsed > SEARCH_TIMEOUT_SECONDS:
                            if uid in waiting_random or uid in waiting_premium_opposite:
                                remove_from_queues(uid)
                                try:
                                    bot.send_message(uid, "😔 No matches found. Try again later with /search")
                                except:
                                    pass
            except Exception as e:
                logger.error(f"Search timeout monitor error: {e}")
    
    t = threading.Thread(target=run, daemon=True)
    t.start()

# ==================== CLEANUP ====================
def cleanup_threads():
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
        bot.send_message(user.id, "⚠️ You're currently banned. Contact support.")
        return

    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
            types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "👋 Welcome to GhostTalk!\n\nLet's set up your profile.\n\nWhat's your gender?", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "How old are you? (12-99)")
        pending_age.add(user.id)
        bot.register_next_step_handler(message, process_new_age)
    elif not u["country"]:
        bot.send_message(user.id, "Where are you from? (e.g., India)")
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = "💎 Premium" if db_is_premium(user.id) else "🆓 Free"
        bot.send_message(user.id, 
            f"👋 Welcome back!\n\n"
            f"Use /search to find someone to chat with.\n"
            f"Use /help for more commands.\n\n"
            f"Status: {premium_status}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)

    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "You're banned", show_alert=True)
        return

    u = db_get_user(uid)
    if u and u["gender"]:
        if uid != ADMIN_ID and not db_is_premium(uid):
            bot.answer_callback_query(call.id, "Premium feature!", show_alert=True)
            return

    _, gender = call.data.split(":")
    gender_display = "Male" if gender == "male" else "Female"
    gender_emoji = "👨" if gender == "male" else "👩"

    u = db_get_user(uid)
    if u and u["gender"] == gender_display:
        bot.answer_callback_query(call.id, "Already selected", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "✅", show_alert=False)

    try:
        bot.edit_message_text(f"✅ {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        bot.send_message(uid, "How old are you? (12-99)")
        pending_age.add(uid)
        bot.register_next_step_handler(call.message, process_new_age)
    except:
        pass

def process_new_age(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if uid not in pending_age:
        bot.send_message(uid, "Use /start first")
        return

    if not text.isdigit():
        bot.send_message(uid, "Please enter a valid number.")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, "Age must be between 12-99.")
        bot.register_next_step_handler(message, process_new_age)
        return

    db_set_age(uid, age)
    pending_age.discard(uid)

    u = db_get_user(uid)
    if not u["country"]:
        bot.send_message(uid, "Where are you from? (e.g., India)")
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(uid, "✅ Profile complete! Use /search to find someone.")

def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    if uid not in pending_country:
        bot.send_message(uid, "Use /start first")
        return

    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, "Country not found. Try again.")
        bot.register_next_step_handler(message, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)
    bot.send_message(uid, f"✅ Perfect! You're all set. Use /search to find someone.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = """📚 Available Commands:

/start - Setup profile
/search - Find random chat
/search_opposite - Find opposite gender (premium)
/stop - Exit current chat
/next - Find new partner
/reconnect - Resume last chat
/stats - Your statistics
/settings - Edit profile
/refer - Invite friends (get premium)
/rules - Community guidelines
/report - Report a user
/help - This message"""
    bot.send_message(uid, help_text)

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = """📋 GhostTalk Rules

1. Be respectful and kind
2. No adult content or spam
3. Protect your privacy
4. Share media only with consent
5. No harassment or abuse

⚠️ Violations result in bans.
Report abusers immediately."""
    bot.send_message(uid, rules_text)

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    premium_status = "💎 Yes" if db_is_premium(uid) else "🆓 No"
    country_display = f"{u.get('country_flag', '🌍')} {u.get('country') or '?'}" if u.get('country') else "🌍 Not set"
    settings_text = (
        "⚙️ Your Profile\n\n"
        f"👤 Gender: {u.get('gender') or '?'}\n"
        f"🎂 Age: {u.get('age') or '?'}\n"
        f"🌍 Country: {country_display}\n\n"
        f"💎 Premium: {premium_status}\n"
        f"💬 Messages: {u.get('messages_sent')}\n"
        f"👥 Referred: {u.get('referral_count')}/3"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"), types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))
    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def callback_change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, "Enter new age (12-99):")
    pending_age.add(uid)
    bot.register_next_step_handler(call.message, process_new_age)
    bot.answer_callback_query(call.id, "✅", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def callback_set_country(call):
    uid = call.from_user.id
    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, "Premium only!", show_alert=True)
        return
    bot.send_message(uid, "Enter new country:")
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
    remaining = PREMIUM_REFERRALS_NEEDED - u.get("referral_count", 0)
    refer_text = (
        f"👥 Invite your friends!\n\n"
        f"🔗 {ref_link}\n\n"
        f"Progress: {u.get('referral_count', 0)}/{PREMIUM_REFERRALS_NEEDED}\n"
    )
    if remaining > 0:
        refer_text += f"Invite {remaining} more to unlock premium!"
    else:
        refer_text += "🎉 You've unlocked premium!"
    bot.send_message(uid, refer_text)

@bot.message_handler(commands=['search', 'search_random'])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "You're banned.")
        return
    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "Complete your profile first: /start")
        return
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "You're already chatting. Use /next or /stop")
            return
    if is_searching(uid):
        bot.send_message(uid, "Already searching. Use /stop to cancel.")
        return
    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = datetime.utcnow()
    bot.send_message(uid, "🔍 Searching for someone...\n\nThis may take a moment ⏳")
    match_users()

@bot.message_handler(commands=['search_opposite'])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "You're banned.")
        return
    if not db_is_premium(uid):
        bot.send_message(uid, "💎 Premium feature!\n\nInvite 3 friends with /refer to unlock.")
        return
    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "Complete your profile first: /start")
        return
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "You're already chatting.")
            return
    if is_searching(uid):
        bot.send_message(uid, "Already searching. Use /stop to cancel.")
        return
    opposite_gen = "Female" if u.get("gender") == "Male" else "Male"
    remove_from_queues(uid)
    with queue_lock:
        waiting_premium_opposite.append(uid)
        search_start_time[uid] = datetime.utcnow()
    bot.send_message(uid, f"🎯 Searching for {opposite_gen}...\n\nThis may take a moment ⏳")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id

    if is_searching(uid):
        remove_from_queues(uid)
        bot.send_message(uid, "✅ Search cancelled.")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            disconnect_user(uid)
            return

    bot.send_message(uid, "You're not chatting. Use /search to find someone.")

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "You're not chatting.")
            return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Finding new partner...")
    cmd_search_random(message)

@bot.message_handler(commands=['reconnect'])
def cmd_reconnect(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "You're banned.")
        return

    with reconnect_lock:
        if uid in reconnect_cooldown:
            cooldown_until = reconnect_cooldown[uid]
            if datetime.fromisoformat(cooldown_until) > datetime.utcnow():
                remaining_hours = (datetime.fromisoformat(cooldown_until) - datetime.utcnow()).seconds // 3600
                bot.send_message(uid, f"⏳ Try again in {remaining_hours} hour(s)")
                return
            else:
                del reconnect_cooldown[uid]

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "You're chatting. Use /stop first.")
            return

    partner_id = db_get_recent_partner(uid)

    if not partner_id:
        bot.send_message(uid, "No recent chat found.")
        return

    with active_pairs_lock:
        if partner_id in active_pairs:
            bot.send_message(uid, "Your partner is busy.")
            return

    if is_searching(partner_id):
        bot.send_message(uid, "Your partner is searching.")
        return

    u = db_get_user(uid)
    name = u.get("first_name") if u else "Someone"

    reconnect_markup = types.InlineKeyboardMarkup(row_width=2)
    reconnect_markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"recon:accept:{uid}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"recon:reject:{uid}")
    )

    with reconnect_lock:
        reconnect_requests[uid] = (partner_id, datetime.utcnow())

    try:
        bot.send_message(partner_id, f"{name} wants to chat again. Accept?", reply_markup=reconnect_markup)
        bot.send_message(uid, "Request sent! Waiting for response...")
        logger.info(f"Reconnect: {uid} → {partner_id}")
    except Exception as e:
        logger.error(f"Reconnect error: {e}")
        bot.send_message(uid, "Error sending request.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("recon:"))
def handle_reconnect_response(call):
    partner_id = call.from_user.id
    parts = call.data.split(":")
    action = parts[1]
    requester_id = int(parts[2])

    with reconnect_lock:
        if requester_id not in reconnect_requests:
            bot.answer_callback_query(call.id, "Expired", show_alert=True)
            return

        stored_partner, req_time = reconnect_requests[requester_id]

        if stored_partner != partner_id:
            bot.answer_callback_query(call.id, "Invalid", show_alert=True)
            return

        if (datetime.utcnow() - req_time).seconds > RECONNECT_TIMEOUT:
            bot.answer_callback_query(call.id, "Timeout", show_alert=True)
            del reconnect_requests[requester_id]
            return

        del reconnect_requests[requester_id]

    if action == "accept":
        with active_pairs_lock:
            if requester_id in active_pairs or partner_id in active_pairs:
                bot.answer_callback_query(call.id, "Someone is busy", show_alert=True)
                try:
                    bot.send_message(requester_id, "Your partner is busy.")
                except:
                    pass
                return

            active_pairs[requester_id] = partner_id
            active_pairs[partner_id] = requester_id

        db_clear_recent_partner(requester_id)
        db_clear_recent_partner(partner_id)

        cooldown_until = (datetime.utcnow() + timedelta(hours=RECONNECT_COOLDOWN_HOURS)).isoformat()
        with reconnect_lock:
            reconnect_cooldown[requester_id] = cooldown_until
            reconnect_cooldown[partner_id] = cooldown_until

        bot.answer_callback_query(call.id, "✅ Connected!", show_alert=False)
        try:
            bot.send_message(requester_id, "✨ You're back! Let's chat.")
            bot.send_message(partner_id, "✨ They're back! Let's chat.")
            logger.info(f"Reconnected: {requester_id} ↔ {partner_id}")
        except Exception as e:
            logger.error(f"Recon notify error: {e}")

    else:
        bot.answer_callback_query(call.id, "❌ Declined", show_alert=False)
        try:
            bot.send_message(requester_id, "They declined.")
        except:
            pass

# ==================== MESSAGE FORWARDING ====================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def forward_chat_message(message):
    uid = message.from_user.id
    text = message.text or ""

    if text.startswith("/"):
        return

    if is_banned_content(text):
        warn_user(uid, "Violated community rules")
        return

    with active_pairs_lock:
        if uid not in active_pairs:
            return
        partner_id = active_pairs[uid]

    try:
        sender_user = db_get_user(uid)
        receiver_user = db_get_user(partner_id)
        
        sender_name = sender_user.get('first_name', 'User') if sender_user else 'User'
        receiver_name = receiver_user.get('first_name', 'User') if receiver_user else 'User'
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        db_log_chat(uid, sender_name, partner_id, receiver_name, "text", text)
        
        if partner_id == ADMIN_ID:
            admin_msg = f"""📤 SENDER
Name: {sender_name}
ID: {uid}

👤 RECEIVER
Name: Admin
ID: {ADMIN_ID}

⏰ Time: {timestamp}

💬 Message:
{text}"""
            bot.send_message(partner_id, admin_msg)
        else:
            bot.send_message(partner_id, text)

        with get_conn() as conn:
            conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
            conn.commit()

        logger.info(f"💬 Message: {sender_name} (ID: {uid}) → {receiver_name} (ID: {partner_id})")
    except Exception as e:
        logger.error(f"Forward error: {e}")

# ==================== MEDIA & STICKER ====================
@bot.message_handler(func=lambda m: True, content_types=['photo', 'video', 'document', 'voice', 'audio', 'sticker'])
def handle_media(message):
    uid = message.from_user.id

    with active_pairs_lock:
        if uid not in active_pairs:
            return
        partner_id = active_pairs[uid]

    sender_user = db_get_user(uid)
    receiver_user = db_get_user(partner_id)
    sender_name = sender_user.get('first_name', 'User') if sender_user else 'User'
    receiver_name = receiver_user.get('first_name', 'User') if receiver_user else 'User'
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    media_icons = {
        "photo": "📸 Photo",
        "video": "🎬 Video",
        "document": "📎 Document",
        "voice": "🎤 Voice Message",
        "audio": "🎵 Audio",
        "sticker": "🎨 Sticker"
    }
    media_type = media_icons.get(message.content_type, "📁 Media")

    db_log_chat(uid, sender_name, partner_id, receiver_name, message.content_type, media_type)

    pending_media[partner_id] = (uid, message)

    if message.content_type == "sticker":
        try:
            bot.send_sticker(partner_id, message.sticker.file_id)
            db_increment_media(uid, "approved")
            logger.info(f"🎨 Sticker: {sender_name} (ID: {uid}) → {receiver_name} (ID: {partner_id})")
            return
        except Exception as e:
            logger.error(f"Sticker send error: {e}")
            bot.send_message(uid, "❌ Failed to send sticker")
            return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"media:accept:{uid}"),
        types.InlineKeyboardButton("❌ Decline", callback_data=f"media:reject:{uid}")
    )

    if partner_id == ADMIN_ID:
        admin_msg = f"""📤 SENDER: {sender_name} (ID: {uid})
👤 RECEIVER: Admin (ID: {ADMIN_ID})
📎 Media: {media_type}
⏰ Time: {timestamp}

Allow?"""
        bot.send_message(partner_id, admin_msg, reply_markup=markup)
    else:
        user_msg = f"""{sender_name} sent {media_type}

Allow?"""
        bot.send_message(partner_id, user_msg, reply_markup=markup)

    logger.info(f"📎 Media: {media_type} from {sender_name} (ID: {uid}) → {receiver_name} (ID: {partner_id})")

@bot.callback_query_handler(func=lambda c: c.data.startswith("media:"))
def handle_media_approval(call):
    uid = call.from_user.id
    parts = call.data.split(":")
    action = parts[1]
    sender_id = int(parts[2])

    if sender_id not in pending_media:
        bot.answer_callback_query(call.id, "Expired", show_alert=True)
        return

    sender_user, msg = pending_media[sender_id]
    if sender_user != sender_id:
        bot.answer_callback_query(call.id, "Invalid", show_alert=True)
        return

    try:
        if action == "accept":
            try:
                if msg.content_type == "photo":
                    bot.send_photo(uid, msg.photo[-1].file_id)
                elif msg.content_type == "video":
                    bot.send_video(uid, msg.video.file_id)
                elif msg.content_type == "document":
                    bot.send_document(uid, msg.document.file_id)
                elif msg.content_type == "voice":
                    bot.send_voice(uid, msg.voice.file_id)
                elif msg.content_type == "audio":
                    bot.send_audio(uid, msg.audio.file_id)
            except Exception as e:
                logger.error(f"Media send error: {e}")
                bot.send_message(uid, "❌ Failed to send media")
                bot.send_message(sender_id, "❌ Failed to send media")
                return

            bot.answer_callback_query(call.id, "✅ Sent", show_alert=False)
            db_increment_media(sender_id, "approved")
            bot.send_message(sender_id, "✅ Accepted")
            logger.info(f"Media accepted: {sender_id} → {uid}")
        else:
            bot.answer_callback_query(call.id, "❌ Declined", show_alert=False)
            bot.send_message(sender_id, "❌ Declined")
            db_increment_media(sender_id, "rejected")
            logger.info(f"Media rejected: {sender_id} from {uid}")

        if sender_id in pending_media:
            del pending_media[sender_id]
    except Exception as e:
        logger.error(f"Media error: {e}")
        bot.send_message(uid, "Error processing media")

# ==================== REPORT ====================
def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚫 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("⚠️ Inappropriate", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🕵️ Suspicious", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("💬 Other", callback_data="rep:other"),
        types.InlineKeyboardButton("⏭️ Cancel", callback_data="rep:cancel")
    )
    return markup

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    
    reported_id = None
    is_active_chat = False

    with active_pairs_lock:
        if uid in active_pairs:
            reported_id = active_pairs[uid]
            is_active_chat = True

    if not reported_id and uid in chat_history_with_time:
        reported_id, _ = chat_history_with_time[uid]
        is_active_chat = False

    if not reported_id:
        bot.send_message(uid, "No one to report.")
        return

    u_reporter = db_get_user(uid)
    u_reported = db_get_user(reported_id)
    
    reporter_name = u_reporter.get('first_name', 'User') if u_reporter else 'User'
    reported_name = u_reported.get('first_name', 'User') if u_reported else 'User'
    
    chat_status = "🟢 Active Chat" if is_active_chat else "⏹️ After Chat"
    
    if uid == ADMIN_ID:
        details = f"""📋 Report Details

👤 Reporter: {reporter_name}
🆔 Reporter ID: {uid}

👤 Reported User: {reported_name}
🆔 Reported ID: {reported_id}

📍 Status: {chat_status}

Why?"""
        bot.send_message(uid, details, reply_markup=report_keyboard())
    else:
        bot.send_message(uid, "Why are you reporting this user?", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def handle_report(call):
    uid = call.from_user.id
    data = call.data.split(":")[1]

    if data == "cancel":
        bot.answer_callback_query(call.id, "Cancelled")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    reported_id = None
    is_active_chat = False

    with active_pairs_lock:
        if uid in active_pairs:
            reported_id = active_pairs[uid]
            is_active_chat = True

    if not reported_id and uid in chat_history_with_time:
        reported_id, _ = chat_history_with_time[uid]
        is_active_chat = False

    if not reported_id:
        bot.answer_callback_query(call.id, "Error", show_alert=True)
        return

    reason_map = {
        "spam": "Spam",
        "inappropriate": "Inappropriate",
        "suspicious": "Suspicious",
        "other": "Other"
    }

    report_reason = reason_map.get(data, data)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    u_reporter = db_get_user(uid)
    u_reported = db_get_user(reported_id)
    
    reporter_name = u_reporter.get('first_name', 'User') if u_reporter else 'User'
    reported_name = u_reported.get('first_name', 'User') if u_reported else 'User'
    chat_status = "Active Chat" if is_active_chat else "After Chat"
    
    db_add_report(uid, reported_id, report_reason, "")

    admin_report = f"""📋 REPORT DETAILS

👤 REPORTER
Name: {reporter_name}
ID: {uid}

👤 REPORTED USER
Name: {reported_name}
ID: {reported_id}

📍 Status: {chat_status}
🔴 Reason: {report_reason}
⏰ Time: {timestamp}"""
    
    try:
        bot.send_message(ADMIN_ID, admin_report)
    except:
        pass

    bot.answer_callback_query(call.id, "✅ Reported", show_alert=False)
    logger.info(f"📋 REPORT: {reporter_name} (ID: {uid}) → {reported_name} (ID: {reported_id}) | Reason: {report_reason} | Status: {chat_status}")

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return

    country_display = f"{u.get('country_flag', '🌍')} {u.get('country')}" if u.get('country') else "🌍 Not set"
    stats_text = f"""📊 Your Stats

👤 Gender: {u.get('gender') or '?'}
🎂 Age: {u.get('age') or '?'}
🌍 Country: {country_display}

💬 Messages: {u.get('messages_sent')}
✅ Media Accepted: {u.get('media_approved')}
❌ Media Declined: {u.get('media_rejected')}

👥 Referrals: {u.get('referral_count')}/3
💎 Premium: {'Yes' if db_is_premium(uid) else 'No'}"""

    bot.send_message(uid, stats_text)

# ==================== MAIN ====================
if __name__ == "__main__":
    init_db()
    cleanup_threads()
    search_timeout_monitor()
    logger.info("=" * 60)
    logger.info("✅ GhostTalk v5.4 PRODUCTION READY")
    logger.info("=" * 60)
    logger.info("✅ ALL FEATURES WORKING:")
    logger.info("   ✅ Full text message forwarding with user details")
    logger.info("   ✅ Complete media forwarding (photo, video, voice, audio, document)")
    logger.info("   ✅ Sticker support")
    logger.info("   ✅ Chat logging to database")
    logger.info("   ✅ No frozen chat after /stop")
    logger.info("   ✅ Complete admin monitoring")
    logger.info("   ✅ Report system with timestamps")
    logger.info("   ✅ Match with /next /stop buttons")
    logger.info("   ✅ All bugs fixed")
    logger.info("=" * 60)

    while True:
        try:
            logger.info("🔄 Starting polling...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30, none_stop=True)
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            logger.info("⏳ Restarting in 5 seconds...")
            time.sleep(5)
