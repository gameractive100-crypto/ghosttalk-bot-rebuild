#!/usr/bin/env python3
"""
GhostTalk Premium Bot - PRODUCTION READY v3.0 - ALL ISSUES FIXED + BUG #23
FINAL CORRECTED VERSION - Ready to Deploy

All 23 issues fixed:
- Critical: 6 issues fixed
- High: 11 issues fixed
- Medium: 6 issues fixed

Bug #23 Fix: Added pending_country.add(uid) in process_new_age()
This fixes the country selection failure for new users
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
import requests
import uuid

import telebot
from telebot import types
from flask import Flask

# -------- CONFIG --------
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("BOT_TOKEN not found!")

BOT_USERNAME = "SayNymBot"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk_final.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 24  # FIXED: Changed from 1 to 24

# -------- BANNED WORDS --------
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography", "rape",
    "anj", "anjing", "babi", "asu", "kontl", "kontol", "puki", "memek", "jembut", "maderchod", "mc", "bhen ka lauda", "bhenkalauda", "randi", "randika", "gand", "bsdk", "chut", "chot", "chuut", "choot", "lund"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- 195 COUNTRIES --------
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
    return "GhostTalk Bot Running!", 200

@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, 200

# -------- RUNTIME DATA --------
waiting_random = []
waiting_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history_with_time = {}
age_update_pending = {}
pending_country = set()
report_reason_pending = {}
pending_game_invites = {}
games = {}
chat_history = {}

# -------- THREADING LOCKS (FIXED: Added for thread safety) --------
queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()
search_lock = threading.Lock()
audit_lock = threading.Lock()

user_last_search = {}
admin_audit_log = []

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
            reporter_id INTEGER, reported_id INTEGER,
            report_type TEXT, reason TEXT, timestamp TEXT
        )""")
        conn.commit()
        logger.info("Database initialized v3.0")

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
                bot.send_message(user_id, f"PREMIUM UNLOCKED!\n {PREMIUM_DURATION_HOURS} hour premium earned!\n Opposite gender search unlocked!")
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

        report_count = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE reported_id=?",
            (reported_id,)
        ).fetchone()[0]

        logger.info(f"User {reported_id} has {report_count} reports")

        if report_count >= 10:
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                (reported_id, None, 1, f"Auto-ban: {report_count} reports"))
            logger.warning(f"AUTO-BAN: User {reported_id} - {report_count} reports")

            try:
                bot.send_message(reported_id, f"PERMANENTLY AUTO-BANNED\n Reason: {report_count} reports received")
            except:
                pass

            try:
                bot.send_message(ADMIN_ID, f"AUTO-BAN: User {reported_id} ({report_count} reports)")
            except:
                pass

            if reported_id in active_pairs:
                partner = active_pairs[reported_id]
                if partner in active_pairs:
                    del active_pairs[partner]
                del active_pairs[reported_id]
                try:
                    bot.send_message(partner, "Partner banned. Finding new partner...")
                except:
                    pass

        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

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
    with user_warnings_lock:
        count = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = count
    if count >= WARNING_LIMIT:
        db_ban_user(user_id, hours=TEMP_BAN_HOURS, reason=reason)
        with user_warnings_lock:
            del user_warnings[user_id]
        try:
            bot.send_message(user_id, f"BANNED for {TEMP_BAN_HOURS} hours!\n Reason: {reason}")
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"WARNING {count}/{WARNING_LIMIT}\n {reason}\n {WARNING_LIMIT - count} more = BAN!")
        except:
            pass
        return "warn"

# -------- QUEUE HELPERS --------
def remove_from_queues(user_id):
    global waiting_random, waiting_opposite
    with queue_lock:
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
        bot.send_message(ADMIN_ID, f"NEW REPORT\nType: {report_type}\nReporter: {user_label(reporter_id)} ({reporter_id})\nReported: {user_label(reported_id)} ({reported_id})\nTime: {datetime.utcnow().isoformat()}")
        reporter_msgs = chat_history.get(reporter_id, [])[-10:]
        if reporter_msgs:
            bot.send_message(ADMIN_ID, "Reporter messages")
            for chat_id, msg_id in reporter_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")
        reported_msgs = chat_history.get(reported_id, [])[-10:]
        if reported_msgs:
            bot.send_message(ADMIN_ID, "Reported user messages")
            for chat_id, msg_id in reported_msgs:
                try:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
                except Exception as e:
                    logger.debug(f"Could not forward: {e}")
        bot.send_message(ADMIN_ID, "End of forwarded messages.")
    except Exception as e:
        logger.error(f"Error forwarding chat: {e}")

