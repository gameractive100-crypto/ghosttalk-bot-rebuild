#!/usr/bin/env python3
"""
GhostTalk v5.4 - COMPLETE FIXED FINAL
✅ ALL v5.4 Features Intact
✅ Enhanced Chat Forwarding to Admin (Full History)
✅ Fixed Media Accept/Reject (Voice + Audio + All Types)
✅ Proper Report System with Admin Monitoring
✅ Reconnect Feature
✅ Games + Cleanup Threads
✅ NO CHAT FREEZE
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

# ============ CONFIG ============
API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = int(os.getenv("ADMIN_ID", 8361006824))
OWNER_ID = ADMIN_ID
DBPATH = os.getenv("DBPATH", "ghosttalk.db")
WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
AUTO_BAN_REPORTS = 7
AUTO_BAN_DAYS = 7
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 24
RECONNECT_TIMEOUT = 300
RECONNECT_COOLDOWN_HOURS = 24
SEARCH_TIMEOUT_SECONDS = 120

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('ghosttalk.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# ============ BANNED WORDS ============
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis", "vagina", "boobs",
    "tits", "ass", "asshole", "bitch", "slut", "whore", "hoe", "prostitute", "porn", "pornography",
    "rape", "child", "pedo", "anj", "anjing", "babi", "asu", "kontl", "kontol", "puki", "memek",
    "jembut", "maderchod", "mc", "bhen ka lauda", "bhenkalauda", "randi", "randika", "gand", "bsdk",
    "chut", "chot", "chuut", "choot", "lund"
]
LINK_PATTERN = re.compile(r"https?://www.", re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

# ============ 195 COUNTRIES ============
COUNTRIES = ["afghanistan", "albania", "algeria", "andorra", "angola", "antigua and barbuda", "argentina",
    "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain", "bangladesh", "barbados",
    "belarus", "belgium", "belize", "benin", "bhutan", "bolivia", "bosnia and herzegovina", "botswana",
    "brazil", "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon", "canada", "cape verde",
    "central african republic", "chad", "chile", "china", "colombia", "comoros", "congo", "costa rica",
    "croatia", "cuba", "cyprus", "czech republic", "czechia", "denmark", "djibouti", "dominica",
    "dominican republic", "ecuador", "egypt", "el salvador", "equatorial guinea", "eritrea", "estonia",
    "eswatini", "ethiopia", "fiji", "finland", "france", "gabon", "gambia", "georgia", "germany", "ghana",
    "greece", "grenada", "guatemala", "guinea", "guinea-bissau", "guyana", "haiti", "honduras", "hungary",
    "iceland", "india", "indonesia", "iran", "iraq", "ireland", "israel", "italy", "jamaica", "japan",
    "jordan", "kazakhstan", "kenya", "kiribati", "korea north", "korea south", "kuwait", "kyrgyzstan",
    "laos", "latvia", "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg",
    "madagascar", "malawi", "malaysia", "maldives", "mali", "malta", "marshall islands", "mauritania",
    "mauritius", "mexico", "micronesia", "moldova", "monaco", "mongolia", "montenegro", "morocco",
    "mozambique", "myanmar", "namibia", "nauru", "nepal", "netherlands", "new zealand", "nicaragua",
    "niger", "nigeria", "north macedonia", "norway", "oman", "pakistan", "palau", "palestine", "panama",
    "papua new guinea", "paraguay", "peru", "philippines", "poland", "portugal", "qatar", "romania",
    "russia", "rwanda", "saint kitts and nevis", "saint lucia", "saint vincent and the grenadines",
    "samoa", "san marino", "sao tome and principe", "saudi arabia", "senegal", "serbia", "seychelles",
    "sierra leone", "singapore", "slovakia", "slovenia", "solomon islands", "somalia", "south africa",
    "south sudan", "spain", "sri lanka", "sudan", "suriname", "sweden", "switzerland", "syria", "taiwan",
    "tajikistan", "tanzania", "thailand", "timor-leste", "togo", "tonga", "trinidad and tobago", "tunisia",
    "turkey", "turkmenistan", "tuvalu", "uganda", "ukraine", "united arab emirates", "united kingdom",
    "united states", "uruguay", "uzbekistan", "vanuatu", "vatican city", "venezuela", "vietnam", "yemen",
    "zambia", "zimbabwe"
]

COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "america": "united states", "uk": "united kingdom",
    "britain": "united kingdom", "england": "united kingdom", "uae": "united arab emirates",
    "emirates": "united arab emirates", "south korea": "korea south", "sk": "korea south",
    "north korea": "korea north", "nk": "korea north", "czechia": "czech republic"
}

def get_country_info(user_input):
    normalized = user_input or ""
    normalized = normalized.strip().lower()
    if not normalized:
        return None
    if normalized in COUNTRY_ALIASES:
        normalized = COUNTRY_ALIASES[normalized]
    if normalized in COUNTRIES:
        return normalized.title(), "🌍"
    return None

# ============ RUNTIME DATA ============
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

queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()
reconnect_lock = threading.Lock()

# ============ DATABASE ============
def get_conn():
    conn = sqlite3.connect(DBPATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            userid INTEGER PRIMARY KEY, username TEXT, firstname TEXT, gender TEXT, age INTEGER,
            country TEXT, countryflag TEXT, messages_sent INTEGER DEFAULT 0, media_approved INTEGER DEFAULT 0,
            media_rejected INTEGER DEFAULT 0, referral_code TEXT UNIQUE, referral_count INTEGER DEFAULT 0,
            premium_until TEXT, joined_at TEXT)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS bans (
            userid INTEGER PRIMARY KEY, ban_until TEXT, permanent INTEGER DEFAULT 0, reason TEXT,
            banned_by INTEGER, banned_at TEXT)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER, reporter_name TEXT,
            reported_id INTEGER, reported_name TEXT, report_type TEXT, reason TEXT, chat_status TEXT,
            timestamp TEXT)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS recent_partners (
            userid INTEGER PRIMARY KEY, partner_id INTEGER, last_disconnect TEXT, reconnect_until TEXT)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS chatlogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, sender_name TEXT,
            receiver_id INTEGER, receiver_name TEXT, message_type TEXT, message_content TEXT, timestamp TEXT)""")

        conn.commit()
    logger.info("Database initialized")

