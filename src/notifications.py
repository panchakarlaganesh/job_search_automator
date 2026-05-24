import os
import requests
from dotenv import load_dotenv
from .logger import logger

load_dotenv()

def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

def send_discord_message(message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    
    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error sending Discord message: {e}")

def notify_application(job_title, company, status, url):
    msg = f"🚀 *Job Application Update*\n\n*Role:* {job_title}\n*Company:* {company}\n*Status:* {status}\n*URL:* {url}"
    send_telegram_message(msg)
    send_discord_message(msg)

def notify_intervention(job_title, company, url):
    msg = f"⚠️ *Manual Intervention Required*\n\n*Role:* {job_title}\n*Company:* {company}\n*Action:* Please check the UI to complete this application.\n*URL:* {url}"
    send_telegram_message(msg)
    send_discord_message(msg)
