import os
import requests
from src.logger import logger


def notify_application(job_title, company, status, url):
    """
    Sends a notification about a job application status.
    """
    message = f"Job {status}\n\nTitle: {job_title}\nCompany: {company}\nURL: {url}"
    _send_telegram(message)
    _send_discord(message)


def notify_intervention(job_title, company, url):
    """
    Sends a notification that manual intervention is required.
    """
    message = f"Manual Intervention Required\n\nTitle: {job_title}\nCompany: {company}\nURL: {url}"
    _send_telegram(message)
    _send_discord(message)


def notify_new_jobs(jobs_list):
    """
    Sends a summary of newly found jobs, categorized by region.
    """
    if not jobs_list:
        return

    # Categorize
    us_jobs = [j for j in jobs_list if "united states" in (j.get("location") or "").lower()]
    india_jobs = [j for j in jobs_list if "india" in (j.get("location") or "").lower()]
    other_jobs = [j for j in jobs_list if j not in us_jobs and j not in india_jobs]

    def send_region_summary(region_name, jobs):
        if not jobs: return
        
        header = f"🌍 *New Jobs in {region_name}* ({len(jobs)})\n"
        header += "═" * 20 + "\n\n"
        
        current_message = header
        for i, job in enumerate(jobs):
            score_text = f"🔥 *Match: {int(job['match_score']*100)}%*" if job.get('match_score') else ""
            job_entry = f"{i + 1}. {job['title']} @ {job['company']}\n{score_text}\n📍 {job.get('location', 'N/A')}\n🔗 [View Job]({job['url']})\n\n"

            if len(current_message) + len(job_entry) > 3500:
                _send_telegram(current_message)
                current_message = f"🌍 *{region_name} (Cont...)*\n\n"
            
            current_message += job_entry
        
        if current_message:
            _send_telegram(current_message)

    # Send separate messages per region
    send_region_summary("United States", us_jobs)
    send_region_summary("India", india_jobs)
    send_region_summary("Other Regions", other_jobs)


def _send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
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
        "content": message,
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