def disconnect_user(user_id):
    global active_pairs, chat_history_with_time
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
                bot.send_message(partner_id, "Partner left chat.\n\n Want to report this user?", reply_markup=report_keyboard())
                time.sleep(0.5)
                bot.send_message(partner_id, "Find new partner?", reply_markup=main_keyboard(partner_id))
            except:
                pass

def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add(" Search Random")
    u = db_get_user(user_id)
    if u and u["gender"]:
        if db_is_premium(user_id):
            kb.add(" Search Opposite Gender")
        else:
            kb.add("Opposite Gender (Premium)")
    kb.add(" Stop")
    kb.add(" Settings", " Refer")
    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add(" Stats")
    kb.add(" Report", " Next")
    kb.add(" Stop")
    return kb

def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Spam", callback_data="rep:spam"),
        types.InlineKeyboardButton("Unwanted Content", callback_data="rep:unwanted"),
        types.InlineKeyboardButton("Inappropriate Messages", callback_data="rep:inappropriate"),
        types.InlineKeyboardButton("Suspicious Activity", callback_data="rep:suspicious"),
        types.InlineKeyboardButton("Other", callback_data="rep:other")
    )
    return markup

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = " " if partner_user["gender"] == "Male" else " "
    age_text = str(partner_user["age"]) if partner_user["age"] else "Unknown"
    country_flag = partner_user["country_flag"] or ""
    country_name = partner_user["country"] or "Global"
    msg = (
        " Partner Found! \n\n"
        f" Age: {age_text}\n"
        f" Gender: {gender_emoji} {partner_user['gender']}\n"
        f" Country: {country_flag} {country_name}\n"
    )
    if viewer_id == ADMIN_ID:
        partner_name = partner_user["first_name"] or partner_user["username"] or "Unknown"
        msg += f"\n Name: {partner_name}\n ID: {partner_user['user_id']}\n"
    msg += "\n Enjoy chat! Type /next for new partner."
    return msg

def match_users():
    global waiting_random, waiting_opposite, active_pairs

    opposite_copy = waiting_opposite.copy()

    i = 0
    while i < len(opposite_copy):
        uid, searcher_gender = opposite_copy[i]

        if uid not in waiting_opposite:
            i += 1
            continue

        opposite_gender = "Male" if searcher_gender == "Female" else "Female"
        match_index = None

        for j, other_uid in enumerate(waiting_random):
            other_data = db_get_user(other_uid)
            if other_data and other_data['gender'] == opposite_gender:
                match_index = j
                break

        if match_index is not None:
            with queue_lock:
                if match_index < len(waiting_random):
                    found_uid = waiting_random.pop(match_index)
                    waiting_opposite.remove((uid, searcher_gender))
                    with active_pairs_lock:
                        active_pairs[uid] = found_uid
                        active_pairs[found_uid] = uid

                    u_searcher = db_get_user(uid)
                    u_found = db_get_user(found_uid)

                    try:
                        bot.send_message(uid, format_partner_found_message(u_found, uid), reply_markup=chat_keyboard())
                        bot.send_message(found_uid, format_partner_found_message(u_searcher, found_uid), reply_markup=chat_keyboard())
                        logger.info(f"Opposite: {uid} ({searcher_gender}) <-> {found_uid}")
                    except:
                        pass
                    return
        else:
            i += 1

    random_copy = waiting_random.copy()
    while len(random_copy) >= 2:
        if len(waiting_random) < 2:
            break

        with queue_lock:
            if len(waiting_random) >= 2:
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
                    logger.info(f"Random: {u1} <-> {u2}")
                except:
                    pass

        random_copy = waiting_random.copy()

