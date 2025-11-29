#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FINAL PRODUCTION v5.0
All requests included:
- Gender Lock REMOVED (Flexible for everyone)
- Render Port Fix (Uses os.getenv("PORT"))
- Report lock-on (chat frozen during report)
- Auto-ban on 10 reports threshold
- Reporter notifications (timestamp only, no identity)
- Independent settings changes
- /help command
- Proper syntax & formatting
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
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))

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
logger.info(f"BASE_DIR: {BASEDIR}")
logger.info(f"DB_PATH: {DB_PATH}")

# ============================================
# TELEBOT & FLASK SETUP
# ============================================

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Text fix for Telegram display
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
report_reason_pending = {}
pending_country = set()

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
# COUNTRIES & ALIASES
# ============================================

COUNTRIES = [
    "afghanistan", "albania", "algeria", "andorra", "angola", "antigua and barbuda",
    "argentina", "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
    "bangladesh", "barbados", "belarus", "belgium", "belize", "benin", "bhutan", "bolivia",
    "bosnia and herzegovina", "botswana", "brazil", "brunei", "bulgaria", "burkina faso",
    "burundi", "cambodia", "cameroon", "canada", "cape verde", "central african republic",
    "chad", "chile", "china", "colombia", "comoros", "congo", "costa rica", "croatia",
    "cuba", "cyprus", "czech republic", "denmark", "djibouti", "dominica", "dominican republic",
    "ecuador", "egypt", "el salvador", "equatorial guinea", "eritrea", "estonia", "eswatini",
    "ethiopia", "fiji", "finland", "france", "gabon", "gambia", "georgia", "germany",
    "ghana", "greece", "grenada", "guatemala", "guinea", "guinea-bissau", "guyana", "haiti",
    "honduras", "hungary", "iceland", "india", "indonesia", "iran", "iraq", "ireland",
    "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya", "kiribati",
    "korea north", "korea south", "kuwait", "kyrgyzstan", "laos", "latvia", "lebanon",
    "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg", "madagascar",
    "malawi", "malaysia", "maldives", "mali", "malta", "marshall islands", "mauritania",
    "mauritius", "mexico", "micronesia", "moldova", "monaco", "mongolia", "montenegro",
    "morocco", "mozambique", "myanmar", "namibia", "nauru", "nepal", "netherlands",
    "new zealand", "nicaragua", "niger", "nigeria", "north macedonia", "norway", "oman",
    "pakistan", "palau", "palestine", "panama", "papua new guinea", "paraguay", "peru",
    "philippines", "poland", "portugal", "qatar", "romania", "russia", "rwanda",
    "saint kitts and nevis", "saint lucia", "saint vincent and the grenadines", "samoa",
    "san marino", "sao tome and principe", "saudi arabia", "senegal", "serbia", "seychelles",
    "sierra leone", "singapore", "slovakia", "slovenia", "solomon islands", "somalia",
    "south africa", "south sudan", "spain", "sri lanka", "sudan", "suriname", "sweden",
    "switzerland", "syria", "taiwan", "tajikistan", "tanzania", "thailand", "timor-leste",
    "togo", "tonga", "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
    "uganda", "ukraine", "united arab emirates", "united kingdom", "united states", "uruguay",
    "uzbekistan", "vanuatu", "vatican city", "venezuela", "vietnam", "yemen", "zambia",
    "zimbabwe"
]

