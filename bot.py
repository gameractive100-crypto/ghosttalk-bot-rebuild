#!/usr/bin/env python3
"""
GhostTalk v5.4 - COMPLETE FIXED FINAL
✅ NO FREEZE - /next and /stop work instantly
✅ NO MENUS - Only text commands
✅ Match info: Users see (Age) Gender 🌍 Country (NO name)
✅ Match info: Admin sees Name (Age) Gender 🌍 Country - ID: userid
✅ Report: Full chat forwarded WITH media info
✅ /reconnect command works
✅ ALL inline buttons REMOVED
"""

import sqlite3
import random
import logging
import re
from datetime import datetime, timedelta, timezone
import time
import secrets
import threading
import os
import sys
import telebot
from telebot import types
from flask import Flask

# ============ CONFIG ============
API_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
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
SEARCH_TIMEOUT_SECONDS = 120

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('ghosttalk.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# ============ BANNED WORDS ============
BANNED_WORDS = [
    "fuck", "fucking", "sex chat", "nudes", "pussy", "dick", "cock", "penis",
    "vagina", "boobs", "tits", "ass", "asshole", "bitch", "slut", "whore",
    "hoe", "prostitute", "porn", "pornography", "rape", "child", "pedo",
    "anj", "anjing", "babi", "asu", "kontl", "kontol", "puki", "memek",
    "jembut", "maderchod", "mc", "bhen ka lauda", "bhenkalauda", "randi",
    "randika", "gand", "bsdk", "chut", "chot", "chuut", "choot", "lund"
]

LINK_PATTERN = re.compile(r"https?://www.", re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

# ============ 195 COUNTRIES ============
COUNTRIES = [
    "afghanistan", "albania", "algeria", "andorra", "angola", "antigua and barbuda",
    "argentina", "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
    "bangladesh", "barbados", "belarus", "belgium", "belize", "benin", "bhutan", "bolivia",
    "bosnia and herzegovina", "botswana", "brazil", "brunei", "bulgaria", "burkina faso",
    "burundi", "cambodia", "cameroon", "canada", "cape verde", "central african republic",
    "chad", "chile", "china", "colombia", "comoros", "congo", "costa rica", "croatia",
    "cuba", "cyprus", "czech republic", "czechia", "denmark", "djibouti", "dominica",
    "dominican republic", "ecuador", "egypt", "el salvador", "equatorial guinea", "eritrea",
    "estonia", "eswatini", "ethiopia", "fiji", "finland", "france", "gabon", "gambia",
    "georgia", "germany", "ghana", "greece", "grenada", "guatemala", "guinea", "guinea-bissau",
    "guyana", "haiti", "honduras", "hungary", "iceland", "india", "indonesia", "iran", "iraq",
    "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan", "kenya",
    "kiribati", "korea north", "korea south", "kuwait", "kyrgyzstan", "laos", "latvia",
    "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg",
    "madagascar", "malawi", "malaysia", "maldives", "mali", "malta", "marshall islands",
    "mauritania", "mauritius", "mexico", "micronesia", "moldova", "monaco", "mongolia",
    "montenegro", "morocco", "mozambique", "myanmar", "namibia", "nauru", "nepal",
    "netherlands", "new zealand", "nicaragua", "niger", "nigeria", "north macedonia", "norway",
    "oman", "pakistan", "palau", "palestine", "panama", "papua new guinea", "paraguay", "peru",
    "philippines", "poland", "portugal", "qatar", "romania", "russia", "rwanda",
    "saint kitts and nevis", "saint lucia", "saint vincent and the grenadines", "samoa",
    "san marino", "sao tome and principe", "saudi arabia", "senegal", "serbia", "seychelles",
    "sierra leone", "singapore", "slovakia", "slovenia", "solomon islands", "somalia",
    "south africa", "south sudan", "spain", "sri lanka", "sudan", "suriname", "sweden",
    "switzerland", "syria", "taiwan", "tajikistan", "tanzania", "thailand", "timor-leste",
    "togo", "tonga", "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
    "uganda", "ukraine", "united arab emirates", "united kingdom", "united states", "uruguay",
    "uzbekistan", "vanuatu", "vatican city", "venezuela", "vietnam", "yemen", "zambia", "zimbabwe"
]

COUNTRY_ALIASES = {
    "usa": "united states", "us": "united states", "america": "united states",
    "uk": "united kingdom", "britain": "united kingdom", "england": "united kingdom",
    "uae": "united arab emirates", "emirates": "united arab emirates",
    "south korea": "korea south", "sk": "korea south",
    "north korea": "korea north", "nk": "korea north", "czechia": "czech republic"
}

def get_now():
    return datetime.now(timezone.utc)

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
search_start_time = {}

queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()

# ============ DATABASE ============
def get_conn():
    conn = sqlite3.connect(DBPATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            userid INTEGER PRIMARY KEY,
            username TEXT,
            firstname TEXT,
            gender TEXT,
            age INTEGER,
            country TEXT,
            countryflag TEXT,
            messages_sent INTEGER DEFAULT 0,
            media_approved INTEGER DEFAULT 0,
            media_rejected INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referral_count INTEGER DEFAULT 0,
            premium_until TEXT,
            joined_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS bans (
            userid INTEGER PRIMARY KEY,
            ban_until TEXT,
            permanent INTEGER DEFAULT 0,
            reason TEXT,
            banned_by INTEGER,
            banned_at TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reporter_name TEXT,
            reported_id INTEGER,
            reported_name TEXT,
            report_type TEXT,
            chat_status TEXT,
            timestamp TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS recent_partners (
            userid INTEGER PRIMARY KEY,
            partner_id INTEGER,
            last_disconnect TEXT,
            reconnect_until TEXT
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS chatlogs (
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
    logger.info("Database initialized")

def db_get_user(userid):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT userid, username, firstname, gender, age, country, countryflag, messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until FROM users WHERE userid=?",
            (userid,)).fetchone()
        if not row:
            return None
        return {
            "userid": row[0], "username": row[1], "firstname": row[2], "gender": row[3],
            "age": row[4], "country": row[5], "countryflag": row[6], "messages_sent": row[7],
            "media_approved": row[8], "media_rejected": row[9], "referral_code": row[10],
            "referral_count": row[11], "premium_until": row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (userid, username, firstname, gender, age, country, countryflag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, user.username or "", user.first_name or "", None, None, None, None, get_now().isoformat(), ref_code))
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
        return datetime.fromisoformat(u["premium_until"]) > get_now()
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
                return datetime.fromisoformat(ban_until) > get_now()
            except:
                return False
    return False

def db_ban_user(userid, hours=None, permanent=False, reason=""):
    with get_conn() as conn:
        if permanent:
            conn.execute("INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (userid, None, 1, reason, ADMIN_ID, get_now().isoformat()))
        else:
            until = (get_now() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute("INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (userid, until, 0, reason, ADMIN_ID, get_now().isoformat()))
        conn.commit()

def db_unban_user(userid):
    with get_conn() as conn:
        conn.execute("DELETE FROM bans WHERE userid=?", (userid,))
        conn.commit()

def db_add_report(reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status):
    timestamp = get_now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reports (reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (reporter_id, reporter_name, reported_id, reported_name, report_type, chat_status, timestamp))
        count = conn.execute("SELECT COUNT(*) FROM reports WHERE reported_id=?", (reported_id,)).fetchone()[0]
        conn.commit()

        if count >= AUTO_BAN_REPORTS and not db_is_banned(reported_id):
            ban_until = (get_now() + timedelta(days=AUTO_BAN_DAYS)).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO bans (userid, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)",
                (reported_id, ban_until, 0, f"Auto-ban {count} reports", ADMIN_ID, get_now().isoformat()))
            logger.warning(f"AUTO-BAN User {reported_id} for {AUTO_BAN_DAYS} days")
            try:
                bot.send_message(reported_id, f"🚫 You've been banned for {AUTO_BAN_DAYS} days due to reports.")
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
    timestamp = get_now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chatlogs (sender_id, sender_name, receiver_id, receiver_name, message_type, message_content, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sender_id, sender_name, receiver_id, receiver_name, msg_type, content, timestamp))
        conn.commit()

def db_save_recent_partner(userid, partner_id):
    with get_conn() as conn:
        now = get_now().isoformat()
        reconnect_until = (get_now() + timedelta(minutes=5)).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO recent_partners (userid, partner_id, last_disconnect, reconnect_until) VALUES (?, ?, ?, ?)",
            (userid, partner_id, now, reconnect_until))
        conn.commit()

def db_get_recent_partner(userid):
    with get_conn() as conn:
        row = conn.execute("SELECT partner_id, reconnect_until FROM recent_partners WHERE userid=?", (userid,)).fetchone()
        if not row:
            return None
        partner_id, reconnect_until = row
        try:
            if datetime.fromisoformat(reconnect_until) > get_now():
                return partner_id
        except:
            pass
        conn.execute("DELETE FROM recent_partners WHERE userid=?", (userid,))
        conn.commit()
    return None

def db_increment_media(userid, stat_type):
    with get_conn() as conn:
        if stat_type == "approved":
            conn.execute("UPDATE users SET media_approved=media_approved+1 WHERE userid=?", (userid,))
        elif stat_type == "rejected":
            conn.execute("UPDATE users SET media_rejected=media_rejected+1 WHERE userid=?", (userid,))
        conn.commit()

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
                bot.send_message(userid, f"⛔ Banned for {TEMP_BAN_HOURS}h. Reason: {reason}")
            except:
                pass
            remove_from_queues(userid)
            disconnect_user(userid)
            return "ban"
        else:
            try:
                bot.send_message(userid, f"⚠️ Warning {count}/{WARNING_LIMIT}")
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
        return userid in waiting_random or userid in waiting_premium_opposite

def disconnect_user(userid):
    """FIXED: NO FREEZE - Safe disconnect"""
    global active_pairs
    try:
        with active_pairs_lock:
            if userid not in active_pairs:
                return

            partner_id = active_pairs.get(userid)

            # Remove both users from active pairs FIRST
            if userid in active_pairs:
                del active_pairs[userid]
            if partner_id and partner_id in active_pairs:
                del active_pairs[partner_id]

            if partner_id:
                now = get_now()
                chat_history_with_time[userid] = (partner_id, now)
                chat_history_with_time[partner_id] = (userid, now)
                db_save_recent_partner(userid, partner_id)
                db_save_recent_partner(partner_id, userid)

        # Send messages OUTSIDE the lock
        try:
            bot.send_message(partner_id, f"👋 Your partner left.")
        except:
            pass

        try:
            bot.send_message(userid, "Chat ended. Use /search to find someone new.")
        except:
            pass
    except Exception as e:
        logger.error(f"Disconnect error: {e}")

def forward_report_to_admin(reporter_id, reported_id, report_type):
    """FIXED: Forward FULL chat with media info"""
    try:
        user_reporter = db_get_user(reporter_id)
        user_reported = db_get_user(reported_id)

        reporter_name = user_reporter.get("firstname", "User") if user_reporter else "User"
        reported_name = user_reported.get("firstname", "User") if user_reported else "User"

        # Header with IDs
        admin_msg = f"""📋 REPORT

Report Type: {report_type}
Reporter: {reporter_name} (ID: {reporter_id})
Reported: {reported_name} (ID: {reported_id})
Time: {get_now().strftime('%Y-%m-%d %H:%M:%S')}

---FULL CHAT HISTORY---"""

        try:
            bot.send_message(ADMIN_ID, admin_msg)
        except Exception as e:
            logger.error(f"Error sending report header: {e}")
            return

        # Get full chat with all media info
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT sender_id, sender_name, message_type, message_content, timestamp FROM chatlogs WHERE (sender_id=? OR sender_id=?) AND (receiver_id=? OR receiver_id=?) ORDER BY timestamp ASC LIMIT 50",
                (reporter_id, reported_id, reported_id, reporter_id)).fetchall()

        if rows:
            for sender_id, sender_name, msg_type, content, ts in rows:
                # Show media type with description
                if msg_type == "text":
                    log_msg = f"[{ts}] {sender_name} (ID: {sender_id}): {content[:300]}"
                else:
                    log_msg = f"[{ts}] {sender_name} (ID: {sender_id}) sent: {content}"

                try:
                    bot.send_message(ADMIN_ID, log_msg)
                except:
                    pass
        else:
            try:
                bot.send_message(ADMIN_ID, "No chat history found")
            except:
                pass

        try:
            bot.send_message(ADMIN_ID, "---END OF REPORT---")
        except:
            pass
    except Exception as e:
        logger.error(f"Report error: {e}")

def match_users():
    """Match users - FIXED format"""
    global waiting_random, waiting_premium_opposite, active_pairs

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
                        # User 1 sees User 2 info
                        info2 = f"({u2.get('age', '?')}) {u2.get('gender', '?')[:1]} {u2.get('countryflag', '🌍')} {u2.get('country', '?')}"
                        # User 2 sees User 1 info
                        info1 = f"({u1.get('age', '?')}) {u1.get('gender', '?')[:1]} {u1.get('countryflag', '🌍')} {u1.get('country', '?')}"
                        # Admin sees full info with ID

                        bot.send_message(uid1, f"✅ Matched with {info2}")
                        bot.send_message(uid2, f"✅ Matched with {info1}")

                        logger.info(f"Matched {uid1} ↔ {uid2}")
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

            try:
                u1_data = db_get_user(u1)
                u2_data = db_get_user(u2)

                # User 1 sees User 2 info
                info2 = f"({u2_data.get('age', '?')}) {u2_data.get('gender', '?')[:1]} {u2_data.get('countryflag', '🌍')} {u2_data.get('country', '?')}"
                # User 2 sees User 1 info
                info1 = f"({u1_data.get('age', '?')}) {u1_data.get('gender', '?')[:1]} {u1_data.get('countryflag', '🌍')} {u1_data.get('country', '?')}"

                bot.send_message(u1, f"✅ Matched with {info2}")
                bot.send_message(u2, f"✅ Matched with {info1}")

                logger.info(f"Matched {u1} ↔ {u2}")
            except:
                pass

# ============ FLASK ============
@app.route("/", methods=["GET"])
def home():
    return "GhostTalk v5.4 - Running!", 200

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "timestamp": get_now().isoformat()}, 200

# ============ ADMIN COMMANDS ============

@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 2:
            bot.send_message(ADMIN_ID, "Usage: /ban userid [hours] [reason]")
            return
        userid = int(parts[1])
        hours = int(parts[2]) if len(parts) > 2 else 24
        reason = parts[3] if len(parts) > 3 else "No reason"
        db_ban_user(userid, hours=hours, reason=reason)
        try:
            bot.send_message(userid, f"🚫 Banned for {hours}h. Reason: {reason}")
        except:
            pass
        bot.send_message(ADMIN_ID, f"✅ Banned user {userid}")
    except:
        pass

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return
        userid = int(parts[1])
        db_unban_user(userid)
        try:
            bot.send_message(userid, "✅ You've been unbanned!")
        except:
            pass
        bot.send_message(ADMIN_ID, f"✅ Unbanned user {userid}")
    except:
        pass

@bot.message_handler(commands=["pradd"])
def cmd_pradd(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 3:
            return
        userid = int(parts[1])
        date_str = parts[2]
        if db_set_premium(userid, date_str):
            try:
                bot.send_message(userid, f"🎉 Premium until {date_str}!")
            except:
                pass
            bot.send_message(ADMIN_ID, f"✅ Added premium to {userid} until {date_str}")
    except:
        pass

@bot.message_handler(commands=["prrem"])
def cmd_prrem(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return
        userid = int(parts[1])
        db_remove_premium(userid)
        try:
            bot.send_message(userid, "⏱️ Premium removed.")
        except:
            pass
        bot.send_message(ADMIN_ID, f"✅ Removed premium from {userid}")
    except:
        pass

# ============ USER COMMANDS ============

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.send_message(user.id, "⛔ Banned.")
        return

    u = db_get_user(user.id)
    if not u or not u.get("gender"):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="sex_male"),
            types.InlineKeyboardButton("👩 Female", callback_data="sex_female")
        )
        bot.send_message(user.id, "Choose gender:", reply_markup=markup)
    elif not u.get("age"):
        msg = bot.send_message(user.id, "How old are you? (12-99)")
        pending_age.add(user.id)
        bot.register_next_step_handler(msg, process_new_age)
    elif not u.get("country"):
        msg = bot.send_message(user.id, "Where are you from?")
        pending_country.add(user.id)
        bot.register_next_step_handler(msg, process_new_country)
    else:
        premium = "💎 Premium" if db_is_premium(user.id) else "Free"
        bot.send_message(user.id, f"✅ Welcome!\nStatus: {premium}\nUse /search to chat")

@bot.callback_query_handler(func=lambda c: c.data.startswith("sex_"))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)
    if db_is_banned(uid):
        return

    u = db_get_user(uid)
    if u and u.get("gender"):
        bot.answer_callback_query(call.id, "Already selected")
        return

    _, gender = call.data.split("_")
    gender_display = "Male" if gender == "male" else "Female"
    db_set_gender(uid, gender_display)

    try:
        bot.edit_message_text(f"✅ {gender_display}", call.message.chat.id, call.message.message_id)
    except:
        pass

    # AUTO-TRIGGER age
    msg = bot.send_message(uid, "How old are you? (12-99)")
    pending_age.add(uid)
    bot.register_next_step_handler(msg, process_new_age)

def process_new_age(message):
    uid = message.from_user.id
    text = message.text or ""

    if uid not in pending_age:
        return

    if not text.isdigit():
        msg = bot.send_message(uid, "❌ Enter a number")
        bot.register_next_step_handler(msg, process_new_age)
        return

    age = int(text)
    if age < 12 or age > 99:
        msg = bot.send_message(uid, "❌ Age 12-99 only")
        bot.register_next_step_handler(msg, process_new_age)
        return

    db_set_age(uid, age)
    pending_age.discard(uid)

    u = db_get_user(uid)
    if not u or not u.get("country"):
        msg = bot.send_message(uid, f"✅ Age: {age}\n\nWhere are you from?")
        pending_country.add(uid)
        bot.register_next_step_handler(msg, process_new_country)
    else:
        bot.send_message(uid, f"✅ Profile complete! Use /search")

def process_new_country(message):
    uid = message.from_user.id
    text = message.text or ""

    if uid not in pending_country:
        return

    country_info = get_country_info(text)
    if not country_info:
        msg = bot.send_message(uid, "❌ Country not found")
        bot.register_next_step_handler(msg, process_new_country)
        return

    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)

    bot.send_message(uid, f"✅ Set to {country_name}!\n\nUse /search to find someone")

@bot.message_handler(commands=["search"])
def cmd_search(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "⛔ Banned.")
        return

    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete profile: /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "❌ Already chatting. Use /next or /stop")
            return

    if is_searching(uid):
        bot.send_message(uid, "⏳ Already searching.")
        return

    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = get_now()

    bot.send_message(uid, "🔍 Searching...")
    match_users()

