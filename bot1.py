#!/usr/bin/env python3
"""
GhostTalk - Single-file Telegram anonymous chat bot (pyTelegramBotAPI)

Features implemented:
- /start (with optional referral: /start ref_<id>)
- /settings (gender select, referral link, referral count, premium status)
- /refer (shows referral link)
- /search_random (everyone)
- /search_male, /search_female (PREMIUM)
- /stop (stop searching or end chat)
- /stats (basic stats)
- Media forwarding with Accept/Reject (photo, sticker, video, document)
- /ban and /unban (admin only) - # admin-config
- SQLite for persistence (users, bans, referrals, pending_media)
- ReplyKeyboardMarkup to show main commands when user types '/'
- All admin-configurable values marked with '# admin-config'
"""

import os
import sqlite3
import random
import logging
from datetime import datetime, timedelta

import telebot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
) # For run this bot  = python "d:\telegram-bot\bot1.py"


# -------------------- CONFIG (edit these) --------------------
API_TOKEN = "8299763849:AAEJr34Cohs4xtqhJtIIFebr7qCAfQfMNuw"           # <-- Put your bot token
BOT_USERNAME = "SayNymBot"        # <-- Put your bot username (without @)
ADMIN_ID = 7779114606                        # <-- Replace with your Telegram user id (admin). # admin-config
DB_PATH = "ghostbot.db"
# ----------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(API_TOKEN)

# In-memory runtime structures (mirrors DB state for quick ops)
waiting_male_desire = []     # users who are waiting and want MALE partner
waiting_female_desire = []   # users who are waiting and want FEMALE partner
waiting_random = []          # users waiting for random partner
active_pairs = {}            # user_id -> partner_id
# pending_media handled in DB (so persists)