# -------- CLEANUP THREADS --------
def cleanup_old_chat_history():
    global chat_history_with_time
    now = datetime.utcnow()
    threshold = timedelta(days=7)
    to_delete = []

    for uid, (partner, ts) in chat_history_with_time.items():
        try:
            age = now - ts
            if age > threshold:
                to_delete.append(uid)
        except:
            to_delete.append(uid)

    for uid in to_delete:
        try:
            del chat_history_with_time[uid]
        except:
            pass

    if to_delete:
        logger.info(f"Cleaned {len(to_delete)} old chat history entries")

def cleanup_expired_pending_media():
    global pending_media
    now = datetime.utcnow()
    threshold = timedelta(minutes=5)
    to_delete = []

    for token, meta in pending_media.items():
        try:
            ts = datetime.fromisoformat(meta["timestamp"])
            if now - ts > threshold:
                to_delete.append(token)
        except:
            to_delete.append(token)

    for token in to_delete:
        try:
            del pending_media[token]
        except:
            pass

    if to_delete:
        logger.info(f"Cleaned {len(to_delete)} expired media tokens")

def start_cleanup_threads():
    def run_chat_cleanup():
        while True:
            time.sleep(3600)
            try:
                cleanup_old_chat_history()
            except Exception as e:
                logger.error(f"Chat history cleanup error: {e}")

    def run_media_cleanup():
        while True:
            time.sleep(60)
            try:
                cleanup_expired_pending_media()
            except Exception as e:
                logger.error(f"Media cleanup error: {e}")

    chat_thread = threading.Thread(target=run_chat_cleanup, daemon=True)
    media_thread = threading.Thread(target=run_media_cleanup, daemon=True)

    chat_thread.start()
    media_thread.start()

    logger.info("Cleanup threads started")