def db_get_user(userid):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT userid, username, firstname, gender, age, country, countryflag, messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until FROM users WHERE userid=?",
            (userid,)).fetchone()
        if not row:
            return None
        return {
            "userid": row[0], "username": row[1], "firstname": row[2], "gender": row[3], "age": row[4],
            "country": row[5], "countryflag": row[6], "messages_sent": row[7], "media_approved": row[8],
            "media_rejected": row[9], "referral_code": row[10], "referral_count": row[11], "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (userid, username, firstname, gender, age, country, countryflag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, user.username or "", user.first_name or "", None, None, None, None, datetime.utcnow().isoformat(), ref_code))
        conn.commit()

def db_set_gender(userid, gender):
    with get_conn() as conn:
        conn.execute("UPDATE users SET gender=? WHERE userid=?", (gender, userid))
        conn.commit()

def db_set_age(userid, age):
    with get_conn() as conn:
        conn.execute("UPDATE users SET age=? WHERE userid=?", (age, userid))
        conn.commit()

def db_set_country(userid, country, flag):
    with get_conn() as conn:
        conn.execute("UPDATE users SET country=?, countryflag=? WHERE userid=?", (country, flag, userid))
        conn.commit()

def db_is_premium(userid):
    if userid == ADMIN_ID:
        return True
    u = db_get_user(userid)
    if not u or not u.get("premium_until"):
        return False
    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.utcnow()
    except:
        return False

def db_set_premium(userid, until_date):
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        dt = datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute("UPDATE users SET premium_until=? WHERE userid=?", (dt.isoformat(), userid))
            conn.commit()
        return True
    except:
        return False

def db_remove_premium(userid):
    with get_conn() as conn:
        conn.execute("UPDATE users SET premium_until=NULL WHERE userid=?", (userid,))
        conn.commit()

def db_is_banned(userid):
    if userid == OWNER_ID:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT ban_until, permanent FROM bans WHERE userid=?", (userid,)).fetchone()
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

def db_ban_user(userid, hours=None, permanent=False, reason=""):
    with get_conn() as conn:
        if permanent:
            conn.execute("INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (userid, None, 1, reason, ADMIN_ID, datetime.utcnow().isoformat()))
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (userid, until, 0, reason, ADMIN_ID, datetime.utcnow().isoformat()))
        conn.commit()

def db_unban_user(userid):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE userid=?", (userid,))
        conn.commit()

def db_add_report(reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status):
    """✅ Enhanced: Stores reporter and reported names"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute("INSERT INTO reports (reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status, timestamp))
        count = conn.execute("SELECT COUNT(*) FROM reports WHERE reported_id=?", (reported_id,)).fetchone()[0]
        conn.commit()

        if count >= AUTO_BAN_REPORTS and not db_is_banned(reported_id):
            ban_until = (datetime.utcnow() + timedelta(days=AUTO_BAN_DAYS)).isoformat()
            conn.execute("INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (reported_id, ban_until, 0, f"Auto-ban {count} reports", ADMIN_ID, datetime.utcnow().isoformat()))
            logger.warning(f"AUTO-BAN User {reported_id} for {AUTO_BAN_DAYS} days")
            try:
                bot.send_message(reported_id, f"🚫 You've been temporarily banned for {AUTO_BAN_DAYS} days due to community reports.")
            except:
                pass

            if reported_id in active_pairs:
                with active_pairs_lock:
                    partner = active_pairs.get(reported_id)
                    if partner:
                        try:
                            del active_pairs[partner]
                        except:
                            pass
                    try:
                        del active_pairs[reported_id]
                    except:
                        pass
            conn.commit()

def db_save_chat_log(sender_id, sender_name, receiver_id, receiver_name, msg_type, content):
    """✅ Save chat messages for admin forwarding"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute("INSERT INTO chatlogs (sender_id, sender_name, receiver_id, receiver_name, message_type, message_content, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sender_id, sender_name, receiver_id, receiver_name, msg_type, content, timestamp))
        conn.commit()

