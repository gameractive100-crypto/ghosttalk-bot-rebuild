#!/usr/bin/env python3
"""
GhostTalk Premium Bot - ULTIMATE MASTERCLASS EDITION v2
Production-ready, error-free, admin monitoring, report after chat end
Expanded ban words (English), storage-optimized, payment integration ready
Age validation: 12-99 years, Search matching FIXED
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
    raise ValueError("BOT_TOKEN environment variable missing!")

BOT_USERNAME = "SayNymBot"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk_fixed.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# -------- EXPANDED BANNED WORDS (ENGLISH ONLY) --------
BANNED_WORDS = [
    "fuck", "fuck you", "fucking", "fucked", "fucker", "motherfucker",
    "sex chat", "sex talk", "sexting", "nudes", "nude pics", "send nudes",
    "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute",
    "porn", "pornography", "rape", "molest", "pedophile", "child abuse",
    "scam", "fraud", "fake", "shit", "damn", "bastard", "cunt", "piss", "prick"
]

LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- 195 COUNTRIES WITH FLAGS --------
COUNTRIES = {
    "afghanistan": "🇦🇫", "albania": "🇦🇱", "algeria": "🇩🇿", "andorra": "🇦🇩", "angola": "🇦🇴",
    "antigua and barbuda": "🇦🇬", "argentina": "🇦🇷", "armenia": "🇦🇲", "australia": "🇦🇺", "austria": "🇦🇹",
    "azerbaijan": "🇦🇿", "bahamas": "🇧🇸", "bahrain": "🇧🇭", "bangladesh": "🇧🇩", "barbados": "🇧🇧",
    "belarus": "🇧🇾", "belgium": "🇧🇪", "belize": "🇧🇿", "benin": "🇧🇯", "bhutan": "🇧🇹",
    "bolivia": "🇧🇴", "bosnia and herzegovina": "🇧🇦", "botswana": "🇧🇼", "brazil": "🇧🇷", "brunei": "🇧🇳",
    "bulgaria": "🇧🇬", "burkina faso": "🇧🇫", "burundi": "🇧🇮", "cabo verde": "🇨🇻", "cambodia": "🇰🇭",
    "cameroon": "🇨🇲", "canada": "🇨🇦", "central african republic": "🇨🇫", "chad": "🇹🇩", "chile": "🇨🇱",
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

# -------- FLASK APP --------
app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN)

@app.route("/")
def home():
    return "GhostTalk Bot is Running!", 200

@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, 200

# -------- RUNTIME DATA --------
waiting_random = []
waiting_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
chat_history = {}

# -------- DATABASE --------
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
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
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            ban_until TEXT,
            permanent INTEGER DEFAULT 0,
            reason TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_id INTEGER,
            report_type TEXT,
            reason TEXT,
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
            "user_id": row[0], "username": row[1], "first_name": row[2],
            "gender": row[3], "age": row[4], "country": row[5], "country_flag": row[6],
            "messages_sent": row[7], "media_approved": row[8], "media_rejected": row[9],
            "referral_code": row[10], "referral_count": row[11], "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000,99999)}"
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

def db_set_media_sharing(user_id, allow: bool):
    with get_conn() as conn:
        if allow:
            conn.execute("UPDATE users SET media_approved=1, media_rejected=0 WHERE user_id=?", (user_id,))
        else:
            conn.execute("UPDATE users SET media_approved=0, media_rejected=1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (user_id,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (user_id,))
        conn.commit()

def db_is_banned(user_id):
    if user_id == OWNER_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        ban_until, permanent = row
        if permanent == 1:
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
                premium_msg = (
                    "🎉 PREMIUM UNLOCKED!\n"
                    f"You've earned {PREMIUM_DURATION_HOURS} hour of premium access!\n"
                    "You can now search opposite gender!\n"
                    f"Expires in {PREMIUM_DURATION_HOURS} hour"
                )
                bot.send_message(user_id, premium_msg)
            except:
                pass

def db_get_referral_link(user_id):
    user = db_get_user(user_id)
    if user:
        return f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    return None

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

# -------- CLEANUP FUNCTIONS --------
def cleanup_old_reports():
    try:
        with get_conn() as conn:
            result = conn.execute("DELETE FROM reports WHERE timestamp < datetime('now', '-30 days')")
            conn.commit()
            deleted = result.rowcount
            if deleted > 0:
                logger.info(f"Cleaned {deleted} old reports")
    except Exception as e:
        logger.error(f"Error cleaning reports: {e}")

def cleanup_pending_media():
    try:
        now = datetime.utcnow()
        tokens_to_remove = []
        for token, meta in list(pending_media.items()):
            try:
                timestamp = datetime.fromisoformat(meta["timestamp"])
                if (now - timestamp).total_seconds() > 3600:
                    tokens_to_remove.append(token)
            except:
                tokens_to_remove.append(token)
        for token in tokens_to_remove:
            del pending_media[token]
        if tokens_to_remove:
            logger.info(f"Cleaned {len(tokens_to_remove)} stale media consents")
    except Exception as e:
        logger.error(f"Error cleaning pending media: {e}")

def auto_unban():
    try:
        now = datetime.utcnow()
        with get_conn() as conn:
            bans = conn.execute("SELECT user_id, ban_until FROM bans WHERE permanent=0 AND ban_until IS NOT NULL").fetchall()
            for user_id, ban_until in bans:
                try:
                    if datetime.fromisoformat(ban_until) < now:
                        conn.execute("DELETE FROM bans WHERE user_id=?", (user_id,))
                        conn.commit()
                        user_warnings[user_id] = 0
                        try:
                            bot.send_message(user_id, "✅ Your ban has been lifted! You can use the bot again.")
                        except:
                            pass
                        logger.info(f"Auto-unbanned user {user_id}")
                except:
                    pass
    except Exception as e:
        logger.error(f"Auto-unban error: {e}")

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
            ban_msg = (
                f"🚫 BANNED - {TEMP_BAN_HOURS} hours\n"
                f"Reason: {reason}\n"
                "Ban will be lifted automatically."
            )
            bot.send_message(user_id, ban_msg)
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            warn_msg = (
                f"⚠️ WARNING {count}/{WARNING_LIMIT}\n"
                f"Reason: {reason}\n"
                f"{WARNING_LIMIT - count} more warnings = BAN!"
            )
            bot.send_message(user_id, warn_msg)
        except:
            pass
        return "warn"

# -------- HELPERS --------
def remove_from_queues(user_id):
    global waiting_random, waiting_opposite
    if user_id in waiting_random:
        waiting_random.remove(user_id)
    waiting_opposite = [(uid, gen) for uid, gen in waiting_opposite if uid != user_id]

def disconnect_user(user_id):
    global active_pairs, pending_media, chat_history
    if user_id in active_pairs:
        partner_id = active_pairs[user_id]
        chat_history[user_id] = partner_id
        chat_history[partner_id] = user_id
        if partner_id in active_pairs:
            del active_pairs[partner_id]
        del active_pairs[user_id]
        try:
            bot.send_message(partner_id, "❌ Partner has left the chat.", reply_markup=main_keyboard(partner_id))
        except:
            pass

    tokens = [t for t, meta in list(pending_media.items()) if meta.get("sender") == user_id or meta.get("partner") == user_id]
    for t in tokens:
        try:
            del pending_media[t]
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
            kb.add("🔒 Opposite Gender (Premium)")
    kb.add("🛑 Stop")
    kb.add("⚙️ Settings", "👥 Refer")
    return kb

def chat_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("📊 Stats")
    kb.add("⚠️ Report", "⏭️ Next")
    kb.add("🛑 Stop")
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

def generate_media_token(sender_id):
    return f"{sender_id}{int(time.time()*1000)}{secrets.token_hex(4)}"

def format_partner_found_message(partner_user, viewer_id):
    gender_emoji = "👨" if partner_user["gender"] == "Male" else "👩"
    age_text = str(partner_user["age"]) if partner_user["age"] else "Unknown"
    country_flag = partner_user["country_flag"] or "🌍"
    country_name = partner_user["country"] or "Global"

    msg = (
        "🎉 Partner found! 🎉\n\n"
        f"🎂 Age: {age_text}\n"
        f"👤 Gender: {gender_emoji} {partner_user['gender']}\n"
        f"🌍 Country: {country_flag} {country_name}\n"
    )

    if viewer_id == ADMIN_ID:
        partner_name = partner_user["first_name"] or partner_user["username"] or "Unknown"
        msg += f"\n👤 Name: {partner_name}\n"
        msg += f"🆔 User ID: {partner_user['user_id']}\n"

    msg += "\n🗨️ Enjoy the chat! Use /next to meet someone new."
    return msg

# -------- KEEP-ALIVE SYSTEM --------
def keep_alive_pinger():
    PING_INTERVAL = 720
    def ping_loop():
        time.sleep(90)
        while True:
            try:
                ping_msg = (
                    "🤖 Keep-Alive\n"
                    f"{datetime.utcnow().strftime('%H:%M')} UTC\n"
                    f"Active: {len(active_pairs)//2} chats"
                )
                bot.send_message(ADMIN_ID, ping_msg)
                logger.info("Keep-alive ping sent")
                cleanup_pending_media()
                auto_unban()
                if datetime.utcnow().hour == 3:
                    cleanup_old_reports()
            except Exception as e:
                logger.error(f"Ping/cleanup failed: {e}")
            time.sleep(PING_INTERVAL)

    thread = threading.Thread(target=ping_loop, daemon=True)
    thread.start()
    logger.info("Keep-alive pinger & cleanup tasks started")

# -------- COMMANDS --------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)

    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are banned from using this bot.")
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
        bot.send_message(user.id, "👋 Welcome to GhostTalk! Please select your gender to start:", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "Please enter your age (numbers only, 12-99):")
    elif not u["country"]:
        bot.send_message(user.id, "Please enter your country name:")
    else:
        premium_status = "✅ Premium Active" if db_is_premium(user.id) else "🆓 Free User"
        welcome_msg = (
            "👋 Welcome back!\n"
            f"👤 Gender: {u['gender']}\n"
            f"🎂 Age: {u['age']}\n"
            f"🌍 Country: {u['country_flag']} {u['country']}\n"
            f"{premium_status}\n\n"
            "Ready to find a chat partner?"
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
        bot.answer_callback_query(call.id, f"You are already {gender_display}!", show_alert=True)
        return

    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "Gender set!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender set to {gender_emoji} {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    try:
        gender_confirm_msg = (
            f"✅ Gender set to {gender_emoji} {gender_display}\n\n"
            "Now, please enter your age (numbers only, 12-99):"
        )
        bot.send_message(uid, gender_confirm_msg)
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
        "⚙️ SETTINGS & STATS\n\n"
        f"👤 Gender: {gender_emoji} {u['gender'] or 'Not set'}\n"
        f"🎂 Age: {u['age'] or 'Not set'}\n"
        f"🌍 Country: {u['country_flag'] or '🌍'} {u['country'] or 'Not set'}\n\n"
        f"📊 Messages Sent: {u['messages_sent']}\n"
        f"✅ Media Approved: {u['media_approved']}\n"
        f"❌ Media Rejected: {u['media_rejected']}\n\n"
        f"{premium_status}\n\n"
        "Change Your Gender:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
        types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
    )
    bot.send_message(uid, settings_text, reply_markup=markup)

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
        refer_text += f"Invite {remaining} more to unlock premium!"
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
    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first using /start")
        return

    if not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete your profile first with /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "You are already in a chat. Use /next to find new partner.")
        return

    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for random partner... Please wait")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    if not db_is_premium(uid):
        premium_required_msg = (
            "💎 This feature requires Premium!\n\n"
            f"Invite {PREMIUM_REFERRALS_NEEDED} friends to unlock {PREMIUM_DURATION_HOURS} hour premium.\n"
            "Use /refer to get your link!"
        )
        bot.send_message(uid, premium_required_msg)
        return

    u = db_get_user(uid)
    if not u or not u["gender"]:
        bot.send_message(uid, "Set gender first using /start")
        return

    if not u["age"] or not u["country"]:
        bot.send_message(uid, "Complete your profile first with /start")
        return

    if uid in active_pairs:
        bot.send_message(uid, "You are already in a chat. Use /next to find new partner.")
        return

    remove_from_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "🎯 Searching for opposite gender partner... Please wait")
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
        bot.send_message(uid, "You're not in a chat. Use search commands first.")
        return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Looking for new partner...", reply_markup=main_keyboard(uid))
    cmd_search_random(message)

@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    if uid not in active_pairs and uid not in chat_history:
        bot.send_message(uid, "You need to be in an active chat or have recent chat history to report.")
        return
    bot.send_message(uid, "What type of abuse do you want to report?", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def callback_report(call):
    uid = call.from_user.id
    partner_id = None

    if uid in active_pairs:
        partner_id = active_pairs[uid]
    elif uid in chat_history:
        partner_id = chat_history[uid]

    if not partner_id:
        bot.answer_callback_query(call.id, "No partner to report", show_alert=True)
        return

    _, report_type = call.data.split(":")
    report_type_map = {
        "child": "Child Abuse",
        "porn": "Pornography",
        "spam": "Spamming",
        "scam": "Scam/Fraud",
        "other": "Other"
    }
    report_type_name = report_type_map.get(report_type, "Other")

    reporter = db_get_user(uid)
    reported = db_get_user(partner_id)
    reporter_name = reporter["first_name"] or reporter["username"] or "Unknown"
    reported_name = reported["first_name"] or reported["username"] or "Unknown"

    db_add_report(uid, partner_id, report_type, report_type_name)
    bot.answer_callback_query(call.id, "Report submitted", show_alert=True)
    bot.send_message(uid, "✅ Your report has been submitted. Admins will review it soon.")

    try:
        admin_msg = (
            "⚠️ NEW REPORT\n\n"
            f"Report Type: {report_type_name}\n"
            f"Reporter: {reporter_name} ({uid})\n"
            f"Reported User: {reported_name} ({partner_id})\n"
            f"Timestamp: {datetime.utcnow().isoformat()}\n\n"
            "To ban this user:\n"
            f"/ban {partner_id} 24 Reported for {report_type}\n"
            "Or permanent:\n"
            f"/ban {partner_id} permanent Reported for {report_type}"
        )
        bot.send_message(ADMIN_ID, admin_msg)
    except:
        pass

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    logger.info(f"cmd_ban invoked by {message.from_user.id}")
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "You are not admin")
        return

    try:
        text = message.text
        parts = text.split(maxsplit=3)

        if len(parts) < 2:
            ban_help_text = (
                "Usage: /ban <user_id> [hours/permanent] [reason]\n\n"
                "Examples:\n"
                "/ban 123456789 24 Vulgar messages\n"
                "/ban 987654321 permanent Child abuse\n"
                "/ban 111111111 12 Spamming"
            )
            bot.reply_to(message, ban_help_text)
            return

        target_id = int(parts[1])
        hours = 24
        permanent = False
        reason = "Banned by admin"

        if len(parts) >= 3:
            if parts[2].lower() == "permanent":
                permanent = True
                hours = None
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
                ban_msg_perm = (
                    "🚫 You have been PERMANENTLY BANNED.\n"
                    f"Reason: {reason}\n"
                    "You cannot use this bot anymore."
                )
                bot.send_message(target_id, ban_msg_perm)
            except:
                pass
        else:
            bot.reply_to(message, f"✅ User {target_id} banned for {hours} hours. {reason}")
            try:
                ban_msg_temp = (
                    f"🚫 You have been banned for {hours} hours.\n"
                    f"Reason: {reason}\n"
                    "Ban will be lifted automatically."
                )
                bot.send_message(target_id, ban_msg_temp)
            except:
                pass

        logger.info(f"Admin {message.from_user.id} banned user {target_id}")
    except ValueError:
        bot.reply_to(message, "Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "You are not admin")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /unban <user_id>")
            return

        target_id = int(parts[1])
        db_unban_user(target_id)
        user_warnings[target_id] = 0

        bot.reply_to(message, f"✅ User {target_id} unbanned")
        try:
            bot.send_message(target_id, "✅ Your ban has been lifted! You can use the bot again.")
        except:
            pass
        logger.info(f"Admin {message.from_user.id} unbanned user {target_id}")
    except ValueError:
        bot.reply_to(message, "Invalid user ID. Must be a number.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

def match_users():
    global waiting_random, waiting_opposite, active_pairs

    # Match random users (same gender or any)
    while len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1

        u1_data = db_get_user(u1)
        u2_data = db_get_user(u2)

        bot.send_message(u1, format_partner_found_message(u2_data, u1), reply_markup=chat_keyboard())
        bot.send_message(u2, format_partner_found_message(u1_data, u2), reply_markup=chat_keyboard())

    # Match opposite gender users
    i = 0
    while i < len(waiting_opposite):
        uid, gen = waiting_opposite[i]
        found = None
        for j, (other_uid, other_gen) in enumerate(waiting_opposite):
            if other_uid != uid and other_gen != gen:
                found = other_uid
                waiting_opposite.pop(j)
                break

        if found:
            waiting_opposite.pop(i)
            active_pairs[uid] = found
            active_pairs[found] = uid

            u1_data = db_get_user(uid)
            u2_data = db_get_user(found)

            bot.send_message(uid, format_partner_found_message(u2_data, uid), reply_markup=chat_keyboard())
            bot.send_message(found, format_partner_found_message(u1_data, found), reply_markup=chat_keyboard())
        else:
            i += 1

@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handler_text(m):
    uid = m.from_user.id
    text = m.text.strip()  # ✅ Clean whitespace

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid)

    if not u["gender"]:
        bot.send_message(uid, "Please set your gender first using /start")
        return

    if not u["age"]:
        try:
            age = int(text)
            if age < 12 or age > 99:  # ✅ Age validation 12-99
                bot.send_message(uid, "Please enter a valid age between 12 and 99.")
                return
            db_set_age(uid, age)
            bot.send_message(uid, f"✅ Age set to {age}\n\nNow, please enter your country name:")
            return
        except:
            bot.send_message(uid, "Please enter age as numbers only (e.g., 21)")
            return

    if not u["country"]:
        country_info = get_country_info(text)
        if not country_info:
            bot.send_message(uid, f"'{text}' is not a valid country name. Please enter a valid country (e.g., India, United States)")
            return
        country_name, country_flag = country_info
        db_set_country(uid, country_name, country_flag)
        country_complete_msg = (
            f"✅ Country set to {country_flag} {country_name}\n\n"
            "Profile complete! Start searching for partners"
        )
        bot.send_message(uid, country_complete_msg, reply_markup=main_keyboard(uid))
        return

    # ✅ BUTTON TEXT MATCHING - Check exact text
    if text == "📊 Stats":
        u = db_get_user(uid)
        if u:
            premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free User"
            gender_emoji = "👨" if u["gender"] == "Male" else "👩"
            stats_msg = (
                "📊 YOUR STATS\n\n"
                f"👤 Gender: {gender_emoji} {u['gender']}\n"
                f"🎂 Age: {u['age']}\n"
                f"🌍 Country: {u['country_flag']} {u['country']}\n\n"
                f"📨 Messages Sent: {u['messages_sent']}\n"
                f"✅ Media Approved: {u['media_approved']}\n"
                f"❌ Media Rejected: {u['media_rejected']}\n\n"
                f"👥 People Referred: {u['referral_count']}\n"
                f"{premium_status}"
            )
            bot.send_message(uid, stats_msg, reply_markup=chat_keyboard())
        return

    if text == "⚠️ Report":
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

    if text == "🔒 Opposite Gender (Premium)":
        premium_locked_msg = (
            "💎 This feature requires Premium!\n\n"
            f"Invite 3 friends to unlock 1 hour premium.\n"
            "Use /refer to get your link!"
        )
        bot.send_message(uid, premium_locked_msg)
        return

    if text == "🎯 Search Opposite Gender":
        cmd_search_opposite(m)
        return

    if text == "⚙️ Settings":
        cmd_settings(m)
        return

    if text == "👥 Refer":
        cmd_refer(m)
        return

    # ✅ Check for banned content
    if is_banned_content(text):
        warn_user(uid, "Vulgar words or links")
        return

    # ✅ Send message to partner
    if uid in active_pairs:
        partner = active_pairs[uid]
        try:
            bot.send_message(partner, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            bot.send_message(uid, "Could not send message")
    else:
        bot.send_message(uid, "Not connected. Use search commands.", reply_markup=main_keyboard(uid))

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker'])
def handle_media(m):
    uid = m.from_user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned")
        return

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
    if u and u["media_approved"] and int(u["media_approved"]) > 0:
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
            logger.error(f"Error forwarding media: {e}")
            bot.send_message(uid, "Could not forward media")
        return

    token = generate_media_token(uid)
    pending_media[token] = {
        "sender": uid,
        "partner": partner,
        "media_type": media_type,
        "file_id": media_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}")
    )

    try:
        consent_msg = bot.send_message(partner, "Your partner wants to send a media. Tap Accept to view it, or Reject to decline.", reply_markup=markup)
        pending_media[token]["consent_chat_id"] = consent_msg.chat.id
        pending_media[token]["consent_message_id"] = consent_msg.message_id
        bot.send_message(uid, "Consent request sent to your partner. Wait for them to Accept.")
    except Exception as e:
        logger.error(f"Error sending consent: {e}")
        bot.send_message(uid, "Could not request consent from partner.")
        if token in pending_media:
            del pending_media[token]

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "This media is no longer available.", show_alert=True)
            return

        sender_id = meta["sender"]
        partner_id = meta["partner"]
        media_type = meta["media_type"]
        file_id = meta["file_id"]

        try:
            if media_type == "photo":
                bot.send_photo(partner_id, file_id, caption="Media delivered (accepted).")
            elif media_type == "document":
                bot.send_document(partner_id, file_id, caption="Document delivered (accepted).")
            elif media_type == "video":
                bot.send_video(partner_id, file_id, caption="Video delivered (accepted).")
            elif media_type == "animation":
                bot.send_animation(partner_id, file_id, caption="Animation delivered (accepted).")
            elif media_type == "sticker":
                bot.send_sticker(partner_id, file_id)
        except Exception as e:
            logger.error(f"Error delivering media: {e}")
            try:
                bot.send_message(partner_id, "Could not deliver the media.")
            except:
                pass
            try:
                bot.send_message(sender_id, "Your media could not be delivered.")
            except:
                pass
            if token in pending_media:
                del pending_media[token]
            bot.answer_callback_query(call.id, "Error delivering media", show_alert=True)
            return

        try:
            db_set_media_sharing(sender_id, True)
            db_increment_media(sender_id, "approved")
        except:
            pass

        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED and delivered.")
        except:
            pass

        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("✅ Partner accepted - media delivered.", chat_id, msg_id)
        except:
            try:
                bot.edit_message_text("✅ Partner accepted - media delivered.", call.message.chat.id, call.message.message_id)
            except:
                pass

        bot.answer_callback_query(call.id, "Media Approved", show_alert=False)
        if token in pending_media:
            del pending_media[token]
    except Exception as e:
        logger.error(f"Error in approve_media_cb: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media_cb(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "This media is no longer available.", show_alert=True)
            return

        sender_id = meta["sender"]
        media_type = meta["media_type"]

        try:
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED. It was not delivered.")
            db_increment_media(sender_id, "rejected")
        except:
            pass

        try:
            chat_id = meta.get("consent_chat_id", call.message.chat.id)
            msg_id = meta.get("consent_message_id", call.message.message_id)
            bot.edit_message_text("❌ Partner rejected this media.", chat_id, msg_id)
        except:
            try:
                bot.edit_message_text("❌ Partner rejected this media.", call.message.chat.id, call.message.message_id)
            except:
                pass

        bot.answer_callback_query(call.id, "Media Rejected", show_alert=False)
        if token in pending_media:
            del pending_media[token]
    except Exception as e:
        logger.error(f"Error in reject_media_cb: {e}")
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# -------- BOT POLLING THREAD --------
def run_bot_polling():
    logger.info("Starting Telegram bot polling...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")

# -------- MAIN EXECUTION --------
if __name__ == "__main__":
    init_db()
    logger.info("Database initialized")
    logger.info("GhostTalk Premium Bot v2 - Starting with ALL FIXES!")

    keep_alive_pinger()

    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    logger.info("Bot polling thread started")

    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"Starting Flask on port {PORT}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info(f"Bot username: {BOT_USERNAME}")
    logger.info(f"Age validation: 12-99 years")
    logger.info(f"Search matching: FIXED")

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
