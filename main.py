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
from src.applier import get_applier
from src.notifications import notify_application, notify_intervention
from src.logger import logger

load_dotenv()

async def run_automation():
    init_db()
    db = SessionLocal()
    run_log = RunLog(status="running")
    db.add(run_log)
    db.commit()

    try:
        # 1. Load Config
        with open("config/search.json", "r") as f:
            config = json.load(f)

        keywords = config.get("keywords", [])
        locations = config.get("locations", [])
        threshold = config.get("match_threshold", 0.6)
        max_items = config.get("max_items_per_search", 150)
        days_back = config.get("days_since_posted", 3)

        # 2. Fetch Jobs
        # Smart Search: Automatically set days_back based on last run
        last_run = db.query(RunLog).filter(RunLog.status == "success").order_by(RunLog.end_time.desc()).first()
        if last_run and last_run.end_time:
            delta = datetime.utcnow() - last_run.end_time
            # Default to at least 1 day, up to 7 days
            smart_days = max(1, min(7, delta.days + 1))
            logger.info(f"Smart Search: It has been {delta.days} days since last run. Setting search window to {smart_days} days.")
            days_back = smart_days
        else:
            logger.info(f"No previous successful run found. Using config default: {days_back} days.")

        logger.info(f"Starting job scrape for last {days_back} days...")
        try:
            raw_jobs = fetch_all_jobs(keywords, locations, max_items, days_back)
        except Exception as e:
            logger.warning(f"Apify scrape failed, falling back to local scrapers: {e}")
            raw_jobs = []

        if not raw_jobs:
            logger.info(f"Fetching jobs using local Playwright scrapers (last {days_back} days)...")
            raw_jobs = await fetch_local_jobs_async(keywords, locations, days_back)
        
        run_log.jobs_found = len(raw_jobs)
        
        new_jobs_count = 0
        for raw_job in raw_jobs:
            try:
                # Source correction based on URL
                url = raw_job.get("url", "").lower()
                if "linkedin.com" in url:
                    raw_job["source"] = "linkedin"
                elif "indeed.com" in url:
                    raw_job["source"] = "indeed"
                elif "dice.com" in url:
                    raw_job["source"] = "dice"

                # Region normalization
                loc = raw_job.get("location", "").lower()
                if any(x in loc for x in ["india", "hyderabad", "bengaluru", "bangalore", "pune", "mumbai"]):
                    raw_job["location"] = "India"
                elif any(x in loc for x in ["united states", "usa", "us", "remote"]):
                    if "india" not in loc: # Avoid mismatch for 'Remote India'
                        raw_job["location"] = "United States"
                
                # Check if exists
                existing = db.query(Job).filter(Job.job_id_external == raw_job["job_id_external"]).first()
                if not existing:
                    job = Job(**raw_job)
                    db.add(job)
                    db.flush() # Flush to catch integrity errors early
                    new_jobs_count += 1
            except Exception as e:
                logger.warning(f"Failed to ingest job {raw_job.get('job_id_external')}: {e}")
                db.rollback() # Rollback the current failed job insert
                continue
        
        db.commit()
        logger.info(f"Scrape complete. Found {len(raw_jobs)} jobs, {new_jobs_count} were newly added.")

        # 3. Match & Tailor
        base_resumes = get_base_resumes()
        if not base_resumes:
            logger.warning("No base resumes found in resumes/ directory.")
            return
        
        base_resume_path = os.path.join("resumes", base_resumes[0])
        base_resume_content = read_resume(base_resume_path)

        jobs_to_process = db.query(Job).filter(Job.status == JobStatus.NEW).all()
        
        # Batch evaluation (5 jobs at a time)
        batch_size = 5
        for i in range(0, len(jobs_to_process), batch_size):
            batch = jobs_to_process[i:i + batch_size]
            batch_data = [{'id': j.id, 'title': j.title, 'description': j.description} for j in batch]
            
            logger.info(f"Batch evaluating {len(batch)} jobs...")
            results = batch_evaluate_matches(batch_data, base_resume_content)
            
            # Map results back to jobs
            results_map = {r['id']: r for r in results if 'id' in r}
            
            for job in batch:
                res = results_map.get(job.id)
                if res:
                    job.match_score = res.get('score', 0.0)
                    job.match_reason = res.get('reason', "")
                    
                    if job.match_score >= threshold:
                        job.status = JobStatus.REVIEW
                        logger.info(f"Match found for {job.title} ({job.match_score})! Tailoring resume...")
                        tailored_content = tailor_resume(job.description, base_resume_content)
                        pdf_path = save_tailored_resume(tailored_content, job.id)
                        job.tailored_resume_path = pdf_path
                    else:
                        job.status = JobStatus.REJECTED
                else:
                    logger.warning(f"No evaluation result for job {job.id}")
                
                db.commit()

        # 4. Auto-Apply (If enabled in .env)
        if os.getenv("AUTO_APPLY_ENABLED") == "true":
            jobs_to_apply = db.query(Job).filter(Job.status == JobStatus.REVIEW).all()
            for job in jobs_to_apply:
                applier = get_applier(job.url)
                if applier:
                    db.commit()
                    success = await applier.apply(job, job.tailored_resume_path, base_resume_content)
                    if success:
                        job.status = JobStatus.APPLIED
                        run_log.jobs_applied += 1
                        notify_application(job.title, job.company, "Applied", job.url)
                    else:
                        job.status = JobStatus.HELP
                        notify_intervention(job.title, job.company, job.url)
                else:
                    logger.info(f"No specific applier for {job.url}, marking for manual intervention.")
                    job.status = JobStatus.HELP
                    notify_intervention(job.title, job.company, job.url)
                db.commit()

        run_log.status = "success"
    except Exception as e:
        logger.error(f"Run failed: {e}")
        run_log.status = "failed"
        run_log.error_message = str(e)
    finally:
        run_log.end_time = datetime.utcnow()
        db.commit()
        db.close()
        
        # 5. Auto-Commit to Git
        auto_commit()

def auto_commit():
    try:
        logger.info("Auto-committing changes to Git...")
        subprocess.run(["git", "add", "."], check=True)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if status.stdout.strip():
            msg = f"Auto-run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", msg], check=True)
            # subprocess.run(["git", "push"], check=True) # Uncomment if remote is set
            logger.info("Committed successfully.")
        else:
            logger.info("No changes to commit.")
    except Exception as e:
        logger.error(f"Git auto-commit failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_automation())