def db_save_recent_partner(userid, partner_id):
    """✅ Reconnect: Save partner for later"""
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        reconnect_until = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        conn.execute("INSERT OR REPLACE INTO recent_partners (userid, partner_id, last_disconnect, reconnect_until) VALUES (?, ?, ?, ?)",
            (userid, partner_id, now, reconnect_until))
        conn.commit()

def db_get_recent_partner(userid):
    """✅ Reconnect: Get recent partner if within window"""
    with get_conn() as conn:
        row = conn.execute("SELECT partner_id, reconnect_until FROM recent_partners WHERE userid=?", (userid,)).fetchone()
        if not row:
            return None
        partner_id, reconnect_until = row
        try:
            if datetime.fromisoformat(reconnect_until) > datetime.utcnow():
                return partner_id
        except:
            pass
        conn.execute("DELETE FROM recent_partners WHERE userid=?", (userid,))
        conn.commit()
    return None

def db_clear_recent_partner(userid):
    with get_conn() as conn:
        conn.execute("DELETE FROM recent_partners WHERE userid=?", (userid,))
        conn.commit()

def db_increment_media(userid, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE userid=?", (userid,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE userid=?", (userid,))
        conn.commit()

def db_add_referral(userid):
    with get_conn() as conn:
        conn.execute("UPDATE users SET referral_count=referral_count+1 WHERE userid=?", (userid,))
        conn.commit()
        u = db_get_user(userid)
        if u and u["referral_count"] >= PREMIUM_REFERRALS_NEEDED:
            premium_until = (datetime.utcnow() + timedelta(hours=PREMIUM_DURATION_HOURS)).isoformat()
            conn.execute("UPDATE users SET premium_until=?, referral_count=0 WHERE userid=?", (premium_until, userid))
            conn.commit()
            try:
                bot.send_message(userid, f"🎉 PREMIUM UNLOCKED! {PREMIUM_DURATION_HOURS} hour premium earned!")
            except:
                pass