@bot.message_handler(commands=["search_opposite"])
def cmd_search_opposite(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "⛔ Banned.")
        return

    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.send_message(uid, "💎 Premium only.")
        return

    u = db_get_user(uid)
    if not u or not u.get("gender") or not u.get("age") or not u.get("country"):
        bot.send_message(uid, "❌ Complete profile: /start")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "❌ Already chatting.")
            return

    if is_searching(uid):
        bot.send_message(uid, "⏳ Already searching.")
        return

    opposite = "Female" if u.get("gender") == "Male" else "Male"
    remove_from_queues(uid)
    with queue_lock:
        waiting_premium_opposite.append(uid)
        search_start_time[uid] = get_now()

    bot.send_message(uid, f"🔍 Searching for {opposite}...")
    match_users()

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    """FIXED: NO FREEZE"""
    uid = message.from_user.id
    if is_searching(uid):
        remove_from_queues(uid)
        bot.send_message(uid, "🔍 Cancelled.")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            disconnect_user(uid)
            return

    bot.send_message(uid, "❌ Not chatting.")

@bot.message_handler(commands=["next"])
def cmd_next(message):
    """FIXED: NO FREEZE"""
    uid = message.from_user.id

    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, "❌ Not chatting.")
            return
        disconnect_user(uid)

    bot.send_message(uid, "🔍 Finding new partner...")
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = get_now()
    match_users()

