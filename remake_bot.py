#!/usr/bin/env python3
BOT_TOKEN = "8299763849:AAEJr34Cohs4xtqhJtIIFebr7qCAfQfMNuw"         # <-- EDIT THIS: Bot token from BotFather
BOT_USERNAME = "SayNymBot"             # <-- EDIT THIS: Bot username without @
ADMIN_ID = 8361006824                        # <-- EDIT THIS: Admin numeric Telegram ID
OWNER_ID = 8361006824                        # <-- EDIT THIS: Owner numeric Telegram ID (superuser)
''''
GhostTalk Full — single-file Telegram anonymous chat bot (pyTelegramBotAPI)

Features included:
- /start (with optional referral code)
- Gender selection via InlineKeyboard (prevents callback conflicts)
  - Duplicate selection -> "Already set"
  - Can change anytime via /settings
- /settings, /refer, /stats
- /search_random (open), /search_male & /search_female (premium unless owner)
- /next (skip partner), /stop (end chat / cancel search)
- Owner highlighting and Owner VIP treatment
- Referral system: every 2 referrals => +1 hour premium
- Reports system + supports (likes)
  - Auto-ban rules:
    * reports > 5 and supports >= 10 => PERMANENT BAN
    * reports >= 5 => TEMPORARY 24h BAN
  - Banned user receives instruction to /appeal
- Appeals: banned users can /appeal; admin can list /appeals and /review_appeal <id> accept|reject
- Media (photo/video/sticker/document) -> pending approval: Accept/Reject inline buttons
- Admin commands: /ban, /unban
- Database: SQLite persisting users, bans, reports, supports, pending_media, appeals
- Reply keyboard for convenience
"""
// python .py

import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta

import telebot
from telebot import types

# ---------------- CONFIG (edit these) ----------------
 # For run this bot  = python "d:\telegram-bot\remake_bot.py"
API_TOKEN = "8299763849:AAEJr34Cohs4xtqhJtIIFebr7qCAfQfMNuw"           # <-- Put your bot token
BOT_USERNAME = "SayNymBot"        # <-- Bot username without @
ADMIN_ID = 8361006824                        # <-- Admin user id (numeric). # admin-config
OWNER_ID = 8361006824                        # <-- Owner user id (numeric). # owner-config
ANNOUNCE_CHANNEL_ID = None                  # <-- Optional channel id to announce bans, e.g. -1001234567890
DB_PATH = "ghosttalk_full.db"
AUTO_BAN_THRESHOLD = 5                      # reports required to trigger ban logic
REFERRALS_FOR_PREMIUM = 2                   # referrals needed for 1 hour premium
PREMIUM_HOURS_PER_REF_REWARD = 1            # hours granted per cycle
# ----------------------------------------------------

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(API_TOKEN)

# Runtime matchmaking structures (in-memory, DB persists important info)
waiting_random = []
waiting_male_desire = []
waiting_female_desire = []
active_pairs = {}  # user_id -> partner_id

# For reply keyboard helper
KeyboardButton = types.KeyboardButton

# ---------------- Database helpers ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        gender TEXT,
        chats_completed INTEGER DEFAULT 0,
        messages_sent INTEGER DEFAULT 0,
        premium_until TEXT DEFAULT NULL,
        referral_code TEXT UNIQUE,
        referral_count INTEGER DEFAULT 0,
        joined_at TEXT
    )''')
    # bans
    c.execute('''CREATE TABLE IF NOT EXISTS bans (
        user_id INTEGER PRIMARY KEY,
        ban_until TEXT DEFAULT NULL,
        permanent INTEGER DEFAULT 0
    )''')
    # reports
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER,
        reported_user_id INTEGER,
        reason TEXT,
        timestamp TEXT
    )''')
    # pending media
    c.execute('''CREATE TABLE IF NOT EXISTS pending_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        to_user INTEGER,
        from_user INTEGER,
        media_type TEXT,
        file_id TEXT,
        timestamp TEXT
    )''')
    # supports (likes / support for contested user)
    c.execute('''CREATE TABLE IF NOT EXISTS supports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supporter_id INTEGER,
        supported_user_id INTEGER,
        timestamp TEXT,
        UNIQUE(supporter_id, supported_user_id)
    )''')
    # appeals
    c.execute('''CREATE TABLE IF NOT EXISTS appeals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        status TEXT DEFAULT 'pending',
        admin_response TEXT,
        created_at TEXT,
        reviewed_at TEXT
    )''')
    conn.commit()
    conn.close()

def db_get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, gender, chats_completed, messages_sent, premium_until, referral_code, referral_count, joined_at FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "user_id": row[0],
        "username": row[1],
        "first_name": row[2],
        "gender": row[3],
        "chats_completed": row[4],
        "messages_sent": row[5],
        "premium_until": row[6],
        "referral_code": row[7],
        "referral_count": row[8],
        "joined_at": row[9],
    }

def db_create_user_if_missing(user):
    uid = user.id
    existing = db_get_user(uid)
    if existing:
        return existing
    anon_ref = f"REF{uid}{random.randint(1000,9999)}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, gender, referral_code, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
              (uid, user.username or "", user.first_name or "", None, anon_ref, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return db_get_user(uid)

def db_set_gender(user_id, gender):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
    conn.commit()
    conn.close()

def db_is_banned(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ban_until, permanent FROM bans WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    ban_until, permanent = row
    if permanent == 1:
        return True
    if ban_until:
        try:
            until = datetime.fromisoformat(ban_until)
            return datetime.utcnow() < until
        except Exception:
            return False
    return False

def db_ban_user(user_id, hours=None, permanent=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if permanent:
        c.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent) VALUES (?, ?, ?)", (user_id, None, 1))
    else:
        until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
        c.execute("INSERT OR REPLACE INTO bans (user_id, ban_until, permanent) VALUES (?, ?, ?)", (user_id, until, 0))
    conn.commit()
    conn.close()
    # cleanup runtime
    remove_from_all_waitlists(user_id)
    if user_id in active_pairs:
        end_pair(user_id, notify=True)

def db_unban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_add_report(reporter_id, reported_user_id, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO reports (reporter_id, reported_user_id, reason, timestamp) VALUES (?, ?, ?, ?)",
              (reporter_id, reported_user_id, reason, datetime.utcnow().isoformat()))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM reports WHERE reported_user_id = ?", (reported_user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def db_add_pending_media(to_user, from_user, media_type, file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO pending_media (to_user, from_user, media_type, file_id, timestamp) VALUES (?, ?, ?, ?, ?)",
              (to_user, from_user, media_type, file_id, datetime.utcnow().isoformat()))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return pid

def db_get_pending_media_for_user(to_user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, from_user, media_type, file_id, timestamp FROM pending_media WHERE to_user = ? ORDER BY id ASC LIMIT 1", (to_user,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "from_user": row[1], "media_type": row[2], "file_id": row[3], "timestamp": row[4]}

def db_delete_pending_media(pid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_media WHERE id = ?", (pid,))
    conn.commit()
    conn.close()

def db_increment_messages(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET messages_sent = messages_sent + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_increment_chats_completed(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET chats_completed = chats_completed + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_add_referral(referrer_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
    conn.commit()
    c.execute("SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,))
    rc = c.fetchone()[0]
    conn.close()
    return rc

def db_add_premium_hours(user_id, hours):
    u = db_get_user(user_id)
    now = datetime.utcnow()
    if u and u["premium_until"]:
        try:
            existing = datetime.fromisoformat(u["premium_until"])
            if existing > now:
                new_until = existing + timedelta(hours=hours)
            else:
                new_until = now + timedelta(hours=hours)
        except Exception:
            new_until = now + timedelta(hours=hours)
    else:
        new_until = now + timedelta(hours=hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET premium_until = ? WHERE user_id = ?", (new_until.isoformat(), user_id))
    conn.commit()
    conn.close()
    return new_until

def db_is_premium(user_id):
    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return False
    try:
        return datetime.fromisoformat(u["premium_until"]) > datetime.utcnow()
    except Exception:
        return False

def db_get_premium_hours(user_id):
    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return 0.0
    try:
        diff = datetime.fromisoformat(u["premium_until"]) - datetime.utcnow()
        return max(0.0, diff.total_seconds() / 3600.0)
    except Exception:
        return 0.0

# Supports & Appeals helpers
def db_support_exists(supporter_id, supported_user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM supports WHERE supporter_id=? AND supported_user_id=?", (supporter_id, supported_user_id))
    r = c.fetchone()
    conn.close()
    return bool(r)

def db_add_support(supporter_id, supported_user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO supports (supporter_id, supported_user_id, timestamp) VALUES (?, ?, ?)",
                  (supporter_id, supported_user_id, datetime.utcnow().isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def db_get_support_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM supports WHERE supported_user_id = ?", (user_id,))
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def db_add_appeal(user_id, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO appeals (user_id, text, created_at) VALUES (?, ?, ?)",
              (user_id, text, datetime.utcnow().isoformat()))
    conn.commit()
    aid = c.lastrowid
    conn.close()
    return aid

def db_get_pending_appeals():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, text, created_at FROM appeals WHERE status='pending' ORDER BY created_at ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def db_get_appeal(aid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, user_id, text, status, admin_response, created_at, reviewed_at FROM appeals WHERE id = ?", (aid,))
    row = c.fetchone()
    conn.close()
    return row

def db_set_appeal_status(aid, status, admin_response=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE appeals SET status = ?, admin_response = ?, reviewed_at = ? WHERE id = ?",
              (status, admin_response, datetime.utcnow().isoformat(), aid))
    conn.commit()
    conn.close()

# ---------------- Utility helpers ----------------
def reply_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row(KeyboardButton("/search_random"), KeyboardButton("/search_male"))
    kb.row(KeyboardButton("/search_female"), KeyboardButton("/stop"))
    kb.row(KeyboardButton("/next"), KeyboardButton("/settings"), KeyboardButton("/refer"))
    kb.row(KeyboardButton("/stats"), KeyboardButton("/report"))
    return kb

def user_is_searching(uid):
    return uid in waiting_random or uid in waiting_male_desire or uid in waiting_female_desire

def remove_from_all_waitlists(uid):
    if uid in waiting_random: waiting_random.remove(uid)
    if uid in waiting_male_desire: waiting_male_desire.remove(uid)
    if uid in waiting_female_desire: waiting_female_desire.remove(uid)

def end_pair(user_id, notify=True):
    partner = active_pairs.pop(user_id, None)
    if partner:
        active_pairs.pop(partner, None)
        db_increment_chats_completed(user_id)
        db_increment_chats_completed(partner)
        if notify:
            try:
                bot.send_message(partner, "❎ Your partner ended the chat.")
            except Exception:
                pass

# ---------------- Handlers ----------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.send_message(user.id, "🚫 You are banned and cannot use the bot.")
        return
    # referral handling: allow /start <ref_code> or /start REF<...> or /start <id>
    args = message.text.split()
    if len(args) > 1:
        ref = args[1]
        ref_id = None
        if ref.lower().startswith("ref"):
            try:
                numeric = ''.join(ch for ch in ref if ch.isdigit())
                ref_id = int(numeric) if numeric else None
            except:
                ref_id = None
        else:
            try:
                ref_id = int(ref)
            except:
                ref_id = None
        if ref_id and ref_id != user.id and db_get_user(ref_id):
            rc = db_add_referral(ref_id)
            # reward: every REFERRALS_FOR_PREMIUM referrals -> add PREMIUM_HOURS_PER_REF_REWARD
            if rc >= REFERRALS_FOR_PREMIUM:
                db_add_premium_hours(ref_id, PREMIUM_HOURS_PER_REF_REWARD)
                # subtract cycle
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE users SET referral_count = referral_count - ? WHERE user_id = ?", (REFERRALS_FOR_PREMIUM, ref_id))
                conn.commit()
                conn.close()
                try:
                    bot.send_message(ref_id, f"🎉 You earned {PREMIUM_HOURS_PER_REF_REWARD} hour(s) premium for referrals!")
                except:
                    pass
            else:
                try:
                    need = REFERRALS_FOR_PREMIUM - rc
                    bot.send_message(ref_id, f"👍 You got a referral! Share {need} more to earn premium.")
                except:
                    pass

    # show gender selection if not set
    u = db_get_user(user.id)
    if not u or not u["gender"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("♂️ Male", callback_data="setgender:Male"),
                   types.InlineKeyboardButton("♀️ Female", callback_data="setgender:Female"))
        bot.send_message(user.id, "Welcome to GhostTalk! Please select your gender:", reply_markup=markup)
    else:
        bot.send_message(user.id, "Welcome back! Use /search_random, /search_male (premium), or /search_female (premium).", reply_markup=reply_keyboard())

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("setgender:"))
def callback_setgender(call):
    uid = call.from_user.id
    if db_is_banned(uid):
        call.answer("You are banned.", show_alert=True)
        return
    _, gender = call.data.split(":", 1)
    gender = gender.capitalize()
    user = db_get_user(uid)
    if user and user["gender"] and user["gender"].lower() == gender.lower():
        try:
            call.answer(f"✅ Already set to {gender}", show_alert=True)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"✅ Your gender is already set to *{gender}*.", parse_mode="Markdown")
            return
        except Exception:
            pass
    db_set_gender(uid, gender)
    try:
        call.answer(f"✅ Gender set to {gender}", show_alert=False)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"✅ Gender set to *{gender}*.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=["settings"])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    gender = u["gender"] or "Not set"
    code = u["referral_code"]
    prem_hours = db_get_premium_hours(uid)
    prem_text = f"{prem_hours:.2f}h remaining" if prem_hours > 0 else "No active premium"
    text = f"⚙️ Settings\nGender: {gender}\nReferrals: {u['referral_count']}\nPremium: {prem_text}\nReferral link: https://t.me/{BOT_USERNAME}?start={code}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Set Male ♂️", callback_data="setgender:Male"),
               types.InlineKeyboardButton("Set Female ♀️", callback_data="setgender:Female"))
    bot.send_message(uid, text, reply_markup=markup)

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    code = u["referral_code"]
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(uid, f"Share this link with friends. For every {REFERRALS_FOR_PREMIUM} successful referrals you get {PREMIUM_HOURS_PER_REF_REWARD} hour(s) premium.\n{link}")

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    prem = db_get_premium_hours(uid)
    prem_text = f"{prem:.2f}h remaining" if prem > 0 else "No active premium"
    bot.send_message(uid, f"📊 Stats:\nGender: {u['gender']}\nChats completed: {u['chats_completed']}\nMessages sent: {u['messages_sent']}\nReferrals: {u['referral_count']}\nPremium: {prem_text}")

# ---------- Matching core ----------
def try_match_for_user(requester_id, desired_gender=None):
    if desired_gender:
        # search waiting_random for someone of desired gender first
        for cand in list(waiting_random):
            if cand == requester_id: continue
            cu = db_get_user(cand)
            if cu and cu["gender"] and cu["gender"].lower() == desired_gender.lower():
                waiting_random.remove(cand)
                return cand
        # then check other queues
        for q in list(waiting_male_desire + waiting_female_desire):
            if q == requester_id: continue
            cu = db_get_user(q)
            if cu and cu["gender"] and cu["gender"].lower() == desired_gender.lower():
                if q in waiting_male_desire: waiting_male_desire.remove(q)
                if q in waiting_female_desire: waiting_female_desire.remove(q)
                return q
        return None
    else:
        # random matching
        for cand in list(waiting_random):
            if cand != requester_id:
                waiting_random.remove(cand)
                return cand
        for cand in list(waiting_male_desire + waiting_female_desire):
            if cand != requester_id:
                if cand in waiting_male_desire: waiting_male_desire.remove(cand)
                if cand in waiting_female_desire: waiting_female_desire.remove(cand)
                return cand
        return None

def send_connected_messages(uid, partner):
    # formatting and owner highlight logic
    def format_msg_for(user_from, user_to):
        if user_from == OWNER_ID:
            return f"🌟 OWNER is connected with you! Start chatting. Use /next to find another partner or /stop to end."
        else:
            return "✅ Partner found! Start typing. Use /next to find a new partner or /stop to end."

    try:
        if uid == OWNER_ID or partner == OWNER_ID:
            # owner present - VIP behavior
            bot.send_message(uid, format_msg_for(OWNER_ID, uid), reply_markup=reply_keyboard())
            bot.send_message(partner, format_msg_for(OWNER_ID, partner), reply_markup=reply_keyboard())
            # ensure owner has long premium (optional)
            db_add_premium_hours(OWNER_ID, 24*365)  # one year effectively; edit if undesired # owner-config
        else:
            bot.send_message(uid, format_msg_for(uid, partner), reply_markup=reply_keyboard())
            bot.send_message(partner, format_msg_for(partner, uid), reply_markup=reply_keyboard())
    except Exception:
        pass

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(message.from_user)
    if uid in active_pairs:
        bot.send_message(uid, "❗ You are already in a chat. Use /stop first.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    partner = try_match_for_user(uid, None)
    if partner:
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        send_connected_messages(uid, partner)
    else:
        waiting_random.append(uid)
        bot.send_message(uid, "🔎 Searching for a random partner... Please wait.", reply_markup=reply_keyboard())

@bot.message_handler(commands=["search_male"])
def cmd_search_male(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(message.from_user)
    if uid in active_pairs:
        bot.send_message(uid, "❗ You are already in a chat. Use /stop first.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    if not db_is_premium(uid) and uid != OWNER_ID:
        u = db_get_user(uid)
        link = f"https://t.me/{BOT_USERNAME}?start={u['referral_code']}"
        bot.send_message(uid, f"🔒 /search_male is premium. Share this link with {REFERRALS_FOR_PREMIUM} people to get premium:\n{link}")
        return
    partner = try_match_for_user(uid, "Male")
    if partner:
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        send_connected_messages(uid, partner)
    else:
        waiting_male_desire.append(uid)
        bot.send_message(uid, "🔎 Searching for a male partner... Please wait.", reply_markup=reply_keyboard())

@bot.message_handler(commands=["search_female"])
def cmd_search_female(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(message.from_user)
    if uid in active_pairs:
        bot.send_message(uid, "❗ You are already in a chat. Use /stop first.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    if not db_is_premium(uid) and uid != OWNER_ID:
        u = db_get_user(uid)
        link = f"https://t.me/{BOT_USERNAME}?start={u['referral_code']}"
        bot.send_message(uid, f"🔒 /search_female is premium. Share this link with {REFERRALS_FOR_PREMIUM} people to get premium:\n{link}")
        return
    partner = try_match_for_user(uid, "Female")
    if partner:
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        send_connected_messages(uid, partner)
    else:
        waiting_female_desire.append(uid)
        bot.send_message(uid, "🔎 Searching for a female partner... Please wait.", reply_markup=reply_keyboard())

@bot.message_handler(commands=["next"])
def cmd_next(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid in active_pairs:
        # end current and immediately try to find a new partner
        partner = active_pairs.get(uid)
        end_pair(uid, notify=True)
        bot.send_message(uid, "🔁 Finding you a new partner...", reply_markup=reply_keyboard())
        partner_id = try_match_for_user(uid, None)
        if partner_id:
            active_pairs[uid] = partner_id
            active_pairs[partner_id] = uid
            send_connected_messages(uid, partner_id)
        else:
            waiting_random.append(uid)
            bot.send_message(uid, "🔎 Searching... Please wait.", reply_markup=reply_keyboard())
    else:
        bot.send_message(uid, "ℹ️ You are not in a chat. Use /search_random to start.", reply_markup=reply_keyboard())

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if user_is_searching(uid):
        remove_from_all_waitlists(uid)
        bot.send_message(uid, "⏹ Search stopped.", reply_markup=reply_keyboard())
        return
    if uid in active_pairs:
        end_pair(uid, notify=True)
        bot.send_message(uid, "🛑 You ended the chat.", reply_markup=reply_keyboard())
        return
    bot.send_message(uid, "ℹ️ You are not in a chat or searching.", reply_markup=reply_keyboard())

# ---------- REPORT / SUPPORT / AUTO-BAN ----------
@bot.message_handler(commands=["report"])
def cmd_report(message):
    uid = message.from_user.id
    if uid not in active_pairs:
        bot.send_message(uid, "❌ You are not in a chat to report someone.")
        return
    partner = active_pairs[uid]
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Abuse", callback_data=f"rep:abuse:{partner}"),
               types.InlineKeyboardButton("Spam", callback_data=f"rep:spam:{partner}"))
    markup.row(types.InlineKeyboardButton("Harassment", callback_data=f"rep:harass:{partner}"),
               types.InlineKeyboardButton("Porn/Explicit", callback_data=f"rep:porn:{partner}"))
    markup.row(types.InlineKeyboardButton("Child Abuse", callback_data=f"rep:child:{partner}"),
               types.InlineKeyboardButton("Other", callback_data=f"rep:other:{partner}"))
    bot.send_message(uid, "Select reason for report:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("rep:"))
def callback_report(call):
    try:
        _, reason, reported = call.data.split(":", 2)
        reported_id = int(reported)
    except Exception:
        call.answer("Invalid", show_alert=True)
        return

    reporter = call.from_user.id
    if reporter == reported_id:
        call.answer("You cannot report yourself.", show_alert=True)
        return

    count = db_add_report(reporter, reported_id, reason)
    support_count = db_get_support_count(reported_id)

    call.answer(f"✅ Reported! ({count} reports, {support_count} supports)", show_alert=False)
    # notify admin
    try:
        bot.send_message(ADMIN_ID, f"📋 Report: {reporter} -> {reported_id} ({reason}) [{count} reports, {support_count} supports]")
    except:
        pass

    # Auto-ban logic
    if count > AUTO_BAN_THRESHOLD and support_count >= 10:
        db_ban_user(reported_id, permanent=True)
        try:
            bot.send_message(reported_id, "🚫 You have been *permanently banned* for repeated critical violations. To appeal, send /appeal <explain what happened>.", parse_mode="Markdown")
        except:
            pass
        if ANNOUNCE_CHANNEL_ID:
            try:
                bot.send_message(ANNOUNCE_CHANNEL_ID, f"🚨 User {reported_id} has been permanently banned for multiple violations.")
            except:
                pass
        try:
            bot.send_message(ADMIN_ID, f"🚨 {reported_id} permanently banned (reports={count}, supports={support_count}).")
        except:
            pass
    elif count >= AUTO_BAN_THRESHOLD:
        db_ban_user(reported_id, hours=24, permanent=False)
        try:
            bot.send_message(reported_id, "⏳ You have been temporarily banned for 24 hours due to multiple reports. To appeal, send /appeal <your explanation>.")
        except:
            pass
        try:
            bot.send_message(ADMIN_ID, f"⚠️ {reported_id} temporarily banned 24h (reports={count}).")
        except:
            pass

@bot.message_handler(commands=["support"])
def cmd_support(message):
    # usage: /support <user_id>
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /support <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.reply_to(message, "Invalid user id.")
        return
    supporter = message.from_user.id
    if supporter == target:
        bot.reply_to(message, "You cannot support yourself.")
        return
    if not db_get_user(target):
        bot.reply_to(message, "User not found.")
        return
    if db_support_exists(supporter, target):
        bot.reply_to(message, "You already supported this user.")
        return
    ok = db_add_support(supporter, target)
    if ok:
        sc = db_get_support_count(target)
        bot.reply_to(message, f"✅ Support recorded. Total supports for {target}: {sc}")
        # re-evaluate auto-ban condition
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM reports WHERE reported_user_id = ?", (target,))
        rc = c.fetchone()[0]
        conn.close()
        if rc > AUTO_BAN_THRESHOLD and sc >= 10:
            db_ban_user(target, permanent=True)
            bot.send_message(target, "🚫 You have been permanently banned.")
            bot.send_message(ADMIN_ID, f"🚨 {target} permanently banned after supports reached {sc} and reports {rc}.")
            if ANNOUNCE_CHANNEL_ID:
                try:
                    bot.send_message(ANNOUNCE_CHANNEL_ID, f"🚨 User {target} has been permanently banned.")
                except:
                    pass
    else:
        bot.reply_to(message, "Could not record support. Possibly you already supported this user.")

# ---------- Appeals ----------
@bot.message_handler(commands=["appeal"])
def cmd_appeal(message):
    uid = message.from_user.id
    if not db_is_banned(uid):
        bot.reply_to(message, "You are not banned. Appeals are only for banned users.")
        return
    text = message.text.partition(' ')[2].strip()
    if not text:
        bot.reply_to(message, "Usage: /appeal <your explanation>")
        return
    aid = db_add_appeal(uid, text)
    bot.reply_to(message, f"✅ Appeal submitted. Admin will review it. Appeal ID: {aid}")
    try:
        bot.send_message(ADMIN_ID, f"📨 New appeal #{aid} from {uid}:\n{text}\nUse /appeals to list or /review_appeal {aid} accept|reject <note>")
    except:
        pass

@bot.message_handler(commands=["appeals"])
def cmd_appeals(message):
    if message.from_user.id != ADMIN_ID:
        return
    rows = db_get_pending_appeals()
    if not rows:
        bot.reply_to(message, "No pending appeals.")
        return
    text = "Pending appeals:\n"
    for r in rows:
        aid, uid, txt, created = r
        text += f"#{aid} from {uid}: {txt[:80]}... ({created})\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=["review_appeal"])
def cmd_review_appeal(message):
    # usage: /review_appeal <appeal_id> <accept|reject> [note]
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /review_appeal <appeal_id> <accept|reject> [note]")
        return
    try:
        aid = int(parts[1])
    except:
        bot.reply_to(message, "Invalid appeal id.")
        return
    action = parts[2].lower()
    note = " ".join(parts[3:]) if len(parts) > 3 else None
    appeal = db_get_appeal(aid)
    if not appeal:
        bot.reply_to(message, "Appeal not found.")
        return
    _, uid, text, status, admin_resp, created, reviewed = appeal
    if status != 'pending':
        bot.reply_to(message, f"Appeal already {status}.")
        return
    if action == "accept":
        db_unban_user(uid)
        db_set_appeal_status(aid, 'accepted', admin_response=note or 'Accepted by admin')
        bot.reply_to(message, f"Appeal #{aid} accepted. User {uid} unbanned.")
        try:
            bot.send_message(uid, f"✅ Your appeal #{aid} was accepted by admin. You have been unbanned. Note: {note or ''}")
        except:
            pass
    elif action == "reject":
        db_set_appeal_status(aid, 'rejected', admin_response=note or 'Rejected by admin')
        bot.reply_to(message, f"Appeal #{aid} rejected.")
        try:
            bot.send_message(uid, f"❌ Your appeal #{aid} was rejected. Admin note: {note or ''}")
        except:
            pass
    else:
        bot.reply_to(message, "Invalid action. Use accept or reject.")

# ---------- Media & pending approval ----------
def send_pending_prompt(to_user):
    pending = db_get_pending_media_for_user(to_user)
    if not pending:
        return
    pid = pending["id"]
    mt = pending["media_type"]
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Accept ✅", callback_data=f"media_accept:{pid}"),
           types.InlineKeyboardButton("Reject ❌", callback_data=f"media_reject:{pid}"))
    bot.send_message(to_user, f"📬 Your partner wants to send a {mt}. Accept to view?", reply_markup=kb)

@bot.message_handler(content_types=["photo"])
def handler_photo(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "You are not in a chat. Use /search_random to find someone.")
        return
    partner = active_pairs[uid]
    if db_get_pending_media_for_user(partner):
        bot.send_message(uid, "⏳ Your partner has a pending item. Wait for them to accept/reject.")
        return
    file_id = m.photo[-1].file_id
    pid = db_add_pending_media(partner, uid, "photo", file_id)
    send_pending_prompt(partner)
    bot.send_message(uid, "📤 Photo sent to partner for approval.")

@bot.message_handler(content_types=["video"])
def handler_video(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "You are not in a chat. Use /search_random to find someone.")
        return
    partner = active_pairs[uid]
    if db_get_pending_media_for_user(partner):
        bot.send_message(uid, "⏳ Your partner has a pending item. Wait for them to accept/reject.")
        return
    file_id = m.video.file_id
    pid = db_add_pending_media(partner, uid, "video", file_id)
    send_pending_prompt(partner)
    bot.send_message(uid, "📤 Video sent to partner for approval.")

@bot.message_handler(content_types=["sticker"])
def handler_sticker(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "You are not in a chat. Use /search_random to find someone.")
        return
    partner = active_pairs[uid]
    if db_get_pending_media_for_user(partner):
        bot.send_message(uid, "⏳ Your partner has a pending item. Wait for them to accept/reject.")
        return
    file_id = m.sticker.file_id
    pid = db_add_pending_media(partner, uid, "sticker", file_id)
    send_pending_prompt(partner)
    bot.send_message(uid, "📤 Sticker sent to partner for approval.")

@bot.message_handler(content_types=["document"])
def handler_document(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "You are not in a chat. Use /search_random to find someone.")
        return
    partner = active_pairs[uid]
    if db_get_pending_media_for_user(partner):
        bot.send_message(uid, "⏳ Your partner has a pending item. Wait for them to accept/reject.")
        return
    file_id = m.document.file_id
    pid = db_add_pending_media(partner, uid, "document", file_id)
    send_pending_prompt(partner)
    bot.send_message(uid, "📤 Document sent to partner for approval.")

@bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("media_accept:") or call.data.startswith("media_reject:")))
def callback_media_accept_reject(call):
    uid = call.from_user.id
    action, pid_str = call.data.split(":", 1)
    try:
        pid = int(pid_str)
    except:
        call.answer("Invalid data", show_alert=True)
        return
    pending = db_get_pending_media_for_user(uid)
    if not pending or pending["id"] != pid:
        call.answer("No pending content or already handled.", show_alert=True)
        return
    from_user = pending["from_user"]
    media_type = pending["media_type"]
    file_id = pending["file_id"]
    if action == "media_accept":
        try:
            if media_type == "photo":
                bot.send_photo(uid, file_id)
            elif media_type == "video":
                bot.send_video(uid, file_id)
            elif media_type == "sticker":
                bot.send_sticker(uid, file_id)
            elif media_type == "document":
                bot.send_document(uid, file_id)
            bot.send_message(from_user, "✅ Your partner accepted and the content was delivered.")
            call.edit_message_text("✅ Content delivered.")
        except Exception:
            bot.send_message(from_user, "❗ Failed to deliver content.")
            call.edit_message_text("❗ Failed to deliver content.")
    else:
        bot.send_message(from_user, "❌ Your partner rejected the content.")
        call.edit_message_text("❌ Content rejected.")
    db_delete_pending_media(pid)

# ---------- text forwarding ----------
@bot.message_handler(func=lambda m: m.content_type == "text" and not m.text.startswith("/"))
def handler_text(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(m.from_user)
    if uid in active_pairs:
        partner = active_pairs.get(uid)
        # Owner special formatting
        if uid == OWNER_ID:
            try:
                bot.send_message(partner, f"🌟 OWNER MESSAGE:\n\n{m.text}")
                db_increment_messages(uid)
            except Exception:
                end_pair(uid, notify=True)
                bot.send_message(uid, "❗ Unable to deliver message; chat ended.")
            return
        try:
            bot.send_message(partner, m.text)
            db_increment_messages(uid)
        except Exception:
            end_pair(uid, notify=True)
            bot.send_message(uid, "❗ Failed to send message to partner. Chat ended.")
    else:
        # convenience
        if m.text.strip().startswith("/"):
            bot.send_message(uid, "Use the keyboard for quick commands.", reply_markup=reply_keyboard())
        else:
            bot.send_message(uid, "Use /search_random or premium searches to find someone to chat with.", reply_markup=reply_keyboard())

# ---------- Admin: ban/unban ----------
@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ No permission.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban <user_id> [hours/permanent]")
        return
    try:
        target = int(parts[1])
    except:
        bot.reply_to(message, "Invalid user id.")
        return
    permanent = False
    hours = None
    if len(parts) >= 3:
        if parts[2].lower() == "permanent":
            permanent = True
        else:
            try:
                hours = int(parts[2])
            except:
                hours = None
    db_ban_user(target, hours=hours, permanent=permanent)
    bot.reply_to(message, f"🚫 User {target} banned. permanent={permanent}, hours={hours}")

@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ No permission.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /unban <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.reply_to(message, "Invalid user id.")
        return
    db_unban_user(target)
    bot.reply_to(message, f"✅ User {target} unbanned.")

# ---------------- Startup ----------------
if __name__ == "__main__":
    init_db()
    logger.info("GhostTalk Full starting...")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception:
        logger.exception("Bot crashed")
