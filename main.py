import os
import json
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from src.database import SessionLocal, init_db
from src.models import Job, JobStatus, RunLog
from src.scrapers import fetch_all_jobs, fetch_naukri_jobs
from src.local_scrapers import fetch_local_jobs_async
from src.evaluator import evaluate_match, tailor_resume
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
        
        try:
            raw_jobs = []
            apify_token = os.getenv("APIFY_API_TOKEN") or os.getenv("APIFY_TOKEN")
            
            # 1. Fetch via Apify first (to secure real descriptions)
            if apify_token:
                logger.info("Fetching LinkedIn jobs via Apify (returns full descriptions)...")
                apify_jobs = await asyncio.to_thread(fetch_all_jobs, keywords, locations, max_items, days_back)
                raw_jobs.extend(apify_jobs)
                logger.info(f"Apify returned {len(apify_jobs)} jobs.")
                
                # Fetch Naukri jobs
                logger.info("Fetching Naukri jobs via Apify...")
                naukri_jobs = await asyncio.to_thread(fetch_naukri_jobs, keywords, locations, max_items)
                raw_jobs.extend(naukri_jobs)
                logger.info(f"Naukri returned {len(naukri_jobs)} jobs.")
            
            # 2. Fetch via local scrapers (to maximize coverage of job titles and URLs)
            logger.info("Running local Playwright scrapers...")
            local_jobs = await fetch_local_jobs_async(keywords, locations, days_back, max_items)
            raw_jobs.extend(local_jobs)
            logger.info(f"Local scrapers returned {len(local_jobs)} jobs.")
                
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
                else:
                    # If job exists but has a placeholder/stub description, and we just fetched a real description, update it!
                    if (not existing.description or len(existing.description) < 200) and (raw_job.get("description") and len(raw_job["description"]) > 200):
                        logger.info(f"Enriching description for existing job: {existing.title} @ {existing.company}")
                        existing.description = raw_job["description"]
                        db.flush()
                        # Also add to newly_added_jobs so it gets scored in the next step
                        newly_added_jobs.append(raw_job)
            except Exception as e:
                logger.warning(f"Failed to ingest job {raw_job.get('job_id_external')}: {e}")
                db.rollback()
                continue
        
        db.commit()
        logger.info(f"Scrape complete. Found {len(raw_jobs)} jobs, {len(newly_added_jobs)} were newly added or enriched.")

        # 2b. Open-Jobs Importer
        try:
            logger.info("Running open-jobs importer...")
            from src.open_jobs_importer import import_open_jobs
            open_jobs = await import_open_jobs()
            if open_jobs:
                newly_added_jobs.extend(open_jobs)
                logger.info(f"Open-jobs importer added {len(open_jobs)} new jobs.")
        except Exception as e:
            logger.error(f"Open-jobs importer failed: {e}")

        # 3. Automatic Scoring (Skip Tailoring during batch to prevent timeouts)
        if newly_added_jobs:
            # Filter to only score jobs with real descriptions (not placeholders)
            scoreable_jobs = [j for j in newly_added_jobs if len(j.get("description", "") or "") > 200]
            skipped = len(newly_added_jobs) - len(scoreable_jobs)
            if skipped:
                logger.info(f"Skipping {skipped} jobs with placeholder/stub descriptions (< 200 chars).")
            
            logger.info(f"Processing analysis for {len(scoreable_jobs)} jobs with real descriptions...")
            base_content = read_resume("resumes/base_resume.md")
            
            for i, job_data in enumerate(scoreable_jobs):
                try:
                    job_obj = db.query(Job).filter(Job.job_id_external == job_data["job_id_external"]).first()
                    if not job_obj: continue

                    if job_obj.match_score is not None and job_obj.match_score > 0.0:
                        logger.info(f"[{i+1}/{len(scoreable_jobs)}] Skipping scoring for {job_obj.company} (already scored: {job_obj.match_score})")
                        continue

                    logger.info(f"[{i+1}/{len(scoreable_jobs)}] Analyzing for {job_obj.company}...")
                    
                    # A. Calculate Match Score
                    analysis = evaluate_match(job_obj.description, base_content)
                    if analysis:
                        job_obj.match_score = analysis.get("score", 0.0)
                        job_obj.match_reason = analysis.get("reason", "")
                        job_obj.tech_stack = json.dumps(analysis.get("breakdown", {}))
                    
                    
                    db.commit()
                    
                except Exception as e:
                    logger.error(f"Failed to process job {job_data.get('job_id_external')}: {e}")
                    db.rollback()
                    continue

        # 4. Direct Notifications
        if newly_added_jobs:
            # Filter by match score threshold (default to 10%)
            try:
                threshold = float(os.getenv("CHECK_MATCH_THRESHOLD", "0.10"))
            except ValueError:
                threshold = 0.10
                
            high_match_jobs = []
            for raw_job in newly_added_jobs:
                # Need to find the DB object to get the calculated score
                job_obj = db.query(Job).filter(Job.job_id_external == raw_job["job_id_external"]).first()
                if job_obj and (job_obj.match_score or 0.0) >= threshold:
                    # Update raw_job with score for notification formatting
                    raw_job['match_score'] = job_obj.match_score
                    high_match_jobs.append(raw_job)

            if high_match_jobs:
                logger.info(f"Sending Telegram summary for {len(high_match_jobs)} high-match jobs (>{int(threshold*100)}%)...")
                notify_new_jobs(high_match_jobs)
            else:
                logger.info(f"No high-match jobs (>{int(threshold*100)}%) to notify.")
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
            subprocess.run(["git", "add", "data/jobs.db", "resumes/tailored/"])
            subprocess.run(["git", "commit", "-m", f"Auto-run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            logger.info("Committed successfully.")
        else:
            logger.info("No changes to commit.")
    except Exception as e:
        logger.error(f"Git auto-commit failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_automation())
