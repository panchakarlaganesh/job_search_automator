import os
import requests
from src.logger import logger

def notify_application(job_title, company, status, url):
    """
    Sends a notification about a job application status.
    """
    message = f"🚀 **Job {status}**\n\n**Title:** {job_title}\n**Company:** {company}\n**URL:** {url}"
    _send_telegram(message)
    _send_discord(message)

def notify_intervention(job_title, company, url):
    """
    Sends a notification that manual intervention is required.
    """
    message = f"⚠️ **Manual Intervention Required**\n\n**Title:** {job_title}\n**Company:** {company}\n**URL:** {url}"
    _send_telegram(message)
    _send_discord(message)

def _send_telegram(message):
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
        logger.error(f"Failed to send Telegram notification: {e}")

def _send_discord(message):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        return

    payload = {
        "content": message
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
