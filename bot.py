#!/usr/bin/env python3
"""
GhostTalk Premium Anonymous Chat Bot v5.0 - COMPLETE FINAL
✅ All countries (195)
✅ Auto-ban on 7 reports
✅ 3-Priority matching
✅ Reconnect feature
✅ Media tokens (no frozen)
✅ Voice + Audio + all media
✅ Admin full chat forwarding
✅ Admin full profile view
✅ Admin ban/unban/premium
✅ All emojis
✅ No duplicates
✅ Gender tap fix
"""

import sqlite3, random, logging, re, time, secrets, threading, os, telebot
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

API_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not API_TOKEN: raise ValueError("BOT_TOKEN!")
ADMIN_ID = int(os.getenv('ADMIN_ID', '8361006824'))
OWNER_ID = ADMIN_ID
DB_PATH = os.getenv('DB_PATH', 'ghosttalk_v5.db')
PORT = int(os.getenv('PORT', 8080))

WARNING_LIMIT = 3
TEMP_BAN_HOURS = 24
AUTO_BAN_REPORTS = 7
AUTO_BAN_DAYS = 7
PREMIUM_REFERRALS_NEEDED = 3
PREMIUM_DURATION_HOURS = 24

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telebot.TeleBot(API_TOKEN, threaded=True)

waiting_random = []
waiting_opposite = []
active_pairs = {}
chat_history_with_time = {}
pending_country = set()
pending_age = set()
report_reason_pending = {}
pending_media = {}
reconnect_requests = {}
stop_cooldown = {}
user_warnings = {}

queue_lock = threading.Lock()
pairs_lock = threading.Lock()
media_lock = threading.Lock()
stop_lock = threading.Lock()
warnings_lock = threading.Lock()

# 195 COUNTRIES WITH FLAGS
COUNTRIES = {
    'afghanistan': '🇦🇫', 'albania': '🇦🇱', 'algeria': '🇩🇿', 'andorra': '🇦🇩', 'angola': '🇦🇴',
    'antigua and barbuda': '🇦🇬', 'argentina': '🇦🇷', 'armenia': '🇦🇲', 'australia': '🇦🇺', 'austria': '🇦🇹',
    'azerbaijan': '🇦🇿', 'bahamas': '🇧🇸', 'bahrain': '🇧🇭', 'bangladesh': '🇧🇩', 'barbados': '🇧🇧',
    'belarus': '🇧🇾', 'belgium': '🇧🇪', 'belize': '🇧🇿', 'benin': '🇧🇯', 'bhutan': '🇧🇹',
    'bolivia': '🇧🇴', 'bosnia and herzegovina': '🇧🇦', 'botswana': '🇧🇼', 'brazil': '🇧🇷', 'brunei': '🇧🇳',
    'bulgaria': '🇧🇬', 'burkina faso': '🇧🇫', 'burundi': '🇧🇮', 'cambodia': '🇰🇭', 'cameroon': '🇨🇲',
    'canada': '🇨🇦', 'cape verde': '🇨🇻', 'central african republic': '🇨🇫', 'chad': '🇹🇩', 'chile': '🇨🇱',
    'china': '🇨🇳', 'colombia': '🇨🇴', 'comoros': '🇰🇲', 'congo': '🇨🇬', 'costa rica': '🇨🇷',
    'croatia': '🇭🇷', 'cuba': '🇨🇺', 'cyprus': '🇨🇾', 'czech republic': '🇨🇿', 'czechia': '🇨🇿',
    'denmark': '🇩🇰', 'djibouti': '🇩🇯', 'dominica': '🇩🇲', 'dominican republic': '🇩🇴', 'ecuador': '🇪🇨',
    'egypt': '🇪🇬', 'el salvador': '🇸🇻', 'equatorial guinea': '🇬🇶', 'eritrea': '🇪🇷', 'estonia': '🇪🇪',
    'eswatini': '🇸🇿', 'ethiopia': '🇪🇹', 'fiji': '🇫🇯', 'finland': '🇫🇮', 'france': '🇫🇷',
    'gabon': '🇬🇦', 'gambia': '🇬🇲', 'georgia': '🇬🇪', 'germany': '🇩🇪', 'ghana': '🇬🇭',
    'greece': '🇬🇷', 'grenada': '🇬🇩', 'guatemala': '🇬🇹', 'guinea': '🇬🇳', 'guinea-bissau': '🇬🇼',
    'guyana': '🇬🇾', 'haiti': '🇭🇹', 'honduras': '🇭🇳', 'hungary': '🇭🇺', 'iceland': '🇮🇸',
    'india': '🇮🇳', 'indonesia': '🇮🇩', 'iran': '🇮🇷', 'iraq': '🇮🇶', 'ireland': '🇮🇪',
    'israel': '🇮🇱', 'italy': '🇮🇹', 'jamaica': '🇯🇲', 'japan': '🇯🇵', 'jordan': '🇯🇴',
    'kazakhstan': '🇰🇿', 'kenya': '🇰🇪', 'kiribati': '🇰🇮', 'korea north': '🇰🇵', 'korea south': '🇰🇷',
    'kuwait': '🇰🇼', 'kyrgyzstan': '🇰🇬', 'laos': '🇱🇦', 'latvia': '🇱🇻', 'lebanon': '🇱🇧',
    'lesotho': '🇱🇸', 'liberia': '🇱🇷', 'libya': '🇱🇾', 'liechtenstein': '🇱🇮', 'lithuania': '🇱🇹',
    'luxembourg': '🇱🇺', 'madagascar': '🇲🇬', 'malawi': '🇲🇼', 'malaysia': '🇲🇾', 'maldives': '🇲🇻',
    'mali': '🇲🇱', 'malta': '🇲🇹', 'marshall islands': '🇲🇭', 'mauritania': '🇲🇷', 'mauritius': '🇲🇺',
    'mexico': '🇲🇽', 'micronesia': '🇫🇲', 'moldova': '🇲🇩', 'monaco': '🇲🇨', 'mongolia': '🇲🇳',
    'montenegro': '🇲🇪', 'morocco': '🇲🇦', 'mozambique': '🇲🇿', 'myanmar': '🇲🇲', 'namibia': '🇳🇦',
    'nauru': '🇳🇷', 'nepal': '🇳🇵', 'netherlands': '🇳🇱', 'new zealand': '🇳🇿', 'nicaragua': '🇳🇮',
    'niger': '🇳🇪', 'nigeria': '🇳🇬', 'north macedonia': '🇲🇰', 'norway': '🇳🇴', 'oman': '🇴🇲',
    'pakistan': '🇵🇰', 'palau': '🇵🇼', 'palestine': '🇵🇸', 'panama': '🇵🇦', 'papua new guinea': '🇵🇬',
    'paraguay': '🇵🇾', 'peru': '🇵🇪', 'philippines': '🇵🇭', 'poland': '🇵🇱', 'portugal': '🇵🇹',
    'qatar': '🇶🇦', 'romania': '🇷🇴', 'russia': '🇷🇺', 'rwanda': '🇷🇼', 'saint kitts and nevis': '🇰🇳',
    'saint lucia': '🇱🇨', 'saint vincent and the grenadines': '🇻🇨', 'samoa': '🇼🇸', 'san marino': '🇸🇲',
    'sao tome and principe': '🇸🇹', 'saudi arabia': '🇸🇦', 'senegal': '🇸🇳', 'serbia': '🇷🇸', 'seychelles': '🇸🇨',
    'sierra leone': '🇸🇱', 'singapore': '🇸🇬', 'slovakia': '🇸🇰', 'slovenia': '🇸🇮', 'solomon islands': '🇸🇧',
    'somalia': '🇸🇴', 'south africa': '🇿🇦', 'south sudan': '🇸🇸', 'spain': '🇪🇸', 'sri lanka': '🇱🇰',
    'sudan': '🇸🇩', 'suriname': '🇸🇷', 'sweden': '🇸🇪', 'switzerland': '🇨🇭', 'syria': '🇸🇾',
    'taiwan': '🇹🇼', 'tajikistan': '🇹🇯', 'tanzania': '🇹🇿', 'thailand': '🇹🇭', 'timor-leste': '🇹🇱',
    'togo': '🇹🇬', 'tonga': '🇹🇴', 'trinidad and tobago': '🇹🇹', 'tunisia': '🇹🇳', 'turkey': '🇹🇷',
    'turkmenistan': '🇹🇲', 'tuvalu': '🇹🇻', 'uganda': '🇺🇬', 'ukraine': '🇺🇦', 'united arab emirates': '🇦🇪',
    'united kingdom': '🇬🇧', 'united states': '🇺🇸', 'uruguay': '🇺🇾', 'uzbekistan': '🇺🇿', 'vanuatu': '🇻🇺',
    'vatican city': '🇻🇦', 'venezuela': '🇻🇪', 'vietnam': '🇻🇳', 'yemen': '🇾🇪', 'zambia': '🇿🇲', 'zimbabwe': '🇿🇼'
}

