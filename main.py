import os
import json
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from src.database import SessionLocal, init_db
from src.models import Job, JobStatus, RunLog
from src.scrapers import fetch_all_jobs
from src.local_scrapers import fetch_local_jobs_async
from src.evaluator import evaluate_match, tailor_resume, batch_evaluate_matches
from src.resume_manager import get_base_resumes, read_resume, save_tailored_resume
from src.notifications import notify_application, notify_intervention, notify_new_jobs
from src.logger import logger
from playwright.async_api import async_playwright

load_dotenv()

async def run_automation():
    init_db()
    db = SessionLocal()
    run_log = RunLog(status="running", start_time=datetime.utcnow())
    db.add(run_log)
    db.commit()

    try:
        # 1. Load Config
        with open("config/search.json", "r") as f:
            config = json.load(f)

        keywords = config.get("keywords", [])
        locations = config.get("locations", [])
        max_items = config.get("max_items_per_search", 150)
        days_back = config.get("days_since_posted", 7)

        # 2. Fetch Jobs
        # Smart Search: Automatically set days_back based on last successful run
        last_run = db.query(RunLog).filter(RunLog.status == "success").order_by(RunLog.end_time.desc()).first()
        if last_run and last_run.end_time:
            delta = datetime.utcnow() - last_run.end_time
            # Default to at least 1 day, up to 7 days
            smart_days = max(1, min(7, delta.days + 1))
            logger.info(f"Smart Search: Last successful run was {delta.days} days ago. Setting search window to {smart_days} days.")
            days_back = smart_days
        else:
            logger.info(f"No previous successful run found. Using config default: {days_back} days.")

        logger.info(f"Starting job scrape for last {days_back} days...")
        
        # We'll use local scrapers primarily for this test phase
        try:
            raw_jobs = await fetch_local_jobs_async(keywords, locations, days_back)
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            raw_jobs = []

        run_log.jobs_found = len(raw_jobs)
        
        newly_added_jobs = []
        for raw_job in raw_jobs:
            try:
                # Check if exists
                existing = db.query(Job).filter(Job.job_id_external == raw_job["job_id_external"]).first()
                if not existing:
                    job = Job(**raw_job)
                    db.add(job)
                    db.flush()
                    newly_added_jobs.append(raw_job)
            except Exception as e:
                logger.warning(f"Failed to ingest job {raw_job.get('job_id_external')}: {e}")
                db.rollback()
                continue
        
        db.commit()
        logger.info(f"Scrape complete. Found {len(raw_jobs)} jobs, {len(newly_added_jobs)} were newly added.")

        # 3. Direct Notifications (AI Paused as requested)
        if newly_added_jobs:
            logger.info(f"Sending Telegram summary for {len(newly_added_jobs)} new jobs...")
            notify_new_jobs(newly_added_jobs)
        else:
            logger.info("No new jobs to notify.")

        # 4. Success Log
        run_log.status = "success"
        run_log.end_time = datetime.utcnow()
        db.commit()

        # 5. Auto-Commit to Git (only if not in CI)
        if not os.getenv("GITHUB_ACTIONS"):
            auto_commit()

    except Exception as e:
        logger.error(f"Automation failed: {e}")
        run_log.status = "failed"
        run_log.error_message = str(e)
        db.commit()
    finally:
        db.close()

def auto_commit():
    """Local-only helper to commit data updates back to git."""
    try:
        # Check if there are changes
        status = subprocess.check_output(["git", "status", "--porcelain"])
        if status:
            subprocess.run(["git", "add", "data/jobs.db", "resumes/tailored/", "logs/"])
            subprocess.run(["git", "commit", "-m", f"Auto-run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            logger.info("Committed successfully.")
        else:
            logger.info("No changes to commit.")
    except Exception as e:
        logger.error(f"Git auto-commit failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_automation())
