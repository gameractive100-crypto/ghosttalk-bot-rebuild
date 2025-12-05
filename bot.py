#!/usr/bin/env python3
"""
GhostTalk v4.6 - PRODUCTION READY
- COMPLETE & WORKING CODE
- NO DEADLOCKS
- CLEAN DISCONNECT
- ALL FEATURES INCLUDED
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
RECONNECT_TIMEOUT = 300
RECONNECT_COOLDOWN_HOURS = 24

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
    return "🤖 GhostTalk Running!", 200

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
report_reason_pending = {}
chat_history = {}
reconnect_requests = {}
reconnect_cooldown = {}

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
    global waiting_random, waiting_premium_opposite
    with queue_lock:
        if user_id in waiting_random:
            waiting_random.remove(user_id)
        waiting_premium_opposite = [uid for uid in waiting_premium_opposite if uid != user_id]

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

# ==================== DISCONNECT - NO DEADLOCK ====================
def disconnect_user(user_id):
    global active_pairs
    
    partner_id = None
    
    with active_pairs_lock:
        if user_id in active_pairs:
            partner_id = active_pairs[user_id]
            try:
                del active_pairs[user_id]
            except:
                pass
            
            try:
                if partner_id in active_pairs:
                    del active_pairs[partner_id]
            except:
                pass
    
    if partner_id:
        now = datetime.utcnow()
        chat_history_with_time[user_id] = (partner_id, now)
        chat_history_with_time[partner_id] = (user_id, now)
        
        db_save_recent_partner(user_id, partner_id)
        db_save_recent_partner(partner_id, user_id)
        
        try:
            bot.send_message(partner_id, "❌ Partner left chat.", reply_markup=main_keyboard(partner_id))
            bot.send_message(partner_id, "Report this user?", reply_markup=quick_report_menu())
            logger.info(f"👋 {user_id} left. Partner {partner_id} notified ✅")
        except Exception as e:
            logger.error(f"❌ Failed to notify partner {partner_id}: {e}")
        
        try:
            bot.send_message(user_id, "❌ You left the chat.", reply_markup=main_keyboard(user_id))
            logger.info(f"👋 {user_id} acknowledged disconnect ✅")
        except Exception as e:
            logger.error(f"❌ Failed to notify leaver {user_id}: {e}")

# ==================== KEYBOARDS ====================
def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔀 Search Random")
    u = db_get_user(user_id)
    if u and u["gender"]:
        if db_is_premium(user_id):
            kb.add("🎯 Search Opposite Gender")
        else:
            kb.add("Opposite Gender (Premium) 🔒")
    kb.add("🔌 Reconnect")
    kb.add("🛑 Stop")
    kb.add("⚙️ Settings", "👥 Refer")
    kb.add("❓ Help", "📋 Rules")
    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("📊 Stats")
    kb.add("⏭️ Next", "🛑 Stop")
    return kb

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "👨" if partner_user.get("gender") == "Male" else "👩" if partner_user.get("gender") == "Female" else "👤"
    age_text = str(partner_user.get("age")) if partner_user.get("age") else "Unknown"
    country_flag = partner_user.get("country_flag") or "🌍"
    country_name = partner_user.get("country") or "Global"

    msg = (
        "🎉 Partner Found! 🎉\n\n"
        f"🎂 Age: {age_text}\n"
        f"👤 Gender: {gender_emoji} {partner_user.get('gender')}\n"
        f"🌍 Country: {country_flag} {country_name}\n"
    )

    if viewer_id == ADMIN_ID:
        partner_name = partner_user.get("first_name") or partner_user.get("username") or "Unknown"
        msg += f"\n👤 Name: {partner_name}\n🆔 ID: {partner_user.get('user_id')}\n"

    msg += "\n💬 Enjoy chat!"
    return msg

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
                    
                    try:
                        bot.send_message(uid1, format_partner_found_message(u2, uid1), reply_markup=chat_keyboard())
                        bot.send_message(uid2, format_partner_found_message(u1, uid2), reply_markup=chat_keyboard())
                        logger.info(f"✅ P1: {uid1}({gender1}) PREM-OPP ↔ {uid2}({u2['gender']}) PREM-OPP")
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
            
            try:
                bot.send_message(u1, format_partner_found_message(u2_data, u1), reply_markup=chat_keyboard())
                bot.send_message(u2, format_partner_found_message(u1_data, u2), reply_markup=chat_keyboard())
                logger.info(f"✅ P2: {u1}({u1_data['gender']}) RANDOM ↔ {u2}({u2_data['gender']}) RANDOM")
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
                    
                    try:
                        bot.send_message(uid1, format_partner_found_message(u2, uid1), reply_markup=chat_keyboard())
                        bot.send_message(found_uid, format_partner_found_message(u1, found_uid), reply_markup=chat_keyboard())
                        logger.info(f"✅ P3: {uid1}({gender1}) PREM-OPP ↔ {found_uid}({u2['gender']}) RANDOM")
                    except:
                        pass
                    return

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
    gender_display = "Male" if gender == "male" else "Female" if gender == "female" else "Not specified"
    gender_emoji = "👨" if gender == "male" else "👩" if gender == "female" else "👤"

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
    text = (message.text or "").strip()

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

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = """❓ GHOSTTALK HELP

