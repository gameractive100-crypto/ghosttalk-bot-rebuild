#!/usr/bin/env python3
"""
GhostTalk Bot - v4.0
A real chat app, by a real developer.
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

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.getenv("DATA_PATH") or os.path.join(BASE_DIR, "data")
os.makedirs(DATA_PATH, exist_ok=True)
DB_PATH = os.getenv("DB_PATH") or os.path.join(DATA_PATH, "ghosttalk.db")

API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))

REPORTS_FOR_BAN = 10
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1
RECONNECT_WINDOW_MINUTES = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.info(f"Starting bot... DB: {DB_PATH}")

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Fix \n display
try:
    _orig_send = bot.send_message
    _orig_callback = bot.answer_callback_query
except:
    _orig_send = None
    _orig_callback = None

def fix_newlines(text):
    return text.replace("\\n", "\n") if isinstance(text, str) else text

if _orig_send:
    bot.send_message = lambda chat_id, text, *args, **kwargs: _orig_send(chat_id, fix_newlines(text), *args, **kwargs)
if _orig_callback:
    bot.answer_callback_query = lambda cid, text=None, *args, **kwargs: _orig_callback(cid, fix_newlines(text) if text else text, *args, **kwargs)

# Runtime
waiting_random = []
waiting_opposite = []
active_pairs = {}
pending_media = {}
chat_history = {}
report_reason_pending = {}
pending_country = set()
last_partner_disconnect = {}

# Words
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs", "tits", "ass", "asshole",
    "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography", "rape", "molest", "anj", "anjing", "babi", "asu",
    "kontl", "kontol", "puki", "memek", "jembut", "mc", "randi", "randika", "maderchod", "bsdk", "lauda", "lund", "chut", "choot",
    "chot", "chuut", "gand", "gaand", "ma ka lauda", "mkc", "teri ma ki chut", "teri ma ki chuut"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# Countries
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

def get_country_info(inp):
    if not inp:
        return None
    norm = inp.strip().lower()
    norm = COUNTRY_ALIASES.get(norm, norm)
    if norm in COUNTRIES:
        return norm.title(), COUNTRIES[norm]
    return None

# Database
def get_conn():
    db_parent = os.path.dirname(DB_PATH) or BASE_DIR
    os.makedirs(db_parent, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    return c

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
            timestamp TEXT
        )
        """)
        conn.commit()

