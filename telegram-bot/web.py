# web.py
import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable not set")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Register your handlers here ---
# Option A (recommended): refactor your existing handlers into a function
#    in remake_bot.py like: def register(bot): ... (that registers handlers)
# Then uncomment the import below:
#
# from remake_bot import register as register_handlers
# register_handlers(bot)
#
# Option B: If you don't refactor now, a tiny test handler is below so you can verify deployment.

@bot.message_handler(commands=["start", "help"])
def send_welcome(msg):
    bot.reply_to(msg, "Bot deployed on Render via webhook!")

# -------------------------------------------------------

@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "", 200

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