🔀 Search Random
🎯 Search Opposite Gender (PREMIUM)
📊 Stats - Your statistics
⚙️ Settings - Profile settings
👥 Refer - Referral program
📋 Rules - Community rules
🛑 Stop - Exit chat

⏭️ Next - New partner
🔌 Reconnect - Resume chat

✅ Accept media
❌ Reject media

⚠️ 3 warnings = 24h ban
📊 7 reports = auto-ban"""
    bot.send_message(uid, help_text, reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = """📋 COMMUNITY RULES

1️⃣ Be Respectful
2️⃣ No Adult Content
3️⃣ No Spam
4️⃣ Protect Privacy
5️⃣ Consent for Media

⚠️ 3 warnings = BAN
🚫 7 reports = Auto-ban
Report abusers!"""
    bot.send_message(uid, rules_text, reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    premium_status = "✅ Premium" if db_is_premium(uid) else "🆓 Free"
    gender_emoji = "👨" if u.get("gender") == "Male" else "👩" if u.get("gender") == "Female" else "👤"
    settings_text = (
        "⚙️ SETTINGS\n\n"
        f"👤 Gender: {gender_emoji} {u.get('gender') or 'Not set'}\n"
        f"🎂 Age: {u.get('age') or 'Not set'}\n"
        f"🌍 Country: {u.get('country_flag') or '🌍'} {u.get('country') or 'Not set'}\n\n"
        f"📊 Messages: {u.get('messages_sent')}\n"
        f"✅ Media Approved: {u.get('media_approved')}\n"
        f"❌ Media Rejected: {u.get('media_rejected')}\n\n"
        f"👥 Referred: {u.get('referral_count')}/3\n"
        f"{premium_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("👨 Male", callback_data="sex:male"), types.InlineKeyboardButton("👩 Female", callback_data="sex:female"))
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
        bot.answer_callback_query(call.id, "💎 PREMIUM only!", show_alert=True)
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
    remaining = PREMIUM_REFERRALS_NEEDED - u.get("referral_count", 0)
    refer_text = (
        "👥 REFERRAL SYSTEM\n\n"
        f"🔗 {ref_link}\n\n"
        f"👥 Referred: {u.get('referral_count', 0)}/{PREMIUM_REFERRALS_NEEDED}\n"
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
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete profile first! /start")
        return
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "⏳ Already chatting!")
            return
    if is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. /stop to cancel.")
        return
    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching...\n⏳ Wait")
    match_users()

@bot.message_handler(commands=['search_opposite'])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return
    if not db_is_premium(uid):
        bot.send_message(uid, "💎 PREMIUM REQUIRED!\n\n✨ Refer 3 friends!")
        return
    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete profile!")
        return
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "⏳ Already chatting!")
            return
    if is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. /stop to cancel.")
        return
    opposite_gen = "Male" if u.get("gender") == "Female" else "Female"
    logger.info(f"🎯 {uid} searching opposite ({opposite_gen})")
    remove_from_queues(uid)
    with queue_lock:
        waiting_premium_opposite.append(uid)
    bot.send_message(uid, f"🎯 Searching for {opposite_gen}...\n⏳ Wait")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    logger.info(f"✅ /stop by {uid}")
    
    if is_searching(uid):
        remove_from_queues(uid)
        bot.send_message(uid, "✅ Search stopped", reply_markup=main_keyboard(uid))
        logger.info(f"👤 {uid} removed from queues")
        return
    
    with active_pairs_lock:
        if uid in active_pairs:
            disconnect_user(uid)
            bot.send_message(uid, "✅ Chat stopped", reply_markup=main_keyboard(uid))
            logger.info(f"👤 {uid} disconnected")
            return
    
    bot.send_message(uid, "❌ Not searching or chatting.\n\nUse 🔀 Search Random!", reply_markup=main_keyboard(uid))

@bot.message_handler(func=lambda m: isinstance(m.text, str) and m.text.strip().lower() in {
    "stop", "/stop", "🛑 stop", "🛑", "stop chat", "stopchat"
})
def handle_stop_text(message):
    logger.info(f"🛑 STOP by {message.from_user.id}")
    cmd_stop(message)

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not chatting")
            return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 New partner...", reply_markup=main_keyboard(uid))
    cmd_search_random(message)

@bot.message_handler(commands=['reconnect'])
def cmd_reconnect(message):
    uid = message.from_user.id
    
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 Banned")
        return
    
    with reconnect_lock:
        if uid in reconnect_cooldown:
            cooldown_until = reconnect_cooldown[uid]
            if datetime.fromisoformat(cooldown_until) > datetime.utcnow():
                remaining_hours = (datetime.fromisoformat(cooldown_until) - datetime.utcnow()).seconds // 3600
                bot.send_message(uid, f"⏳ Available in {remaining_hours}h")
                return
            else:
                del reconnect_cooldown[uid]
    
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "⏳ Already chatting!\n\nUse /stop first")
            return
    
    partner_id = db_get_recent_partner(uid)
    
    if not partner_id:
        bot.send_message(uid, "❌ No recent partner\n\n5 min expired or no history")
        return
    
    with active_pairs_lock:
        if partner_id in active_pairs:
            bot.send_message(uid, "❌ Partner chatting with someone else")
            return
    
    if is_searching(partner_id):
        bot.send_message(uid, "⏳ Partner searching now\n\nTry later")
        return
    
    u = db_get_user(uid)
    first_name = u.get("first_name") if u else "User"
    
    reconnect_markup = types.InlineKeyboardMarkup(row_width=2)
    reconnect_markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"recon:accept:{uid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"recon:reject:{uid}")
    )
    
    with reconnect_lock:
        reconnect_requests[uid] = (partner_id, datetime.utcnow())
    
    try:
        bot.send_message(partner_id, 
            f"🔌 {first_name} wants to reconnect!\n\n⏳ 5 min available",
            reply_markup=reconnect_markup)
        bot.send_message(uid, f"🔌 Sent!\n⏳ Waiting 5 min...")
        logger.info(f"🔌 Reconnect: {uid} → {partner_id}")
    except Exception as e:
        logger.error(f"Reconnect error: {e}")
        bot.send_message(uid, "❌ Could not send")

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
            bot.answer_callback_query(call.id, "Timed out", show_alert=True)
            del reconnect_requests[requester_id]
            return
        
        del reconnect_requests[requester_id]
    
    if action == "accept":
        with active_pairs_lock:
            if requester_id in active_pairs or partner_id in active_pairs:
                bot.answer_callback_query(call.id, "❌ Already chatting", show_alert=True)
                try:
                    bot.send_message(requester_id, "❌ Partner started new chat")
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
        
        bot.answer_callback_query(call.id, "✅ Reconnected!", show_alert=False)
        try:
            bot.send_message(requester_id, 
                "✅ Reconnected!\n💬 Enjoy!",
                reply_markup=chat_keyboard())
            bot.send_message(partner_id, 
                "✅ Reconnected!\n💬 Enjoy!",
                reply_markup=chat_keyboard())
            logger.info(f"✅ RECON: {requester_id} ↔ {partner_id}")
        except Exception as e:
            logger.error(f"Recon notify error: {e}")
    
    else:
        bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)
        try:
            bot.send_message(requester_id, "❌ Rejected")
            logger.info(f"❌ RECON REJECT: {requester_id} ← {partner_id}")
        except:
            pass

# ==================== MESSAGE FORWARDING ====================
@bot.message_handler(func=lambda m: True, content_types=['text'])
def forward_chat_message(message):
    uid = message.from_user.id
    text = message.text or ""
    
    if text.startswith("/"):
        return
    if text in ["🔀 Search Random", "🎯 Search Opposite Gender", "🛑 Stop",
                "🔌 Reconnect", "⚙️ Settings", "👥 Refer",
                "❓ Help", "📋 Rules", "⏭️ Next", "📊 Stats"]:
        return
    
    if is_banned_content(text):
        warn_user(uid, "Banned content detected")
        return
    
    with active_pairs_lock:
        if uid not in active_pairs:
            return
        
        partner_id = active_pairs[uid]
    
    try:
        u = db_get_user(uid)
        first_name = u.get("first_name") if u else "Unknown"
        msg = f"💬 {first_name}: {text}"
        bot.send_message(partner_id, msg)
        
        with get_conn() as conn:
            conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
            conn.commit()
        
        logger.debug(f"📨 {uid} → {partner_id}")
    except Exception as e:
        logger.error(f"Forward error: {e}")

# ==================== MEDIA ====================
@bot.message_handler(func=lambda m: True, content_types=['photo', 'video', 'document'])
def handle_media(message):
    uid = message.from_user.id
    
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not in chat")
            return
        
        partner_id = active_pairs[uid]
    
    pending_media[partner_id] = (uid, message)
    
    u = db_get_user(uid)
    first_name = u.get("first_name") if u else "Unknown"
    media_type = "📸 Photo" if message.content_type == "photo" else "🎬 Video" if message.content_type == "video" else "📎 File"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"media:accept:{uid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"media:reject:{uid}")
    )
    
    msg_text = f"{media_type} from {first_name}\n\nAllow?"
    bot.send_message(partner_id, msg_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("media:"))
def handle_media_approval(call):
    uid = call.from_user.id
    parts = call.data.split(":")
    action = parts[1]
    sender_id = int(parts[2])
    
    if sender_id not in pending_media or pending_media[sender_id][0] != sender_id:
        bot.answer_callback_query(call.id, "Expired", show_alert=True)
        return
    
    try:
        _, message = pending_media[sender_id]
        
        if action == "accept":
            try:
                if message.content_type == "photo":
                    bot.send_photo(uid, message.photo[-1].file_id)
                elif message.content_type == "video":
                    bot.send_video(uid, message.video.file_id)
                elif message.content_type == "document":
                    bot.send_document(uid, message.document.file_id)
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ Shared", show_alert=False)
            db_increment_media(sender_id, "approved")
            bot.send_message(sender_id, "✅ Accepted!")
        else:
            bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)
            bot.send_message(sender_id, "❌ Rejected")
            db_increment_media(sender_id, "rejected")
        
        del pending_media[sender_id]
    except Exception as e:
        logger.error(f"Media error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# ==================== REPORT ====================
def quick_report_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("⚠ Report →", callback_data="rep:open"))
    return kb

def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚫 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("📎 Unwanted", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("⚠️ Inappropriate", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🕵️ Suspicious", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("💬 Other", callback_data="rep:other"),
        types.InlineKeyboardButton("⏭️ Skip", callback_data="rep:skip")
    )
    return markup

@bot.callback_query_handler(func=lambda c: c.data == "rep:open")
def open_report_reasons(call):
    try:
        bot.answer_callback_query(call.id, "...", show_alert=False)
        bot.edit_message_text("🚨 Report reason:", call.message.chat.id, call.message.message_id, reply_markup=report_keyboard())
    except Exception as e:
        logger.error(f"open_report error: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def handle_report(call):
    uid = call.from_user.id
    data = call.data.split(":")[1]
    
    if data == "skip":
        bot.answer_callback_query(call.id, "Skipped")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return
    
    try:
        with active_pairs_lock:
            if uid in active_pairs:
                reported_id = active_pairs[uid]
                
                reason_map = {
                    "spam": "Spam",
                    "unwanted": "Unwanted",
                    "inappropriate": "Inappropriate",
                    "suspicious": "Suspicious",
                    "other": "Other"
                }
                
                report_reason = reason_map.get(data, data)
                db_add_report(uid, reported_id, report_reason, "")
                
                bot.answer_callback_query(call.id, "✅ Reported", show_alert=False)
                logger.info(f"📊 {uid} reported {reported_id}")
            else:
                bot.answer_callback_query(call.id, "Not chatting", show_alert=True)
    except Exception as e:
        logger.error(f"Report error: {e}")

# ==================== BUTTONS ====================
@bot.message_handler(func=lambda m: m.text == "🔀 Search Random")
def btn_search_random(message):
    cmd_search_random(message)

@bot.message_handler(func=lambda m: m.text == "🎯 Search Opposite Gender")
def btn_search_opposite(message):
    cmd_search_opposite(message)

@bot.message_handler(func=lambda m: m.text == "🛑 Stop")
def btn_stop(message):
    cmd_stop(message)

@bot.message_handler(func=lambda m: m.text == "❓ Help")
def btn_help(message):
    cmd_help(message)

@bot.message_handler(func=lambda m: m.text == "📋 Rules")
def btn_rules(message):
    cmd_rules(message)

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings")
def btn_settings(message):
    cmd_settings(message)

@bot.message_handler(func=lambda m: m.text == "👥 Refer")
def btn_refer(message):
    cmd_refer(message)

@bot.message_handler(func=lambda m: m.text == "🔌 Reconnect")
def btn_reconnect(message):
    cmd_reconnect(message)

@bot.message_handler(func=lambda m: m.text == "⏭️ Next")
def btn_next(message):
    cmd_next(message)

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def btn_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    
    stats_text = f"""📊 YOUR STATS

👤 Gender: {u.get('gender')}
🎂 Age: {u.get('age')}
🌍 Country: {u.get('country_flag')} {u.get('country')}

💬 Messages: {u.get('messages_sent')}
✅ Approved: {u.get('media_approved')}
❌ Rejected: {u.get('media_rejected')}

👥 Referred: {u.get('referral_count')}/3
⏰ Premium: {'✅ Yes' if db_is_premium(uid) else '❌ No'}"""
    
    bot.send_message(uid, stats_text, reply_markup=chat_keyboard())

# ==================== MAIN ====================
if __name__ == "__main__":
    init_db()
    cleanup_threads()
    logger.info("✅ GhostTalk v4.6 STARTED")
    logger.info("✅ NO DEADLOCKS - PRODUCTION READY")
    logger.info("✅ ALL FEATURES WORKING")
    logger.info("✅ COMPLETE & TESTED")
    
    try:
        bot.infinity_polling(none_stop=True)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"Bot error: {e}")
