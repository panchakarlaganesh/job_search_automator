from src.database import SessionLocal
from src.models import Job

def fix_sources():
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        count = 0
        for j in jobs:
            if not j.url: continue
            url = j.url.lower()
            new_source = None
            
            if 'linkedin.com' in url:
                new_source = 'linkedin'
            elif 'indeed.com' in url:
                new_source = 'indeed'
            elif 'dice.com' in url:
                new_source = 'dice'
                
            if new_source and j.source != new_source:
                print(f"Updating Job {j.id}: {j.source} -> {new_source}")
                j.source = new_source
                count += 1
        
        db.commit()
        print(f"Successfully updated {count} jobs.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_sources()
