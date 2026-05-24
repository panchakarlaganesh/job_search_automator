import sys
import os
import random
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Job, JobStatus

def manual_import():
    print("--- Manual Job Importer ---")
    title = input("Enter Job Title: ")
    company = input("Enter Company Name: ")
    location = input("Enter Location: ")
    url = input("Enter Job URL: ")
    print("Paste Job Description (Enter a blank line when finished):")
    
    desc_lines = []
    while True:
        line = input()
        if line == "":
            break
        desc_lines.append(line)
    description = "\n".join(desc_lines)

    db = SessionLocal()
    try:
        job = Job(
            job_id_external=f"manual_{random.randint(1000, 9999)}",
            title=title,
            company=company,
            location=location,
            url=url,
            description=description,
            source="manual",
            status=JobStatus.NEW,
            posted_date=datetime.now()
        )
        db.add(job)
        db.commit()
        print(f"\n✅ Successfully imported: {title} at {company}")
    except Exception as e:
        print(f"\n❌ Failed to import: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    manual_import()