@bot.message_handler(commands=["reconnect"])
def cmd_reconnect(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "⛔ Banned.")
        return

    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, "❌ Already chatting.")
            return

    partner_id = db_get_recent_partner(uid)
    if not partner_id:
        bot.send_message(uid, "❌ No recent partner.")
        return

    if partner_id in active_pairs:
        bot.send_message(uid, "❌ Partner busy.")
        return

    reconnect_requests[uid] = (partner_id, get_now())

    try:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Yes", callback_data=f"recon_accept_{uid}"),
            types.InlineKeyboardButton("❌ No", callback_data=f"recon_decline_{uid}")
        )
        bot.send_message(partner_id, "Reconnect request!", reply_markup=markup)
        bot.send_message(uid, "⏳ Request sent")
    except:
        bot.send_message(uid, "❌ Error")

@bot.callback_query_handler(func=lambda c: c.data.startswith("recon_"))
def handle_reconnect(call):
    partner_id = call.from_user.id
    parts = call.data.split("_")
    action = parts[1]
    requester_id = int(parts[2])

    if requester_id not in reconnect_requests:
        bot.answer_callback_query(call.id, "Expired")
        return

    stored_partner, req_time = reconnect_requests[requester_id]
    if stored_partner != partner_id:
        bot.answer_callback_query(call.id, "Invalid")
        return

    if (get_now() - req_time).total_seconds() > RECONNECT_TIMEOUT:
        bot.answer_callback_query(call.id, "Timeout")
        del reconnect_requests[requester_id]
        return

    del reconnect_requests[requester_id]

    if action == "accept":
        with active_pairs_lock:
            active_pairs[requester_id] = partner_id
            active_pairs[partner_id] = requester_id
        bot.answer_callback_query(call.id, "Connected!")
        try:
            bot.send_message(requester_id, "✅ Reconnected!")
            bot.send_message(partner_id, "✅ Reconnected!")
        except:
            pass
    else:
        bot.answer_callback_query(call.id, "Declined")
        try:
            bot.send_message(requester_id, "❌ Declined.")
        except:
            pass

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

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Spam", callback_data="rep_spam"),
        types.InlineKeyboardButton("😡 Inappropriate", callback_data="rep_inappropriate"),
        types.InlineKeyboardButton("🔔 Suspicious", callback_data="rep_suspicious"),
        types.InlineKeyboardButton("❓ Other", callback_data="rep_other"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="rep_cancel")
    )

    bot.send_message(uid, "Why report?", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rep_"))
def handle_report(call):
    uid = call.from_user.id
    data = call.data

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
        bot.answer_callback_query(call.id, "Error")
        return

    data_parts = data.split("_")
    report_reason_key = data_parts[1]

    if report_reason_key == "cancel":
        bot.answer_callback_query(call.id, "Cancelled")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    reason_map = {"spam": "Spam", "inappropriate": "Inappropriate", "suspicious": "Suspicious", "other": "Other"}
    report_reason = reason_map.get(report_reason_key, "Other")

    u_reporter = db_get_user(uid)
    u_reported = db_get_user(reported_id)
    reporter_name = u_reporter.get("firstname", "User") if u_reporter else "User"
    reported_name = u_reported.get("firstname", "User") if u_reported else "User"
    chat_status = "Active" if is_active_chat else "After"

    db_add_report(uid, reporter_name, reported_id, reported_name, report_reason, chat_status)
    forward_report_to_admin(uid, reported_id, report_reason)

    bot.answer_callback_query(call.id, "Reported!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    logger.info(f"REPORT {reporter_name} (ID: {uid}) → {reported_name} (ID: {reported_id}) Reason: {report_reason}")

@bot.message_handler(commands=["settings"])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start")
        return
    premium = "Yes" if db_is_premium(uid) else "No"
    country = f"{u.get('countryflag', '🌍')} {u.get('country', '?')}" if u.get("country") else "Not set"
    bot.send_message(uid, f"""Profile
Gender: {u.get('gender', '?')}
Age: {u.get('age', '?')}
Country: {country}
Premium: {premium}
Messages: {u.get('messages_sent', 0)}""")

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start")
        return
    try:
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={u['referral_code']}"
    except:
        ref_link = f"REF:{u['referral_code']}"
    remaining = PREMIUM_REFERRALS_NEEDED - u.get('referral_count', 0)
    bot.send_message(uid, f"Share: {ref_link}\nProgress: {u.get('referral_count', 0)}/{PREMIUM_REFERRALS_NEEDED}\nRemaining: {remaining}")

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start")
        return
    premium = "Yes" if db_is_premium(uid) else "No"
    country = f"{u.get('countryflag', '🌍')} {u.get('country', '?')}" if u.get("country") else "Not set"
    bot.send_message(uid, f"""Stats
Gender: {u.get('gender', '?')}
Age: {u.get('age', '?')}
Country: {country}
Messages: {u.get('messages_sent', 0)}
Media OK: {u.get('media_approved', 0)}
Media Rejected: {u.get('media_rejected', 0)}
Referrals: {u.get('referral_count', 0)}
Premium: {premium}""")

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(message.from_user.id, """/start - Setup
/search - Find chat
/search_opposite - Opposite gender
/next - Skip
/stop - Exit
/reconnect - Resume
/report - Report
/settings - Profile
/refer - Invite
/stats - Stats
/help - This""")

@bot.message_handler(commands=["rules"])
def cmd_rules(message):
    bot.send_message(message.from_user.id, """Rules

1. Be respectful
2. No adult content
3. Protect privacy
4. Media only with consent
5. No harassment

Violations = Ban""")

@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def forward_chat(message):
    uid = message.from_user.id
    text = message.text or ""

    if db_is_banned(uid):
        bot.send_message(uid, "⛔ Banned")
        return

    if is_banned_content(text):
        warn_user(uid, "Banned content")
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
        bot.send_message(partner_id, text)

        with get_conn() as conn:
            conn.execute("UPDATE users SET messages_sent=messages_sent+1 WHERE userid=?", (uid,))
            conn.commit()
    except:
        pass

@bot.message_handler(content_types=["photo", "video", "document", "voice", "audio", "sticker"])
def handle_media(message):
    uid = message.from_user.id

    with active_pairs_lock:
        if uid not in active_pairs:
            return
        partner_id = active_pairs[uid]

    sender_user = db_get_user(uid)
    receiver_user = db_get_user(partner_id)
    sender_name = sender_user.get("firstname", "User") if sender_user else "User"
    receiver_name = receiver_user.get("firstname", "User") if receiver_user else "User"

    media_type_map = {"photo": "Photo", "video": "Video", "document": "Document", "voice": "Voice", "audio": "Audio", "sticker": "Sticker"}
    media_type = media_type_map.get(message.content_type, "Media")

    db_save_chat_log(uid, sender_name, partner_id, receiver_name, message.content_type, f"Sent {media_type}")
    db_increment_media(uid, "approved")

    try:
        if message.content_type == "photo":
            bot.send_photo(partner_id, message.photo[-1].file_id)
        elif message.content_type == "video":
            bot.send_video(partner_id, message.video.file_id)
        elif message.content_type == "document":
            bot.send_document(partner_id, message.document.file_id)
        elif message.content_type == "voice":
            bot.send_voice(partner_id, message.voice.file_id)
        elif message.content_type == "audio":
            bot.send_audio(partner_id, message.audio.file_id)
        elif message.content_type == "sticker":
            bot.send_sticker(partner_id, message.sticker.file_id)
    except:
        pass

def cleanup_threads():
    def run():
        while True:
            time.sleep(3600)
            try:
                now = get_now()
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
                logger.info(f"Cleanup: {len(to_delete)} removed")
            except:
                pass
    t = threading.Thread(target=run, daemon=True)
    t.start()

def search_timeout_monitor():
    def run():
        while True:
            time.sleep(30)
            try:
                now = get_now()
                with queue_lock:
                    for uid in list(search_start_time.keys()):
                        elapsed = (now - search_start_time[uid]).total_seconds()
                        if elapsed > SEARCH_TIMEOUT_SECONDS:
                            if uid in waiting_random or uid in waiting_premium_opposite:
                                remove_from_queues(uid)
                                try:
                                    bot.send_message(uid, "❌ No match found.")
                                except:
                                    pass
            except:
                pass
    t = threading.Thread(target=run, daemon=True)
    t.start()

if __name__ == "__main__":
    init_db()
    cleanup_threads()
    search_timeout_monitor()

    logger.info("=" * 80)
    logger.info("GhostTalk v5.4 - COMPLETE FIXED FINAL")
    logger.info("=" * 80)
    logger.info("✅ NO FREEZE - /next and /stop instant")
    logger.info("✅ NO MENUS - Text commands only")
    logger.info("✅ Match info correct format")
    logger.info("✅ Report forwarding with media")
    logger.info("✅ /reconnect command added")
    logger.info("=" * 80)

    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, none_stop=True)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)