COUNTRY_FLAGS = {
    "afghanistan": "🇦🇫", "albania": "🇦🇱", "algeria": "🇩🇿", "andorra": "🇦🇩", "angola": "🇦🇴",
    "antigua and barbuda": "🇦🇬", "argentina": "🇦🇷", "armenia": "🇦🇲", "australia": "🇦🇺",
    "austria": "🇦🇹", "azerbaijan": "🇦🇿", "bahamas": "🇧🇸", "bahrain": "🇧🇭",
    "bangladesh": "🇧🇩", "barbados": "🇧🇧", "belarus": "🇧🇾", "belgium": "🇧🇪",
    "belize": "🇧🇿", "benin": "🇧🇯", "bhutan": "🇧🇹", "bolivia": "🇧🇴",
    "bosnia and herzegovina": "🇧🇦", "botswana": "🇧🇼", "brazil": "🇧🇷", "brunei": "🇧🇳",
    "bulgaria": "🇧🇬", "burkina faso": "🇧🇫", "burundi": "🇧🇮", "cambodia": "🇰🇭",
    "cameroon": "🇨🇲", "canada": "🇨🇦", "cape verde": "🇨🇻", "central african republic": "🇨🇫",
    "chad": "🇹🇩", "chile": "🇨🇱", "china": "🇨🇳", "colombia": "🇨🇴", "comoros": "🇰🇲",
    "congo": "🇨🇬", "costa rica": "🇨🇷", "croatia": "🇭🇷", "cuba": "🇨🇺", "cyprus": "🇨🇾",
    "czech republic": "🇨🇿", "denmark": "🇩🇰", "djibouti": "🇩🇯", "dominica": "🇩🇲",
    "dominican republic": "🇩🇴", "ecuador": "🇪🇨", "egypt": "🇪🇬", "el salvador": "🇸🇻",
    "equatorial guinea": "🇬🇶", "eritrea": "🇪🇷", "estonia": "🇪🇪", "eswatini": "🇸🇿",
    "ethiopia": "🇪🇹", "fiji": "🇫🇯", "finland": "🇫🇮", "france": "🇫🇷", "gabon": "🇬🇦",
    "gambia": "🇬🇲", "georgia": "🇬🇪", "germany": "🇩🇪", "ghana": "🇬🇭", "greece": "🇬🇷",
    "grenada": "🇬🇩", "guatemala": "🇬🇹", "guinea": "🇬🇳", "guinea-bissau": "🇬🇼",
    "guyana": "🇬🇾", "haiti": "🇭🇹", "honduras": "🇭🇳", "hungary": "🇭🇺", "iceland": "🇮🇸",
    "india": "🇮🇳", "indonesia": "🇮🇩", "iran": "🇮🇷", "iraq": "🇮🇶", "ireland": "🇮🇪",
    "israel": "🇮🇱", "italy": "🇮🇹", "jamaica": "🇯🇲", "japan": "🇯🇵", "jordan": "🇯🇴",
    "kazakhstan": "🇰🇿", "kenya": "🇰🇪", "kiribati": "🇰🇮", "korea north": "🇰🇵",
    "korea south": "🇰🇷", "kuwait": "🇰🇼", "kyrgyzstan": "🇰🇬", "laos": "🇱🇦",
    "latvia": "🇱🇻", "lebanon": "🇱🇧", "lesotho": "🇱🇸", "liberia": "🇱🇷", "libya": "🇱🇾",
    "liechtenstein": "🇱🇮", "lithuania": "🇱🇹", "luxembourg": "🇱🇺", "madagascar": "🇲🇬",
    "malawi": "🇲🇼", "malaysia": "🇲🇾", "maldives": "🇲🇻", "mali": "🇲🇱", "malta": "🇲🇹",
    "marshall islands": "🇲🇭", "mauritania": "🇲🇷", "mauritius": "🇲🇺", "mexico": "🇲🇽",
    "micronesia": "🇫🇲", "moldova": "🇲🇩", "monaco": "🇲🇨", "mongolia": "🇲🇳",
    "montenegro": "🇲🇪", "morocco": "🇲🇦", "mozambique": "🇲🇿", "myanmar": "🇲🇲",
    "namibia": "🇳🇦", "nauru": "🇳🇷", "nepal": "🇳🇵", "netherlands": "🇳🇱",
    "new zealand": "🇳🇿", "nicaragua": "🇳🇮", "niger": "🇳🇪", "nigeria": "🇳🇬",
    "north macedonia": "🇲🇰", "norway": "🇳🇴", "oman": "🇴🇲", "pakistan": "🇵🇰",
    "palau": "🇵🇼", "palestine": "🇵🇸", "panama": "🇵🇦", "papua new guinea": "🇵🇬",
    "paraguay": "🇵🇾", "peru": "🇵🇪", "philippines": "🇵🇭", "poland": "🇵🇱",
    "portugal": "🇵🇹", "qatar": "🇶🇦", "romania": "🇷🇴", "russia": "🇷🇺", "rwanda": "🇷🇼",
    "saint kitts and nevis": "🇰🇳", "saint lucia": "🇱🇨",
    "saint vincent and the grenadines": "🇻🇨", "samoa": "🇼🇸", "san marino": "🇸🇲",
    "sao tome and principe": "🇸🇹", "saudi arabia": "🇸🇦", "senegal": "🇸🇳", "serbia": "🇷🇸",
    "seychelles": "🇸🇨", "sierra leone": "🇸🇱", "singapore": "🇸🇬", "slovakia": "🇸🇰",
    "slovenia": "🇸🇮", "solomon islands": "🇸🇧", "somalia": "🇸🇴", "south africa": "🇿🇦",
    "south sudan": "🇸🇸", "spain": "🇪🇸", "sri lanka": "🇱🇰", "sudan": "🇸🇩",
    "suriname": "🇸🇷", "sweden": "🇸🇪", "switzerland": "🇨🇭", "syria": "🇸🇾",
    "taiwan": "🇹🇼", "tajikistan": "🇹🇯", "tanzania": "🇹🇿", "thailand": "🇹🇭",
    "timor-leste": "🇹🇱", "togo": "🇹🇬", "tonga": "🇹🇴", "trinidad and tobago": "🇹🇹",
    "tunisia": "🇹🇳", "turkey": "🇹🇷", "turkmenistan": "🇹🇲", "tuvalu": "🇹🇻",
    "uganda": "🇺🇬", "ukraine": "🇺🇦", "united arab emirates": "🇦🇪",
    "united kingdom": "🇬🇧", "united states": "🇺🇸", "uruguay": "🇺🇾",
    "uzbekistan": "🇺🇿", "vanuatu": "🇻🇺", "vatican city": "🇻🇦", "venezuela": "🇻🇪",
    "vietnam": "🇻🇳", "yemen": "🇾🇪", "zambia": "🇿🇲", "zimbabwe": "🇿🇼"
}

COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "america": "united states",
    "uk": "united kingdom", "britain": "united kingdom", "uae": "united arab emirates",
    "south korea": "korea south", "north korea": "korea north", "czechia": "czech republic"
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

        u = db_get_user(user_id)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.now(timezone.utc) + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            conn.execute(
                "UPDATE users SET premium_until = ?, referral_count = 0 WHERE user_id = ?",
                (premium_until, user_id)
            )
            conn.commit()

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

        # Check if 10+ reports
        count = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE reported_id = ?",
            (reported_id,)
        ).fetchone()[0]

        conn.commit()

        # AUTO-BAN ON 10 REPORTS
        if count >= 10 and not db_is_banned(reported_id):
            db_ban_user(reported_id, hours=168, permanent=False, reason="Auto-banned: 10+ reports")

            # Notify all reporters (timestamp only, no identity)
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

    # Try numeric ID first
    try:
        uid = int(identifier)
        return uid
    except:
        pass

    # Try username
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

def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔀 Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("🚫 Unwanted Content", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("😠 Inappropriate Messages", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("🤔 Suspicious Activity", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep:other")
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

    # Try to match opposite gender first
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

    # Match random pairs
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
        bot.send_message(user.id, "🌐 Welcome to FenLix - Anonymous Chat Platform!\n\n👋 Select your gender to get started:", reply_markup=markup)
        bot.register_next_step_handler(message, lambda m: None)
    elif not u["age"]:
        bot.send_message(user.id, "📅 Enter your age (12-99 only):")
        bot.register_next_step_handler(message, process_new_age)
    elif not u["country"]:
        bot.send_message(user.id, "🌍 Enter your country name (e.g., India)\n\n⚠️ Country CANNOT be changed later unless PREMIUM!")
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

    # ✅ FLEXIBLE GENDER: No Lock!
    # Log change if already set
    if u and u["gender"] and u["gender"] != gender_display:
        try:
            bot.send_message(ADMIN_ID, f"🔄 Gender Change: {user_label(uid)} | {u['gender']} -> {gender_display}")
        except:
            pass

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, f"✅ Gender set: {gender_display}!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender updated to: {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    u = db_get_user(uid)
    if not u or not u.get("age"):
        try:
            bot.send_message(uid, "📅 Enter your age (12-99 only):")
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
            f"🌍 Enter your country name (e.g., India)\n"
            f"⚠️ Country CANNOT be changed later unless PREMIUM!"
        )
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(
            uid,
            f"✅ Age updated to {age}!\n\n"
            f"Use /settings to change something else.",
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
        bot.send_message(uid, f"'{text}' not valid. Try again (e.g., India)")
        bot.register_next_step_handler(message, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)

    bot.send_message(
        uid,
        f"✅ Country updated to {country_flag} {country_name}!\n\n"
        f"Profile complete! Ready to chat?",
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
        f"⚙️ SETTINGS PROFILE\n\n"
        f"{gender_emoji} Gender: {u['gender'] or 'Not set'}\n"
        f"📅 Age: {u['age'] or 'Not set'}\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\n\n"
        f"📊 STATS\n"
        f"💬 Messages Sent: {u['messages_sent']}\n"
        f"📸 Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n"
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n\n"
        f"🎁 {premium_status}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Refer Link", callback_data="ref:link"),
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
    bot.send_message(uid, "🌍 Enter your new country name (e.g., India):")
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
        f"🔗 Your Referral Link:\n{ref_link}\n\n"
        f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"🏆 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n"
        f"♀️ Unlock opposite gender search!\n\n"
    )

    if remaining > 0:
        refer_text += f"📢 Invite {remaining} more friends to unlock premium!"
    else:
        refer_text += "🎉 Premium unlocked! Keep inviting for more!"

    refer_text += "\n\n📖 How it works:\n1️⃣ Share your link with friends\n2️⃣ They join with your link\n3️⃣ Get premium after 3 referrals!"

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

        ref_link = db_get_referral_link(uid)
        remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]

        refer_text = (
            f"🎁 REFERRAL SYSTEM\n\n"
            f"🔗 Your Referral Link:\n{ref_link}\n\n"
            f"👥 People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
            f"🏆 Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n\n"
        )

        if remaining > 0:
            refer_text += f"📢 Invite {remaining} more friends to unlock premium!"
        else:
            refer_text += "🎉 Premium unlocked! Keep inviting for more!"

        bot.send_message(uid, refer_text)
        bot.answer_callback_query(call.id)

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile first! Use /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "Already in chat! Use /next for new partner.")
        return

    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)

    if in_waiting_random or in_waiting_opposite:
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
        premium_required_msg = (
            f"💎 PREMIUM REQUIRED!\n\n"
            f"Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock {PREMIUM_DURATION_HOURS} hour premium.\n"
            f"Use /refer to get your link!"
        )
        bot.send_message(uid, premium_required_msg)
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile first! Use /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "Already in chat! Use /next for new partner.")
        return

    in_waiting_random = uid in waiting_random
    in_waiting_opposite = any(uid == w[0] for w in waiting_opposite)

    if in_waiting_random or in_waiting_opposite:
        bot.send_message(uid, "You're already in the queue. /stop to cancel anytime.")
        return

    remove_from_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "🔍 Searching for opposite gender partner... Please wait...")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    bot.send_message(
        uid,
        "✅ Search/chat stopped. Use main menu to start again.",
        reply_markup=main_keyboard(uid)
    )

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