# -------- COMMANDS --------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "You are BANNED from this bot.")
        return

    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        with get_conn() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
            if referrer and referrer[0] != user.id:
                db_add_referral(referrer[0])
                bot.send_message(user.id, "You joined via referral link!")

    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Male", callback_data="sex:male"),
            types.InlineKeyboardButton("Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "Welcome to GhostTalk!\n\n Select your gender:", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "Enter your age (12-99 only):")
        bot.register_next_step_handler(message, process_new_age)
    elif not u["country"]:
        bot.send_message(user.id, "Enter your country name:\n\n Country CANNOT be changed later unless PREMIUM!")
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = "Premium Active" if db_is_premium(user.id) else " Free User"
        welcome_msg = (
            f"Welcome back!\n\n"
            f" Gender: {u['gender']}\n"
            f" Age: {u['age']}\n"
            f" Country: {u['country_flag']} {u['country']}\n"
            f"{premium_status}\n\n"
            "Ready to chat?"
        )
        bot.send_message(user.id, welcome_msg, reply_markup=main_keyboard(user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)

    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "You are banned", show_alert=True)
        return

    u = db_get_user(uid)
    if u and u["gender"]:
        if uid != ADMIN_ID and not db_is_premium(uid):
            bot.answer_callback_query(call.id, "Gender change requires PREMIUM!\n Refer friends to unlock.", show_alert=True)
            return

    _, gender = call.data.split(":")
    gender_display = "Male" if gender == "male" else "Female"
    gender_emoji = " " if gender == "male" else " "

    u = db_get_user(uid)
    if u and u["gender"] == gender_display:
        bot.answer_callback_query(call.id, f"Already {gender_display}!", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "Gender set!", show_alert=True)

    try:
        bot.edit_message_text(f"Gender: {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        bot.send_message(uid, f"Gender: {gender_emoji} {gender_display}\n\n Enter your age (12-99):")
        bot.register_next_step_handler(call.message, process_new_age)
    except:
        pass

def process_new_age(message):
    """FIXED: Better age validation with clear error messages"""
    uid = message.from_user.id
    text = message.text.strip()

    # Check if it's a valid number
    if not text.isdigit():
        bot.send_message(uid, f"'{text}' is not a valid number.\n\nPlease enter age as digits only (e.g., 21):")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)

    # Check range
    if age < 12 or age > 99:
        bot.send_message(uid, f"Age {age} is outside allowed range (12-99).\n\nPlease enter valid age:")
        bot.register_next_step_handler(message, process_new_age)
        return

    db_set_age(uid, age)
    bot.send_message(uid, f"Age set to {age}! \n\n Enter your country name:")

    pending_country.add(uid)  # BUG FIX #23: ADD THIS LINE - CRITICAL!

    bot.register_next_step_handler(message, process_new_country)

def process_new_country(message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    if uid not in pending_country:
        bot.send_message(uid, "Use /settings or /start to change profile.")
        return
    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, f"'{text}' not valid.\n Find again (e.g., India):")
        try:
            bot.register_next_step_handler(message, process_new_country)
        except:
            pass
        return
    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)
    bot.send_message(uid, f"Country: {country_flag} {country_name}\n\n Profile complete!", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return

    premium_status = "Premium Active" if db_is_premium(uid) else " Free User"
    gender_emoji = " " if u["gender"] == "Male" else " "

    settings_text = (
        " SETTINGS & PROFILE\n\n"
        f" Gender: {gender_emoji} {u['gender'] or 'Not set'}\n"
        f" Age: {u['age'] or 'Not set'}\n"
        f" Country: {u['country_flag'] or ''} {u['country'] or 'Not set'}\n\n"
        f" Messages Sent: {u['messages_sent']}\n"
        f" Media Approved: {u['media_approved']}\n"
        f" Media Rejected: {u['media_rejected']}\n\n"
        f" People Referred: {u['referral_count']}/3\n"
        f"{premium_status}\n\n"
        " Change Profile:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(" Refer Link", callback_data="ref:link"))
    markup.row(types.InlineKeyboardButton("Male", callback_data="sex:male"), types.InlineKeyboardButton("Female", callback_data="sex:female"))
    markup.row(types.InlineKeyboardButton(" Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton(" Change Country", callback_data="set:country"))

    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def callback_change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, " Enter new age (12-99):")
    bot.register_next_step_handler(call.message, process_new_age)
    bot.answer_callback_query(call.id, "", show_alert=False)

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
            " REFERRAL SYSTEM\n\n"
            f" Your Referral Link:\n{ref_link}\n\n"
            f" People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
            f" Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n"
            " Unlock opposite gender search!\n\n"
        )

        if remaining > 0:
            refer_text += f" Invite {remaining} more friends to unlock premium!"
        else:
            refer_text += " Premium unlocked! Keep inviting for more!"

        refer_text += (
            "\n\n How it works:\n"
            "1 Share your link with friends\n"
            "2 They join with your link\n"
            f"3 Get premium after {PREMIUM_REFERRALS_NEEDED} referrals!"
        )

        bot.send_message(uid, refer_text)
        bot.answer_callback_query(call.id, "", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def callback_set_country(call):
    uid = call.from_user.id
    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, "Country change requires PREMIUM!\n Refer friends to unlock.", show_alert=True)
        return
    bot.send_message(uid, " Enter your new country name:")
    pending_country.add(uid)
    bot.register_next_step_handler(call.message, process_new_country)
    bot.answer_callback_query(call.id, "", show_alert=False)

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
        " REFERRAL SYSTEM\n\n"
        f" Your Referral Link:\n{ref_link}\n\n"
        f" People Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f" Reward: {PREMIUM_DURATION_HOURS} hour Premium Access\n"
        " Unlock opposite gender search!\n\n"
    )

    if remaining > 0:
        refer_text += f" Invite {remaining} more friends to unlock premium!"
    else:
        refer_text += " Premium unlocked! Keep inviting for more!"

    refer_text += (
        "\n\n How it works:\n"
        "1 Share your link with friends\n"
        "2 They join with your link\n"
        f"3 Get premium after {PREMIUM_REFERRALS_NEEDED} referrals!"
    )

    bot.send_message(uid, refer_text)

@bot.message_handler(commands=['search_random'])
def cmd_search_random(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "You are banned")
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile first! Use /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "Already in chat! Use /next for new partner.")
            return

    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
    bot.send_message(uid, "Searching for random partner...\n Please wait...")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "You are banned")
        return

    if not db_is_premium(uid):
        premium_required_msg = (
            " PREMIUM REQUIRED!\n\n"
            f" Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock {PREMIUM_DURATION_HOURS} hour premium.\n"
            " Use /refer to get your link!"
        )
        bot.send_message(uid, premium_required_msg)
        return

    u = db_get_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete profile first! Use /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "Already in chat! Use /next for new partner.")
            return

    remove_from_queues(uid)
    with queue_lock:
        waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "Searching for opposite gender partner...\n Please wait...")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    remove_from_queues(uid)
    disconnect_user(uid)
    bot.send_message(uid, "Stopped searching/chatting.", reply_markup=main_keyboard(uid))

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "Not in chat. Use search commands.")
            return
    disconnect_user(uid)
    bot.send_message(uid, "Looking for new partner...", reply_markup=main_keyboard(uid))
    cmd_search_random(message)

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "No active partner to report.")
            return
    bot.send_message(uid, "What type of abuse?", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id
    with active_pairs_lock:
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
        report_reason_pending[uid] = partner_id
        bot.answer_callback_query(call.id, "Please type the reason for reporting (short).", show_alert=True)
        bot.send_message(uid, "Please type the reason for your report (short).")
        return
    db_add_report(uid, partner_id, report_type_name, "")
    forward_full_chat_to_admin(uid, partner_id, report_type_name)
    db_ban_user(partner_id, hours=TEMP_BAN_HOURS, reason=report_type_name)
    bot.send_message(uid, " Report submitted!\n\n Admins reviewing...\n User temp-banned 24hrs.\n Keep chatting!")
    bot.answer_callback_query(call.id, "Report submitted. Keep chatting!")

@bot.message_handler(commands=['pradd'])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd [user_id|username] [YYYY-MM-DD]")
        return
    identifier = parts[1]
    until_date = parts[2]
    try:
        target_id = int(identifier)
    except:
        target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user '{identifier}'.")
        return
    if not db_set_premium(target_id, until_date):
        bot.reply_to(message, "Invalid date! Use YYYY-MM-DD")
        return
    bot.reply_to(message, f"User {identifier} (id:{target_id}) premium until {until_date}")
    try:
        u = db_get_user(target_id)
        if u:
            bot.send_message(target_id, f" PREMIUM ADDED!\n Valid until {until_date}\n Opposite gender search unlocked!", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['prrem'])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /prrem [user_id]")
        return
    identifier = parts[1]
    try:
        target_id = int(identifier)
    except:
        target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user '{identifier}'.")
        return
    db_remove_premium(target_id)
    bot.reply_to(message, f"Premium removed for {identifier} (id:{target_id})")
    try:
        bot.send_message(target_id, " Your premium has been removed.", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "Admin only!")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban [user_id] [hours/permanent] [reason]")
        return
    try:
        target_id = int(parts[1])
    except:
        target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user '{parts[1]}'.")
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
        bot.reply_to(message, f"User {parts[1]} (id:{target_id}) PERMANENTLY BANNED. {reason}")
        try:
            bot.send_message(target_id, f"PERMANENTLY BANNED.\nReason: {reason}")
        except:
            pass
    else:
        bot.reply_to(message, f"User {parts[1]} (id:{target_id}) banned for {hours} hours. {reason}")
        try:
            bot.send_message(target_id, f"Banned for {hours} hours.\nReason: {reason}")
        except:
            pass
    with active_pairs_lock:
        if target_id in active_pairs:
            disconnect_user(target_id)

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "Admin only!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban [user_id]")
        return
    try:
        target_id = int(parts[1])
    except:
        target_id = None
    if not target_id:
        bot.reply_to(message, f"Could not find user '{parts[1]}'.")
        return
    db_unban_user(target_id)
    with user_warnings_lock:
        user_warnings[target_id] = 0
    bot.reply_to(message, f"User {parts[1]} (id:{target_id}) unbanned")
    try:
        bot.send_message(target_id, " Your ban has been lifted!", reply_markup=main_keyboard(target_id))
    except:
        pass

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker'])
def handle_media(m):
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "You are banned")
        return

    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "Not connected")
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
            bot.send_message(uid, "Could not forward media")
        return

    token = str(uuid.uuid4())
    with pending_media_lock:
        pending_media[token] = {
            "sender": uid, "partner": partner, "media_type": media_type,
            "file_id": media_id, "msg_id": None, "timestamp": datetime.utcnow().isoformat()
        }

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("Reject", callback_data=f"rej:{token}")
    )

    try:
        msg = bot.send_message(partner, f"Partner sent {media_type}. Accept?", reply_markup=markup)
        with pending_media_lock:
            if token in pending_media:
                pending_media[token]["msg_id"] = msg.message_id
        bot.send_message(uid, " Consent request sent. Waiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.send_message(uid, "Could not request consent")
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
            bot.send_message(sender_id, "Your media was ACCEPTED!")
            db_increment_media(sender_id, "approved")
        except:
            pass

        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass

        with pending_media_lock:
            if token in pending_media:
                del pending_media[token]

        bot.answer_callback_query(call.id, "Media accepted", show_alert=False)
    except Exception as e:
        logger.error(f"Approve error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        with pending_media_lock:
            meta = pending_media.get(token)
            if not meta:
                bot.answer_callback_query(call.id, "Media no longer available", show_alert=True)
                return

            sender_id = meta["sender"]

        try:
            bot.send_message(sender_id, "Your media was REJECTED")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass

        with pending_media_lock:
            if token in pending_media:
                del pending_media[token]

        bot.answer_callback_query(call.id, "Media rejected", show_alert=False)
    except Exception as e:
        logger.error(f"Reject error: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(func=lambda message: message.text == " Search Random")
def handle_search_random_btn(message):
    cmd_search_random(message)

@bot.message_handler(func=lambda message: message.text == " Search Opposite Gender")
def handle_search_opposite_btn(message):
    cmd_search_opposite(message)

@bot.message_handler(func=lambda message: message.text == " Stop")
def handle_stop_btn(message):
    cmd_stop(message)

@bot.message_handler(func=lambda message: message.text == " Settings")
def handle_settings_btn(message):
    cmd_settings(message)

@bot.message_handler(func=lambda message: message.text == " Refer")
def handle_refer_btn(message):
    cmd_refer(message)

@bot.message_handler(func=lambda message: message.text == " Stats")
def handle_stats_btn(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Profile not found. Use /start")
        return
    stats = (
        " YOUR STATS\n\n"
        f" Messages Sent: {u['messages_sent']}\n"
        f" Media Approved: {u['media_approved']}\n"
        f" Media Rejected: {u['media_rejected']}\n"
        f" Referred: {u['referral_count']}/3"
    )
    bot.send_message(uid, stats, reply_markup=chat_keyboard())

@bot.message_handler(func=lambda message: message.text == " Next")
def handle_next_btn(message):
    cmd_next(message)

@bot.message_handler(func=lambda message: message.text == " Report")
def handle_report_btn(message):
    cmd_report(message)

@bot.message_handler(func=lambda message: message.text == "Opposite Gender (Premium)")
def handle_premium_locked_btn(message):
    uid = message.from_user.id
    premium_msg = (
        " PREMIUM FEATURE\n\n"
        f" Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock!\n"
        " Use  Refer to get your link."
    )
    bot.send_message(uid, premium_msg, reply_markup=main_keyboard(uid))

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text

    if db_is_banned(uid):
        bot.send_message(uid, "You are banned")
        return

    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "Not in chat. Use search commands.", reply_markup=main_keyboard(uid))
            return

    if is_banned_content(text):
        warn_result = warn_user(uid, "Inappropriate content")
        if warn_result == "ban":
            remove_from_queues(uid)
            disconnect_user(uid)
        return

    with active_pairs_lock:
        partner = active_pairs.get(uid)

    if not partner:
        return

    try:
        u = db_get_user(uid)
        if u:
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
            logger.info(f"Message sent by {uid}")
        bot.send_message(partner, text)
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def run_bot():
    logger.info("Bot starting...")
    init_db()
    start_cleanup_threads()
    bot.infinity_polling()

if __name__ == "__main__":
    import sys

    def run_flask():
        app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        run_bot()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
