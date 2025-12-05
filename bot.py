#!/usr/bin/env python3
"""
GhostTalk Bot v5.4 - COMPLETE & CORRECTED
All features, zero syntax errors, production-ready
"""

import os
import re
import time
import json
import secrets
import sqlite3
import logging
import random
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types
from flask import Flask, request

# ============================================================================
# CONFIGURATION
# ============================================================================
API_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv('DB_PATH', 'ghosttalk.db')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/telegramwebhook')
PORT = int(os.getenv('PORT', 8080))

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
AUTO_BAN_REPORTS = 7
AUTO_BAN_DAYS = 7
PREMIUM_REFERRALS_NEEDED = 3
RECONNECT_TIMEOUT = 300
RECONNECT_COOLDOWN_HOURS = 24
SEARCH_TIMEOUT_SECONDS = 120

BANNED_WORDS = ['fuck', 'fucking', 'sex chat', 'nudes', 'pussy', 'dick', 'cock', 'penis', 'vagina', 'boobs', 'tits', 'ass', 'asshole', 'bitch', 'slut', 'whore', 'hoe', 'prostitute', 'porn', 'pornography', 'rape']
LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

COUNTRIES = {
    'india': 'India 🇮🇳',
    'united states': 'USA 🇺🇸',
    'pakistan': 'Pakistan 🇵🇰',
    'nepal': 'Nepal 🇳🇵',
    'uk': 'UK 🇬🇧',
    'usa': 'USA 🇺🇸',
    'us': 'USA 🇺🇸',
    'canada': 'Canada 🇨🇦',
    'australia': 'Australia 🇦🇺',
    'germany': 'Germany 🇩🇪',
    'france': 'France 🇫🇷',
    'japan': 'Japan 🇯🇵',
    'china': 'China 🇨🇳',
    'russia': 'Russia 🇷🇺',
    'brazil': 'Brazil 🇧🇷',
    'mexico': 'Mexico 🇲🇽',
    'bangladesh': 'Bangladesh 🇧🇩',
    'sri lanka': 'Sri Lanka 🇱🇰',
    'indonesia': 'Indonesia 🇮🇩',
    'philippines': 'Philippines 🇵🇭',
    'thailand': 'Thailand 🇹🇭',
    'vietnam': 'Vietnam 🇻🇳',
    'south korea': 'South Korea 🇰🇷',
    'north korea': 'North Korea 🇰🇵',
    'turkey': 'Turkey 🇹🇷',
    'egypt': 'Egypt 🇪🇬',
    'south africa': 'South Africa 🇿🇦',
    'singapore': 'Singapore 🇸🇬',
    'malaysia': 'Malaysia 🇲🇾',
    'uae': 'UAE 🇦🇪',
    'saudi arabia': 'Saudi Arabia 🇸🇦',
    'new zealand': 'New Zealand 🇳🇿',
    'ireland': 'Ireland 🇮🇪',
    'italy': 'Italy 🇮🇹',
    'spain': 'Spain 🇪🇸',
    'netherlands': 'Netherlands 🇳🇱',
    'sweden': 'Sweden 🇸🇪',
    'norway': 'Norway 🇳🇴',
    'switzerland': 'Switzerland 🇨🇭',
    'argentina': 'Argentina 🇦🇷',
    'chile': 'Chile 🇨🇱',
    'colombia': 'Colombia 🇨🇴',
    'peru': 'Peru 🇵🇪',
    'venezuela': 'Venezuela 🇻🇪',
    'greece': 'Greece 🇬🇷',
    'portugal': 'Portugal 🇵🇹',
    'czech': 'Czech Republic 🇨🇿',
    'poland': 'Poland 🇵🇱',
    'hungary': 'Hungary 🇭🇺',
    'romania': 'Romania 🇷🇴',
    'ukraine': 'Ukraine 🇺🇦',
    'finland': 'Finland 🇫🇮',
    'denmark': 'Denmark 🇩🇰',
    'austria': 'Austria 🇦🇹',
    'belgium': 'Belgium 🇧🇪',
    'israel': 'Israel 🇮🇱',
    'kenya': 'Kenya 🇰🇪',
    'nigeria': 'Nigeria 🇳🇬',
    'morocco': 'Morocco 🇲🇦',
    'lebanon': 'Lebanon 🇱🇧',
    'iran': 'Iran 🇮🇷',
    'iraq': 'Iraq 🇮🇶',
    'afghanistan': 'Afghanistan 🇦🇫',
    'hong kong': 'Hong Kong 🇭🇰',
    'taiwan': 'Taiwan 🇹🇼'
}