@bot.message_handler(commands=["report"])
def cmd_report(message):
    uid = message.from_user.id

    if uid not in active_pairs:
        bot.send_message(
            uid,
            "⚠️ You are not in an active chat.\n\n"
            "You can only report while chatting with someone."
        )
        return

    bot.send_message(uid, "Select reason for report:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id

    if uid not in active_pairs:
        bot.answer_callback_query(call.id, "Partner not connected or changed.", show_alert=True)
        return

    partner_id = active_pairs.get(uid)
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
        report_reason_pending[uid] = partner_id
        bot.answer_callback_query(call.id, "Please type the reason for reporting (short).", show_alert=True)
        bot.send_message(uid, "❓ Why are you reporting this partner? Please type a short reason (required).")
        return

    # 🔒 LOCK CHAT DURING REPORT
    report_reason_pending[uid] = partner_id
    db_add_report(uid, partner_id, report_type_name, "")
    forward_full_chat_to_admin(uid, partner_id, report_type_name)

    bot.answer_callback_query(call.id, "Report submitted.", show_alert=False)
    bot.send_message(uid, "✅ Report submitted! Admins reviewing... Keep chatting!")

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

    if active_pairs.get(uid) != partner_id:
        bot.answer_callback_query(call.id, "Partner changed.", show_alert=True)
        return

    if game_type == "guess":
        secret = random.randint(1, 10)
        state = {"type": "guess", "secret": secret, "guesser": partner_id, "initiator": uid}
        games[uid] = state
        games[partner_id] = state

        try:
            bot.send_message(
                uid,
                "🎮 Game started: Guess the Number (1-10).\n\n"
                "Your partner will try to guess the secret number.\n"
                "You may still chat normally."
            )
            bot.send_message(
                partner_id,
                "🎮 Game started: Guess the Number (1-10).\n\n"
                "To guess the number, send a number 1-10."
            )
        except:
            pass

        bot.answer_callback_query(call.id)
        return
    else:
        state = {"type": "word", "turn": uid, "other": partner_id, "last_letter": None, "used_words": set()}
        games[uid] = state
        games[partner_id] = state

        try:
            bot.send_message(
                uid,
                "🎮 Game started: Word Chain.\n\n"
                "You start. Send the first word with /word word."
            )
            bot.send_message(
                partner_id,
                "🎮 Game started: Word Chain.\n\n"
                "Waiting for partner to send the first word.\n"
                "You can still chat normally."
            )
        except:
            pass

        bot.answer_callback_query(call.id)
        return

def process_game_message(message):
    uid = message.from_user.id
    state = games.get(uid)

    if not state:
        return False

    if state["type"] == "guess":
        if uid != state["guesser"]:
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
        if uid != state["turn"]:
            return False

        return False

    return False

@bot.message_handler(commands=["endgame"])
def cmd_end_game(message):
    uid = message.from_user.id

    if uid not in games:
        bot.send_message(uid, "You are not in a game.")
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
            bot.send_message(other, "Game ended by your partner. You may continue chatting freely.")
        except:
            pass

    bot.send_message(uid, "You ended the game. You may continue chatting freely.")

@bot.message_handler(commands=["rules"])
def cmd_rules(message):
    uid = message.from_user.id

    rules_text = (
        "📋 CHAT RULES\n\n"
        "Please read before chatting:\n\n"
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
        "/game - Propose game to partner\n"
        "  • Guess the Number (1-10)\n"
        "  • Word Chain\n"
        "/endgame - Stop current game\n\n"
        "👤 PROFILE\n"
        "/settings - Edit profile (gender, age, country)\n"
        "/refer - Get referral link & earn premium\n\n"
        "⚠️ SAFETY & RULES\n"
        "/report - Report inappropriate partner\n"
        "/rules - Read community guidelines\n\n"
        "🎁 PREMIUM\n"
        "Unlock opposite gender search by inviting 3 friends\n"
        f"Reward: {PREMIUM_DURATION_HOURS} hour premium access\n\n"
        "❓ Questions? Contact admin!"
    )

    bot.send_message(uid, help_text, reply_markup=main_keyboard(uid))

# ============================================
# ADMIN COMMANDS
# ============================================

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

        reporters = conn.execute(
            "SELECT DISTINCT reporter_id FROM reports WHERE reported_id = ?",
            (target_id,)
        ).fetchall()

    for (reporter_id,) in reporters:
        try:
            bot.send_message(
                reporter_id,
                f"✅ Action Taken!\n"
                f"Report reviewed & action taken on {time_str}\n"
                f"Thanks for keeping our community clean! 🧹\n"
                f"Keep chatting & stay safe! 💬"
            )
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
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return

    db_unban_user(target_id)
    user_warnings[target_id] = 0

    bot.reply_to(message, f"✅ User {target_id} unbanned.")

    try:
        bot.send_message(
            target_id,
            "✅ Your ban has been lifted!",
            reply_markup=main_keyboard(target_id)
        )
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
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return

    if not db_set_premium(target_id, until_date):
        bot.reply_to(message, "Invalid date! Use YYYY-MM-DD")
        return

    bot.reply_to(message, f"✅ User {target_id} premium until {until_date}")

    try:
        u = db_get_user(target_id)
        if u:
            premium_msg = (
                f"🎉 PREMIUM ADDED!\n\n"
                f"✅ Valid until {until_date}\n"
                f"♀️ Opposite gender search unlocked!"
            )
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
        bot.reply_to(message, f"Could not find user: {identifier}. Use numeric ID or @username.")
        return

    db_remove_premium(target_id)
    bot.reply_to(message, f"✅ Premium removed for user {target_id}")

    try:
        bot.send_message(
            target_id,
            "Your premium has been removed.",
            reply_markup=main_keyboard(target_id)
        )
    except:
        pass

# ============================================
# TEXT HANDLER
# ============================================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handler_text(m):
    uid = m.from_user.id
    text = m.text or ""

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    if not u["gender"]:
        bot.send_message(uid, "Set gender first! Use /start")
        return

    # 🔒 CHECK IF REPORT PENDING (LOCKED)
    if uid in report_reason_pending:
        partner_id = report_reason_pending[uid]

        if text.lower().strip() == "cancel":
            report_reason_pending.pop(uid, None)
            bot.send_message(
                uid,
                "❌ Report cancelled. You can now chat normally.",
                reply_markup=chat_keyboard()
            )
            return

        # Submit report with custom reason
        if text.strip():
            db_add_report(uid, partner_id, "Other", text)
            forward_full_chat_to_admin(uid, partner_id, "Other")
            report_reason_pending.pop(uid, None)

            bot.send_message(
                uid,
                "✅ Report submitted! Admins reviewing... Keep chatting!",
                reply_markup=chat_keyboard()
            )
            return
        else:
            bot.send_message(uid, "Report in progress. Please type reason or type 'cancel' to exit.")
            return

    # 🔒 CHECK PENDING COUNTRY
    if uid in pending_country:
        country_info = get_country_info(text)
        if country_info:
            country_name, country_flag = country_info
            db_set_country(uid, country_name, country_flag)
            pending_country.discard(uid)

            bot.send_message(
                uid,
                f"✅ Country updated to {country_flag} {country_name}!\n\n"
                f"Profile complete! Ready to chat?",
                reply_markup=main_keyboard(uid)
            )
            return
        else:
            bot.send_message(uid, f"'{text}' not valid. Try again (e.g., India)")
            return

    # Game processing
    if uid in games:
        handled = process_game_message(m)
        if handled:
            return

    # Button responses
    if text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            premium_status = "Premium Active ⭐" if db_is_premium(uid) else "Free"
            gender_emoji = "♂️" if u["gender"] == "Male" else "♀️"

            stats_msg = (
                f"📊 YOUR STATS\n\n"
                f"👤 Gender: {u['gender']}\n"
                f"🎂 Age: {u['age']}\n"
                f"🌍 Country: {u['country_flag']} {u['country']}\n\n"
                f"💬 Messages: {u['messages_sent']}\n"
                f"📸 Media Approved: {u['media_approved']}\n"
                f"❌ Media Rejected: {u['media_rejected']}\n"
                f"👥 People Referred: {u['referral_count']}\n\n"
                f"🎁 {premium_status}"
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

    if text == "♀️ Opposite Gender (Premium)":
        bot.send_message(uid, "💎 Premium required! Use /refer to unlock.")
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

    # Check banned content
    if is_banned_content(text):
        warn_user(uid, "Vulgar words or links")
        return

    # Forward to partner
    if uid in report_reason_pending:
        bot.send_message(uid, "⛔ Chat locked during report! Waiting for admin review.\nType 'cancel' to exit report.")
        return

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
            logger.error(f"Error forwarding chat text: {e}")
            bot.send_message(uid, "Could not send message")
    else:
        bot.send_message(uid, "Not connected. Use /search_random.", reply_markup=main_keyboard(uid))

# ============================================
# MEDIA HANDLER
# ============================================

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
            bot.send_message(uid, "Could not forward media")

# ============================================
# DISCONNECT LOGIC
# ============================================

def disconnect_user(user_id):
    global active_pairs

    if user_id in active_pairs:
        partner_id = active_pairs[user_id]

        chat_history[user_id] = chat_history.get(user_id, [])
        chat_history[partner_id] = chat_history.get(partner_id, [])

        try:
            del active_pairs[partner_id]
        except:
            pass

        try:
            del active_pairs[user_id]
        except:
            pass

        try:
            games.pop(user_id, None)
            games.pop(partner_id, None)
        except:
            pass

        remove_from_queues(user_id)
        remove_from_queues(partner_id)

# ============================================
# BOT COMMANDS SETUP
# ============================================

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

    bot.set_my_commands(user_cmds)

    try:
        admin_scope = types.BotCommandScopeChat(chat_id=ADMIN_ID)
        admin_cmds = user_cmds + [
            types.BotCommand("ban", "Ban a user"),
            types.BotCommand("unban", "Unban a user"),
            types.BotCommand("pradd", "Add premium"),
            types.BotCommand("prrem", "Remove premium"),
        ]
        bot.set_my_commands(admin_cmds, scope=admin_scope)
    except Exception as e:
        logger.warning(f"Could not set admin commands: {e}")

# ============================================
# INITIALIZATION & RUN
# ============================================

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()

    logger.info("Setting up bot commands...")
    setup_bot_commands()

    logger.info("GhostTalk Bot v5.0 FINAL starting...")
    logger.info("All fixes applied:")
    logger.info("✅ Gender Lock REMOVED (Flexible for all)")
    logger.info("✅ Render Port Fix (os.getenv('PORT'))")
    logger.info("✅ Report lock-on (chat frozen)")
    logger.info("✅ Auto-ban 10 reports")
    logger.info("✅ Reporter notifications (timestamp only)")
    logger.info("✅ Independent settings changes")
    logger.info("✅ /help command")
    logger.info("✅ Full syntax fixed")

    # ✅ FIX FOR RENDER PORT ERROR
    port = int(os.getenv("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False), daemon=True).start()

    # Start bot polling
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
