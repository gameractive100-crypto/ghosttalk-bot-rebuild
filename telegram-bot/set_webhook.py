# set_webhook.py
import os, requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
SERVICE_URL = os.getenv("SERVICE_URL")  # set on Render OR set locally before running

if not TOKEN or not SERVICE_URL:
    raise RuntimeError("TELEGRAM_TOKEN and SERVICE_URL env vars must be set")

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
resp = requests.post(url, data={"url": f"{SERVICE_URL}/webhook"})
print(resp.text)
