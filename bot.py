#!/usr/bin/env python3
"""
GhostTalk Premium Bot - FINAL v3.0
- FIXES: gender dup, username-based admin actions, robust report flow, removed unused commands/UI.
- Copy this file to bot.py and deploy.
"""

import os
import re
import random
import secrets
import sqlite3
import logging
import threading
import time
from datetime import datetime, timedelta

import telebot
from telebot import types
from flask import Flask

# -------- CONFIG --------
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise ValueError("🚨 BOT_TOKEN not found!")

BOT_USERNAME = os.getenv("BOT_USERNAME", "SayNymBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8361006824"))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv("DB_PATH", "ghosttalk_final.db")

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 1

# -------- LOGGING --------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------- TELEGRAM BOT & FLASK --------
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return "🤖 GhostTalk Bot Running!", 200

@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, 200

# -------- CONTENT FILTERS --------
BANNED_WORDS = [
    # shortened list for readability; keep as required
    "fuck", "nudes", "pussy", "dick", "porn", "rape", "molest",
    "anj", "babi", "asu","kontol","puki","maderchod","bsdk","lauda","lund","chut","gand"
]
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in BANNED_WORDS]

# -------- COUNTRIES (kept minimal here; expand as needed) --------
COUNTRIES = {"india": "🇮🇳", "united states": "🇺🇸", "uk": "🇬🇧"}
COUNTRY_ALIASES = {"usa": "united states", "us": "united states", "america": "united states"}

def get_country_info(user_input):
    n = user_input.strip().lower()
    n = COUNTRY_ALIASES.get(n, n)
    if n in COUNTRIES:
        return n.title(), COUNTRIES[n]
    return None

# -------- RUNTIME STATE --------
waiting_random = []
waiting_opposite = []  # list of (uid, gender)
active_pairs = {}      # uid -> partner_uid
user_warnings = {}
pending_media = {}     # token -> meta
chat_history = {}      # uid -> last_partner_uid
pending_reports = {}   # reporter_id -> {reported_id, report_type}

