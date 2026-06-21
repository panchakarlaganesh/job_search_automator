import os
import json
import time
import urllib.request
from datetime import datetime
import pyarrow.parquet as pq
from src.database import SessionLocal, init_db
from src.models import Job, JobStatus
from src.logger import logger
from src.job_utils import stable_job_id
from src.evaluator import evaluate_match

COLS = ["id", "company", "company_name", "title", "url", "function", "sub_function", "level",
        "work_mode", "is_remote", "remote_scope", "country_code", "salary_min_k", "salary_max_k",
        "salary_currency", "visa_sponsorship", "alt_titles", "skills", "jd_markdown"]

PROMPT = """You compare two jobs for fit to a candidate's resume. Decide which job is the better fit for
THIS candidate (skills, level, domain, trajectory). Output 'A' if job A fits better, 'B' if job B does.
You must choose one even when it's close."""

def _source(path):
    if path.startswith(("http://", "https://")):
        import fsspec
        return fsspec.open(path, "rb").open()
    return path

def ask_gemini(resume, a, b, key, model="gemini-2.5-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    user_prompt = f"RESUME:\n{resume}\n\n=== JOB A: {a['title']} @ {a['company']} ===\n{a['description'][:4000]}\n\n=== JOB B: {b['title']} @ {b['company']} ===\n{b['description'][:4000]}"
    full_text = f"{PROMPT}\n\n{user_prompt}"
    body = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "winner": {
                        "type": "STRING",
                        "enum": ["A", "B"]
                    }
                },
                "required": ["winner"]
            }
        }
    }
    data = json.dumps(body).encode()
    time.sleep(4.5)  # 15 RPM rate limiting for free tier
    for i in range(5):
        try:
            req = urllib.request.Request(url, data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                res = json.load(r)
                txt = res["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(txt.strip())["winner"]
        except Exception as e:
            if i < 4:
                time.sleep(min(2 ** i, 30))
                continue
            logger.error(f"Gemini API comparison failed: {e}")
            raise

async def import_open_jobs():
    init_db()
    db = SessionLocal()
    
    try:
        # Load search config
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, "config", "search.json")
        if not os.path.exists(config_path):
            logger.error(f"No config/search.json found at {config_path}.")
            return
            
        with open(config_path, "r") as f:
            config = json.load(f)
            
        # Load resume
        resume_path = os.path.join(project_root, "resumes", "base_resume.md")
        if not os.path.exists(resume_path):
            logger.error(f"No base resume found at {resume_path}.")
            return
        with open(resume_path, "r", encoding="utf-8") as f:
            resume = f.read()

        keywords = config.get("keywords", [])
        locations = config.get("locations", [])
        
        # Parse level properly
        levels_config = config.get("level", "Senior,Staff")
        levels = levels_config.split(",") if isinstance(levels_config, str) else ["Senior", "Staff"]
        levels = [l.strip() for l in levels if l.strip()]
        
        parquet_url = "https://download.jobscream.com/open-jobs.parquet"
        logger.info(f"Connecting to remote Parquet: {parquet_url}")
        
        terms = [k.lower() for k in keywords]
        
        def country_ok(r):
            for loc in locations:
                if "united states" in loc.lower() or "us" in loc.lower():
                    if r["country_code"] == "US" or r["remote_scope"] in ("us-only", "us-canada"):
                        return True
                if "india" in loc.lower() or "in" in loc.lower():
                    if r["country_code"] == "IN":
                        return True
            return False

        def title_ok(r):
            fields = [(r["title"] or "").lower(), *[(a or "").lower() for a in (r["alt_titles"] or [])]]
            return any(t in f for f in fields for t in terms)

        def passes(r):
            if r["function"] != "engineering": return False
            if levels and r["level"] not in levels: return False
            if not country_ok(r): return False
            return title_ok(r)

        # Stream and filter
        pf = pq.ParquetFile(_source(parquet_url))
        candidates = []
        seen = set()
        logger.info("Scanning open-jobs database for candidate matches...")
        
        for b in pf.iter_batches(batch_size=20000, columns=COLS):
            cols = b.to_pydict()
            for i in range(len(cols["id"])):
                r = {k: cols[k][i] for k in COLS}
                if not passes(r): continue
                key = (str(r["company_name"] or r["company"]).lower(), str(r["title"]).lower())
                if key in seen: continue
                seen.add(key)
                candidates.append({
                    "id": r["id"],
                    "company": r["company_name"] or r["company"],
                    "title": r["title"],
                    "url": r["url"],
                    "level": r["level"],
                    "salary_min_k": r["salary_min_k"],
                    "salary_max_k": r["salary_max_k"],
                    "work_mode": r["work_mode"],
                    "description": r["jd_markdown"],
                    "skills": r["skills"]
                })
        
        logger.info(f"Found {len(candidates)} candidates in convex hull.")
        if not candidates:
            return
            
        # Top 10 scoring via Gemini
        top_candidates = candidates[:10]
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            # Fallback to loading from .env
            from dotenv import dotenv_values
            env_vals = dotenv_values(".env")
            gemini_key = env_vals.get("GEMINI_API_KEY", "").strip()
            
        if not gemini_key:
            logger.error("No GEMINI_API_KEY found.")
            return

        logger.info(f"Ranking top {len(top_candidates)} jobs with Gemini...")
        
        # Simple selection sort to order them
        ranked_jobs = []
        remaining = list(top_candidates)
        
        for rank in range(min(5, len(top_candidates))):
            if not remaining: break
            best = remaining[0]
            for candidate in remaining[1:]:
                winner = ask_gemini(resume, best, candidate, gemini_key)
                if winner == "B":
                    best = candidate
            ranked_jobs.append(best)
            remaining.remove(best)
            
        ranked_jobs.extend(remaining)
        
        # Ingest into SQLite database
        newly_added = 0
        for idx, job_data in enumerate(ranked_jobs):
            ext_id = stable_job_id("open-jobs", job_data["url"], job_data["title"], job_data["company"])
            
            existing = db.query(Job).filter(Job.job_id_external == ext_id).first()
            if not existing:
                # Calculate actual match score and reasons instead of mock scoring
                analysis = evaluate_match(job_data["description"], resume)
                if analysis:
                    score = float(analysis.get("score", 0.40))
                    reason = analysis.get("reason", f"Open-Jobs import. Rank: #{idx+1} in batch.")
                    tech_stack = json.dumps(analysis.get("breakdown", {}))
                else:
                    score = max(0.40, 0.95 - (idx * 0.08))
                    reason = f"Open-Jobs import. Rank: #{idx+1} in batch."
                    tech_stack = "{}"

                salary_str = ""
                if job_data["salary_min_k"] and job_data["salary_min_k"] > 0:
                    salary_str = f"${job_data['salary_min_k']}k - ${job_data['salary_max_k']}k"
                    
                job = Job(
                    job_id_external=ext_id,
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data["work_mode"] or "Remote",
                    description=job_data["description"],
                    url=job_data["url"],
                    source="open-jobs",
                    salary=salary_str,
                    posted_date=datetime.utcnow(),
                    seniority=job_data["level"],
                    match_score=score,
                    match_reason=reason,
                    tech_stack=tech_stack,
                    status=JobStatus.REVIEW if score >= 0.70 else JobStatus.NEW
                )
                db.add(job)
                newly_added += 1
                
        db.commit()
        logger.info(f"Successfully imported {newly_added} open-jobs matches into SQLite database.")
        
    except Exception as e:
        logger.error(f"Failed open-jobs import: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(import_open_jobs())