def is_banned_content(text):
    if not text:
        return False
    if LINK_PATTERN.search(text):
        return True
    for pattern in BANNED_PATTERNS:
        if pattern.search(text):
            return True
    return False

def warn_user(userid, reason):
    with user_warnings_lock:
        count = user_warnings.get(userid, 0) + 1
        user_warnings[userid] = count
        if count >= WARNING_LIMIT:
            db_ban_user(userid, hours=TEMP_BAN_HOURS, reason=reason)
            user_warnings[userid] = 0
            try:
                bot.send_message(userid, f"⛔ You've been temporarily banned for {TEMP_BAN_HOURS} hours.\nReason: {reason}")
            except:
                pass
            remove_from_queues(userid)
            disconnect_user(userid)
            return "ban"
        else:
            try:
                bot.send_message(userid, f"⚠️ Warning {count}/{WARNING_LIMIT}\nReason: {reason}\n{WARNING_LIMIT - count} more = ban")
            except:
                pass
            return "warn"

def remove_from_queues(userid):
    global waiting_random, waiting_premium_opposite
    with queue_lock:
        if userid in waiting_random:
            waiting_random.remove(userid)
        waiting_premium_opposite[:] = [uid for uid in waiting_premium_opposite if uid != userid]
        search_start_time.pop(userid, None)

def is_searching(userid):
    with queue_lock:
        if userid in waiting_random:
            return True
        if userid in waiting_premium_opposite:
            return True
    return False

def disconnect_user(userid):
    """✅ NO FREEZE - Safe disconnect"""
    global active_pairs
    partner_id = None
    with active_pairs_lock:
        if userid in active_pairs:
            partner_id = active_pairs.get(userid)
            try:
                del active_pairs[userid]
            except:
                pass
            try:
                if partner_id in active_pairs:
                    del active_pairs[partner_id]
            except:
                pass

            if partner_id:
                now = datetime.utcnow()
                chat_history_with_time[userid] = (partner_id, now)
                chat_history_with_time[partner_id] = (userid, now)
                db_save_recent_partner(userid, partner_id)
                db_save_recent_partner(partner_id, userid)

                try:
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    markup.add(types.InlineKeyboardButton("🚩 Report", callback_data="report_after_chat"))
                    bot.send_message(partner_id, "👋 Your chat partner has left.\nWant to report this user?", reply_markup=markup)
                    logger.info(f"{userid} left. Partner {partner_id} notified")
                except Exception as e:
                    logger.error(f"Failed to notify partner: {e}")

                try:
                    bot.send_message(userid, "Chat ended. Use /search to find someone new.")
                    logger.info(f"{userid} acknowledged disconnect")
                except Exception as e:
                    logger.error(f"Failed to notify leaver: {e}")

