"""
Telegram Anonymous Chat Bot
Features:
- Anonymous chat with gender-based match (/search_random, /search_male, /search_female)
- Users set gender via /settings
- Chat tips and safe chat guidelines at match start
- /next and /stop commands for chat control
- Media sharing (images, stickers, videos, voice, docs, GIFs) only with recipient acceptance
- Admin commands: /ban, /unban, /status (admin ID via ADMIN_ID env variable)
- Improved matching logic to avoid repeat matches
- SQLite for persistence, Flask server for webhook (port 10000 for Render)
- Keep-alive ping to admin every 10 min
Requires: pyTelegramBotAPI, Flask
"""
import os
import logging
import sqlite3
import time
import threading
from flask import Flask, request, abort
import telebot
from telebot import types

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # e.g. https://yourapp.onrender.com
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID environment variable not set")
ADMIN_ID = int(ADMIN_ID)
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable not set")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    gender TEXT,
    banned INTEGER DEFAULT 0,
    partner_id INTEGER,
    last_partner_id INTEGER,
    last_search_pref TEXT,
    media_accepted INTEGER DEFAULT 0
)""")
conn.commit()

def get_user(uid):
    """Retrieve user from DB, create if not exists."""
    user = cursor.execute("SELECT id, gender, banned, partner_id, last_partner_id, last_search_pref, media_accepted FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        cursor.execute("INSERT INTO users (id, banned) VALUES (?,0)", (uid,))
        conn.commit()
        return (uid, None, 0, None, None, None, 0)
    return user

def set_user_field(uid, field, value):
    """Set a single field for user."""
    cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, uid))
    conn.commit()

def is_banned(uid):
    user = get_user(uid)
    return bool(user[2])

def get_partner(uid):
    user = get_user(uid)
    return user[3]  # partner_id

def set_partner(uid, partner_id):
    set_user_field(uid, 'partner_id', partner_id)

def set_last_partner(uid, partner_id):
    set_user_field(uid, 'last_partner_id', partner_id)

def set_search_pref(uid, pref):
    set_user_field(uid, 'last_search_pref', pref)

def get_last_partner(uid):
    user = get_user(uid)
    return user[4]

def get_last_search_pref(uid):
    user = get_user(uid)
    return user[5]

def set_gender(uid, gender):
    set_user_field(uid, 'gender', gender)

def get_gender(uid):
    user = get_user(uid)
    return user[1]

def set_media_accepted(uid, accepted):
    set_user_field(uid, 'media_accepted', 1 if accepted else 0)

def get_media_accepted(uid):
    user = get_user(uid)
    return bool(user[6])

def ban_user(uid):
    set_user_field(uid, 'banned', 1)
    # Also end chat if in chat
    partner = get_partner(uid)
    if partner:
        end_chat(uid)

def unban_user(uid):
    set_user_field(uid, 'banned', 0)

def active_chat_count():
    count = cursor.execute("SELECT COUNT(*) FROM users WHERE partner_id IS NOT NULL").fetchone()[0]
    return count // 2

def banned_count():
    count = cursor.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
    return count

# Chat queue
waiting_list = []
waiting_lock = threading.Lock()

def add_to_queue(uid, pref):
    """Add user to waiting list."""
    with waiting_lock:
        if uid not in waiting_list:
            waiting_list.append(uid)
            set_search_pref(uid, pref)

def remove_from_queue(uid):
    with waiting_lock:
        if uid in waiting_list:
            waiting_list.remove(uid)

def find_match(uid, pref):
    """Find a match for user with id=uid and pref in waiting_list."""
    gender = get_gender(uid)
    last_partner = get_last_partner(uid)
    for candidate in waiting_list:
        if candidate == uid:
            continue
        if is_banned(candidate):
            continue
        cand_data = get_user(candidate)
        cand_gender = cand_data[1]
        cand_partner = cand_data[3]
        cand_last_partner = cand_data[4]
        cand_pref = cand_data[5]
        # skip if any in chat
        if cand_partner:
            continue
        # skip if they recently chatted
        if cand_last_partner == uid or last_partner == candidate:
            continue
        # Check preferences matching:
        # User wants pref, candidate gender must match or pref random
        if pref != 'random' and cand_gender != pref:
            continue
        # Candidate wants target, user's gender must match or candidate pref random
        if cand_pref and cand_pref != 'random' and gender != cand_pref:
            continue
        # Candidate must have set gender
        if not cand_gender:
            continue
        # If all good, return candidate
        return candidate
    return None

def start_chat(u1, u2):
    """Pair two users into chat."""
    # Set partners
    set_partner(u1, u2)
    set_partner(u2, u1)
    # Reset media acceptance for both
    set_media_accepted(u1, False)
    set_media_accepted(u2, False)
    # Remove both from queue if present
    remove_from_queue(u1)
    remove_from_queue(u2)
    logger.info(f"Matched users {u1} and {u2}")
    # Send tips and keyboard
    tips = ("You have been matched! 🎉\\n\\n"
            "Chat Tips:\\n"
            "• Be respectful and kind.\\n"
            "• Keep topics light: hobbies, movies, music, etc.\\n"
            "• Avoid personal information and stay safe.\\n\\n"
            "To end chat, use /stop. To find a new partner, use /next.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(types.KeyboardButton('/next'), types.KeyboardButton('/stop'))
    try:
        bot.send_message(u1, tips, reply_markup=markup)
        bot.send_message(u2, tips, reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending match message: {e}")

def end_chat(uid):
    """End chat for user, notify partner."""
    user = get_user(uid)
    partner = user[3]
    if not partner:
        # Not in chat, just remove from queue if needed
        remove_from_queue(uid)
        return
    # Notify both
    try:
        bot.send_message(uid, "Chat ended.", reply_markup=types.ReplyKeyboardRemove())
    except:
        pass
    try:
        bot.send_message(partner, "Chat ended. Your partner has left.", reply_markup=types.ReplyKeyboardRemove())
    except:
        pass
    # Update DB for both
    set_last_partner(uid, partner)
    set_last_partner(partner, uid)
    set_partner(uid, None)
    set_partner(partner, None)
    logger.info(f"Chat between {uid} and {partner} ended")

# Flask setup
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Handlers
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    get_user(uid)  # ensure in DB
    if is_banned(uid):
        bot.reply_to(message, "You are banned from this bot.")
        return
    welcome = ("Welcome to Anonymous Chat Bot!\\n"
               "Please set your gender using /settings before searching for a partner.")
    bot.send_message(uid, welcome)

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    # Inline keyboard for gender
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Male", callback_data="set_gender_male"),
               types.InlineKeyboardButton("Female", callback_data="set_gender_female"))
    bot.send_message(uid, "Please select your gender:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("set_gender_"))
def callback_set_gender(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "You are banned.")
        return
    if call.data == "set_gender_male":
        set_gender(uid, "male")
        bot.answer_callback_query(call.id, "Gender set to male.")
        bot.send_message(uid, "Your gender has been set to Male.")
    elif call.data == "set_gender_female":
        set_gender(uid, "female")
        bot.answer_callback_query(call.id, "Gender set to female.")
        bot.send_message(uid, "Your gender has been set to Female.")
    else:
        bot.answer_callback_query(call.id, "Invalid selection.")

@bot.message_handler(commands=['search_random', 'search_male', 'search_female'])
def cmd_search(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    if not user[1]:
        bot.send_message(uid, "Please set your gender first with /settings.")
        return
    if user[3]:
        bot.send_message(uid, "You are already in a chat. Use /stop to end current chat.")
        return
    text = message.text.lower()
    pref = None
    if text == "/search_random":
        pref = 'random'
    elif text == "/search_male":
        pref = 'male'
    elif text == "/search_female":
        pref = 'female'
    else:
        return
    # Add to queue
    add_to_queue(uid, pref)
    bot.send_message(uid, f"Searching for a {pref} partner..." if pref != 'random' else "Searching for a partner...")
    # Try to find match
    with waiting_lock:
        match_id = find_match(uid, pref)
        if match_id:
            start_chat(uid, match_id)

@bot.message_handler(commands=['next'])
def cmd_next(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    partner = user[3]
    if not partner:
        bot.send_message(uid, "No active chat to skip.")
        return
    pref = user[5] or 'random'
    end_chat(uid)
    bot.send_message(uid, "Looking for a new partner...")
    add_to_queue(uid, pref)
    with waiting_lock:
        match_id = find_match(uid, pref)
        if match_id:
            start_chat(uid, match_id)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    user = get_user(uid)
    partner = user[3]
    if partner:
        end_chat(uid)
    else:
        remove_from_queue(uid)
        bot.send_message(uid, "Stopped searching for a partner.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['ban'])
def cmd_ban(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /ban <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.send_message(uid, "Invalid user ID.")
        return
    ban_user(target)
    bot.send_message(uid, f"User {target} has been banned.")
    try:
        bot.send_message(target, "You have been banned by the admin.")
    except:
        pass

@bot.message_handler(commands=['unban'])
def cmd_unban(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(uid, "Usage: /unban <user_id>")
        return
    try:
        target = int(parts[1])
    except:
        bot.send_message(uid, "Invalid user ID.")
        return
    unban_user(target)
    bot.send_message(uid, f"User {target} has been unbanned.")
    try:
        bot.send_message(target, "You have been unbanned.")
    except:
        pass

@bot.message_handler(commands=['status'])
def cmd_status(message):
    uid = message.from_user.id
    if uid != ADMIN_ID:
        return
    waiting_count = len(waiting_list)
    active = active_chat_count()
    banned = banned_count()
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    status_msg = (f"Users waiting: {waiting_count}\\n"
                  f"Active chats: {active}\\n"
                  f"Banned users: {banned}\\n"
                  f"Total users: {total_users}")
    bot.send_message(uid, status_msg)

# Media handling
pending_media = {}
pending_id_counter = 1
pending_lock = threading.Lock()

@bot.message_handler(content_types=['photo', 'video', 'voice', 'document', 'sticker', 'animation', 'audio'])
def handle_media(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    partner = get_partner(uid)
    if not partner:
        bot.send_message(uid, "You are not in a chat. Start a chat first.")
        return
    if get_media_accepted(partner):
        # Partner has already accepted, forward directly
        forward_media(message, partner)
        return
    # Ask for acceptance from partner
    media_type = message.content_type
    file_id = None
    caption = message.caption if hasattr(message, 'caption') else None
    if media_type == 'photo':
        file_id = message.photo[-1].file_id
    elif media_type == 'video':
        file_id = message.video.file_id
    elif media_type == 'voice':
        file_id = message.voice.file_id
    elif media_type == 'document':
        file_id = message.document.file_id
    elif media_type == 'sticker':
        file_id = message.sticker.file_id
    elif media_type == 'animation':
        file_id = message.animation.file_id
    elif media_type == 'audio':
        file_id = message.audio.file_id
    else:
        bot.send_message(uid, "Unsupported media type.")
        return
    global pending_id_counter
    with pending_lock:
        pid = pending_id_counter
        pending_id_counter += 1
        pending_media[pid] = {'from': uid, 'to': partner, 'file_id': file_id,
                              'type': media_type, 'caption': caption}
    try:
        # Send prompt to partner
        markup = types.InlineKeyboardMarkup()
        accept_btn = types.InlineKeyboardButton("Accept 📤", callback_data=f"accept_{pid}")
        decline_btn = types.InlineKeyboardButton("Decline 🚫", callback_data=f"decline_{pid}")
        markup.row(accept_btn, decline_btn)
        bot.send_message(partner, f"Your partner wants to send a {media_type}. Accept?", reply_markup=markup)
        bot.send_message(uid, f"Waiting for partner to accept the {media_type}...")
    except Exception as e:
        logger.error(f"Error in media acceptance prompt: {e}")

@bot.callback_query_handler(func=lambda call: call.data and (call.data.startswith("accept_") or call.data.startswith("decline_")))
def callback_media(call):
    parts = call.data.split('_')
    action = parts[0]
    pid = int(parts[1])
    uid = call.from_user.id
    with pending_lock:
        pending = pending_media.get(pid)
        if not pending:
            bot.answer_callback_query(call.id, "No pending request.")
            return
        if uid != pending['to']:
            bot.answer_callback_query(call.id, "This request is not for you.")
            return
        if action == 'accept':
            forward_media_specific(pending, pending['to'])
            set_media_accepted(pending['to'], True)
            bot.answer_callback_query(call.id, "Content sent.")
            try:
                bot.send_message(pending['from'], "Your content was accepted and sent.")
            except:
                pass
        else:
            bot.answer_callback_query(call.id, "Content declined.")
            try:
                bot.send_message(pending['from'], "Your content was declined by the partner.")
            except:
                pass
        # Remove pending
        pending_media.pop(pid, None)

def forward_media(message, to_id):
    """Forward media message to to_id."""
    media_type = message.content_type
    caption = message.caption if hasattr(message, 'caption') else None
    try:
        if media_type == 'photo':
            bot.send_photo(to_id, message.photo[-1].file_id, caption=caption)
        elif media_type == 'video':
            bot.send_video(to_id, message.video.file_id, caption=caption)
        elif media_type == 'voice':
            bot.send_voice(to_id, message.voice.file_id)
        elif media_type == 'document':
            bot.send_document(to_id, message.document.file_id, caption=caption)
        elif media_type == 'sticker':
            bot.send_sticker(to_id, message.sticker.file_id)
        elif media_type == 'animation':
            bot.send_animation(to_id, message.animation.file_id, caption=caption)
        elif media_type == 'audio':
            bot.send_audio(to_id, message.audio.file_id, caption=caption)
    except Exception as e:
        logger.error(f"Error forwarding media: {e}")

def forward_media_specific(media, to_id):
    """Forward pending media after acceptance."""
    media_type = media['type']
    file_id = media['file_id']
    caption = media.get('caption')
    try:
        if media_type == 'photo':
            bot.send_photo(to_id, file_id, caption=caption)
        elif media_type == 'video':
            bot.send_video(to_id, file_id, caption=caption)
        elif media_type == 'voice':
            bot.send_voice(to_id, file_id)
        elif media_type == 'document':
            bot.send_document(to_id, file_id, caption=caption)
        elif media_type == 'sticker':
            bot.send_sticker(to_id, file_id)
        elif media_type == 'animation':
            bot.send_animation(to_id, file_id, caption=caption)
        elif media_type == 'audio':
            bot.send_audio(to_id, file_id, caption=caption)
    except Exception as e:
        logger.error(f"Error forwarding accepted media: {e}")

@bot.message_handler(func=lambda m: m.content_type == 'text')
def handle_text(message):
    uid = message.from_user.id
    if is_banned(uid):
        return
    text = message.text
    if text.startswith('/'):
        # Unknown command or handled above
        return
    partner = get_partner(uid)
    if not partner:
        bot.send_message(uid, "You are not in a chat. Use /search to find a partner.")
        return
    try:
        bot.send_message(partner, text)
    except Exception as e:
        logger.error(f"Error forwarding text: {e}")

def ping_admin():
    """Keep-alive ping to admin every 10 minutes."""
    while True:
        time.sleep(600)  # 10 minutes
        try:
            bot.send_message(ADMIN_ID, "🔄 Bot is alive")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {e}")

# Start keep-alive thread
ping_thread = threading.Thread(target=ping_admin, daemon=True)
ping_thread.start()

# Webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@app.route('/')
def index():
    return 'Bot is running.'

if __name__ == '__main__':
    # Set webhook
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    # Run Flask
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