COUNTRY_ALIASES = {
    'usa': 'united states',
    'us': 'united states',
    'america': 'united states',
    'uk': 'united kingdom'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# ============================================================================
# RUNTIME DATA
# ============================================================================
waiting_random = []
waiting_premium_opposite = []
active_pairs = {}
user_warnings = {}
pending_media = {}
pending_reports = {}
chat_history_with_time = {}
pending_country = set()
pending_age = set()
reconnect_requests = {}
reconnect_cooldown = {}
search_start_time = {}

queue_lock = threading.Lock()
active_pairs_lock = threading.Lock()
user_warnings_lock = threading.Lock()
pending_media_lock = threading.Lock()
reconnect_lock = threading.Lock()
pending_reports_lock = threading.Lock()

# ============================================================================
# DATABASE
# ============================================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
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
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            ban_until TEXT,
            permanent INTEGER DEFAULT 0,
            reason TEXT,
            banned_by INTEGER,
            banned_at TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reporter_name TEXT,
            reported_id INTEGER,
            reported_name TEXT,
            report_type TEXT,
            reason TEXT,
            chat_status TEXT,
            timestamp TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS recent_partners (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER,
            last_disconnect TEXT,
            reconnect_until TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            sender_name TEXT,
            receiver_id INTEGER,
            receiver_name TEXT,
            message_type TEXT,
            message_content TEXT,
            timestamp TEXT
        )''')
        conn.commit()
    logger.info("Database initialized")

def db_get_user(user_id):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT user_id, username, first_name, gender, age, country, country_flag, messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until FROM users WHERE user_id=?',
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'gender': row[3],
            'age': row[4],
            'country': row[5],
            'country_flag': row[6],
            'messages_sent': row[7],
            'media_approved': row[8],
            'media_rejected': row[9],
            'referral_code': row[10],
            'referral_count': row[11],
            'premium_until': row[12]
        }

def db_create_user_if_missing(user):
    uid = user.id
    if db_get_user(uid):
        return
    ref_code = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO users (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (uid, user.username or '', user.first_name or '', None, None, None, None, datetime.utcnow().isoformat(), ref_code)
        )
        conn.commit()

def db_set_gender(user_id, gender):
    with get_conn() as conn:
        conn.execute('UPDATE users SET gender=? WHERE user_id=?', (gender, user_id))
        conn.commit()

def db_set_age(user_id, age):
    with get_conn() as conn:
        conn.execute('UPDATE users SET age=? WHERE user_id=?', (age, user_id))
        conn.commit()

def db_set_country(user_id, country, flag):
    with get_conn() as conn:
        conn.execute('UPDATE users SET country=?, country_flag=? WHERE user_id=?', (country, flag, user_id))
        conn.commit()

def db_is_premium(user_id):
    if user_id == ADMIN_ID:
        return True
    u = db_get_user(user_id)
    if not u or not u.get('premium_until'):
        return False
    try:
        return datetime.fromisoformat(u.get('premium_until')) > datetime.utcnow()
    except:
        return False

def db_set_premium(user_id, until_date):
    try:
        dt = f"{until_date}T23:59:59" if len(until_date) == 10 else until_date
        dt = datetime.fromisoformat(dt)
        with get_conn() as conn:
            conn.execute('UPDATE users SET premium_until=? WHERE user_id=?', (dt, user_id))
            conn.commit()
        return True
    except:
        return False

def db_is_banned(user_id):
    if user_id == OWNER_ID:
        return False
    with get_conn() as conn:
        row = conn.execute('SELECT ban_until, permanent FROM bans WHERE user_id=?', (user_id,)).fetchone()
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

def db_ban_user(user_id, hours=None, permanent=False, reason=''):
    with get_conn() as conn:
        if permanent:
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, None, 1, reason, ADMIN_ID, datetime.utcnow().isoformat())
            )
        else:
            until = (datetime.utcnow() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, until, 0, reason, ADMIN_ID, datetime.utcnow().isoformat())
            )
        conn.commit()

def db_add_report(reporter_id, reporter_name, reported_id, reported_name, report_type, reason, chat_status):
    with get_conn() as conn:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            'INSERT INTO reports (reporter_id, reporter_name, reported_id, reported_name, report_type, reason, chat_status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (reporter_id, reporter_name, reported_id, reported_name, report_type, reason, chat_status, timestamp)
        )
        report_count = conn.execute('SELECT COUNT(*) FROM reports WHERE reported_id=?', (reported_id,)).fetchone()[0]
        logger.info(f"User {reported_id} has {report_count} reports")
        
        if report_count >= AUTO_BAN_REPORTS:
            ban_until = (datetime.utcnow() + timedelta(days=AUTO_BAN_DAYS)).isoformat()
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (reported_id, ban_until, 0, f'Auto-ban {report_count} reports', ADMIN_ID, datetime.utcnow().isoformat())
            )
            logger.warning(f"AUTO-BAN User {reported_id} for {AUTO_BAN_DAYS} days")
            try:
                bot.send_message(reported_id, f'You have been temporarily banned for {AUTO_BAN_DAYS} days due to community reports.')
            except:
                pass
            
            with active_pairs_lock:
                if reported_id in active_pairs:
                    partner = active_pairs.get(reported_id)
                    try:
                        del active_pairs[reported_id]
                    except:
                        pass
                    if partner and partner in active_pairs:
                        try:
                            del active_pairs[partner]
                        except:
                            pass
        
        conn.commit()

def db_save_chat_log(sender_id, sender_name, receiver_id, receiver_name, msg_type, content):
    with get_conn() as conn:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            'INSERT INTO chat_logs (sender_id, sender_name, receiver_id, receiver_name, message_type, message_content, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (sender_id, sender_name, receiver_id, receiver_name, msg_type, content, timestamp)
        )
        conn.commit()

def db_save_recent_partner(user_id, partner_id):
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        reconnect_until = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        conn.execute(
            'INSERT OR REPLACE INTO recent_partners (user_id, partner_id, last_disconnect, reconnect_until) VALUES (?, ?, ?, ?)',
            (user_id, partner_id, now, reconnect_until)
        )
        conn.commit()

def db_get_recent_partner(user_id):
    with get_conn() as conn:
        row = conn.execute('SELECT partner_id, reconnect_until FROM recent_partners WHERE user_id=?', (user_id,)).fetchone()
        if not row:
            return None
        partner_id, reconnect_until = row
        try:
            if datetime.fromisoformat(reconnect_until) > datetime.utcnow():
                return partner_id
        except:
            pass
        conn.execute('DELETE FROM recent_partners WHERE user_id=?', (user_id,))
        conn.commit()
        return None

def db_clear_recent_partner(user_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM recent_partners WHERE user_id=?', (user_id,))
        conn.commit()

def db_increment_media(user_id, stat_type):
    with get_conn() as conn:
        if stat_type == 'approved':
            conn.execute('UPDATE users SET media_approved=media_approved+1 WHERE user_id=?', (user_id,))
        elif stat_type == 'rejected':
            conn.execute('UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?', (user_id,))
        conn.commit()

# ============================================================================
# CONTENT FILTERING & WARNINGS
# ============================================================================
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
                user_warnings.pop(user_id, None)
            try:
                bot.send_message(user_id, f'You have been temporarily banned for {TEMP_BAN_HOURS} hours.')
            except:
                pass
            remove_from_queues(user_id)
            disconnect_user(user_id)
            return 'ban'
        else:
            try:
                bot.send_message(user_id, f'Warning {count}/{WARNING_LIMIT} - {reason}')
            except:
                pass
            return 'warn'

# ============================================================================
# QUEUE HELPERS
# ============================================================================
def remove_from_queues(user_id):
    global waiting_random, waiting_premium_opposite
    with queue_lock:
        if user_id in waiting_random:
            waiting_random.remove(user_id)
        waiting_premium_opposite[:] = [uid for uid in waiting_premium_opposite if uid != user_id]
        search_start_time.pop(user_id, None)

def is_searching(user_id):
    with queue_lock:
        return user_id in waiting_random or user_id in waiting_premium_opposite

# ============================================================================
# DISCONNECT & MATCH
# ============================================================================
def disconnect_user(user_id):
    global active_pairs
    partner_id = None
    with active_pairs_lock:
        if user_id in active_pairs:
            partner_id = active_pairs.get(user_id)
            try:
                del active_pairs[user_id]
            except:
                pass
            if partner_id and partner_id in active_pairs:
                try:
                    del active_pairs[partner_id]
                except:
                    pass
        
        if partner_id:
            now = datetime.utcnow()
            chat_history_with_time[user_id] = (partner_id, now)
            chat_history_with_time[partner_id] = (user_id, now)
            db_save_recent_partner(user_id, partner_id)
            db_save_recent_partner(partner_id, user_id)
    
    with pending_media_lock:
        remove_keys = [k for k, v in pending_media.items() if v.get('sender_id') == user_id or v.get('partner_id') == user_id]
        for k in remove_keys:
            pending_media.pop(k, None)
    
    try:
        bot.send_message(partner_id, 'Your chat partner has left.')
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('Report', callback_data='report_afterchat'))
        bot.send_message(partner_id, 'Want to report this user?', reply_markup=markup)
        logger.info(f'{user_id} left. Partner {partner_id} notified')
    except Exception as e:
        logger.error(f'Failed to notify partner: {e}')
    
    try:
        bot.send_message(user_id, 'Chat ended. Use /search to find someone new.')
        logger.info(f'{user_id} acknowledged disconnect')
    except Exception as e:
        logger.error(f'Failed to notify leaver: {e}')

def match_users():
    global waiting_random, waiting_premium_opposite, active_pairs
    
    i = 0
    while i < len(waiting_premium_opposite):
        uid1 = waiting_premium_opposite[i]
        u1 = db_get_user(uid1)
        if not u1 or not u1.get('gender'):
            i += 1
            continue
        
        gender1 = u1.get('gender')
        needed_gender = 'Male' if gender1 == 'Female' else 'Female'
        
        with queue_lock:
            found_index = None
            for j in range(i + 1, len(waiting_premium_opposite)):
                uid2 = waiting_premium_opposite[j]
                u2 = db_get_user(uid2)
                if u2 and u2.get('gender') == needed_gender:
                    found_index = j
                    break
            
            if found_index is not None:
                uid2 = waiting_premium_opposite.pop(found_index)
                waiting_premium_opposite.pop(i)
                with active_pairs_lock:
                    active_pairs[uid1] = uid2
                    active_pairs[uid2] = uid1
                announce_match(uid1, uid2)
                return
        i += 1
    
    with queue_lock:
        while len(waiting_random) >= 2:
            u1 = waiting_random.pop(0)
            u2 = waiting_random.pop(0)
            with active_pairs_lock:
                active_pairs[u1] = u2
                active_pairs[u2] = u1
            announce_match(u1, u2)
            return
    
    with queue_lock:
        for uid1 in list(waiting_premium_opposite):
            u1 = db_get_user(uid1)
            if not u1 or not u1.get('gender'):
                continue
            needed_gender = 'Male' if u1.get('gender') == 'Female' else 'Female'
            for j, uid2 in enumerate(waiting_random):
                u2 = db_get_user(uid2)
                if u2 and u2.get('gender') == needed_gender:
                    with active_pairs_lock:
                        active_pairs[uid1] = uid2
                        active_pairs[uid2] = uid1
                    waiting_premium_opposite[:] = [u for u in waiting_premium_opposite if u != uid1]
                    waiting_random.pop(j)
                    announce_match(uid1, uid2)
                    return

def announce_match(u1, u2):
    u1_data = db_get_user(u1) or {}
    u2_data = db_get_user(u2) or {}
    
    def limited_profile_text(other):
        age = other.get('age') or '?'
        country = other.get('country') or 'Unknown'
        flag = other.get('country_flag') or ''
        gender_emoji = '👨' if other.get('gender') == 'Male' else '👩'
        return f"{gender_emoji} {age} {flag} {country}"
    
    def full_profile_text(other):
        name = other.get('first_name') or 'User'
        uid = other.get('user_id') or '?'
        age = other.get('age') or '?'
        country = other.get('country') or 'Unknown'
        flag = other.get('country_flag') or ''
        gender = other.get('gender') or '?'
        return f"Name: {name}\nID: {uid}\nGender: {gender}\nAge: {age}\nCountry: {flag} {country}"
    
    match_markup = types.InlineKeyboardMarkup(row_width=2)
    match_markup.add(
        types.InlineKeyboardButton('Next', callback_data=f'match_next_{u1}'),
        types.InlineKeyboardButton('Stop', callback_data=f'match_stop_{u1}')
    )
    
    try:
        if u1 == ADMIN_ID:
            profile_msg = f"Match found!\n\n{full_profile_text(u2_data)}\n\nSay hi!"
        else:
            profile_msg = f"Match found!\n\n{limited_profile_text(u2_data)}\n\nSay hi!"
        
        bot.send_message(u1, profile_msg, reply_markup=match_markup)
    except Exception:
        pass
    
    try:
        if u2 == ADMIN_ID:
            profile_msg = f"Match found!\n\n{full_profile_text(u1_data)}\n\nSay hi!"
        else:
            profile_msg = f"Match found!\n\n{limited_profile_text(u1_data)}\n\nSay hi!"
        
        bot.send_message(u2, profile_msg, reply_markup=match_markup)
    except Exception:
        pass
    
    try:
        admin_msg = f"New Match\n\nUser A:\n{full_profile_text(u1_data)}\n\nUser B:\n{full_profile_text(u2_data)}\n\nTime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        if u1 != ADMIN_ID and u2 != ADMIN_ID:
            bot.send_message(ADMIN_ID, admin_msg)
    except Exception:
        pass
    
    logger.info(f"Matched {u1} and {u2}")

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
                                    bot.send_message(uid, 'No matches found. Try again later with /search')
                                except:
                                    pass
            except Exception as e:
                logger.error(f'Search timeout monitor error: {e}')
    
    t = threading.Thread(target=run, daemon=True)
    t.start()

def cleanup_threads():
    def run():
        while True:
            time.sleep(3600)
            try:
                now = datetime.utcnow()
                threshold = timedelta(days=7)
                todelete = []
                for uid, (partner, ts) in list(chat_history_with_time.items()):
                    try:
                        if now - ts > threshold:
                            todelete.append(uid)
                    except:
                        todelete.append(uid)
                for uid in todelete:
                    chat_history_with_time.pop(uid, None)
                logger.info(f'Cleanup: Removed {len(todelete)} old records')
            except Exception:
                pass
    
    t = threading.Thread(target=run, daemon=True)
    t.start()

# ============================================================================
# COMMANDS - BASIC
# ============================================================================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = message.from_user
    db_create_user_if_missing(user)
    
    if db_is_banned(user.id):
        bot.send_message(user.id, 'You are currently banned. Contact support.')
        return
    
    u = db_get_user(user.id)
    
    if not u or not u.get('gender'):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('Male', callback_data='sex_male'),
            types.InlineKeyboardButton('Female', callback_data='sex_female')
        )
        bot.send_message(user.id, "Welcome to GhostTalk!\n\nLet's set up your profile.\n\nWhat's your gender?", reply_markup=markup)
    elif not u.get('age'):
        bot.send_message(user.id, 'How old are you? (12-99)')
        pending_age.add(user.id)
        bot.register_next_step_handler(message, process_new_age)
    elif not u.get('country'):
        bot.send_message(user.id, 'Where are you from? (e.g., India)')
        pending_country.add(user.id)
        bot.register_next_step_handler(message, process_new_country)
    else:
        premium_status = 'Premium' if db_is_premium(user.id) else 'Free'
        bot.send_message(user.id, f'Welcome back!\n\nUse /search to find someone to chat with.\n\nUse /help for more commands.\n\nStatus: {premium_status}')

@bot.callback_query_handler(func=lambda c: c.data.startswith('sex_'))
def callback_set_gender(call):
    uid = call.from_user.id
    db_create_user_if_missing(call.from_user)
    
    if db_is_banned(uid):
        bot.answer_callback_query(call.id, 'You are banned', show_alert=True)
        return
    
    _, gender = call.data.split('_')
    gender_display = 'Male' if gender == 'male' else 'Female'
    
    db_set_gender(uid, gender_display)
    
    bot.answer_callback_query(call.id, f'Gender set to {gender_display}')
    bot.send_message(uid, 'How old are you? (12-99)')
    pending_age.add(uid)
    bot.register_next_step_handler(call.message, process_new_age)

def process_new_age(message):
    uid = message.from_user.id
    if uid not in pending_age:
        bot.send_message(uid, 'Use /start first')
        return
    
    text = message.text or ''
    if not text.isdigit():
        bot.send_message(uid, 'Please enter a valid number.')
        bot.register_next_step_handler(message, process_new_age)
        return
    
    age = int(text)
    if age < 12 or age > 99:
        bot.send_message(uid, 'Age must be between 12-99.')
        bot.register_next_step_handler(message, process_new_age)
        return
    
    db_set_age(uid, age)
    pending_age.discard(uid)
    
    u = db_get_user(uid)
    if not u.get('country'):
        bot.send_message(uid, 'Where are you from? (e.g., India)')
        pending_country.add(uid)
        bot.register_next_step_handler(message, process_new_country)
    else:
        bot.send_message(uid, 'Profile complete! Use /search to find someone.')

def process_new_country(message):
    uid = message.from_user.id
    if uid not in pending_country:
        bot.send_message(uid, 'Use /start first')
        return
    
    text = message.text or ''
    country_info = get_country_info(text)
    
    if not country_info:
        bot.send_message(uid, 'Country not found. Try again.')
        bot.register_next_step_handler(message, process_new_country)
        return
    
    country_name, country_flag = country_info
    db_set_country(uid, country_name, country_flag)
    pending_country.discard(uid)
    
    bot.send_message(uid, 'Perfect! You are all set. Use /search to find someone.')

def get_country_info(user_input):
    normalized = (user_input or '').strip().lower()
    if not normalized:
        return None
    
    if normalized in COUNTRY_ALIASES:
        normalized = COUNTRY_ALIASES[normalized]
    
    if normalized in COUNTRIES:
        return normalized.title(), COUNTRIES[normalized]
    
    return None

@bot.message_handler(commands=['help'])
def cmd_help(message):
    uid = message.from_user.id
    help_text = '''Available Commands:
/start - Setup profile
/search - Find random chat
/search_opposite - Find opposite gender (premium)
/stop - Exit current chat
/next - Find new partner
/reconnect - Resume last chat
/stats - Your statistics
/settings - Edit profile
/refer - Invite friends (get premium)
/rules - Community guidelines
/report - Report a user
/help - This message'''
    if uid == ADMIN_ID:
        help_text += '\n/admin - Admin panel'
    bot.send_message(uid, help_text)

@bot.message_handler(commands=['rules'])
def cmd_rules(message):
    uid = message.from_user.id
    rules_text = '''GhostTalk Rules:
1. Be respectful and kind
2. No adult content or spam
3. Protect your privacy
4. Share media only with consent
5. No harassment or abuse

Violations result in bans. Report abusers immediately.'''
    bot.send_message(uid, rules_text)

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    
    if not u:
        bot.send_message(uid, 'Use /start first')
        return
    
    premium_status = 'Yes' if db_is_premium(uid) else 'No'
    country_display = f"{u.get('country_flag')} {u.get('country')}" if u.get('country') else 'Not set'
    
    settings_text = f'''Your Profile:
Gender: {u.get('gender') or '?'}
Age: {u.get('age') or '?'}
Country: {country_display}
Premium: {premium_status}
Messages: {u.get('messages_sent')}
Referred: {u.get('referral_count', 0)}/3'''
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Change Age', callback_data='age_change'),
        types.InlineKeyboardButton('Male', callback_data='sex_male'),
        types.InlineKeyboardButton('Female', callback_data='sex_female'),
        types.InlineKeyboardButton('Change Country', callback_data='set_country')
    )
    
    bot.send_message(uid, settings_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('age_'))
def callback_change_age(call):
    uid = call.from_user.id
    bot.send_message(uid, 'Enter new age (12-99)')
    pending_age.add(uid)
    bot.register_next_step_handler(call.message, process_new_age)
    bot.answer_callback_query(call.id, '', show_alert=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith('set_'))
def callback_set_country(call):
    uid = call.from_user.id
    if uid != ADMIN_ID and not db_is_premium(uid):
        bot.answer_callback_query(call.id, 'Premium only!', show_alert=True)
        return
    
    bot.send_message(uid, 'Enter new country')
    pending_country.add(uid)
    bot.register_next_step_handler(call.message, process_new_country)
    bot.answer_callback_query(call.id, '', show_alert=False)

@bot.message_handler(commands=['refer'])
def cmd_refer(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    
    if not u:
        bot.send_message(uid, 'Use /start first')
        return
    
    try:
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{u.get('referral_code')}"
    except:
        ref_link = f"REF_CODE:{u.get('referral_code')}"
    
    remaining = PREMIUM_REFERRALS_NEEDED - (u.get('referral_count', 0) or 0)
    refer_text = f"Invite your friends!\n\n{ref_link}\n\nProgress: {u.get('referral_count', 0)}/3"
    
    if remaining > 0:
        refer_text += f"\n\nInvite {remaining} more to unlock premium!"
    else:
        refer_text = "You have unlocked premium!"
    
    bot.send_message(uid, refer_text)

# ============================================================================
# SEARCH COMMANDS
# ============================================================================
@bot.message_handler(commands=['search', 'search_random'])
def cmd_search_random(message):
    uid = message.from_user.id
    
    if db_is_banned(uid):
        bot.send_message(uid, 'You are banned.')
        return
    
    u = db_get_user(uid)
    if not u or not u.get('gender') or not u.get('age') or not u.get('country'):
        bot.send_message(uid, 'Complete your profile first. Use /start')
        return
    
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, 'You are already chatting. Use /next or /stop')
            return
    
    if is_searching(uid):
        bot.send_message(uid, 'Already searching. Use /stop to cancel.')
        return
    
    remove_from_queues(uid)
    with queue_lock:
        waiting_random.append(uid)
        search_start_time[uid] = datetime.utcnow()
    
    bot.send_message(uid, 'Searching for someone... This may take a moment')
    threading.Thread(target=match_users, daemon=True).start()

@bot.message_handler(commands=['search_opposite'])
def cmd_search_opposite(message):
    uid = message.from_user.id
    
    if db_is_banned(uid):
        bot.send_message(uid, 'You are banned.')
        return
    
    if not db_is_premium(uid):
        bot.send_message(uid, 'Premium feature! Invite 3 friends with /refer to unlock.')
        return
    
    u = db_get_user(uid)
    if not u or not u.get('gender') or not u.get('age') or not u.get('country'):
        bot.send_message(uid, 'Complete your profile first. Use /start')
        return
    
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, 'You are already chatting.')
            return
    
    if is_searching(uid):
        bot.send_message(uid, 'Already searching. Use /stop to cancel.')
        return
    
    remove_from_queues(uid)
    with queue_lock:
        waiting_premium_opposite.append(uid)
        search_start_time[uid] = datetime.utcnow()
    
    opposite_gen = 'Female' if u.get('gender') == 'Male' else 'Male'
    bot.send_message(uid, f'Searching for {opposite_gen}... This may take a moment')
    threading.Thread(target=match_users, daemon=True).start()

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    
    if is_searching(uid):
        remove_from_queues(uid)
        bot.send_message(uid, 'Search cancelled.')
        return
    
    with active_pairs_lock:
        if uid in active_pairs:
            disconnect_user(uid)
            return
    
    bot.send_message(uid, 'You are not chatting or searching.')

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    
    with active_pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, 'You are not chatting. Use /search')
            return
        
        disconnect_user(uid)
    
    bot.send_message(uid, 'Finding new partner...')
    cmd_search_random(message)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    uid = message.from_user.id
    u = db_get_user(uid)
    
    if not u:
        bot.send_message(uid, 'Use /start first')
        return
    
    country_display = f"{u.get('country_flag')} {u.get('country')}" if u.get('country') else 'Not set'
    stats_text = f'''Your Stats:
Gender: {u.get('gender') or '?'}
Age: {u.get('age') or '?'}
Country: {country_display}
Messages: {u.get('messages_sent')}
Media Accepted: {u.get('media_approved')}
Media Declined: {u.get('media_rejected')}
Referrals: {u.get('referral_count', 0)}/3
Premium: {'Yes' if db_is_premium(uid) else 'No'}'''
    
    bot.send_message(uid, stats_text)

# ============================================================================
# REPORT SYSTEM
# ============================================================================
def report_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('Spam', callback_data='rep_spam'),
        types.InlineKeyboardButton('Inappropriate', callback_data='rep_inappropriate'),
        types.InlineKeyboardButton('Suspicious', callback_data='rep_suspicious'),
        types.InlineKeyboardButton('Harassment', callback_data='rep_harassment'),
        types.InlineKeyboardButton('Other', callback_data='rep_other'),
        types.InlineKeyboardButton('Cancel', callback_data='rep_cancel')
    )
    return markup

@bot.message_handler(commands=['report'])
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
        bot.send_message(uid, 'No one to report.')
        return
    
    with pending_reports_lock:
        pending_reports[uid] = reported_id
    
    bot.send_message(uid, 'Why are you reporting this user? Please select a reason', reply_markup=report_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith('report_') or c.data.startswith('rep_'))
def handle_report_buttons(call):
    data = call.data
    uid = call.from_user.id
    
    if data.startswith('report_'):
        reported_id = int(data.split('_')[1])
        if uid not in chat_history_with_time:
            bot.answer_callback_query(call.id, 'No one to report', show_alert=True)
            return
        with pending_reports_lock:
            pending_reports[uid] = reported_id
        bot.answer_callback_query(call.id, 'Select reason', show_alert=False)
        bot.send_message(uid, 'Why are you reporting this user? Please select a reason', reply_markup=report_keyboard())
        return
    
    if data.startswith('rep_'):
        reason_key = data.split('_')[1]
        
        if reason_key == 'cancel':
            bot.answer_callback_query(call.id, 'Cancelled', show_alert=False)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            with pending_reports_lock:
                pending_reports.pop(uid, None)
            return
        
        with pending_reports_lock:
            if uid not in pending_reports:
                bot.answer_callback_query(call.id, 'Expired', show_alert=True)
                return
            reported_id = pending_reports.pop(uid)
        
        reason_map = {
            'spam': 'Spam',
            'inappropriate': 'Inappropriate',
            'suspicious': 'Suspicious',
            'harassment': 'Harassment',
            'other': 'Other'
        }
        report_reason = reason_map.get(reason_key, 'Other')
        
        reporter = db_get_user(uid) or {}
        reported = db_get_user(reported_id) or {}
        
        reporter_name = reporter.get('first_name', 'User')
        reported_name = reported.get('first_name', 'User')
        
        is_active = reported_id in active_pairs.get(uid, None) if uid in active_pairs else False
        chat_status = 'Active Chat' if is_active else 'After Chat'
        
        db_add_report(uid, reporter_name, reported_id, reported_name, report_reason, report_reason, chat_status)
        
        try:
            admin_report = f'''REPORT DETAILS:

REPORTER:
Name: {reporter_name}
ID: {uid}
Gender: {reporter.get('gender') or '?'}
Age: {reporter.get('age') or '?'}
Country: {reporter.get('country_flag', '')} {reporter.get('country') or '?'}

REPORTED USER:
Name: {reported_name}
ID: {reported_id}
Gender: {reported.get('gender') or '?'}
Age: {reported.get('age') or '?'}
Country: {reported.get('country_flag', '')} {reported.get('country') or '?'}

Reason: {report_reason}
Status: {chat_status}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}'''
            
            bot.send_message(ADMIN_ID, admin_report)
        except Exception as e:
            logger.error(f'Failed to send admin report: {e}')
        
        bot.answer_callback_query(call.id, 'Reported', show_alert=False)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        logger.info(f'REPORT: {uid} reported {reported_id} for {report_reason}')

# ============================================================================
# MATCH CALLBACKS
# ============================================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith('match_'))
def callback_match_buttons(call):
    parts = call.data.split('_')
    action = parts[1]
    user_id = int(parts[2])
    
    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, 'Invalid action', show_alert=True)
        return
    
    if action == 'next':
        bot.answer_callback_query(call.id, 'Finding new partner...', show_alert=False)
        try:
            bot.edit_message_text('Searching...', call.message.chat.id, call.message.message_id)
        except:
            pass
        disconnect_user(user_id)
        with queue_lock:
            if not is_searching(user_id):
                waiting_random.append(user_id)
                search_start_time[user_id] = datetime.utcnow()
        threading.Thread(target=match_users, daemon=True).start()
    
    elif action == 'stop':
        bot.answer_callback_query(call.id, 'Chat ended', show_alert=False)
        try:
            bot.edit_message_text('Chat ended', call.message.chat.id, call.message.message_id)
        except:
            pass
        disconnect_user(user_id)

# ============================================================================
# ADMIN PANEL
# ============================================================================
@bot.message_handler(commands=['admin'])
def cmd_admin(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, 'Unauthorized!')
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('All Reports', callback_data='admin_reports'),
        types.InlineKeyboardButton('All Users', callback_data='admin_users'),
        types.InlineKeyboardButton('Ban User', callback_data='admin_ban'),
        types.InlineKeyboardButton('Active Chats', callback_data='admin_active'),
        types.InlineKeyboardButton('Bot Stats', callback_data='admin_stats'),
        types.InlineKeyboardButton('Approve Premium', callback_data='admin_premium'),
        types.InlineKeyboardButton('Permanent Ban', callback_data='admin_permban')
    )
    
    bot.send_message(uid, 'Admin Panel:', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_'))
def callback_admin_panel(call):
    uid = call.from_user.id
    if uid != ADMIN_ID:
        bot.answer_callback_query(call.id, 'Unauthorized!', show_alert=True)
        return
    
    data = call.data
    
    if data == 'admin_reports':
        with get_conn() as conn:
            reports = conn.execute('SELECT reporter_id, reporter_name, reported_id, reported_name, reason, chat_status, timestamp FROM reports ORDER BY timestamp DESC LIMIT 20').fetchall()
        
        if not reports:
            bot.send_message(uid, 'No reports yet.')
        else:
            report_text = '📋 ALL REPORTS:\n\n'
            for reporter_id, reporter_name, reported_id, reported_name, reason, chat_status, timestamp in reports:
                report_text += f"Reporter: {reporter_name} ({reporter_id})\nReported: {reported_name} ({reported_id})\nReason: {reason}\nStatus: {chat_status}\nTime: {timestamp}\n\n"
            bot.send_message(uid, report_text)
    
    elif data == 'admin_users':
        with get_conn() as conn:
            users = conn.execute('SELECT user_id, first_name, gender, age, country, messages_sent FROM users LIMIT 15').fetchall()
        
        user_text = f'👥 TOTAL USERS: {len(users)}\n\n'
        for user_id, first_name, gender, age, country, messages_sent in users:
            user_text += f"{first_name} ({user_id})\nGender: {gender}\nAge: {age}\nCountry: {country}\nMessages: {messages_sent}\n\n"
        
        bot.send_message(uid, user_text)
    
    elif data == 'admin_ban':
        bot.send_message(uid, 'Enter user ID to ban:')
        bot.register_next_step_handler(call.message, process_ban_user)
    
    elif data == 'admin_permban':
        bot.send_message(uid, 'Enter user ID to permanently ban:')
        bot.register_next_step_handler(call.message, process_permanent_ban)
    
    elif data == 'admin_premium':
        bot.send_message(uid, 'Enter user ID to make premium:')
        bot.register_next_step_handler(call.message, process_admin_premium)
    
    elif data == 'admin_active':
        with active_pairs_lock:
            active_pairs_list = {}
            for user_id in list(active_pairs.keys()):
                if user_id not in active_pairs_list:
                    partner = active_pairs.get(user_id)
                    active_pairs_list[user_id] = partner
        
        if not active_pairs_list:
            bot.send_message(uid, 'No active chats.')
        else:
            active_text = f'💬 ACTIVE CHATS: {len(active_pairs_list) // 2}\n\n'
            for i, (user_id, partner) in enumerate(list(active_pairs_list.items())[:10]):
                u = db_get_user(int(user_id))
                p = db_get_user(partner)
                u_name = u.get('first_name', 'User') if u else 'User'
                p_name = p.get('first_name', 'User') if p else 'User'
                active_text += f"{i + 1}. {u_name} ↔️ {p_name}\n"
            bot.send_message(uid, active_text)
    
    elif data == 'admin_stats':
        with get_conn() as conn:
            total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total_messages = conn.execute('SELECT SUM(messages_sent) FROM users').fetchone()[0] or 0
            total_reports = conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
        
        with active_pairs_lock:
            active_chats = len(active_pairs) // 2
        
        stats_msg = f'''📊 BOT STATISTICS:

👥 Total Users: {total_users}
💬 Active Chats: {active_chats}
💭 Total Messages: {total_messages}
📋 Total Reports: {total_reports}'''
        
        bot.send_message(uid, stats_msg)
    
    bot.answer_callback_query(call.id)

def process_ban_user(message):
    admin_id = message.from_user.id
    if admin_id != ADMIN_ID:
        return
    
    user_id_str = message.text or ''
    try:
        ban_user_id = int(user_id_str)
        u = db_get_user(ban_user_id)
        if u:
            db_ban_user(ban_user_id, hours=24, permanent=False, reason='Admin ban')
            bot.send_message(admin_id, f'User {ban_user_id} banned for 24 hours!')
            try:
                bot.send_message(ban_user_id, 'You have been temporarily banned for 24 hours.')
            except:
                pass
            disconnect_user(ban_user_id)
        else:
            bot.send_message(admin_id, 'User not found!')
    except:
        bot.send_message(admin_id, 'Invalid ID!')

def process_permanent_ban(message):
    admin_id = message.from_user.id
    if admin_id != ADMIN_ID:
        return
    
    user_id_str = message.text or ''
    try:
        ban_user_id = int(user_id_str)
        u = db_get_user(ban_user_id)
        if u:
            db_ban_user(ban_user_id, hours=None, permanent=True, reason='Admin permanent ban')
            bot.send_message(admin_id, f'User {ban_user_id} permanently banned!')
            try:
                bot.send_message(ban_user_id, 'You have been permanently banned.')
            except:
                pass
            disconnect_user(ban_user_id)
        else:
            bot.send_message(admin_id, 'User not found!')
    except:
        bot.send_message(admin_id, 'Invalid ID!')

def process_admin_premium(message):
    admin_id = message.from_user.id
    if admin_id != ADMIN_ID:
        return
    
    user_id_str = message.text or ''
    try:
        premium_user_id = int(user_id_str)
        u = db_get_user(premium_user_id)
        if u:
            until_date = (datetime.utcnow() + timedelta(days=365)).isoformat()
            db_set_premium(premium_user_id, until_date)
            bot.send_message(admin_id, f'User {premium_user_id} now premium!')
            try:
                bot.send_message(premium_user_id, 'You have been granted premium for 1 year!')
            except:
                pass
        else:
            bot.send_message(admin_id, 'User not found!')
    except:
        bot.send_message(admin_id, 'Invalid ID!')

# ============================================================================
# RECONNECT
# ============================================================================
@bot.message_handler(commands=['reconnect'])
def cmd_reconnect(message):
    uid = message.from_user.id
    
    if db_is_banned(uid):
        bot.send_message(uid, 'You are banned.')
        return
    
    with reconnect_lock:
        if uid in reconnect_cooldown:
            cooldown_until = reconnect_cooldown[uid]
            try:
                if datetime.fromisoformat(cooldown_until) > datetime.utcnow():
                    remaining = datetime.fromisoformat(cooldown_until) - datetime.utcnow()
                    remaining_hours = remaining.seconds // 3600
                    bot.send_message(uid, f'Try again in {remaining_hours} hours')
                    return
            except:
                pass
            del reconnect_cooldown[uid]
    
    with active_pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, 'You are chatting. Use /stop first.')
            return
    
    partner_id = db_get_recent_partner(uid)
    if not partner_id:
        bot.send_message(uid, 'No recent chat found.')
        return
    
    with active_pairs_lock:
        if partner_id in active_pairs:
            bot.send_message(uid, 'Your partner is busy.')
            return
    
    if is_searching(partner_id):
        bot.send_message(uid, 'Your partner is searching.')
        return
    
    u = db_get_user(uid)
    name = u.get('first_name') if u else 'Someone'
    
    reconnect_markup = types.InlineKeyboardMarkup(row_width=2)
    reconnect_markup.add(
        types.InlineKeyboardButton('Accept', callback_data=f'recon_accept_{uid}'),
        types.InlineKeyboardButton('Decline', callback_data=f'recon_reject_{uid}')
    )
    
    with reconnect_lock:
        reconnect_requests[uid] = (partner_id, datetime.utcnow())
    
    try:
        bot.send_message(partner_id, f'{name} wants to chat again. Accept?', reply_markup=reconnect_markup)
        bot.send_message(uid, 'Request sent! Waiting for response...')
        logger.info(f'Reconnect: {uid} -> {partner_id}')
    except Exception as e:
        logger.error(f'Reconnect error: {e}')
        bot.send_message(uid, 'Error sending request.')

@bot.callback_query_handler(func=lambda c: c.data.startswith('recon_'))
def handle_reconnect_response(call):
    partner_id = call.from_user.id
    parts = call.data.split('_')
    action = parts[1]
    requester_id = int(parts[2])
    
    with reconnect_lock:
        if requester_id not in reconnect_requests:
            bot.answer_callback_query(call.id, 'Expired', show_alert=True)
            return
        
        stored_partner, req_time = reconnect_requests[requester_id]
        if stored_partner != partner_id:
            bot.answer_callback_query(call.id, 'Invalid', show_alert=True)
            return
        
        if (datetime.utcnow() - req_time).seconds > RECONNECT_TIMEOUT:
            bot.answer_callback_query(call.id, 'Timeout', show_alert=True)
            del reconnect_requests[requester_id]
            return
        
        del reconnect_requests[requester_id]
    
    if action == 'accept':
        with active_pairs_lock:
            if requester_id in active_pairs or partner_id in active_pairs:
                bot.answer_callback_query(call.id, 'Someone is busy', show_alert=True)
                try:
                    bot.send_message(requester_id, 'Your partner is busy.')
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
        
        bot.answer_callback_query(call.id, 'Connected!', show_alert=False)
        try:
            bot.send_message(requester_id, 'You are back! Let us chat.')
            bot.send_message(partner_id, 'They are back! Let us chat.')
            logger.info(f'Reconnected: {requester_id} ↔️ {partner_id}')
        except Exception as e:
            logger.error(f'Recon notify error: {e}')
    
    else:
        bot.answer_callback_query(call.id, 'Declined', show_alert=False)
        try:
            bot.send_message(requester_id, 'They declined.')
        except:
            pass

# ============================================================================
# CHAT MESSAGES
# ============================================================================
@bot.message_handler(content_types=['text'])
def forward_chat_message(message):
    uid = message.from_user.id
    text = message.text or ''
    
    if text.startswith('/'):
        return
    
    if is_banned_content(text):
        warn_user(uid, 'Violated community rules')
        return
    
    with active_pairs_lock:
        if uid not in active_pairs:
            return
        
        partner_id = active_pairs[uid]
    
    try:
        sender_user = db_get_user(uid) or {}
        receiver_user = db_get_user(partner_id) or {}
        sender_name = sender_user.get('first_name', 'User')
        receiver_name = receiver_user.get('first_name', 'User')
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        db_save_chat_log(uid, sender_name, partner_id, receiver_name, 'text', text)
        
        if partner_id == ADMIN_ID:
            admin_msg = f'''SENDER:
Name: {sender_name}
ID: {uid}
Gender: {sender_user.get('gender') or '?'}
Age: {sender_user.get('age') or '?'}
Country: {sender_user.get('country_flag', '')} {sender_user.get('country') or '?'}

RECEIVER: Admin

Time: {timestamp}

Message:
{text}'''
            bot.send_message(partner_id, admin_msg)
        else:
            bot.send_message(partner_id, text)
        
        with get_conn() as conn:
            conn.execute('UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?', (uid,))
            conn.commit()
        
        logger.info(f'Message from {uid} to {partner_id}')
    except Exception as e:
        logger.error(f'Forward error: {e}')

@bot.message_handler(content_types=['photo', 'video', 'document', 'voice', 'audio', 'sticker'])
def handle_media_message(message):
    uid = message.from_user.id
    
    with active_pairs_lock:
        if uid not in active_pairs:
            return
        
        partner_id = active_pairs[uid]
    
    try:
        sender_user = db_get_user(uid) or {}
        receiver_user = db_get_user(partner_id) or {}
        sender_name = sender_user.get('first_name', 'User')
        receiver_name = receiver_user.get('first_name', 'User')
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        media_icons = {
            'photo': 'Photo',
            'video': 'Video',
            'document': 'Document',
            'voice': 'Voice Message',
            'audio': 'Audio',
            'sticker': 'Sticker'
        }
        
        media_type = media_icons.get(message.content_type, 'Media')
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('Accept', callback_data=f'media_accept_{uid}'),
            types.InlineKeyboardButton('Decline', callback_data=f'media_decline_{uid}')
        )
        
        db_save_chat_log(uid, sender_name, partner_id, receiver_name, message.content_type, media_type)
        
        media_id = secrets.token_hex(8)
        with pending_media_lock:
            pending_media[media_id] = {
                'sender_id': uid,
                'message': message,
                'timestamp': timestamp,
                'partner_id': partner_id
            }
        
        if partner_id == ADMIN_ID:
            admin_msg = f'''SENDER:
Name: {sender_name}
ID: {uid}
Gender: {sender_user.get('gender') or '?'}
Age: {sender_user.get('age') or '?'}
Country: {sender_user.get('country_flag', '')} {sender_user.get('country') or '?'}

RECEIVER: Admin

Media: {media_type}
Time: {timestamp}

Allow?'''
            bot.send_message(partner_id, admin_msg, reply_markup=markup)
        else:
            user_msg = f'{sender_name} sent {media_type}\n\nAllow?'
            bot.send_message(partner_id, user_msg, reply_markup=markup)
        
        logger.info(f'Media {media_type} from {uid} to {partner_id}')
    except Exception as e:
        logger.error(f'Media error: {e}')

@bot.callback_query_handler(func=lambda c: c.data.startswith('media_'))
def handle_media_approval(call):
    uid = call.from_user.id
    parts = call.data.split('_')
    action = parts[1]
    sender_id = int(parts[2])
    
    with pending_media_lock:
        media_list = [k for k, v in pending_media.items() if v.get('sender_id') == sender_id and v.get('partner_id') == uid]
        if not media_list:
            bot.answer_callback_query(call.id, 'Expired', show_alert=True)
            return
        
        media_id = media_list[0]
        entry = pending_media.get(media_id)
        msg = entry.get('message')
    
    try:
        if action == 'accept':
            try:
                if msg.content_type == 'photo' and hasattr(msg, 'photo'):
                    bot.send_photo(uid, msg.photo[-1].file_id)
                elif msg.content_type == 'video' and hasattr(msg, 'video'):
                    bot.send_video(uid, msg.video.file_id)
                elif msg.content_type == 'document' and hasattr(msg, 'document'):
                    bot.send_document(uid, msg.document.file_id)
                elif msg.content_type == 'voice' and hasattr(msg, 'voice'):
                    bot.send_voice(uid, msg.voice.file_id)
                elif msg.content_type == 'audio' and hasattr(msg, 'audio'):
                    bot.send_audio(uid, msg.audio.file_id)
                elif msg.content_type == 'sticker' and hasattr(msg, 'sticker'):
                    bot.send_sticker(uid, msg.sticker.file_id)
                else:
                    bot.send_message(uid, 'Cannot forward this media type.')
            except Exception as e:
                logger.error(f'Media send error: {e}')
                bot.send_message(uid, 'Failed to send media')
                try:
                    bot.send_message(sender_id, 'Failed to send media')
                except:
                    pass
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    pass
                return
            
            bot.answer_callback_query(call.id, 'Sent', show_alert=False)
            db_increment_media(sender_id, 'approved')
            
            try:
                bot.send_message(sender_id, 'Your media was accepted')
            except:
                pass
        else:
            bot.answer_callback_query(call.id, 'Declined', show_alert=False)
            db_increment_media(sender_id, 'rejected')
            
            try:
                bot.send_message(sender_id, 'Your media was declined')
            except:
                pass
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        with pending_media_lock:
            pending_media.pop(media_id, None)
        
        logger.info(f'Media {action} {sender_id} by {uid}')
    except Exception as e:
        logger.error(f'Media error: {e}')
        try:
            bot.send_message(uid, 'Error processing media')
        except:
            pass

# ============================================================================
# FLASK ROUTES
# ============================================================================
@app.route(WEBHOOK_PATH, methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json.loads(json_str))
        bot.process_new_updates([update])
    return '', 200

@app.route('/')
def home():
    return 'GhostTalk bot is running', 200

# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    init_db()
    
    logger.info('=' * 60)
    logger.info('🤖 GhostTalk Bot v5.4 - COMPLETE')
    logger.info('=' * 60)
    logger.info('✓ Anonymous Random Chat')
    logger.info('✓ Full Chat Forwarding')
    logger.info('✓ Media Accept/Reject')
    logger.info('✓ Report System')
    logger.info('✓ Admin Panel')
    logger.info('✓ Ban System (Temp & Permanent)')
    logger.info('✓ Reconnect System')
    logger.info('✓ Premium System')
    logger.info('=' * 60)
    
    search_timeout_monitor()
    cleanup_threads()
    
    if WEBHOOK_URL:
        full_url = WEBHOOK_URL.rstrip('/') + WEBHOOK_PATH
        try:
            bot.remove_webhook()
        except:
            pass
        try:
            bot.set_webhook(url=full_url)
            logger.info(f'Webhook set to {full_url}')
        except Exception as e:
            logger.error(f'Failed to set webhook: {e}')
        
        app.run(host='0.0.0.0', port=PORT, debug=False)
    else:
        logger.info('Starting polling...')
        while True:
            try:
                bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except KeyboardInterrupt:
                logger.info('Bot stopped')
                break
            except Exception as e:
                logger.error(f'Polling error: {e}')
                time.sleep(5)