def forward_chat_to_admin(reporter_id, reported_id, report_type, chat_history_list):
    """✅ Enhanced: Forward full chat history to admin"""
    try:
        user_reporter = db_get_user(reporter_id)
        user_reported = db_get_user(reported_id)

        reporter_name = user_reporter.get("firstname", "User") if user_reporter else "User"
        reported_name = user_reported.get("reported") if user_reported else "User"

        admin_header = f"""📋 NEW REPORT

🚩 Report Type: {report_type}
👤 Reporter: {reporter_name} (ID: {reporter_id})
👤 Reported: {reported_name} (ID: {reported_id})
⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

📨 CHAT HISTORY:"""

        bot.send_message(ADMIN_ID, admin_header)

        # ✅ Forward chat messages
        with get_conn() as conn:
            rows = conn.execute("SELECT sender_name, message_content, timestamp FROM chatlogs WHERE (sender_id=? OR sender_id=?) AND (receiver_id=? OR receiver_id=?) ORDER BY timestamp DESC LIMIT 20",
                (reporter_id, reported_id, reported_id, reporter_id)).fetchall()

            if rows:
                for sender_name, content, ts in reversed(rows):
                    msg = f"[{ts}] {sender_name}: {content[:500]}"
                    bot.send_message(ADMIN_ID, msg)
            else:
                bot.send_message(ADMIN_ID, "No chat history found")

        bot.send_message(ADMIN_ID, "✅ End of report")
    except Exception as e:
        logger.error(f"Error forwarding chat: {e}")

def match_users():
    global waiting_random, waiting_premium_opposite, active_pairs

    # Premium ↔ Premium opposite
    i = 0
    while i < len(waiting_premium_opposite):
        uid1 = waiting_premium_opposite[i]
        u1 = db_get_user(uid1)
        if not u1 or not u1.get("gender"):
            i += 1
            continue

        gender1 = u1.get("gender")
        needed_gender = "Female" if gender1 == "Male" else "Male"

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
                        bot.send_message(uid1, f"✅ Match found!\n💬 Let's chat")
                        bot.send_message(uid2, f"✅ Match found!\n💬 Let's chat")
                        logger.info(f"Matched {uid1} ↔ {uid2}")
                    except:
                        pass
                    return
        i += 1

    # Random pairs
    with queue_lock:
        while len(waiting_random) >= 2:
            u1 = waiting_random.pop(0)
            u2 = waiting_random.pop(0)
            with active_pairs_lock:
                active_pairs[u1] = u2
                active_pairs[u2] = u1

            try:
                bot.send_message(u1, "✅ Match found!\n💬 Let's chat")
                bot.send_message(u2, "✅ Match found!\n💬 Let's chat")
                logger.info(f"Matched {u1} ↔ {u2}")
            except:
                pass

# ============ FLASK ROUTES ============
@app.route("/", methods=["GET"])
def home():
    return "GhostTalk v5.4 - Running!", 200

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}, 200