COUNTRY_ALIASES = {
    'usa': 'united states', 'us': 'united states', 'america': 'united states',
    'uk': 'united kingdom', 'britain': 'united kingdom', 'england': 'united kingdom',
    'uae': 'united arab emirates', 'emirates': 'united arab emirates',
    'south korea': 'korea south', 'sk': 'korea south', 'north korea': 'korea north', 'nk': 'korea north',
    'czechia': 'czech republic'
}

BANNED_WORDS = [
    'fuck', 'fucking', 'sex chat', 'nudes', 'pussy', 'dick', 'cock', 'penis', 'vagina', 'boobs', 'tits',
    'ass', 'asshole', 'bitch', 'slut', 'whore', 'hoe', 'prostitute', 'porn', 'pornography', 'rape', 'child',
    'pedo', 'anj', 'anjing', 'babi', 'asu', 'kontl', 'kontol', 'puki', 'memek', 'jembut', 'maderchod', 'mc',
    'bhen ka lauda', 'bhenkalauda', 'randi', 'randika', 'gand', 'bsdk', 'chut', 'chot', 'chuut', 'choot', 'lund'
]

LINK_PATTERN = re.compile(r'https?://|www\.', re.IGNORECASE)
BANNED_PATTERNS = [re.compile(re.escape(w), re.IGNORECASE) for w in BANNED_WORDS]

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            gender TEXT, age INTEGER, country TEXT, country_flag TEXT,
            messages_sent INTEGER DEFAULT 0, media_approved INTEGER DEFAULT 0,
            media_rejected INTEGER DEFAULT 0, referral_code TEXT UNIQUE,
            referral_count INTEGER DEFAULT 0, premium_until TEXT, joined_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY, ban_until TEXT, permanent INTEGER DEFAULT 0,
            reason TEXT, banned_by INTEGER, banned_at TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER,
            reported_id INTEGER, reason TEXT, timestamp TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS recent_partners (
            user_id INTEGER PRIMARY KEY, partner_id INTEGER, reconnect_until TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            partner_id INTEGER, message_type TEXT, message_id INTEGER,
            chat_id INTEGER, timestamp TEXT)''')
        conn.commit()
    logger.info("✅ DB ready")

def db_user(uid):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT user_id, username, first_name, gender, age, country, country_flag, messages_sent, media_approved, media_rejected, referral_code, referral_count, premium_until FROM users WHERE user_id=?',
            (uid,)
        ).fetchone()
        if not row: return None
        return {
            'user_id': row[0], 'username': row[1], 'first_name': row[2], 'gender': row[3], 'age': row[4],
            'country': row[5], 'country_flag': row[6], 'messages_sent': row[7], 'media_approved': row[8],
            'media_rejected': row[9], 'referral_code': row[10], 'referral_count': row[11], 'premium_until': row[12]
        }

def db_create(user):
    uid = user.id
    if db_user(uid): return
    ref = f"REF{uid}{random.randint(1000, 99999)}"
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO users (user_id, username, first_name, gender, age, country, country_flag, joined_at, referral_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (uid, user.username or '', user.first_name or '', None, None, None, None, datetime.now().isoformat(), ref)
        )
        conn.commit()

def db_gender(uid, gender):
    with get_conn() as conn:
        conn.execute('UPDATE users SET gender=? WHERE user_id=?', (gender, uid))
        conn.commit()

def db_age(uid, age):
    with get_conn() as conn:
        conn.execute('UPDATE users SET age=? WHERE user_id=?', (age, uid))
        conn.commit()

def db_country(uid, country, flag):
    with get_conn() as conn:
        conn.execute('UPDATE users SET country=?, country_flag=? WHERE user_id=?', (country, flag, uid))
        conn.commit()

def is_premium(uid):
    if uid == ADMIN_ID: return True
    u = db_user(uid)
    if not u or not u.get('premium_until'): return False
    try: return datetime.fromisoformat(u.get('premium_until')) > datetime.now()
    except: return False

def is_banned(uid):
    if uid == OWNER_ID: return False
    with get_conn() as conn:
        row = conn.execute('SELECT ban_until, permanent FROM bans WHERE user_id=?', (uid,)).fetchone()
        if not row: return False
        ban_until, permanent = row
        if permanent: return True
        if ban_until:
            try: return datetime.fromisoformat(ban_until) > datetime.now()
            except: return False
        return False

def ban_user(uid, hours=None, permanent=False, reason=''):
    with get_conn() as conn:
        if permanent:
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (uid, None, 1, reason, ADMIN_ID, datetime.now().isoformat())
            )
        else:
            until = (datetime.now() + timedelta(hours=hours)).isoformat() if hours else None
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (uid, until, 0, reason, ADMIN_ID, datetime.now().isoformat())
            )
        conn.commit()

def unban_user(uid):
    with get_conn() as conn:
        conn.execute('DELETE FROM bans WHERE user_id=?', (uid,))
        conn.commit()

def add_report(reporter_id, reported_id, reason):
    with get_conn() as conn:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO reports (reporter_id, reported_id, reason, timestamp) VALUES (?, ?, ?, ?)',
                     (reporter_id, reported_id, reason, timestamp))
        count = conn.execute('SELECT COUNT(*) FROM reports WHERE reported_id=?', (reported_id,)).fetchone()[0]
        if count >= AUTO_BAN_REPORTS:
            ban_until = (datetime.now() + timedelta(days=AUTO_BAN_DAYS)).isoformat()
            conn.execute(
                'INSERT OR REPLACE INTO bans (user_id, ban_until, permanent, reason, banned_by, banned_at) VALUES (?, ?, ?, ?, ?, ?)',
                (reported_id, ban_until, 0, f'Auto-ban {count} reports', ADMIN_ID, datetime.now().isoformat())
            )
            try: bot.send_message(reported_id, f'🚫 Auto-banned for {AUTO_BAN_DAYS} days.')
            except: pass
            disconnect(reported_id)
        conn.commit()

def save_partner(uid, partner_id):
    with get_conn() as conn:
        until = (datetime.now() + timedelta(minutes=5)).isoformat()
        conn.execute('INSERT OR REPLACE INTO recent_partners (user_id, partner_id, reconnect_until) VALUES (?, ?, ?)',
                     (uid, partner_id, until))
        conn.commit()

def get_partner(uid):
    with get_conn() as conn:
        row = conn.execute('SELECT partner_id, reconnect_until FROM recent_partners WHERE user_id=?', (uid,)).fetchone()
        if not row: return None
        partner_id, until = row
        try:
            if datetime.fromisoformat(until) > datetime.now(): return partner_id
        except: pass
        conn.execute('DELETE FROM recent_partners WHERE user_id=?', (uid,))
        conn.commit()
        return None

def clear_partner(uid):
    with get_conn() as conn:
        conn.execute('DELETE FROM recent_partners WHERE user_id=?', (uid,))
        conn.commit()

def save_message(uid, partner_id, msg_type, msg_id, chat_id):
    with get_conn() as conn:
        conn.execute('INSERT INTO chat_messages (user_id, partner_id, message_type, message_id, chat_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                     (uid, partner_id, msg_type, msg_id, chat_id, datetime.now().isoformat()))
        conn.commit()

def get_chat_messages(uid, partner_id, limit=50):
    with get_conn() as conn:
        rows = conn.execute('SELECT message_type, message_id, chat_id FROM chat_messages WHERE user_id=? AND partner_id=? ORDER BY timestamp DESC LIMIT ?',
                            (uid, partner_id, limit)).fetchall()
        return rows

def inc_media(uid, stat):
    with get_conn() as conn:
        if stat == 'approved':
            conn.execute('UPDATE users SET media_approved=media_approved+1 WHERE user_id=?', (uid,))
        else:
            conn.execute('UPDATE users SET media_rejected=media_rejected+1 WHERE user_id=?', (uid,))
        conn.commit()

def is_banned_content(text):
    if not text: return False
    if LINK_PATTERN.search(text): return True
    for p in BANNED_PATTERNS:
        if p.search(text): return True
    return False

def warn_user(uid, reason):
    with warnings_lock:
        count = user_warnings.get(uid, 0) + 1
        user_warnings[uid] = count
        if count >= WARNING_LIMIT:
            ban_user(uid, hours=TEMP_BAN_HOURS, reason=reason)
            try: bot.send_message(uid, f'🚫 BANNED for {TEMP_BAN_HOURS} hours! Reason: {reason}')
            except: pass
            user_warnings[uid] = 0
            return 'ban'
        else:
            try: bot.send_message(uid, f'⚠️ WARNING {count}/{WARNING_LIMIT}! {reason}. {WARNING_LIMIT - count} more = BAN!')
            except: pass
            return 'warn'

def remove_queue(uid):
    global waiting_random, waiting_opposite
    with queue_lock:
        if uid in waiting_random: waiting_random.remove(uid)
        waiting_opposite = [x for x in waiting_opposite if x[0] != uid]

def is_searching(uid):
    with queue_lock:
        if uid in waiting_random: return True
        for u, _ in waiting_opposite:
            if u == uid: return True
        return False

def disconnect(uid):
    global active_pairs, chat_history_with_time
    partner_id = None
    
    with pairs_lock:
        if uid in active_pairs:
            partner_id = active_pairs[uid]
            del active_pairs[uid]
            if partner_id in active_pairs: del active_pairs[partner_id]
    
    if partner_id:
        chat_history_with_time[uid] = (partner_id, datetime.now())
        chat_history_with_time[partner_id] = (uid, datetime.now())
        save_partner(uid, partner_id)
        save_partner(partner_id, uid)
    
    try: bot.send_message(partner_id, "👤 Partner left", reply_markup=report_menu())
    except: pass
    try: bot.send_message(uid, "✅ Chat ended", reply_markup=main_kb(uid))
    except: pass

def match():
    global waiting_random, waiting_opposite, active_pairs
    
    i = 0
    while i < len(waiting_opposite):
        uid1, gender1 = waiting_opposite[i]
        if not is_premium(uid1):
            i += 1
            continue
        need = 'Female' if gender1 == 'Male' else 'Male'
        
        with queue_lock:
            for j in range(i + 1, len(waiting_opposite)):
                uid2, gender2 = waiting_opposite[j]
                if is_premium(uid2) and gender2 == need:
                    waiting_opposite.pop(j)
                    waiting_opposite.pop(i)
                    with pairs_lock:
                        active_pairs[uid1] = uid2
                        active_pairs[uid2] = uid1
                    announce(uid1, uid2)
                    return
        i += 1
    
    opp_copy = list(waiting_opposite)
    for uid1, gender1 in opp_copy:
        if not is_premium(uid1): continue
        need = 'Female' if gender1 == 'Male' else 'Male'
        with queue_lock:
            for j, uid2 in enumerate(waiting_random):
                u2 = db_user(uid2)
                if u2 and u2.get('gender') == need:
                    waiting_random.pop(j)
                    waiting_opposite = [x for x in waiting_opposite if x[0] != uid1]
                    with pairs_lock:
                        active_pairs[uid1] = uid2
                        active_pairs[uid2] = uid1
                    announce(uid1, uid2)
                    return
    
    with queue_lock:
        while len(waiting_random) >= 2:
            u1 = waiting_random.pop(0)
            u2 = waiting_random.pop(0)
            with pairs_lock:
                active_pairs[u1] = u2
                active_pairs[u2] = u1
            announce(u1, u2)
            return

def announce(u1, u2):
    u1_data = db_user(u1) or {}
    u2_data = db_user(u2) or {}
    try:
        msg1 = f"✨ Match! {u2_data.get('gender')} | {u2_data.get('age')} | {u2_data.get('country_flag')} {u2_data.get('country')}\n👋 Say hi!"
        msg2 = f"✨ Match! {u1_data.get('gender')} | {u1_data.get('age')} | {u1_data.get('country_flag')} {u1_data.get('country')}\n👋 Say hi!"
        bot.send_message(u1, msg1, reply_markup=chat_kb())
        bot.send_message(u2, msg2, reply_markup=chat_kb())
    except: pass

def cleanup_threads():
    def run():
        while True:
            time.sleep(3600)
            try:
                now = datetime.now()
                threshold = timedelta(days=7)
                to_delete = []
                for uid, (partner, ts) in list(chat_history_with_time.items()):
                    try:
                        if now - ts > threshold:
                            to_delete.append(uid)
                    except:
                        to_delete.append(uid)
                for uid in to_delete:
                    chat_history_with_time.pop(uid, None)
            except:
                pass
    t = threading.Thread(target=run, daemon=True)
    t.start()

def main_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('🔍 Search Random')
    u = db_user(uid)
    if u and u.get('gender'):
        if is_premium(uid):
            kb.add('💎 Search Opposite')
        else:
            kb.add('💎 Opposite (Premium)')
    kb.add('⚙️ Settings', '👥 Refer')
    kb.add('❓ Help', '📋 Rules')
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('📊 Stats')
    kb.add('⏭️ Next', '🛑 Stop')
    return kb

def report_menu():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('📋 Report', callback_data='report_open'))
    return m

def report_kb():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton('🚫 Spam', callback_data='rep_spam'),
        types.InlineKeyboardButton('😡 Inappropriate', callback_data='rep_inapp'),
        types.InlineKeyboardButton('⚠️ Suspicious', callback_data='rep_susp'),
        types.InlineKeyboardButton('😠 Harassment', callback_data='rep_harr'),
        types.InlineKeyboardButton('❓ Other', callback_data='rep_other'),
        types.InlineKeyboardButton('❌ Cancel', callback_data='rep_skip')
    )
    return m

def get_country(text):
    norm = (text or '').strip().lower()
    if norm in COUNTRY_ALIASES:
        norm = COUNTRY_ALIASES[norm]
    if norm in COUNTRIES:
        return norm.title(), COUNTRIES[norm]
    return None

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    db_create(msg.from_user)
    if is_banned(uid):
        bot.send_message(uid, '🚫 Banned')
        return
    u = db_user(uid)
    if not u or not u.get('gender'):
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton('👨 Male', callback_data='sex_m'), types.InlineKeyboardButton('👩 Female', callback_data='sex_f'))
        bot.send_message(uid, "👋 Welcome! Gender?", reply_markup=m)
    elif not u.get('age'):
        bot.send_message(uid, '🎂 Age? (12-99)')
        pending_age.add(uid)
        bot.register_next_step_handler(msg, age_process)
    elif not u.get('country'):
        bot.send_message(uid, '🌍 Country?')
        pending_country.add(uid)
        bot.register_next_step_handler(msg, country_process)
    else:
        bot.send_message(uid, '✅ Ready!', reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith('sex_'))
def sex_cb(call):
    uid = call.from_user.id
    if uid in [x[0] for x in waiting_opposite] or uid in waiting_random:
        bot.answer_callback_query(call.id, '⏳ Stop search first')
        return
    gender = 'Male' if call.data == 'sex_m' else 'Female'
    db_gender(uid, gender)
    bot.answer_callback_query(call.id, f'✅ {gender}')
    bot.send_message(uid, '🎂 Age?')
    pending_age.add(uid)
    bot.register_next_step_handler(call.message, age_process)

def age_process(msg):
    uid = msg.from_user.id
    if uid not in pending_age: return
    try:
        age = int(msg.text)
        if age < 12 or age > 99: raise ValueError
    except:
        bot.send_message(uid, '❌ Invalid')
        bot.register_next_step_handler(msg, age_process)
        return
    db_age(uid, age)
    pending_age.discard(uid)
    bot.send_message(uid, '🌍 Country?')
    pending_country.add(uid)
    bot.register_next_step_handler(msg, country_process)

def country_process(msg):
    uid = msg.from_user.id
    if uid not in pending_country: return
    info = get_country(msg.text)
    if not info:
        bot.send_message(uid, '❌ Not found')
        bot.register_next_step_handler(msg, country_process)
        return
    db_country(uid, info[0], info[1])
    pending_country.discard(uid)
    bot.send_message(uid, f'✅ {info[1]} {info[0]}!', reply_markup=main_kb(uid))

@bot.message_handler(commands=['search'])
def search(msg):
    uid = msg.from_user.id
    if is_banned(uid):
        bot.send_message(uid, '🚫 Banned')
        return
    u = db_user(uid)
    if not u or not u.get('gender') or not u.get('age') or not u.get('country'):
        bot.send_message(uid, '❌ Profile incomplete')
        return
    with pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, '⚠️ Already chatting')
            return
    if is_searching(uid):
        bot.send_message(uid, '⏳ Already searching')
        return
    remove_queue(uid)
    with queue_lock:
        waiting_random.append(uid)
    bot.send_message(uid, '🔍 Searching...')
    threading.Thread(target=match, daemon=True).start()

@bot.message_handler(commands=['search_opposite'])
def search_opp(msg):
    uid = msg.from_user.id
    if is_banned(uid):
        bot.send_message(uid, '🚫 Banned')
        return
    if not is_premium(uid):
        bot.send_message(uid, '💎 Premium! Invite 3 friends')
        return
    u = db_user(uid)
    if not u or not u.get('gender'):
        bot.send_message(uid, '❌ Profile incomplete')
        return
    with pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, '⚠️ Already chatting')
            return
    if is_searching(uid):
        bot.send_message(uid, '⏳ Already searching')
        return
    remove_queue(uid)
    with queue_lock:
        waiting_opposite.append((uid, u.get('gender')))
    bot.send_message(uid, '🔍 Searching opposite...')
    threading.Thread(target=match, daemon=True).start()

@bot.message_handler(commands=['stop'])
def stop(msg):
    uid = msg.from_user.id
    if is_searching(uid):
        remove_queue(uid)
        bot.send_message(uid, '✅ Stopped', reply_markup=main_kb(uid))
        return
    with pairs_lock:
        if uid in active_pairs:
            disconnect(uid)
            return
    now = time.time()
    with stop_lock:
        last = stop_cooldown.get(uid, 0)
        if now - last < 30: return
        stop_cooldown[uid] = now
    bot.send_message(uid, '❌ Not chatting', reply_markup=main_kb(uid))

@bot.message_handler(commands=['next'])
def next_cmd(msg):
    uid = msg.from_user.id
    with pairs_lock:
        if uid not in active_pairs:
            bot.send_message(uid, '❌ Not chatting')
            return
        disconnect(uid)
    bot.send_message(uid, '🔍 Finding new...')
    search(msg)

@bot.message_handler(commands=['reconnect'])
def reconnect(msg):
    uid = msg.from_user.id
    with pairs_lock:
        if uid in active_pairs:
            bot.send_message(uid, '⚠️ Already chatting')
            return
    partner_id = get_partner(uid)
    if not partner_id:
        bot.send_message(uid, '❌ No recent chat')
        return
    u = db_user(uid)
    name = u.get('first_name') if u else 'Someone'
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('✅ Yes', callback_data=f'recon_y_{uid}'), types.InlineKeyboardButton('❌ No', callback_data=f'recon_n_{uid}'))
    reconnect_requests[uid] = (partner_id, datetime.now())
    try:
        bot.send_message(partner_id, f'{name} wants to reconnect!', reply_markup=m)
        bot.send_message(uid, '⏳ Waiting...')
    except:
        bot.send_message(uid, '❌ Error')

@bot.callback_query_handler(func=lambda c: c.data.startswith('recon_'))
def recon_cb(call):
    parts = call.data.split('_')
    action = parts[1]
    req_id = int(parts[2])
    partner_id = call.from_user.id
    if req_id not in reconnect_requests:
        bot.answer_callback_query(call.id, '⏰ Expired')
        return
    stored, _ = reconnect_requests[req_id]
    if stored != partner_id:
        bot.answer_callback_query(call.id, '❌ Invalid')
        return
    del reconnect_requests[req_id]
    if action == 'y':
        with pairs_lock:
            active_pairs[req_id] = partner_id
            active_pairs[partner_id] = req_id
        clear_partner(req_id)
        clear_partner(partner_id)
        bot.answer_callback_query(call.id, '✅ Connected')
        bot.send_message(req_id, '✅ Reconnected!', reply_markup=chat_kb())
        bot.send_message(partner_id, '✅ Reconnected!', reply_markup=chat_kb())
    else:
        bot.answer_callback_query(call.id, '❌ Declined')
        bot.send_message(req_id, '❌ Declined')

@bot.message_handler(commands=['report'])
def report_cmd(msg):
    uid = msg.from_user.id
    with pairs_lock:
        if uid not in active_pairs:
            if uid not in chat_history_with_time:
                bot.send_message(uid, '❌ No one to report')
                return
            partner_id, _ = chat_history_with_time[uid]
        else:
            partner_id = active_pairs[uid]
    report_reason_pending[uid] = partner_id
    bot.send_message(uid, '📋 Reason?', reply_markup=report_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith('rep_'))
def report_cb(call):
    uid = call.from_user.id
    key = call.data.split('_')[1]
    if key == 'skip':
        bot.answer_callback_query(call.id, '❌ Skipped')
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        report_reason_pending.pop(uid, None)
        return
    if uid not in report_reason_pending:
        bot.answer_callback_query(call.id, '⏰ Expired')
        return
    reported_id = report_reason_pending.pop(uid)
    reasons = {'spam': 'Spam', 'inapp': 'Inappropriate', 'susp': 'Suspicious', 'harr': 'Harassment', 'other': 'Other'}
    reason = reasons.get(key, 'Other')
    
    reporter = db_user(uid)
    reported = db_user(reported_id)
    
    add_report(uid, reported_id, reason)
    
    try:
        admin_msg = f"""📋 REPORT SUBMITTED:
👤 Reporter: {reporter.get('first_name')} | ID: {uid}
👤 Reported: {reported.get('first_name')} | ID: {reported_id}
📌 Reason: {reason}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        bot.send_message(ADMIN_ID, admin_msg)
        
        messages = get_chat_messages(uid, reported_id)
        if messages:
            try:
                for msg_type, msg_id, chat_id in messages[:20]:
                    bot.forward_message(ADMIN_ID, chat_id, msg_id)
            except:
                pass
    except:
        pass
    
    bot.answer_callback_query(call.id, '✅ Reported')
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data == 'report_open')
def report_open_cb(call):
    uid = call.from_user.id
    if uid not in chat_history_with_time:
        bot.answer_callback_query(call.id, '❌ No one to report')
        return
    partner_id, _ = chat_history_with_time[uid]
    report_reason_pending[uid] = partner_id
    bot.answer_callback_query(call.id)
    bot.send_message(uid, '📋 Reason?', reply_markup=report_kb())

@bot.message_handler(commands=['admin'])
def admin_cmd(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, '🚫 Admin only')
        return
    
    with get_conn() as conn:
        reports = conn.execute('SELECT reporter_id, reported_id, reason, timestamp FROM reports ORDER BY timestamp DESC LIMIT 10').fetchall()
    
    if not reports:
        bot.send_message(uid, '📋 No reports')
        return
    
    text = '📋 REPORTS:\n\n'
    for reporter_id, reported_id, reason, ts in reports:
        reporter = db_user(reporter_id)
        reported = db_user(reported_id)
        r_name = reporter.get('first_name') if reporter else 'Unknown'
        rep_name = reported.get('first_name') if reported else 'Unknown'
        text += f"📌 {reason}\n👤 Reporter: {r_name} ({reporter_id})\n👤 Reported: {rep_name} ({reported_id})\n⏰ {ts}\n\n"
    
    bot.send_message(uid, text)

@bot.message_handler(commands=['adminuser'])
def admin_user(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, '🚫 Admin only')
        return
    
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(uid, '🔍 Usage: /adminuser userid')
        return
    
    try:
        target_id = int(parts[1])
    except:
        bot.send_message(uid, '❌ Invalid user ID')
        return
    
    user = db_user(target_id)
    if not user:
        bot.send_message(uid, '❌ User not found')
        return
    
    premium = '✅ YES' if is_premium(target_id) else '❌ NO'
    banned = '✅ YES' if is_banned(target_id) else '❌ NO'
    
    text = f"""👤 USER PROFILE:
🆔 ID: {target_id}
📝 Name: {user.get('first_name')}
📱 Username: {user.get('username')}
👥 Gender: {user.get('gender')}
🎂 Age: {user.get('age')}
🌍 Country: {user.get('country_flag')} {user.get('country')}
💬 Messages: {user.get('messages_sent')}
✅ Media Approved: {user.get('media_approved')}
❌ Media Rejected: {user.get('media_rejected')}
👫 Referred: {user.get('referral_count')}/3
💎 Premium: {premium}
🚫 Banned: {banned}"""
    
    bot.send_message(uid, text)

@bot.message_handler(commands=['ban'])
def ban_cmd(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, '🚫 Admin only')
        return
    
    parts = msg.text.split(maxsplit=3)
    if len(parts) < 2:
        bot.send_message(uid, '❌ Usage: /ban userid [hours/permanent] [reason]')
        return
    
    try:
        target_id = int(parts[1])
    except:
        bot.send_message(uid, '❌ Invalid user ID')
        return
    
    permanent = False
    hours = 24
    reason = 'Banned by admin'
    
    if len(parts) >= 3:
        if parts[2].lower() == 'permanent':
            permanent = True
        else:
            try:
                hours = int(parts[2])
            except:
                hours = 24
    
    if len(parts) >= 4:
        reason = parts[3]
    
    ban_user(target_id, hours=hours, permanent=permanent, reason=reason)
    
    try:
        if permanent:
            bot.send_message(target_id, f'🚫 PERMANENTLY BANNED. Reason: {reason}')
        else:
            bot.send_message(target_id, f'⏱️ Banned for {hours}h. Reason: {reason}')
    except:
        pass
    
    bot.send_message(uid, f'✅ User {target_id} banned')

@bot.message_handler(commands=['unban'])
def unban_cmd(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, '🚫 Admin only')
        return
    
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(uid, '❌ Usage: /unban userid')
        return
    
    try:
        target_id = int(parts[1])
    except:
        bot.send_message(uid, '❌ Invalid user ID')
        return
    
    unban_user(target_id)
    
    try:
        bot.send_message(target_id, '✅ Ban lifted!')
    except:
        pass
    
    bot.send_message(uid, f'✅ User {target_id} unbanned')

@bot.message_handler(commands=['premium'])
def premium_cmd(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, '🚫 Admin only')
        return
    
    parts = msg.text.split()
    if len(parts) < 3:
        bot.send_message(uid, '❌ Usage: /premium userid YYYY-MM-DD')
        return
    
    try:
        target_id = int(parts[1])
        until_date = parts[2]
        dt = datetime.fromisoformat(f"{until_date}T23:59:59" if len(until_date) == 10 else until_date)
    except:
        bot.send_message(uid, '❌ Invalid format')
        return
    
    with get_conn() as conn:
        conn.execute('UPDATE users SET premium_until=? WHERE user_id=?', (dt.isoformat(), target_id))
        conn.commit()
    
    try:
        bot.send_message(target_id, f'💎 Premium added until {until_date}!')
    except:
        pass
    
    bot.send_message(uid, f'✅ Premium set for {target_id} until {until_date}')

@bot.message_handler(commands=['help'])
def help_cmd(msg):
    uid = msg.from_user.id
    text = """📚 COMMANDS:
/start - Setup
/search - Random
/search_opposite - Opposite (💎)
/next - Next
/stop - Stop
/reconnect - Resume
/report - Report
/admin - Reports
/adminuser userid - View user
/ban userid - Ban user
/unban userid - Unban
/premium userid YYYY-MM-DD - Add premium
/settings - Settings
/stats - Stats
/refer - Refer"""
    bot.send_message(uid, text, reply_markup=main_kb(uid))

@bot.message_handler(commands=['settings'])
def settings_cmd(msg):
    uid = msg.from_user.id
    u = db_user(uid)
    if not u:
        bot.send_message(uid, '❌ Use /start')
        return
    text = f"""⚙️ PROFILE:
👤 {u.get('gender')} | 🎂 {u.get('age')} | 🌍 {u.get('country')}
💬 {u.get('messages_sent')}
✅ {u.get('media_approved')} ❌ {u.get('media_rejected')}"""
    bot.send_message(uid, text, reply_markup=main_kb(uid))

@bot.message_handler(commands=['stats'])
def stats_cmd(msg):
    uid = msg.from_user.id
    u = db_user(uid)
    if not u:
        bot.send_message(uid, '❌ Use /start')
        return
    premium = '✅' if is_premium(uid) else '❌'
    text = f"""📊 STATS:
👤 {u.get('gender')} | 🎂 {u.get('age')}
💬 {u.get('messages_sent')}
✅ {u.get('media_approved')} ❌ {u.get('media_rejected')}
👥 {u.get('referral_count')}/3
💎 {premium}"""
    bot.send_message(uid, text)

@bot.message_handler(commands=['refer'])
def refer_cmd(msg):
    uid = msg.from_user.id
    u = db_user(uid)
    if not u:
        bot.send_message(uid, '❌ Use /start')
        return
    remaining = PREMIUM_REFERRALS_NEEDED - u.get('referral_count', 0)
    text = f"""👥 INVITE:
Code: {u.get('referral_code')}
Progress: {u.get('referral_count')}/{PREMIUM_REFERRALS_NEEDED}
Remaining: {remaining}"""
    bot.send_message(uid, text)

@bot.message_handler(func=lambda m: m.text == '🔍 Search Random')
def btn_search(msg): search(msg)

@bot.message_handler(func=lambda m: m.text == '💎 Search Opposite' or m.text == '💎 Opposite (Premium)')
def btn_opp(msg): search_opp(msg)

@bot.message_handler(func=lambda m: m.text == '⏭️ Next')
def btn_next(msg): next_cmd(msg)

@bot.message_handler(func=lambda m: m.text == '🛑 Stop')
def btn_stop(msg): stop(msg)

@bot.message_handler(func=lambda m: m.text == '⚙️ Settings')
def btn_settings(msg): settings_cmd(msg)

@bot.message_handler(func=lambda m: m.text == '👥 Refer')
def btn_refer(msg): refer_cmd(msg)

@bot.message_handler(func=lambda m: m.text == '❓ Help')
def btn_help(msg): help_cmd(msg)

@bot.message_handler(func=lambda m: m.text == '📋 Rules')
def btn_rules(msg):
    uid = msg.from_user.id
    text = """📋 RULES:
1️⃣ Respectful
2️⃣ No adult
3️⃣ No spam/links
4️⃣ No harassment
5️⃣ Media consent

⚠️ 3 warnings = 24h ban
7 reports = auto-ban"""
    bot.send_message(uid, text, reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == '📊 Stats')
def btn_stats(msg): stats_cmd(msg)

@bot.message_handler(content_types=['text'])
def fwd_text(msg):
    uid = msg.from_user.id
    text = msg.text or ''
    if text.startswith('/'): return
    if is_banned_content(text):
        warn_user(uid, 'Vulgar words/links')
        return
    with pairs_lock:
        if uid not in active_pairs:
            return
        partner_id = active_pairs[uid]
    try:
        u = db_user(uid)
        name = u.get('first_name') if u else 'User'
        bot.send_message(partner_id, f"{name}: {text}")
        save_message(uid, partner_id, 'text', msg.message_id, msg.chat.id)
        with get_conn() as conn:
            conn.execute('UPDATE users SET messages_sent=messages_sent+1 WHERE user_id=?', (uid,))
            conn.commit()
    except: pass

@bot.message_handler(content_types=['photo', 'video', 'document', 'voice', 'audio', 'sticker', 'animation'])
def fwd_media(msg):
    uid = msg.from_user.id
    with pairs_lock:
        if uid not in active_pairs: return
        partner_id = active_pairs[uid]
    icons = {'photo': '🖼️', 'video': '🎥', 'document': '📄', 'voice': '🎤', 'audio': '🎵', 'sticker': '😊', 'animation': '🎬'}
    icon = icons.get(msg.content_type, '📎')
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('✅ Accept', callback_data=f'med_y_{uid}'), types.InlineKeyboardButton('❌ Reject', callback_data=f'med_n_{uid}'))
    token = secrets.token_hex(8)
    with media_lock:
        pending_media[token] = {'sender_id': uid, 'message': msg, 'partner_id': partner_id}
    try:
        bot.send_message(partner_id, f"Partner sent {icon}. Allow?", reply_markup=m)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith('med_'))
def media_cb(call):
    parts = call.data.split('_')
    action = parts[1]
    sender_id = int(parts[2])
    uid = call.from_user.id
    with media_lock:
        media_list = [k for k, v in pending_media.items() if v.get('sender_id') == sender_id and v.get('partner_id') == uid]
        if not media_list:
            bot.answer_callback_query(call.id, '⏰ Expired')
            return
        token = media_list[0]
        msg = pending_media[token]['message']
    try:
        if action == 'y':
            if msg.content_type == 'photo': bot.send_photo(uid, msg.photo[-1].file_id)
            elif msg.content_type == 'video': bot.send_video(uid, msg.video.file_id)
            elif msg.content_type == 'document': bot.send_document(uid, msg.document.file_id)
            elif msg.content_type == 'voice': bot.send_voice(uid, msg.voice.file_id)
            elif msg.content_type == 'audio': bot.send_audio(uid, msg.audio.file_id)
            elif msg.content_type == 'sticker': bot.send_sticker(uid, msg.sticker.file_id)
            elif msg.content_type == 'animation': bot.send_animation(uid, msg.animation.file_id)
            inc_media(sender_id, 'approved')
            bot.send_message(sender_id, '✅ Approved')
            bot.answer_callback_query(call.id, '✅')
        else:
            inc_media(sender_id, 'rejected')
            bot.send_message(sender_id, '❌ Rejected')
            bot.answer_callback_query(call.id, '❌')
        with media_lock: pending_media.pop(token, None)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except: pass

@app.route('/')
def home(): return 'GhostTalk v5.0', 200

if __name__ == '__main__':
    init_db()
    logger.info("🤖 GhostTalk v5.0 COMPLETE")
    cleanup_threads()
    bot.infinity_polling(timeout=30)
