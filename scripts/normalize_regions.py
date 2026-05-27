import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal

def normalize_regions():
    db = SessionLocal()
    try:
        # Use raw SQL to update locations to avoid Enum or Model validation issues
        # that might arise if the database state is partially migrated.
        
        # 1. Normalize India-related locations
        india_keywords = ["india", "hyderabad", "bengaluru", "bangalore", "pune", "mumbai", "chennai", "delhi", "noida", "gurgaon"]
        for kw in india_keywords:
            db.execute(text("UPDATE jobs SET location = 'India' WHERE LOWER(location) LIKE :kw"), {"kw": f"%{kw}%"})
            print(f"Normalized location contains '{kw}' -> India")

        # 2. Normalize USA-related locations
        usa_keywords = ["united states", "usa", " us ", "us,", "remote"] # 'remote' often defaults to US in these scrapers
        for kw in usa_keywords:
            # We add a secondary check to NOT override if 'India' is already there (e.g. 'Remote India')
            db.execute(text("UPDATE jobs SET location = 'United States' WHERE LOWER(location) LIKE :kw AND location != 'India'"), {"kw": f"%{kw}%"})
            print(f"Normalized location contains '{kw}' -> United States")
        
        db.commit()
        print("Region normalization complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    normalize_regions()