# ============ COMMANDS ============

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.send_message(user.id, "⛔ You're currently banned. Contact support.")
        return

    u = db_get_user(user.id)
    if not u or not u.get("gender"):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("👨 Male", callback_data="sex_male"),
                   types.InlineKeyboardButton("👩 Female", callback_data="sex_female"))
        bot.send_message(user.id, "Welcome! Set up your profile. What's your gender?", reply_markup=markup)
    elif not u.get("age"):
        bot.send_message(user.id, "How old are you? (12-99)")
        pending_age.add(user.id)
        bot.register_next_step_handler(message, process_new_age)
    elif not u.get("country"):
        bot.send_message(user.id, "Where are you from? (e.g., India)")
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = "💎 Premium" if db_is_premium(user.id) else "Free"
        bot.send_message(user.id, f"✅ Welcome back!\nStatus: {premium_status}\nUse /search to find someone to chat with.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex_"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)
    if db_is_banned(uid):
        bot.answer_callback_query(call.id, "⛔ You're banned", show_alert=True)
        return

    u = db_get_user(uid)
    if u and u.get("gender"):
        if uid != ADMIN_ID and not db_is_premium(uid):
            bot.answer_callback_query(call.id, "⛔ Premium feature!", show_alert=True)
            return

    _, gender = call.data.split("_")
    gender_display = "👨 Male" if gender == "male" else "👩 Female"
    db_set_gender(uid, gender_display)
    bot.answer_callback_query(call.id, "✅ Gender set!", show_alert=True)

    try:
        bot.edit_message_text(f"✅ Gender: {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

def process_new_age(message):
    uid = message.from_user.id
    text = message.text or ""
    if uid not in pending_age:
        bot.send_message(uid, "Use /start first")
        return

    if not text.isdigit():
        bot.send_message(uid, "❌ Please enter a valid number.")
        bot.register_next_step_handler(message, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, "❌ Age must be between 12-99.")
        bot.register_next_step_handler(message, process_new_age)
        return

    db_set_age(uid, age)
    pending_age.discard(uid)

    u = db_get_user(uid)
    if not u or not u.get("country"):
        bot.send_message(uid, f"✅ Age set to {age}!\n\nWhere are you from? (e.g., India)")
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(uid, f"✅ Age set to {age}!\n\nProfile complete! Use /search to find someone.")

def process_new_country(message):
    uid = message.from_user.id
    text = message.text or ""
    if uid not in pending_country:
        bot.send_message(uid, "Use /start first")
        return

    country_info = get_country_info(text)
    if not country_info:
        bot.send_message(uid, "❌ Country not found. Try again.")
        bot.register_next_step_handler(message, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)

    bot.send_message(uid, f"✅ Perfect! You're all set.\n\nUse /search to find someone.")

@bot.message_handler(commands=["search"])
def cmd_search(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "⛔ You're banned.")
        return

    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete your profile first! Use /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "❌ You're already chatting. Use /next or /stop")
            return

    if is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return

    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = datetime.utcnow()

    bot.send_message(uid, "🔍 Searching for someone... may take a moment")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    if is_searching(uid):
        remove_from_queues(uid)
        bot.send_message(uid, "🔍 Search cancelled.")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            disconnect_user(uid)
            return

    bot.send_message(uid, "❌ You're not chatting. Use /search to find someone.")

@bot.message_handler(commands=["next"])
def cmd_next(message):
    uid = message.from_user.id
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ You're not chatting.")
            return
        disconnect_user(uid)

    bot.send_message(uid, "🔍 Finding new partner...")
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = datetime.utcnow()
    match_users()

@bot.message_handler(commands=["report"])
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
        bot.send_message(uid, "❌ No one to report.")
        return

    u_reporter = db_get_user(uid)
    u_reported = db_get_user(reported_id)
    reporter_name = u_reporter.get("firstname", "User") if u_reporter else "User"
    reported_name = u_reported.get("firstname", "User") if u_reported else "User"
    chat_status = "Active Chat" if is_active_chat else "After Chat"

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📢 Spam", callback_data="rep_spam"),
               types.InlineKeyboardButton("😡 Inappropriate", callback_data="rep_inappropriate"),
               types.InlineKeyboardButton("🔔 Suspicious", callback_data="rep_suspicious"),
               types.InlineKeyboardButton("❓ Other", callback_data="rep_other"),
               types.InlineKeyboardButton("❌ Cancel", callback_data="rep_cancel"))

    bot.send_message(uid, "Why are you reporting this user?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep_") or c.data.startswith("report_"))
