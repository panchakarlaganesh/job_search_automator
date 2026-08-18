import sys
import asyncio
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 so Windows cp1252 doesn't crash on emoji from browser-use
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from src.database import SessionLocal, init_db
from src.models import Job, JobStatus
from src.applier import BrowserUseApplier
from src.resume_manager import read_resume
from src.logger import logger

MATCH_THRESHOLD = 0.85
LOCATION_FILTER = "india"   # only India jobs
RESUME_PATH = "resumes/base_resume.md"

async def run_apply():
    init_db()
    db = SessionLocal()

    base_resume = read_resume(RESUME_PATH)

    # Fetch top-tier India jobs not yet applied to
    candidates = db.query(Job).filter(
        Job.match_score >= MATCH_THRESHOLD,
        Job.location.ilike(f"%{LOCATION_FILTER}%"),
        Job.status.notin_([JobStatus.APPLIED, JobStatus.REJECTED])
    ).order_by(Job.match_score.desc()).all()

    if not candidates:
        print(f"No unapplied India jobs >= {MATCH_THRESHOLD:.0%} found.")
        db.close()
        return

    print(f"\nFound {len(candidates)} jobs to apply to:\n")
    for i, job in enumerate(candidates):
        print(f"  [{i+1}] [{job.match_score:.0%}] {job.title} @ {job.company}")
        print(f"        {job.url}\n")

    print("Starting applications... (browser will open for each job)\n")
    print("=" * 60)

    applier = BrowserUseApplier()
    applied = 0
    failed = 0
    expired = 0

    for i, job in enumerate(candidates):
        print(f"\n[{i+1}/{len(candidates)}] Applying to: {job.title} @ {job.company}")
        print(f"  Match: {job.match_score:.0%} | URL: {job.url}")

        try:
            result = await applier.apply(job, RESUME_PATH, base_resume)
            if result == "EXPIRED":
                job.status = JobStatus.REJECTED
                db.commit()
                expired += 1
                print(f"  EXPIRED - listing no longer active, skipping.")
            elif result:
                job.status = JobStatus.APPLIED
                db.commit()
                applied += 1
                print(f"  SUCCESS - Application submitted!")
            else:
                failed += 1
                print(f"  FAILED - Agent returned no result")
        except Exception as e:
            failed += 1
            logger.error(f"  ERROR applying to {job.company}: {e}")
            print(f"  ERROR: {e}")

        # Pause between applications to avoid rate limiting
        if i < len(candidates) - 1:
            print(f"  Waiting 10s before next application...")
            await asyncio.sleep(10)

    print(f"\n{'='*60}")
    print(f"Done! Applied: {applied} | Expired: {expired} | Failed: {failed} | Total: {len(candidates)}")
    db.close()

if __name__ == "__main__":
    asyncio.run(run_apply())
