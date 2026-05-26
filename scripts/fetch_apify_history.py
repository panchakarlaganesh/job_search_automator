import os
import sys
from apify_client import ApifyClient
from dotenv import load_dotenv
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Job, JobStatus

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(APIFY_API_TOKEN) if APIFY_API_TOKEN else None

def fetch_history():
    if not client:
        print("❌ APIFY_API_TOKEN not set in .env")
        return

    print("🔍 Fetching recent Apify runs...")
    db = SessionLocal()
    try:
        # List all runs
        runs = client.runs().list(limit=20, desc=True).items
        
        total_ingested = 0
        for run in runs:
            # client.runs().list returns RunShort objects
            run_id = getattr(run, 'id', None)
            dataset_id = getattr(run, 'default_dataset_id', getattr(run, 'defaultDatasetId', None))
            
            if not dataset_id: continue
            
            print(f"  Checking dataset {dataset_id} from run {run_id}...")
            items = list(client.dataset(dataset_id).iterate_items())
            
            for item in items:
                # Items are usually dicts
                ext_id = item.get('id') or item.get('jobId')
                title = item.get('title') or item.get('jobTitle')
                
                if ext_id and title:
                    source = "linkedin" if "linkedin" in str(item.get('url', '')).lower() else "dice"
                    external_key = f"{source[0]}_{ext_id}"
                    
                    existing = db.query(Job).filter(Job.job_id_external == external_key).first()
                    if not existing:
                        job = Job(
                            job_id_external=external_key,
                            title=title,
                            company=item.get("companyName") or item.get("company"),
                            location=item.get("location"),
                            description=item.get("description") or item.get("jobDescription") or f"Job: {title}",
                            url=item.get("url") or item.get("jobUrl"),
                            source=source,
                            status=JobStatus.NEW,
                            posted_date=datetime.now()
                        )
                        db.add(job)
                        total_ingested += 1
            
            db.commit()
            
        print(f"\n✅ Finished! Ingested {total_ingested} historical jobs into the database.")
        
    except Exception as e:
        print(f"❌ Error fetching history: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fetch_history()