def db_user(uid):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT user_id, username, first_name, gender, age, country, country_flag,
            messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until
            FROM users WHERE user_id=?
        """, (uid,)).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1], "first_name": row[2], "gender": row[3], 
            "age": row[4], "country": row[5], "country_flag": row[6], "messages_sent": row[7],
            "media_approved": row[8], "media_rejected": row[9], "referral_code": row[10],
            "referral_count": row[11], "premium_until": row[12]
        }

def db_new_user(user):
    uid = user.id
    if db_user(uid):
        return
    ref = f"REF{uid}{random.randint(1000,99999)}"
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, user.username or "", user.first_name or "", None, None, None, None, 
              datetime.utcnow().isoformat(), ref))
        conn.commit()

def db_set_gender(uid, g):
    with get_conn() as conn:
        conn.execute("UPDATE users SET gender=? WHERE user_id=?", (g, uid))
        conn.commit()

def db_set_age(uid, a):
    with get_conn() as conn:
        conn.execute("UPDATE users SET age=? WHERE user_id=?", (a, uid))
        conn.commit()

def db_set_country(uid, c, f):
    with get_conn() as conn:
        conn.execute("UPDATE users SET country=?, country_flag=? WHERE user_id=?", (c, f, uid))
        conn.commit()

def is_premium(uid):
    if uid == ADMIN_ID:
        return True
    u = db_user(uid)
    if not u or not u["premium_until"]:
        return False
    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.utcnow()
    except:
        return False

def set_premium(uid, until):
    try:
        dt = f"{until}T23:59:59" if len(until) == 10 else until
        datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute("UPDATE users SET premium_until=? WHERE user_id=?", (dt, uid))
            conn.commit()
        return True
    except:
        return False

def remove_premium(uid):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until=NULL WHERE user_id=?", (uid,))
        conn.commit()

def get_ref_link(uid):
    user = db_user(uid)
    try:
        bot_user = bot.get_me().username
    except:
        bot_user = None
    if user and bot_user:
        return f"https://t.me/{bot_user}?start={user['referral_code']}"
    if user:
        return f"REFCODE:{user['referral_code']}"
    return None

def add_referral(uid):
    with get_conn() as conn:
        conn.execute("UPDATE users SET referral_count=referral_count+1 WHERE user_id=?", (uid,))
        conn.commit()
        u = db_user(uid)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            until = (datetime.utcnow() + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            conn.execute("UPDATE users SET premium_until=?, referral_count=0 WHERE user_id=?", (until, uid))
            conn.commit()
            try:
                bot.send_message(uid, f"Yo! You got premium for {PREMIUM_DURATION_HOURS} hour! 🎉\nEnjoy opposite gender search now.")
            except:
                pass

def is_banned(uid):
    if uid == ADMIN_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE user_id=?", (uid,)).fetchone()
        if not row:
            return False
        ban_until, perm = row
        if perm:
            return True
        if ban_until:
            try:
                return datetime.fromisoformat(ban_until) > datetime.utcnow()
            except:
                return False
        return False

def ban_user(uid, hours=None, perm=False, reason=""):
    with get_conn() as conn:
        if perm:
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                         (uid, None, 1, reason))
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason) VALUES (?, ?, ?, ?)",
                         (uid, until, 0, reason))
        conn.commit()

def unban_user(uid):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE user_id=?", (uid,))
        conn.commit()

def count_reports(uid):
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM reports WHERE reported_id=?", (uid,)).fetchone()
        return row[0] if row else 0

def add_report(reporter, reported):
    with get_conn() as conn:
        conn.execute("INSERT INTO reports (reporter_id, reported_id, timestamp) VALUES (?, ?, ?)",
                    (reporter, reported, datetime.utcnow().isoformat()))
        conn.commit()

# Helpers
def resolve_id(ident):
    if not ident:
        return None
    ident = ident.strip()
    try:
        return int(ident)
    except:
        pass
    name = ident.lstrip("@").strip()
    if not name:
        return None
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE LOWER(username)=LOWER(?)", (name,)).fetchone()
            if row:
                return row[0]
    except:
        pass
    return None

def has_bad_content(text):
    if not text:
        return False
    if LINK_PATTERN.search(text):
        return True
    for p in BANNED_PATTERNS:
        if p.search(text):
            return True
    return False

def remove_queues(uid):
    global waiting_random, waiting_opposite
    if uid in waiting_random:
        waiting_random.remove(uid)
    waiting_opposite = [(u, g) for u, g in waiting_opposite if u != uid]

def save_msg(uid, cid, mid):
    if uid not in chat_history:
        chat_history[uid] = []
    chat_history[uid].append((cid, mid))
    if len(chat_history[uid]) > 50:
        chat_history[uid].pop(0)

def user_name(uid):
    u = db_user(uid)
    if u and u.get("username"):
        return f"@{u['username']}"
    return str(uid)

def partner_msg(partner, viewer):
    gender_emoji = "👨" if partner["gender"] == "Male" else ("👩" if partner["gender"] == "Female" else "")
    age = str(partner["age"]) if partner["age"] else "?"
    flag = partner["country_flag"] or "🌍"
    country = partner["country"] or "?"
    msg = f"Great! Found someone:\n\n{age} years old • {gender_emoji} {partner['gender']}\nFrom {flag} {country}\n\nLet's chat!"
    return msg

# Matching
def match_users():
    global waiting_random, waiting_opposite, active_pairs
    
    i = 0
    while i < len(waiting_opposite):
        uid, gender = waiting_opposite[i]
        opp = "Male" if gender == "Female" else "Female"
        match_idx = None
        for j, other in enumerate(waiting_random):
            other_data = db_user(other)
            if other_data and other_data['gender'] == opp:
                match_idx = j
                break
        if match_idx is not None:
            found = waiting_random.pop(match_idx)
            waiting_opposite.pop(i)
            active_pairs[uid] = found
            active_pairs[found] = uid
            u1 = db_user(uid)
            u2 = db_user(found)
            bot.send_message(uid, partner_msg(u2, uid), reply_markup=chat_kb())
            bot.send_message(found, partner_msg(u1, found), reply_markup=chat_kb())
            logger.info(f"Matched {uid} <-> {found}")
            return
        else:
            i += 1
    
    while len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1
        u1_data = db_user(u1)
        u2_data = db_user(u2)
        bot.send_message(u1, partner_msg(u2_data, u1), reply_markup=chat_kb())
        bot.send_message(u2, partner_msg(u1_data, u2), reply_markup=chat_kb())
        logger.info(f"Random match {u1} <-> {u2}")

# Keyboards
def main_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("🔍 Find Someone")
    u = db_user(uid)
    if u and u["gender"]:
        if is_premium(uid):
            kb.add("💕 Find Opposite Gender")
        else:
            kb.add("💎 Opposite Gender (Premium)")
    kb.add("❌ Stop")
    kb.add("⚙️ Settings", "👥 Refer")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add("👤 Info")
    kb.add("➡️ Next", "❌ Stop")
    return kb

def report_kb():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Report This Person", callback_data="rep:confirm"))
    return markup

# Flask
@app.route("/")
def home():
    return "Bot running!", 200

@app.route("/health")
def health():
    return {"ok": True}, 200

# Commands
@bot.message_handler(commands=['start'])
def cmd_start(m):
    user = m.from_user
    db_new_user(user)
    
    if is_banned(user.id):
        bot.send_message(user.id, "You're banned lol")
        return
    
    if len(m.text.split()) > 1:
        ref = m.text.split()[1]
        with get_conn() as conn:
            referrer = conn.execute("SELECT user_id FROM users WHERE referral_code=?", (ref,)).fetchone()
            if referrer and referrer[0] != user.id:
                add_referral(referrer[0])
    
    u = db_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
            types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
        )
        bot.send_message(user.id, "Yo! What's your gender?", reply_markup=markup)
    elif not u["age"]:
        bot.send_message(user.id, "How old are you? (12-99)")
        bot.register_next_step_handler(m, process_age)
    elif not u["country"]:
        bot.send_message(user.id, "Where you from? (Can't change later without premium)")
        bot.register_next_step_handler(m, process_country)
    else:
        status = "Premium ✨" if is_premium(user.id) else "Free"
        welcome = f"Hey there!\n\n{u['gender']}, {u['age']} years • {u['country_flag']} {u['country']}\nStatus: {status}\n\nReady to chat?"
        bot.send_message(user.id, welcome, reply_markup=main_kb(user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def set_gender(call):
    uid = call.from_user.id
    db_new_user(call.from_user)
    
    if is_banned(uid):
        bot.answer_callback_query(call.id, "You're banned", show_alert=True)
        return
    
    _, g = call.data.split(":")
    gender = "Male" if g == "male" else "Female"
    u = db_user(uid)
    
    if u and u["gender"] == gender:
        bot.answer_callback_query(call.id, "Already set!", show_alert=True)
        return
    
    if u and u["gender"]:
        bot.answer_callback_query(call.id, "Get premium to change gender", show_alert=True)
        return
    
    db_set_gender(uid, gender)
    bot.answer_callback_query(call.id, "Got it!")
    try:
        bot.edit_message_text(f"Gender: {gender} ✓", call.message.chat.id, call.message.message_id)
    except:
        pass
    
    bot.send_message(uid, "How old? (12-99)")
    bot.register_next_step_handler(call.message, process_age)

def process_age(m):
    uid = m.from_user.id
    text = (m.text or "").strip()
    
    if not text.isdigit():
        bot.send_message(uid, "Enter your age as a number (like 21)")
        bot.register_next_step_handler(m, process_age)
        return
    
    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, "Age must be 12-99")
        bot.register_next_step_handler(m, process_age)
        return
    
    db_set_age(uid, age)
    bot.send_message(uid, f"Cool, you're {age}! Now where you from? (Can't change later without premium)")
    pending_country.add(uid)
    bot.register_next_step_handler(m, process_country)

def process_country(m):
    uid = m.from_user.id
    text = (m.text or "").strip()
    
    if uid not in pending_country:
        bot.send_message(uid, "Go to settings to change profile")
        return
    
    info = get_country_info(text)
    if not info:
        bot.send_message(uid, f"Hmm, '{text}' not found. Try another country:")
        bot.register_next_step_handler(m, process_country)
        return
    
    country, flag = info
    db_set_country(uid, country, flag)
    pending_country.discard(uid)
    
    bot.send_message(uid, f"Perfect! {flag} {country}\n\nProfile done. Let's find someone!", reply_markup=main_kb(uid))

@bot.message_handler(commands=['settings'])
def cmd_settings(m):
    uid = m.from_user.id
    u = db_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first")
        return
    
    status = "Premium ✨" if is_premium(uid) else "Free"
    gender = "👨 Male" if u["gender"] == "Male" else ("👩 Female" if u["gender"] == "Female" else "?")
    text = (
        f"Your Profile:\n\n"
        f"{gender}\n"
        f"Age: {u['age']}\n"
        f"Location: {u['country_flag']} {u['country']}\n\n"
        f"Messaged: {u['messages_sent']}\n"
        f"Referred: {u['referral_count']}\n"
        f"Status: {status}\n\n"
        "Change:"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔗 My Ref Link", callback_data="ref:link"))
    markup.row(
        types.InlineKeyboardButton("👨 Male", callback_data="sex:male"),
        types.InlineKeyboardButton("👩 Female", callback_data="sex:female")
    )
    markup.row(types.InlineKeyboardButton("🎂 Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("🌍 Country", callback_data="set:country"))
    
    bot.send_message(uid, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def change_gender(call):
    uid = call.from_user.id
    if uid == ADMIN_ID:
        return set_gender(call)
    if not is_premium(uid):
        bot.answer_callback_query(call.id, "Premium only to change gender", show_alert=True)
        return
    _, g = call.data.split(":")
    gender = "Male" if g == "male" else "Female"
    db_set_gender(uid, gender)
    bot.answer_callback_query(call.id, f"Changed to {gender}!")
    bot.send_message(uid, f"Gender: {gender} ✓", reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, "New age?")
    bot.register_next_step_handler(call.message, process_age)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref:"))
def referral(call):
    uid = call.from_user.id
    _, action = call.data.split(":")
    if action == "link":
        u = db_user(uid)
        if not u:
            bot.answer_callback_query(call.id, "Error!", show_alert=True)
            return
        link = get_ref_link(uid)
        remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]
        text = (
            f"Your Link: {link}\n\n"
            f"Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
            f"Reward: {PREMIUM_DURATION_HOURS} hour premium\n\n"
        )
        if remaining > 0:
            text += f"Invite {remaining} more to unlock premium!"
        else:
            text += "You got premium! Keep inviting for more!"
        bot.send_message(uid, text)
        bot.answer_callback_query(call.id, "Copied link!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set:"))
def set_country(call):
    uid = call.from_user.id
    u = db_user(uid)
    if u and u["country"] and not is_premium(uid):
        bot.answer_callback_query(call.id, "Premium only to change country", show_alert=True)
        return
    bot.send_message(uid, "Which country?")
    pending_country.add(uid)
    bot.register_next_step_handler(call.message, process_country)

@bot.message_handler(commands=['refer'])
def cmd_refer(m):
    uid = m.from_user.id
    u = db_user(uid)
    if not u:
        bot.send_message(uid, "Use /start")
        return
    link = get_ref_link(uid)
    remaining = PREMIUM_REFERRALS_NEEDED - u["referral_count"]
    text = (
        f"Share & Get Premium:\n\n"
        f"Link: {link}\n\n"
        f"Referred: {u['referral_count']}/{PREMIUM_REFERRALS_NEEDED}\n"
        f"Reward: {PREMIUM_DURATION_HOURS} hour access\n\n"
    )
    if remaining > 0:
        text += f"Invite {remaining} more!"
    else:
        text += "You're premium!"
    bot.send_message(uid, text)

@bot.message_handler(commands=['search'])
def cmd_search(m):
    uid = m.from_user.id
    if is_banned(uid):
        bot.send_message(uid, "You're banned")
        return
    u = db_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Finish your profile first (/start)")
        return
    if uid in active_pairs:
        bot.send_message(uid, "Already chatting! Use /next")
        return
    in_random = uid in waiting_random
    in_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_random or in_opposite:
        bot.send_message(uid, "Already searching. Use /stop to cancel")
        return
    remove_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "Finding someone... hold on")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opp(m):
    uid = m.from_user.id
    if is_banned(uid):
        bot.send_message(uid, "You're banned")
        return
    if not is_premium(uid):
        bot.send_message(uid, "Premium only. Refer friends to unlock!")
        return
    u = db_user(uid)
    if not u or not u["gender"] or not u["age"] or not u["country"]:
        bot.send_message(uid, "Finish profile first")
        return
    if uid in active_pairs:
        bot.send_message(uid, "Already chatting!")
        return
    in_random = uid in waiting_random
    in_opposite = any(uid == w[0] for w in waiting_opposite)
    if in_random or in_opposite:
        bot.send_message(uid, "Already searching!")
        return
    remove_queues(uid)
    waiting_opposite.append((uid, u["gender"]))
    bot.send_message(uid, "Finding opposite gender... one sec")
    match_users()

@bot.message_handler(commands=['stop'])
def cmd_stop(m):
    uid = m.from_user.id
    remove_queues(uid)
    disc_user(uid)
    bot.send_message(uid, "Stopped. See you!", reply_markup=main_kb(uid))

@bot.message_handler(commands=['next'])
def cmd_next(m):
    uid = m.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "Not chatting. Search first")
        return
    disc_user(uid)
    bot.send_message(uid, "Next one coming...", reply_markup=main_kb(uid))
    waiting_random.append(uid)
    match_users()

@bot.message_handler(commands=['reconnect'])
def cmd_reconnect(m):
    uid = m.from_user.id
    
    if uid not in last_partner_disconnect:
        bot.send_message(uid, "No one to reconnect with")
        return
    
    pdata = last_partner_disconnect[uid]
    partner = pdata["partner_id"]
    disc_time = pdata["disconnect_time"]
    
    elapsed = (datetime.utcnow() - disc_time).total_seconds() / 60
    if elapsed > RECONNECT_WINDOW_MINUTES:
        bot.send_message(uid, "Window expired. Find someone new!")
        del last_partner_disconnect[uid]
        return
    
    p = db_user(partner)
    if not p:
        bot.send_message(uid, "Person not found")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Yes", callback_data=f"recon:accept:{uid}"),
        types.InlineKeyboardButton("Nope", callback_data=f"recon:decline:{uid}")
    )
    
    try:
        bot.send_message(partner, f"{user_name(uid)} wants to chat again. Accept?", reply_markup=markup)
        bot.send_message(uid, "Sent them a request...")
    except:
        bot.send_message(uid, "Couldn't send request")

@bot.callback_query_handler(func=lambda c: c.data.startswith("recon:"))
def recon_reply(call):
    responder = call.from_user.id
    try:
        _, action, req_str = call.data.split(":")
        requester = int(req_str)
    except:
        bot.answer_callback_query(call.id, "Expired", show_alert=True)
        return
    
    if action == "decline":
        try:
            bot.send_message(requester, "They said nope")
        except:
            pass
        bot.answer_callback_query(call.id, "Declined")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return
    
    if action == "accept":
        active_pairs[requester] = responder
        active_pairs[responder] = requester
        
        try:
            bot.send_message(requester, "They said yes! 🔥", reply_markup=chat_kb())
            bot.send_message(responder, "Connected!", reply_markup=chat_kb())
        except:
            pass
        
        bot.answer_callback_query(call.id, "Connected!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        if requester in last_partner_disconnect:
            del last_partner_disconnect[requester]

@bot.message_handler(commands=['report'])
def cmd_report(m):
    uid = m.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "Report them while chatting with them")
        return
    bot.send_message(uid, "Report this person?", reply_markup=report_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def report(call):
    uid = call.from_user.id
    partner = active_pairs.get(uid)
    
    if not partner:
        bot.answer_callback_query(call.id, "No one to report", show_alert=True)
        return
    
    _, action = call.data.split(":")
    
    if action == "confirm":
        add_report(uid, partner)
        cnt = count_reports(partner)
        
        if cnt >= REPORTS_FOR_BAN:
            ban_user(partner, hours=TEMP_BAN_HOURS, reason="Too many reports")
            try:
                bot.send_message(partner, "Banned for 24 hours. Thanks for keeping it clean!")
            except:
                pass
            disc_user(partner)
        
        bot.send_message(uid, "Thanks for reporting. Keep chatting!", reply_markup=chat_kb())
        bot.answer_callback_query(call.id, "Reported")

def disc_user(uid):
    global active_pairs
    if uid in active_pairs:
        partner = active_pairs[uid]
        
        last_partner_disconnect[uid] = {
            "partner_id": partner,
            "disconnect_time": datetime.utcnow()
        }
        
        try:
            del active_pairs[partner]
        except:
            pass
        try:
            del active_pairs[uid]
        except:
            pass
        
        try:
            bot.send_message(partner, "They left. Use /reconnect to find them again (5 min window)", reply_markup=main_kb(partner))
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Report", callback_data=f"report_req:{partner}"))
            bot.send_message(uid, "Left the chat. Need to report?", reply_markup=markup)
        except:
            pass
        
        remove_queues(uid)
        remove_queues(partner)

@bot.callback_query_handler(func=lambda c: c.data.startswith("report_req:"))
def report_req(call):
    try:
        reporter = call.from_user.id
        _, reported_str = call.data.split(":", 1)
        try:
            reported = int(reported_str)
        except:
            reported = resolve_id(reported_str)
        if not reported:
            bot.answer_callback_query(call.id, "Invalid", show_alert=True)
            return
        report_reason_pending[reporter] = reported
        bot.answer_callback_query(call.id, "Type reason")
        bot.send_message(reporter, "Why report them?")
    except:
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(content_types=['photo', 'document', 'video', 'animation', 'sticker', 'audio', 'voice'])
def handle_media(m):
    uid = m.from_user.id
    save_msg(uid, m.chat.id, m.message_id)
    
    if is_banned(uid):
        bot.send_message(uid, "You're banned")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "Not connected")
        return
    
    partner = active_pairs[uid]
    mtype = m.content_type
    
    if mtype == "photo":
        mid = m.photo[-1].file_id
    elif mtype == "document":
        mid = m.document.file_id
    elif mtype == "video":
        mid = m.video.file_id
    elif mtype == "animation":
        mid = m.animation.file_id
    elif mtype == "sticker":
        mid = m.sticker.file_id
    elif mtype == "audio":
        mid = m.audio.file_id
    elif mtype == "voice":
        mid = m.voice.file_id
    else:
        return
    
    u = db_user(uid)
    if u and u["media_approved"]:
        try:
            if mtype == "photo":
                bot.send_photo(partner, mid)
            elif mtype == "document":
                bot.send_document(partner, mid)
            elif mtype == "video":
                bot.send_video(partner, mid)
            elif mtype == "animation":
                bot.send_animation(partner, mid)
            elif mtype == "sticker":
                bot.send_sticker(partner, mid)
            elif mtype == "audio":
                bot.send_audio(partner, mid)
            elif mtype == "voice":
                bot.send_voice(partner, mid)
            with get_conn() as conn:
                conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (uid,))
                conn.commit()
        except:
            bot.send_message(uid, "Couldn't send")
        return
    
    for token, meta in list(pending_media.items()):
        try:
            if meta.get("sender") == uid and meta.get("partner") == partner:
                bot.send_message(uid, "Already asked for permission")
                return
        except:
            continue
    
    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    pending_media[token] = {
        "sender": uid, "partner": partner, "media_type": mtype, 
        "file_id": mid, "timestamp": datetime.utcnow().isoformat()
    }
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("OK", callback_data=f"app:{token}"),
        types.InlineKeyboardButton("Nope", callback_data=f"rej:{token}")
    )
    
    try:
        msg = bot.send_message(partner, f"They want to send {mtype}. Cool?", reply_markup=markup)
        pending_media[token]["consent_msg_id"] = msg.message_id
        bot.send_message(uid, "Waiting for their answer...")
    except:
        bot.send_message(uid, "Couldn't ask")
        pending_media.pop(token, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def approve_media(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Expired", show_alert=True)
            return
        
        sender = meta["sender"]
        mid = meta["file_id"]
        mtype = meta["media_type"]
        cmid = meta.get("consent_msg_id")
        
        try:
            if mtype == "photo":
                bot.send_photo(call.message.chat.id, mid)
            elif mtype == "document":
                bot.send_document(call.message.chat.id, mid)
            elif mtype == "video":
                bot.send_video(call.message.chat.id, mid)
            elif mtype == "animation":
                bot.send_animation(call.message.chat.id, mid)
            elif mtype == "sticker":
                bot.send_sticker(call.message.chat.id, mid)
            elif mtype == "audio":
                bot.send_audio(call.message.chat.id, mid)
            elif mtype == "voice":
                bot.send_voice(call.message.chat.id, mid)
        except:
            try:
                bot.send_message(call.message.chat.id, "Couldn't send")
                bot.send_message(sender, "Couldn't deliver")
            except:
                pass
            pending_media.pop(token, None)
            bot.answer_callback_query(call.id, "Error", show_alert=True)
            return
        
        with get_conn() as conn:
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE user_id=?", (sender,))
            conn.commit()
        
        try:
            bot.send_message(sender, "They said yes! ✓")
        except:
            pass
        
        try:
            if cmid:
                bot.delete_message(call.message.chat.id, cmid)
        except:
            pass
        
        bot.answer_callback_query(call.id, "Approved")
        pending_media.pop(token, None)
    except:
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def reject_media(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "Expired", show_alert=True)
            return
        
        sender = meta["sender"]
        mtype = meta["media_type"]
        
        try:
            bot.send_message(sender, "They said nope")
            with get_conn() as conn:
                conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?", (sender,))
                conn.commit()
        except:
            pass
        
        bot.answer_callback_query(call.id, "Rejected")
        pending_media.pop(token, None)
    except:
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handler(m):
    uid = m.from_user.id
    text = (m.text or "").strip()
    
    if uid in report_reason_pending:
        reported = report_reason_pending.pop(uid, None)
        if reported:
            add_report(uid, reported)
            cnt = count_reports(reported)
            
            if cnt >= REPORTS_FOR_BAN:
                ban_user(reported, hours=TEMP_BAN_HOURS, reason="Too many")
                try:
                    bot.send_message(reported, "Banned 24h. Thanks for keeping it clean!")
                except:
                    pass
                disc_user(reported)
            
            bot.send_message(uid, "Reported. Thanks!")
        return
    
    if is_banned(uid):
        bot.send_message(uid, "You're banned")
        return
    
    db_new_user(m.from_user)
    u = db_user(uid)
    
    if not u["gender"]:
        bot.send_message(uid, "Set gender first")
        return
    
    if not u["age"]:
        try:
            age = int(text)
            if age < 12 or age > 99:
                bot.send_message(uid, "12-99 only")
                return
            db_set_age(uid, age)
            bot.send_message(uid, f"Cool! Now which country? (Can't change later)")
            pending_country.add(uid)
            bot.register_next_step_handler(m, process_country)
            return
        except:
            bot.send_message(uid, "Send age as number")
            return
    
    if uid in pending_country and not u.get("country"):
        try:
            process_country(m)
        except:
            bot.send_message(uid, "Invalid country")
        return
    
    # Buttons
    if text == "👤 Info":
        u = db_user(uid)
        if u:
            status = "Premium ✨" if is_premium(uid) else "Free"
            gender = "👨 Male" if u["gender"] == "Male" else ("👩 Female" if u["gender"] == "Female" else "?")
            msg = (
                f"{gender}\n"
                f"Age: {u['age']}\n"
                f"From: {u['country_flag']} {u['country']}\n\n"
                f"Messages: {u['messages_sent']}\n"
                f"Referred: {u['referral_count']}\n"
                f"Status: {status}"
            )
            bot.send_message(uid, msg, reply_markup=chat_kb())
        return
    
    if text == "➡️ Next":
        cmd_next(m)
        return
    if text == "❌ Stop":
        cmd_stop(m)
        return
    if text == "🔍 Find Someone":
        cmd_search(m)
        return
    if text == "💕 Find Opposite Gender":
        cmd_search_opp(m)
        return
    if text == "💎 Opposite Gender (Premium)":
        bot.send_message(uid, "Refer friends to unlock premium!")
        return
    if text == "⚙️ Settings":
        cmd_settings(m)
        return
    if text == "👥 Refer":
        cmd_refer(m)
        return
    
    if has_bad_content(text):
        bot.send_message(uid, "No bad words or links bro")
        return
    
    if uid in active_pairs:
        partner = active_pairs[uid]
        save_msg(uid, m.chat.id, m.message_id)
        save_msg(partner, m.chat.id, m.message_id)
        try:
            bot.send_message(partner, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
        except:
            bot.send_message(uid, "Couldn't send")
    else:
        bot.send_message(uid, "Not connected. Search someone", reply_markup=main_kb(uid))

# Admin
@bot.message_handler(commands=['pradd'])
def cmd_pradd(m):
    if m.from_user.id != ADMIN_ID:
        bot.send_message(m.from_user.id, "Admin only")
        return
    parts = m.text.split()
    if len(parts) < 3:
        bot.reply_to(m, "Usage: /pradd [user_id|username] [YYYY-MM-DD]")
        return
    ident = parts[1]
    until = parts[2]
    tid = resolve_id(ident)
    if not tid:
        bot.reply_to(m, f"Can't find user '{ident}'")
        return
    if not set_premium(tid, until):
        bot.reply_to(m, "Bad date")
        return
    bot.reply_to(m, f"Premium added until {until}")
    try:
        bot.send_message(tid, f"Premium until {until}! 🎉", reply_markup=main_kb(tid))
    except:
        pass

@bot.message_handler(commands=['prrem'])
def cmd_prrem(m):
    if m.from_user.id != ADMIN_ID:
        bot.send_message(m.from_user.id, "Admin only")
        return
    parts = m.text.split()
    if len(parts) < 2:
        bot.reply_to(m, "Usage: /prrem [user_id|username]")
        return
    ident = parts[1]
    tid = resolve_id(ident)
    if not tid:
        bot.reply_to(m, f"Can't find user")
        return
    remove_premium(tid)
    bot.reply_to(m, "Premium removed")
    try:
        bot.send_message(tid, "Premium removed", reply_markup=main_kb(tid))
    except:
        pass

@bot.message_handler(commands=['ban'])
def cmd_ban(m):
    if m.from_user.id != ADMIN_ID:
        bot.send_message(m.from_user.id, "Admin only")
        return
    parts = m.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(m, "Usage: /ban [user_id|username] [hours] [reason]")
        return
    ident = parts[1]
    tid = resolve_id(ident)
    if not tid:
        bot.reply_to(m, "Can't find user")
        return
    hours = 24
    reason = "Admin ban"
    if len(parts) >= 3:
        try:
            hours = int(parts[2])
        except:
            pass
    if len(parts) >= 4:
        reason = parts[3]
    ban_user(tid, hours=hours, reason=reason)
    bot.reply_to(m, f"Banned for {hours}h")
    try:
        bot.send_message(tid, f"Banned {hours}h. Reason: {reason}")
    except:
        pass
    disc_user(tid)

@bot.message_handler(commands=['unban'])
def cmd_unban(m):
    if m.from_user.id != ADMIN_ID:
        bot.send_message(m.from_user.id, "Admin only")
        return
    parts = m.text.split()
    if len(parts) < 2:
        bot.reply_to(m, "Usage: /unban [user_id|username]")
        return
    ident = parts[1]
    tid = resolve_id(ident)
    if not tid:
        bot.reply_to(m, "Can't find user")
        return
    unban_user(tid)
    bot.reply_to(m, "Unbanned")
    try:
        bot.send_message(tid, "You're unbanned! 🎉", reply_markup=main_kb(tid))
    except:
        pass

def set_cmds():
    try:
        cmds = [
            types.BotCommand("start", "Setup profile"),
            types.BotCommand("search", "Find partner"),
            types.BotCommand("search_opposite_gender", "Find opposite gender"),
            types.BotCommand("reconnect", "Reconnect"),
            types.BotCommand("next", "Next partner"),
            types.BotCommand("stop", "Stop"),
            types.BotCommand("refer", "Invite friends"),
            types.BotCommand("settings", "Your profile"),
            types.BotCommand("report", "Report"),
        ]
        bot.set_my_commands(cmds)
    except:
        pass

# Run
def poll():
    logger.info("Bot running...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Polling error: {e}")

def flask():
    PORT = int(os.getenv("PORT", 10000))
    logger.info(f"Flask on 0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    init_db()
    set_cmds()
    logger.info("GhostTalk v4.0 - Ready")
    
    t = threading.Thread(target=poll, daemon=True)
    t.start()
    
    flask()