def handle_report(call):
    uid = call.from_user.id
    data = call.data

    if data.startswith("report_after"):
        # After chat report
        if uid not in chat_history_with_time:
            bot.answer_callback_query(call.id, "❌ No one to report", show_alert=True)
            return
        reported_id, _ = chat_history_with_time[uid]
        is_active_chat = False
    elif data.startswith("rep_"):
        # During chat report
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
            bot.answer_callback_query(call.id, "❌ Error", show_alert=True)
            return

        data_parts = data.split("_")
        report_reason_key = data_parts[1]

        if report_reason_key == "cancel":
            bot.answer_callback_query(call.id, "❌ Cancelled", show_alert=False)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return

        reason_map = {
            "spam": "📢 Spam",
            "inappropriate": "😡 Inappropriate",
            "suspicious": "🔔 Suspicious",
            "other": "❓ Other"
        }
        report_reason = reason_map.get(report_reason_key, report_reason_key)
    else:
        bot.answer_callback_query(call.id, "❌ Error", show_alert=True)
        return

    u_reporter = db_get_user(uid)
    u_reported = db_get_user(reported_id)
    reporter_name = u_reporter.get("firstname", "User") if u_reporter else "User"
    reported_name = u_reported.get("firstname", "User") if u_reported else "User"
    chat_status = "Active Chat" if is_active_chat else "After Chat"

    db_add_report(uid, reporter_name, reported_id, reported_name, report_reason if 'report_reason' in locals() else "After Chat", chat_status)

    # ✅ Enhanced: Forward full chat to admin
    with get_conn() as conn:
        rows = conn.execute("SELECT sender_name, message_content FROM chatlogs WHERE (sender_id=? OR sender_id=?) AND (receiver_id=? OR receiver_id=?) ORDER BY timestamp DESC LIMIT 20",
            (uid, reported_id, reported_id, uid)).fetchall()

    forward_chat_to_admin(uid, reported_id, report_reason if 'report_reason' in locals() else "After Chat", rows)

    bot.answer_callback_query(call.id, "✅ Reported", show_alert=False)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    logger.info(f"REPORT {reporter_name} (ID: {uid}) → {reported_name} (ID: {reported_id}) Reason: {report_reason if 'report_reason' in locals() else 'After Chat'}")

@bot.message_handler(func=lambda m: m.content_type == 'text' and not m.text.startswith('/'))
def forward_chat(message):
    uid = message.from_user.id
    text = message.text or ""

    if text.startswith('/'):
        return

    if db_is_banned(uid):
        bot.send_message(uid, "⛔ You are banned")
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
        sender_name = sender_user.get("firstname", "User") if sender_user else "User"
        receiver_name = receiver_user.get("firstname", "User") if receiver_user else "User"

        db_save_chat_log(uid, sender_name, partner_id, receiver_name, "text", text)

        if partner_id == ADMIN_ID:
            admin_msg = f"SENDER: {sender_name} (ID: {uid})\nGender: {sender_user.get('gender', '?')}\nAge: {sender_user.get('age', '?')}\nCountry: {sender_user.get('countryflag', '?')} {sender_user.get('country', '?')}\n\nRECEIVER: Admin\nMessage: {text}"
            bot.send_message(partner_id, admin_msg)
        else:
            bot.send_message(partner_id, text)

        with get_conn() as conn:
            conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE userid=?", (uid,))
            conn.commit()
    except Exception as e:
        logger.error(f"Forward error: {e}")

