"""
Force re-score all jobs in the DB that have real descriptions (>200 chars)
but have not been scored yet (match_score is NULL or 0).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from src.database import SessionLocal, init_db
from src.models import Job
from src.evaluator import evaluate_match
from src.resume_manager import read_resume
from src.logger import logger

def run_rescore():
    init_db()
    db = SessionLocal()

    base_content = read_resume("resumes/base_resume.md")

    # Only rescore jobs posted within the last 7 days to avoid burning API quota on stale listings
    from datetime import timezone, timedelta
    days_back = 7
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    unscored = db.query(Job).filter(
        Job.description.isnot(None),
        Job.description != "",
        Job.posted_date >= cutoff,
    ).filter(
        (Job.match_score == None) | (Job.match_score == 0.0)
    ).all()

    unscored = [j for j in unscored if len(j.description or "") > 200]

    print(f"\nFound {len(unscored)} unscored jobs with real descriptions. Scoring now...\n")

    scored = 0
    matched = 0
    THRESHOLD = 0.40

    for i, job in enumerate(unscored):
        try:
            print(f"[{i+1}/{len(unscored)}] Scoring: {job.title} @ {job.company}...")
            analysis = evaluate_match(job.description, base_content)
            if analysis:
                score = float(analysis.get("score", 0.0))
                job.match_score = score
                job.match_reason = analysis.get("reason", "")
                job.tech_stack = json.dumps(analysis.get("breakdown", {}))
                db.commit()
                scored += 1
                flag = "✅ MATCH" if score >= THRESHOLD else "  skip"
                if score >= THRESHOLD:
                    matched += 1
                print(f"  {flag} [{score:.0%}] — {analysis.get('reason', '')[:80]}")
        except Exception as e:
            logger.error(f"Failed scoring {job.job_id_external}: {e}")
            db.rollback()
            continue

    print(f"\n{'='*60}")
    print(f"Re-score complete: {scored}/{len(unscored)} scored, {matched} matched >= {THRESHOLD:.0%}")

    # Print final top matches
    print(f"\n--- ALL JOBS MATCHING >= {THRESHOLD:.0%} ---")
    from src.models import Job as J
    top = db.query(J).filter(J.match_score >= THRESHOLD).order_by(J.match_score.desc()).all()
    print(f"Total: {len(top)} jobs\n")
    for j in top:
        print(f"  [{j.match_score:.0%}] {j.title} @ {j.company} ({j.location})")
        print(f"         {j.url}")
    db.close()

if __name__ == "__main__":
    run_rescore()