# -------------------- DATABASE HELPERS --------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
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
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            to_user INTEGER,
            from_user INTEGER,
            media_type TEXT,
            file_id TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def db_get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, gender, chats_completed, messages_sent, premium_until, referral_code, referral_count, joined_at FROM users WHERE user_id = ?", (user_id,))
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
    u = db_get_user(uid)
    if u:
        return u
    anon_ref = f"REF{uid}{random.randint(1000,9999)}"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, first_name, gender, referral_code, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
        (uid, user.username or "", user.first_name or "", None, anon_ref, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return db_get_user(uid)

def db_set_gender(user_id, gender):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
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

def db_get_referral_info(user_id):
    u = db_get_user(user_id)
    if not u:
        return None, 0
    return u["referral_code"], u["referral_count"]

def db_add_premium_hours(user_id, hours):
    u = db_get_user(user_id)
    now = datetime.utcnow()
    if u and u["premium_until"]:
        current = datetime.fromisoformat(u["premium_until"])
        if current > now:
            new_until = current + timedelta(hours=hours)
        else:
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

def db_get_premium_hours_remaining(user_id):
    u = db_get_user(user_id)
    if not u or not u["premium_until"]:
        return 0.0
    try:
        diff = datetime.fromisoformat(u["premium_until"]) - datetime.utcnow()
        return max(0.0, diff.total_seconds() / 3600.0)
    except Exception:
        return 0.0

def db_increment_stat_messages(user_id):
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

def db_is_banned(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM bans WHERE user_id = ?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r is not None

def db_ban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO bans (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def db_unban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

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
    return {
        "id": row[0],
        "from_user": row[1],
        "media_type": row[2],
        "file_id": row[3],
        "timestamp": row[4]
    }

def db_delete_pending_media(pending_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_media WHERE id = ?", (pending_id,))
    conn.commit()
    conn.close()

# -------------------- UTIL --------------------
def reply_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row(KeyboardButton("/search_random"), KeyboardButton("/search_male"))
    kb.row(KeyboardButton("/search_female"), KeyboardButton("/stop"))
    kb.row(KeyboardButton("/settings"), KeyboardButton("/refer"), KeyboardButton("/stats"))
    return kb

def user_is_searching(user_id):
    return user_id in waiting_random or user_id in waiting_male_desire or user_id in waiting_female_desire

def remove_from_all_waitlists(user_id):
    if user_id in waiting_random:
        waiting_random.remove(user_id)
    if user_id in waiting_male_desire:
        waiting_male_desire.remove(user_id)
    if user_id in waiting_female_desire:
        waiting_female_desire.remove(user_id)

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

# -------------------- HANDLERS --------------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
    # usage: /start or /start ref_<user_id>
    user = message.from_user
    db_create_user_if_missing(user)
    if db_is_banned(user.id):
        bot.reply_to(message, "🚫 You are permanently banned.")
        return

    args = message.text.split()
    # referral parsing: allow /start ref_12345 or /start 12345
    if len(args) > 1:
        ref = args[1]
        ref_id = None
        if ref.lower().startswith("ref_"):
            try:
                ref_id = int(ref.split("_", 1)[1])
            except Exception:
                ref_id = None
        else:
            try:
                ref_id = int(ref)
            except Exception:
                ref_id = None
        if ref_id and ref_id != user.id and db_get_user(ref_id):
            rc = db_add_referral(ref_id)
            # Every 2 referrals → +1 hour premium
            if rc >= 2:
                db_add_premium_hours(ref_id, 1)
                # subtract 2 referrals
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE users SET referral_count = referral_count - 2 WHERE user_id = ?", (ref_id,))
                conn.commit()
                conn.close()
                try:
                    bot.send_message(ref_id, "🎉 You got 1 hour premium for referring 2 users!")
                except Exception:
                    pass
            else:
                try:
                    needed = 2 - rc
                    bot.send_message(ref_id, f"👍 You got a referral! Share {needed} more to earn 1 hour premium.")
                except Exception:
                    pass

    # Reply and show keyboard
    u = db_get_user(user.id)
    msg = f"👋 Hi {user.first_name or user.username or user.id}!\nThis is GhostTalk.\nUse the keyboard /search_random, /search_male (premium), /search_female (premium)."
    bot.send_message(user.id, msg, reply_markup=reply_keyboard())

@bot.message_handler(commands=["settings"])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Please /start first.")
        return
    gender = u["gender"] or "Not set"
    ref_code = u["referral_code"] if u["referral_code"] else f"REF{uid}"
    ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
    prem_hours = db_get_premium_hours_remaining(uid)
    prem_text = f"{prem_hours:.2f}h remaining" if prem_hours > 0 else "No active premium"
    text = f"⚙️ Settings:\nGender: {gender}\nReferral link: {ref_link}\nReferrals: {u['referral_count']}\nPremium: {prem_text}"
    # show inline buttons to change gender
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Set Male ♂️", callback_data="setgender:Male"),
               InlineKeyboardButton("Set Female ♀️", callback_data="setgender:Female"))
    bot.send_message(uid, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("setgender:"))
def callback_setgender(call):
    uid = call.from_user.id
    if db_is_banned(uid):
        try:
            call.answer("You are banned.", show_alert=True)
        except:
            pass
        return
    _, gender = call.data.split(":", 1)
    gender = gender.capitalize()
    db_set_gender(uid, gender)
    try:
        call.answer(f"✅ Gender set to {gender}", show_alert=False)
        call.edit_message_text(f"✅ Gender set to {gender}")
    except Exception:
        pass

@bot.message_handler(commands=["refer"])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    code = u["referral_code"]
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(uid, f"Share this with friends. For every 2 successful referrals you get 1 hour premium.\nLink:\n{link}")

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    if not u:
        bot.send_message(uid, "Use /start first.")
        return
    prem = db_get_premium_hours_remaining(uid)
    prem_text = f"{prem:.2f}h remaining" if prem > 0 else "No active premium"
    bot.send_message(uid, f"📊 Stats:\nGender: {u['gender']}\nChats completed: {u['chats_completed']}\nMessages sent: {u['messages_sent']}\nReferrals: {u['referral_count']}\nPremium: {prem_text}")

# ---------- SEARCH HANDLERS ----------
def try_match_for_user(requester_id, desired_gender=None):
    """
    Try to find a partner for requester_id whose gender matches desired_gender.
    If desired_gender is None -> random match from waiting_random.
    Matching strategy:
      - If desired_gender specified: look in waiting_random for user with that gender first,
        then look in waiting lists where users are waiting (male_desire/female_desire) but match only if their own gender matches desired_gender.
      - If not found, return None.
    """
    # search waiting_random for someone whose gender matches desired_gender
    if desired_gender is not None:
        # first try waiting_random
        for candidate in list(waiting_random):
            if candidate == requester_id:
                continue
            cu = db_get_user(candidate)
            if cu and cu["gender"] and cu["gender"].lower() == desired_gender.lower():
                waiting_random.remove(candidate)
                return candidate
        # then try waiting_male_desire and waiting_female_desire
        all_queues = waiting_male_desire + waiting_female_desire
        for candidate in list(all_queues):
            if candidate == requester_id:
                continue
            cu = db_get_user(candidate)
            if cu and cu["gender"] and cu["gender"].lower() == desired_gender.lower():
                # remove candidate from whichever queue they're in
                if candidate in waiting_male_desire:
                    waiting_male_desire.remove(candidate)
                if candidate in waiting_female_desire:
                    waiting_female_desire.remove(candidate)
                return candidate
        return None
    else:
        # random: pair from waiting_random with any candidate
        for candidate in list(waiting_random):
            if candidate != requester_id:
                waiting_random.remove(candidate)
                return candidate
        # if none in random, try any waiting_male_desire or waiting_female_desire
        for candidate in list(waiting_male_desire + waiting_female_desire):
            if candidate != requester_id:
                if candidate in waiting_male_desire:
                    waiting_male_desire.remove(candidate)
                if candidate in waiting_female_desire:
                    waiting_female_desire.remove(candidate)
                return candidate
        return None

@bot.message_handler(commands=["search_random"])
def cmd_search_random(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(message.from_user)
    if uid in active_pairs:
        bot.send_message(uid, "❗ You are already in a chat. Use /stop to end it.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    # try to find match
    partner = try_match_for_user(uid, desired_gender=None)
    if partner:
        # create active pair
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        bot.send_message(uid, f"✅ Partner found! Start chatting. Use /stop to end.")
        bot.send_message(partner, f"✅ Partner found! Start chatting. Use /stop to end.")
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
        bot.send_message(uid, "❗ You are already in a chat. Use /stop to end it.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    # premium required
    if not db_is_premium(uid):
        code, rc = db_get_referral_info(uid)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.send_message(uid, f"🔒 /search_male is premium. Share this link with 2 people to get 1 hour premium:\n{link}")
        return
    # try match for male
    partner = try_match_for_user(uid, desired_gender="Male")
    if partner:
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        bot.send_message(uid, "✅ Male partner found! Start chatting. Use /stop to end.")
        bot.send_message(partner, "✅ Partner found! Start chatting. Use /stop to end.")
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
        bot.send_message(uid, "❗ You are already in a chat. Use /stop to end it.")
        return
    if user_is_searching(uid):
        bot.send_message(uid, "⏳ Already searching. Use /stop to cancel.")
        return
    # premium required
    if not db_is_premium(uid):
        code, rc = db_get_referral_info(uid)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.send_message(uid, f"🔒 /search_female is premium. Share this link with 2 people to get 1 hour premium:\n{link}")
        return
    # try match for female
    partner = try_match_for_user(uid, desired_gender="Female")
    if partner:
        active_pairs[uid] = partner
        active_pairs[partner] = uid
        bot.send_message(uid, "✅ Female partner found! Start chatting. Use /stop to end.")
        bot.send_message(partner, "✅ Partner found! Start chatting. Use /stop to end.")
    else:
        waiting_female_desire.append(uid)
        bot.send_message(uid, "🔎 Searching for a female partner... Please wait.", reply_markup=reply_keyboard())

@bot.message_handler(commands=["stop"])
def cmd_stop(message):
    uid = message.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    # if searching, remove
    if uid in waiting_random or uid in waiting_male_desire or uid in waiting_female_desire:
        remove_from_all_waitlists(uid)
        bot.send_message(uid, "⏹ Search stopped.", reply_markup=reply_keyboard())
        return
    # if in active pair, end it
    if uid in active_pairs:
        partner = active_pairs.get(uid)
        end_pair(uid, notify=True)
        bot.send_message(uid, "🛑 You ended the chat.", reply_markup=reply_keyboard())
        return
    bot.send_message(uid, "ℹ️ You are not currently searching or in a chat.", reply_markup=reply_keyboard())

# ---------- MEDIA & MESSAGES ----------

@bot.message_handler(func=lambda m: m.content_type == "text")
def handler_text(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    db_create_user_if_missing(m.from_user)
    if uid in active_pairs:
        partner = active_pairs[uid]
        try:
            bot.send_message(partner, m.text)
            db_increment_stat_messages(uid)
        except Exception:
            # if delivery fails, end pair
            end_pair(uid, notify=False)
            bot.send_message(uid, "❗ Failed to send message to partner. Chat ended.")
    else:
        # convenience: if user types '/', show keyboard
        if m.text.strip().startswith("/"):
            bot.send_message(uid, "Use keyboard for quick commands.", reply_markup=reply_keyboard())
        else:
            bot.send_message(uid, "Use /search_random (or premium search) to find someone to chat with.", reply_markup=reply_keyboard())

def send_pending_prompt(to_user):
    pending = db_get_pending_media_for_user(to_user)
    if not pending:
        return
    mid = pending["id"]
    mt = pending["media_type"]
    from_user = pending["from_user"]
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("Accept ✅", callback_data=f"media_accept:{mid}"),
           InlineKeyboardButton("Reject ❌", callback_data=f"media_reject:{mid}"))
    bot.send_message(to_user, f"📬 Your partner wants to send a {mt}. Accept to view?", reply_markup=kb)

@bot.message_handler(content_types=["photo"])
def handler_photo(m):
    uid = m.from_user.id
    if db_is_banned(uid):
        bot.send_message(uid, "🚫 You are banned.")
        return
    if uid not in active_pairs:
        bot.send_message(uid, "You are not in a chat. Use /search to find someone.")
        return
    partner = active_pairs[uid]
    # check if partner already has pending
    pending = db_get_pending_media_for_user(partner)
    if pending:
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
        bot.send_message(uid, "You are not in a chat. Use /search to find someone.")
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
        bot.send_message(uid, "You are not in a chat. Use /search to find someone.")
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
        bot.send_message(uid, "You are not in a chat. Use /search to find someone.")
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
    data = call.data
    uid = call.from_user.id
    try:
        action, pid_str = data.split(":", 1)
        pid = int(pid_str)
    except Exception:
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
        # deliver media to recipient (which is call.from_user)
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
        except Exception as e:
            logger.exception("Error delivering media")
            bot.send_message(from_user, "❗ Failed to deliver content.")
            call.edit_message_text("❗ Failed to deliver content.")
    else:
        # reject
        bot.send_message(from_user, "❌ Your partner rejected the content.")
        call.edit_message_text("❌ Content rejected.")
    # delete pending
    db_delete_pending_media(pid)

# ----------------- ADMIN: ban / unban -----------------
@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    # admin only
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ No permission.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /ban <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.reply_to(message, "Invalid user id.")
        return
    db_ban_user(target)
    # remove from waitlists and active pairs
    remove_from_all_waitlists(target)
    if target in active_pairs:
        end_pair(target, notify=True)
    bot.reply_to(message, f"🚫 User {target} banned permanently.")

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

# -------------------- STARTUP --------------------
if __name__ == "__main__":
    init_db()
    logger.info("GhostTalk bot starting...")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception:
        logger.exception("Unexpected error - bot crashed.")