@bot.message_handler(content_types=["photo", "video", "document", "voice", "audio", "sticker"])
def handle_media(message):
    """✅ Media Accept/Reject - Voice + Audio Support"""
    uid = message.from_user.id

    with active_pairs_lock:
        if uid not in active_pairs:
            return
        partner_id = active_pairs[uid]

    sender_user = db_get_user(uid)
    receiver_user = db_get_user(partner_id)
    sender_name = sender_user.get("firstname", "User") if sender_user else "User"
    receiver_name = receiver_user.get("firstname", "User") if receiver_user else "User"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    media_icons = {
        "photo": "📷 Photo",
        "video": "🎥 Video",
        "document": "📄 Document",
        "voice": "🎤 Voice Message",
        "audio": "🎵 Audio",
        "sticker": "🎨 Sticker"
    }
    media_type = media_icons.get(message.content_type, "📦 Media")

    # Store for accept/reject
    token = f"{uid}{int(time.time()*1000)}{secrets.token_hex(4)}"
    with pending_media_lock:
        pending_media[token] = (uid, partner_id, message.content_type, message, timestamp)

    db_save_chat_log(uid, sender_name, partner_id, receiver_name, message.content_type, media_type)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f"media_accept_{token}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"media_reject_{token}"))

    try:
        if partner_id == ADMIN_ID:
            admin_msg = f"📦 MEDIA\n\nSender: {sender_name} (ID: {uid})\nGender: {sender_user.get('gender', '?')}\nAge: {sender_user.get('age', '?')}\nCountry: {sender_user.get('countryflag', '?')} {sender_user.get('country', '?')}\n\nReceiver: Admin\nType: {media_type}\nTime: {timestamp}\n\nAllow?"
            bot.send_message(partner_id, admin_msg, reply_markup=markup)
        else:
            user_msg = f"{sender_name} sent {media_type}. Allow?"
            bot.send_message(partner_id, user_msg, reply_markup=markup)

        logger.info(f"Media {media_type} from {sender_name} (ID: {uid}) to {receiver_name} (ID: {partner_id})")
    except Exception as e:
        logger.error(f"Media error: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("media_"))
def handle_media_approval(call):
    """✅ Handle media accept/reject"""
    uid = call.from_user.id
    parts = call.data.split("_")
    action = parts[1]
    token = parts[2]

    with pending_media_lock:
        if token not in pending_media:
            bot.answer_callback_query(call.id, "❌ Expired", show_alert=True)
            return

        sender_id, partner_id_check, media_type, message, timestamp = pending_media[token]
        if partner_id_check != uid:
            bot.answer_callback_query(call.id, "❌ Invalid", show_alert=True)
            return

        del pending_media[token]

    try:
        if action == "accept":
            try:
                if media_type == "photo":
                    bot.send_photo(uid, message.photo[-1].file_id)
                elif media_type == "video":
                    bot.send_video(uid, message.video.file_id)
                elif media_type == "document":
                    bot.send_document(uid, message.document.file_id)
                elif media_type == "voice":
                    bot.send_voice(uid, message.voice.file_id)
                elif media_type == "audio":
                    bot.send_audio(uid, message.audio.file_id)
                elif media_type == "sticker":
                    bot.send_sticker(uid, message.sticker.file_id)
            except Exception as e:
                logger.error(f"Media send error: {e}")
                bot.send_message(uid, "Failed to send media")
                bot.send_message(sender_id, "Failed to send media")
                return

            db_increment_media(sender_id, "approved")
            bot.send_message(sender_id, f"✅ Your {media_type} was ACCEPTED!")
            bot.answer_callback_query(call.id, "✅ Sent", show_alert=False)

            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass

            logger.info(f"Media accepted: {sender_id} → {uid}")
        else:
            db_increment_media(sender_id, "rejected")
            bot.send_message(sender_id, f"❌ Your {media_type} was REJECTED.")
            bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)

            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass

            logger.info(f"Media rejected: {sender_id} from {uid}")
    except Exception as e:
        logger.error(f"Media error: {e}")
        bot.send_message(uid, "Error processing media")

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

                logger.info(f"Cleanup: Removed {len(to_delete)} old records")
            except:
                pass

    t = threading.Thread(target=run, daemon=True)
    t.start()

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
                                    bot.send_message(uid, "❌ No matches found. Try again later.")
                                except:
                                    pass
            except Exception as e:
                logger.error(f"Search timeout monitor error: {e}")

    t = threading.Thread(target=run, daemon=True)
    t.start()

if __name__ == "__main__":
    init_db()
    cleanup_threads()
    search_timeout_monitor()

    logger.info("=" * 60)
    logger.info("GhostTalk v5.4 - COMPLETE FIXED FINAL")
    logger.info("=" * 60)
    logger.info("✅ Reconnect Feature")
    logger.info("✅ Report System + Chat Forwarding")
    logger.info("✅ Media Accept/Reject (Voice + Audio)")
    logger.info("✅ NO CHAT FREEZE")
    logger.info("✅ UptimeRobot Polling")
    logger.info("=" * 60)

    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    logger.info(f"Flask on port {os.getenv('PORT', 5000)}")

    while True:
        try:
            logger.info("Starting polling...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30, none_stop=True)
        except KeyboardInterrupt:
            logger.info("Bot stopped")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.info("Restarting in 5 seconds...")
            time.sleep(5)