# -------- DATABASE HELPERS --------
def get_conn():
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
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            ban_until TEXT,
            permanent INTEGER DEFAULT 0,
            reason TEXT
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reporter_name TEXT,
            reported_id INTEGER,
            reported_name TEXT,
            report_type TEXT,
            reason TEXT,
            timestamp TEXT
        )""")
        conn.commit()

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT user_id, username, first_name, gender, age, country, country_flag,
                   messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until
            FROM users WHERE user_id=?""", (user_id,)).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0], "username": row[1], "first_name": row[2], "gender": row[3],
            "age": row[4], "country": row[5], "country_flag": row[6],
            "messages_sent": row[7], "media_approved": row[8], "media_rejected": row[9],
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
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at, referral_code)
            VALUES (?, ?, ?, ?, ?)""",
            (uid, user.username or "", user.first_name or "", datetime.utcnow().isoformat(), ref_code))
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

def db_add_referral(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (user_id,))
        conn.commit()
        u = db_get_user(user_id)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.utcnow() + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            conn.execute("UPDATE users SET premium_until=?, referral_count=0 WHERE user_id=?", (premium_until, user_id))
            conn.commit()
            try:
                bot.send_message(user_id, f"🎉 PREMIUM UNLOCKED! {PREMIUM_DURATION_HOURS} hour premium earned!")
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
        conn.execute("""
            INSERT INTO reports (reporter_id, reporter_name, reported_id, reported_name, report_type, reason, timestamp)
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
    Accept numeric ID or @username or username (without @). 
    Tries DB first, then bot.get_chat for usernames.
    Returns user_id (int) or None.
    """
    if not identifier:
        return None
    identifier = identifier.strip()
    if identifier.isdigit():
        return int(identifier)
    uname = identifier.lstrip("@")
    # try DB
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE username=? COLLATE NOCASE", (uname,)).fetchone()
        if row:
            return row[0]
    # try telegram
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
    for p in BANNED_PATTERNS:
        if p.search(text):
            return True
    return False

def warn_user(user_id, reason):
    count = user_warnings.get(user_id, 0) + 1
    user_warnings[user_id] = count
    if count >= WARNING_LIMIT:
        db_ban_user(user_id, hours=TEMP_BAN_HOURS, reason=reason)
        user_warnings[user_id] = 0
        try:
            bot.send_message(user_id, f"🚫 You have been banned for {TEMP_BAN_HOURS} hours. Reason: {reason}")
        except:
            pass
        remove_from_queues(user_id)
        disconnect_user(user_id)
        return "ban"
    else:
        try:
            bot.send_message(user_id, f"⚠️ Warning {count}/{WARNING_LIMIT}: {reason}")
        except:
            pass
        return "warn"

# -------- QUEUE HELPERS & MATCHING --------
def remove_from_queues(user_id):
    global waiting_random, waiting_opposite
    if user_id in waiting_random:
        waiting_random.remove(user_id)
    waiting_opposite = [(uid, g) for uid, g in waiting_opposite if uid != user_id]

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
            bot.send_message(partner_id, "❌ Partner left the chat. Use 🔀 Search Random to find another.", reply_markup=main_keyboard(partner_id))
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
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("👶 Child Abuse", callback_data="rep:child"),
        types.InlineKeyboardButton("🔞 Pornography", callback_data="rep:porn"),
        types.InlineKeyboardButton("📧 Spamming", callback_data="rep:spam"),
        types.InlineKeyboardButton("💰 Scam/Fraud", callback_data="rep:scam"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep:other")
    )
    return kb

def format_partner_found_message(partner_user, viewer_id):
    g = partner_user.get("gender") or "Unknown"
    gender_emoji = "👨" if g == "Male" else ("👩" if g == "Female" else "👤")
    age_text = str(partner_user["age"]) if partner_user.get("age") else "Unknown"
    country_flag = partner_user.get("country_flag") or "🌍"
    country_name = partner_user.get("country") or "Global"
    msg = (
        "🎉 Partner Found!\n\n"
        f"🎂 Age: {age_text}\n"
        f"👤 Gender: {gender_emoji} {g}\n"
        f"🌍 Country: {country_flag} {country_name}\n"
    )
    if viewer_id == ADMIN_ID:
        partner_name = partner_user.get("first_name") or partner_user.get("username") or "Unknown"
        msg += f"\n👤 Name: {partner_name}\n🆔 ID: {partner_user['user_id']}\n"
    msg += "\n💬 Enjoy the chat — type /next to find someone else."
    return msg

def match_users():
    global waiting_random, waiting_opposite, active_pairs
    # first match opposite-gender seekers with random queue
    i = 0
    while i < len(waiting_opposite):
        uid, gender = waiting_opposite[i]
        opposite_gender = "Male" if gender == "Female" else "Female"
        match_idx = None
        for j, other_uid in enumerate(waiting_random):
            od = db_get_user(other_uid)
            if od and od.get("gender") == opposite_gender:
                match_idx = j
                break
        if match_idx is not None:
            found_uid = waiting_random.pop(match_idx)
            waiting_opposite.pop(i)
            active_pairs[uid] = found_uid
            active_pairs[found_uid] = uid
            u1 = db_get_user(uid) or {}
            u2 = db_get_user(found_uid) or {}
            bot.send_message(uid, format_partner_found_message(u2, uid), reply_markup=chat_keyboard())
            bot.send_message(found_uid, format_partner_found_message(u1, found_uid), reply_markup=chat_keyboard())
            logger.info(f"Matched opposite: {uid} <-> {found_uid}")
            return
        i += 1
    # then match random pairs FIFO
    while len(waiting_random) >= 2:
        u1 = waiting_random.pop(0)
        u2 = waiting_random.pop(0)
        active_pairs[u1] = u2
        active_pairs[u2] = u1
        u1d = db_get_user(u1) or {}
        u2d = db_get_user(u2) or {}
        bot.send_message(u1, format_partner_found_message(u2d, u1), reply_markup=chat_keyboard())
        bot.send_message(u2, format_partner_found_message(u1d, u2), reply_markup=chat_keyboard())
        logger.info(f"Matched random: {u1} <-> {u2}")

# ---------------- COMMANDS & HANDLERS ----------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    uid = user.id

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned from GhostTalk.")
        return

    # referral handling
    parts = message.text.split()
    if len(parts) > 1:
        ref_code = parts[1]
        with get_conn() as conn:
            ref = conn.execute("SELECT user_id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
            if ref and ref[0] != uid:
                db_add_referral(ref[0])
                bot.send_message(uid, "✅ Joined via referral link!")

    u = db_get_user(uid) or {}
    # only show gender selection if not set
    if not u.get("gender"):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("👨 Male", callback_data="sex:Male"),
                   types.InlineKeyboardButton("👩 Female", callback_data="sex:Female"))
        bot.send_message(uid, "👋 Welcome to GhostTalk — select your gender:", reply_markup=markup)
        return

    if not u.get("age"):
        bot.send_message(uid, "📍 Enter your age (12-99):")
        return

    if not u.get("country"):
        bot.send_message(uid, "🌍 Enter your country name:\n⚠️ (Change allowed only for premium users)")
        return

    premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free User"
    welcome = (
        f"👋 Welcome back!\n\n"
        f"👤 Gender: {u.get('gender')}\n"
        f"🎂 Age: {u.get('age')}\n"
        f"🌍 Country: {u.get('country_flag')} {u.get('country')}\n"
        f"{premium_status}\n\n"
        "Ready to chat?"
    )
    bot.send_message(uid, welcome, reply_markup=main_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex:"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)
    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 You are banned", show_alert=True)
        return
    _, gender = call.data.split(":", 1)
    # Set only if not set or different
    u = db_get_user(uid) or {}
    if u.get("gender") == gender:
        bot.answer_callback_query(call.id, f"Gender already set to {gender}", show_alert=True)
        return
    db_set_gender(uid, gender)
    # Edit original message (if possible) to avoid duplicate messages
    try:
        bot.edit_message_text(f"✅ Gender set: { '👨' if gender=='Male' else '👩' } {gender}", call.message.chat.id, call.message.message_id)
    except Exception:
        # fallback: answer callback
        bot.answer_callback_query(call.id, "✅ Gender set!", show_alert=False)
    # prompt for next step (age) if not present
    u2 = db_get_user(uid) or {}
    if not u2.get("age"):
        try:
            bot.send_message(uid, "📍 Enter your age (12-99):")
        except:
            pass

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = (
        "🤖 GhostTalk — Quick Guide\n\n"
        "Getting started:\n"
        "• Send /start and complete profile: gender → age → country.\n"
        "• Use 🔀 Search Random to find a chat partner.\n\n"
        "During chat:\n"
        "• ⏭️ Next — skip to a new partner.\n"
        "• 🛑 Stop — end current chat or cancel search.\n"
        "• Media is sent only after recipient accepts.\n\n"
        "Safety & reporting:\n"
        "• If someone breaks rules, use Report (visible after chat too).\n"
        "• You'll be asked to pick a reason and optionally add details.\n"
        "• Admins review every report.\n\n"
        "Premium & referrals:\n"
        "• Use /refer to see your invitation link and progress.\n\n"
        "If you need help from admins, contact the admin ID in bot settings."
    )
    bot.send_message(uid, help_text)

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start to set up your profile.")
        return
    premium_status = "✅ Premium Active" if db_is_premium(uid) else "🆓 Free User"
    gender_emoji = "👨" if u.get("gender") == "Male" else ("👩" if u.get("gender") == "Female" else "👤")
    text = (
        "⚙️ SETTINGS\n\n"
        f"👤 Gender: {gender_emoji} {u.get('gender') or 'Not set'}\n"
        f"🎂 Age: {u.get('age') or 'Not set'}\n"
        f"🌍 Country: {u.get('country_flag') or '🌍'} {u.get('country') or 'Not set'}\n\n"
        f"📨 Messages: {u.get('messages_sent')}\n"
        f"✅ Media approved: {u.get('media_approved')}\n"
        f"❌ Media rejected: {u.get('media_rejected')}\n"
        f"{premium_status}"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🔗 Refer", callback_data="ref:link"))
    markup.row(types.InlineKeyboardButton("🎂 Change Age", callback_data="age:change"))
    markup.row(types.InlineKeyboardButton("🌍 Change Country", callback_data="set:country"))
    bot.send_message(uid, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref:"))
def cb_ref(call):
    uid = call.from_user.id
    _, action = call.data.split(":", 1)
    if action == "link":
        u = db_get_user(uid)
        if not u:
            bot.answer_callback_query(call.id, "Error", show_alert=True)
            return
        ref_link = f"https://t.me/{BOT_USERNAME}?start={u.get('referral_code')}"
        remaining = PREMIUM_REFERRALS_NEEDED - (u.get('referral_count') or 0)
        txt = f"🔗 Your invite link:\n{ref_link}\n\nReferred: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}"
        if remaining > 0:
            txt += f"\nInvite {remaining} more to unlock premium."
        else:
            txt += "\nPremium unlocked or ready to claim."
        bot.send_message(uid, txt)
        bot.answer_callback_query(call.id, "Sent", show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("age:"))
def cb_age_change(call):
    uid = call.from_user.id
    bot.send_message(uid, "🎂 Enter new age (12-99):")
    bot.register_next_step_handler(call.message, process_new_age)

def process_new_age(message):
    uid = message.from_user.id
    try:
        age = int(message.text.strip())
        if age < 12 or age > 99:
            bot.send_message(uid, "❌ Age must be between 12 and 99. Try again:")
            bot.register_next_step_handler(message, process_new_age)
            return
        db_set_age(uid, age)
        bot.send_message(uid, f"✅ Age set to {age}.", reply_markup=main_keyboard(uid))
    except:
        bot.send_message(uid, "❌ Enter a valid number (e.g., 21).")
        bot.register_next_step_handler(message, process_new_age)

@bot.message_handler(commands=['refer'])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    ref_link = f"https://t.me/{BOT_USERNAME}?start={u.get('referral_code')}"
    remaining = PREMIUM_REFERRALS_NEEDED - (u.get('referral_count') or 0)
    txt = f"🔗 Your referral link:\n{ref_link}\nReferred: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}"
    if remaining > 0:
        txt += f"\nInvite {remaining} more to unlock premium."
    else:
        txt += "\nYou've unlocked premium or are close — keep inviting!"
    bot.send_message(uid, txt)

@bot.message_handler(commands=['search_random'])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete your profile first. Use /start.")
        return
    if uid in active_pairs:
        bot.send_message(uid, "⏳ You are already in a chat. Use /next to move on.")
        return
    already_in_random = uid in waiting_random
    already_in_opposite = any(uid == x for x, _ in waiting_opposite)
    if already_in_random or already_in_opposite:
        bot.send_message(uid,
                         "⏳ You're already searching. Chill a bit — I'll connect you soon.\n\n"
                         "To cancel the search, send /stop.")
        return
    remove_from_queues(uid)
    waiting_random.append(uid)
    bot.send_message(uid, "🔍 Searching for a random partner... Please wait.")
    match_users()

@bot.message_handler(commands=['search_opposite_gender'])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if not db_is_premium(uid):
        bot.send_message(uid, "💎 Premium required. Use /refer to invite friends and unlock.")
        return
    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete your profile first. Use /start.")
        return
    if uid in active_pairs:
        bot.send_message(uid, "⏳ You are already in a chat. Use /next to move on.")
        return
    already_in_random = uid in waiting_random
    already_in_opposite = any(uid == x for x, _ in waiting_opposite)
    if already_in_random or already_in_opposite:
        bot.send_message(uid,
                         "⏳ You're already searching. Chill a bit — I'll connect you soon.\n\n"
                         "To cancel the search, send /stop.")
        return
    remove_from_queues(uid)
    waiting_opposite.append((uid, u.get("gender")))
    bot.send_message(uid, "🎯 Searching for opposite gender partner... Please wait.")
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
        bot.send_message(uid, "❌ You're not in a chat. Use 🔀 Search Random.")
        return
    disconnect_user(uid)
    bot.send_message(uid, "🔍 Finding a new partner...", reply_markup=main_keyboard(uid))
    cmd_search_random(message)

# --- REPORT flow (works during and after chat) ---
@bot.message_handler(commands=['report'])
def cmd_report(message):
    uid = message.from_user.id
    partner = active_pairs.get(uid) or chat_history.get(uid)
    if not partner:
        bot.send_message(uid, "❌ No partner to report (you haven't chatted yet).")
        return
    bot.send_message(uid, "⚠️ Choose a reason for reporting:", reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep:"))
def cb_report_choice(call):
    uid = call.from_user.id
    reported = active_pairs.get(uid) or chat_history.get(uid)
    if not reported:
        bot.answer_callback_query(call.id, "No partner to report.", show_alert=True)
        return
    _, rpt = call.data.split(":", 1)
    pending_reports[uid] = {"reported_id": reported, "report_type": rpt}
    bot.answer_callback_query(call.id, "Selected. Please type a short reason (1-500 chars).", show_alert=False)
    bot.send_message(uid, "📝 Please type the reason for reporting. Be concise and factual. (Example: 'sent explicit media', 'harassment', etc.)")

@bot.message_handler(func=lambda m: m.content_type == "text" and m.from_user.id in pending_reports)
def process_report_reason(message):
    uid = message.from_user.id
    data = pending_reports.get(uid)
    if not data:
        bot.send_message(uid, "❌ No active report found.")
        return
    reason = message.text.strip()[:500]
    reported_id = data["reported_id"]
    report_type = data["report_type"]

    reporter = db_get_user(uid) or {}
    reported = db_get_user(reported_id) or {}

    reporter_name = reporter.get("first_name") or reporter.get("username") or str(uid)
    reported_name = reported.get("first_name") or reported.get("username") or str(reported_id)

    db_add_report_db(uid, reporter_name, reported_id, reported_name, report_type, reason)

    bot.send_message(uid, "✅ Report submitted. Admins will review it.")
    admin_msg = (
        "⚠️ NEW REPORT\n\n"
        f"Reporter: {reporter_name} (ID: {uid})\n"
        f"Reported: {reported_name} (ID: {reported_id})\n"
        f"Type: {report_type}\n"
        f"Reason: {reason}\n"
        f"Time: {datetime.utcnow().isoformat()}\n"
    )
    try:
        bot.send_message(ADMIN_ID, admin_msg)
    except Exception:
        logger.warning("Could not send report to admin (maybe chat blocked).")
    pending_reports.pop(uid, None)

# --- ADMIN: premium add/remove (accept id or @username) ---
@bot.message_handler(commands=['pradd', 'addpremium'])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only.")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /pradd [user_id|@username] [YYYY-MM-DD]")
        return
    identifier = parts[1]
    until = parts[2]
    target = resolve_user_identifier(identifier)
    if not target:
        bot.reply_to(message, f"❌ Could not resolve user: {identifier}")
        return
    if not db_set_premium(target, until):
        bot.reply_to(message, "❌ Invalid date format. Use YYYY-MM-DD")
        return
    bot.reply_to(message, f"✅ Premium set for {target} until {until}")
    try:
        bot.send_message(target, f"🎉 Premium granted until {until}!", reply_markup=main_keyboard(target))
    except:
        pass

@bot.message_handler(commands=['prrem', 'removepremium'])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /prrem [user_id|@username]")
        return
    identifier = parts[1]
    target = resolve_user_identifier(identifier)
    if not target:
        bot.reply_to(message, f"❌ Could not resolve user: {identifier}")
        return
    db_remove_premium(target)
    bot.reply_to(message, f"✅ Premium removed for {target}")
    try:
        bot.send_message(target, "❌ Your premium has been removed.", reply_markup=main_keyboard(target))
    except:
        pass

# --- ADMIN: ban/unban (id or @username) ---
@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only.")
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban [user_id|@username] [hours/permanent] [reason]")
        return
    identifier = parts[1]
    target = resolve_user_identifier(identifier)
    if not target:
        bot.reply_to(message, f"❌ Could not resolve user: {identifier}")
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
    db_ban_user(target, hours=hours, permanent=permanent, reason=reason)
    if permanent:
        bot.reply_to(message, f"✅ User {target} permanently banned. Reason: {reason}")
    else:
        bot.reply_to(message, f"✅ User {target} banned for {hours} hours. Reason: {reason}")
    try:
        bot.send_message(target, f"🚫 You were banned. Reason: {reason}")
    except:
        pass

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.from_user.id, "❌ Admin only.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban [user_id|@username]")
        return
    identifier = parts[1]
    target = resolve_user_identifier(identifier)
    if not target:
        bot.reply_to(message, f"❌ Could not resolve user: {identifier}")
        return
    db_unban_user(target)
    user_warnings[target] = 0
    bot.reply_to(message, f"✅ User {target} unbanned.")
    try:
        bot.send_message(target, "✅ Your ban was lifted.", reply_markup=main_keyboard(target))
    except:
        pass

# --- Media handlers (consent) ---
@bot.message_handler(content_types=['photo', 'video', 'document', 'animation', 'sticker'])
def handle_media(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "❌ Not in a chat.")
        return
    partner = active_pairs[uid]
    media_type = m.content_type
    if media_type == "photo":
        file_id = m.photo[-1].file_id
    elif media_type == "video":
        file_id = m.video.file_id
    elif media_type == "document":
        file_id = m.document.file_id
    elif media_type == "animation":
        file_id = m.animation.file_id
    elif media_type == "sticker":
        file_id = m.sticker.file_id
    else:
        return

    sender_user = db_get_user(uid) or {}
    # keep previous auto-forward behavior if they have prior approvals
    if sender_user.get("media_approved"):
        try:
            if media_type == "photo":
                bot.send_photo(partner, file_id)
            elif media_type == "video":
                bot.send_video(partner, file_id)
            elif media_type == "document":
                bot.send_document(partner, file_id)
            elif media_type == "animation":
                bot.send_animation(partner, file_id)
            elif media_type == "sticker":
                bot.send_sticker(partner, file_id)
            db_increment_media(uid, "approved")
        except Exception as e:
            logger.error("Forward error: %s", e)
            bot.send_message(uid, "❌ Could not forward media.")
        return

    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(3)}"
    pending_media[token] = {"sender": uid, "partner": partner, "file_id": file_id, "media_type": media_type, "msg_id": None}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"app:{token}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"rej:{token}"))
    try:
        msg = bot.send_message(partner, f"Your partner wants to send a {media_type}. Accept?", reply_markup=markup)
        pending_media[token]["msg_id"] = msg.message_id
        bot.send_message(uid, "📤 Consent request sent. Waiting for partner to accept.")
    except Exception as e:
        logger.error("Consent send error: %s", e)
        bot.send_message(uid, "❌ Could not request consent.")
        pending_media.pop(token, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("app:"))
def cb_accept_media(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "No longer available", show_alert=True)
            return
        file_id = meta["file_id"]
        media_type = meta["media_type"]
        sender_id = meta["sender"]
        msg_id = meta.get("msg_id")
        # deliver to acceptor
        try:
            if media_type == "photo":
                bot.send_photo(call.from_user.id, file_id)
            elif media_type == "video":
                bot.send_video(call.from_user.id, file_id)
            elif media_type == "document":
                bot.send_document(call.from_user.id, file_id)
            elif media_type == "animation":
                bot.send_animation(call.from_user.id, file_id)
            elif media_type == "sticker":
                bot.send_sticker(call.from_user.id, file_id)
        except Exception as e:
            logger.error("Media deliver error: %s", e)
            bot.answer_callback_query(call.id, "Could not deliver", show_alert=True)
            pending_media.pop(token, None)
            return
        db_increment_media(sender_id, "approved")
        try:
            bot.send_message(sender_id, f"✅ Your {media_type} was accepted.")
        except:
            pass
        # hide consent message
        try:
            if msg_id:
                bot.delete_message(call.message.chat.id, msg_id)
        except:
            try:
                if msg_id:
                    bot.edit_message_reply_markup(call.message.chat.id, msg_id, reply_markup=None)
            except:
                pass
        bot.answer_callback_query(call.id, "Accepted", show_alert=False)
        pending_media.pop(token, None)
    except Exception as e:
        logger.error("Accept callback error: %s", e)
        bot.answer_callback_query(call.id, "Error", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rej:"))
def cb_reject_media(call):
    try:
        token = call.data.split(":", 1)[1]
        meta = pending_media.get(token)
        if not meta:
            bot.answer_callback_query(call.id, "No longer available", show_alert=True)
            return
        sender = meta["sender"]
        media_type = meta["media_type"]
        msg_id = meta.get("msg_id")
        try:
            bot.send_message(sender, f"❌ Your {media_type} was rejected by partner.")
            db_increment_media(sender, "rejected")
        except:
            pass
        try:
            if msg_id:
                bot.delete_message(call.message.chat.id, msg_id)
        except:
            try:
                if msg_id:
                    bot.edit_message_reply_markup(call.message.chat.id, msg_id, reply_markup=None)
            except:
                pass
        bot.answer_callback_query(call.id, "Rejected", show_alert=False)
        pending_media.pop(token, None)
    except Exception as e:
        logger.error("Reject callback error: %s", e)
        bot.answer_callback_query(call.id, "Error", show_alert=True)

# ------------- TEXT HANDLER -------------
# Note: handler for pending_reports is above this (registered earlier)
@bot.message_handler(func=lambda m: m.content_type == "text" and m.from_user.id not in pending_reports)
def handler_text(m):
    uid = m.from_user.id
    text = m.text.strip()

    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return

    db_create_user_if_missing(m.from_user)
    u = db_get_user(uid) or {}

    # gender not set
    if not u.get("gender"):
        bot.send_message(uid, "❌ Set your gender first. Use /start.")
        return

    # age flow
    if not u.get("age"):
        try:
            age = int(text)
            if age < 12 or age > 99:
                bot.send_message(uid, "❌ Age must be 12-99.")
                return
            db_set_age(uid, age)
            bot.send_message(uid, "✅ Age recorded. Now enter your country (e.g., India).")
            return
        except:
            bot.send_message(uid, "❌ Enter age as a number (e.g., 21).")
            return

    # country flow
    if not u.get("country"):
        info = get_country_info(text)
        if not info:
            bot.send_message(uid, "❌ Country not recognized. Try 'India' or 'USA'.")
            return
        name, flag = info
        db_set_country(uid, name, flag)
        bot.send_message(uid, f"✅ Country set: {flag} {name}", reply_markup=main_keyboard(uid))
        return

    # buttons
    if text == "📊 Stats":
        u = db_get_user(uid) or {}
        premium_status = "✅ Premium" if db_is_premium(uid) else "🆓 Free"
        gender_emoji = "👨" if u.get("gender") == "Male" else ("👩" if u.get("gender") == "Female" else "👤")
        stats = (
            f"📊 Stats\n\nGender: {gender_emoji} {u.get('gender')}\nAge: {u.get('age')}\n"
            f"Country: {u.get('country_flag')} {u.get('country')}\nMessages: {u.get('messages_sent')}\n{premium_status}"
        )
        bot.send_message(uid, stats, reply_markup=chat_keyboard())
        return

    if text == "🔀 Search Random":
        cmd_search_random(m)
        return

    if text == "🎯 Search Opposite Gender":
        cmd_search_opposite(m)
        return

    if text == "⏭️ Next":
        cmd_next(m)
        return

    if text == "🛑 Stop":
        cmd_stop(m)
        return

    if text == "⚙️ Settings":
        cmd_settings(m)
        return

    if text == "👥 Refer":
        cmd_refer(m)
        return

    # moderation
    if is_banned_content(text):
        warn_user(uid, "Inappropriate content or links")
        return

    # chat relay
    if uid in active_pairs:
        partner = active_pairs[uid]
        try:
            bot.send_message(partner, text)
            with get_conn() as conn:
                conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?", (uid,))
                conn.commit()
        except Exception as e:
            logger.error("Relay error: %s", e)
            bot.send_message(uid, "❌ Could not send message.")
    else:
        bot.send_message(uid, "❌ You're not connected. Use 🔀 Search Random.", reply_markup=main_keyboard(uid))

# ------------- RUN BOT -------------
def run_bot_polling():
    logger.info("Bot polling started")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.exception("Polling crashed: %s", e)
        time.sleep(5)
        run_bot_polling()

if __name__ == "__main__":
    init_db()
    logger.info("✅ GhostTalk FINAL v3.0 starting")
    thread = threading.Thread(target=run_bot_polling, daemon=True)
    thread.start()
    PORT = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
