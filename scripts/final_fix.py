import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal

def final_fix():
    db = SessionLocal()
    try:
        # 1. Fix Status Discrepancy
        # The database still has 'tailored' and other old values as strings, 
        # but the Enum in models.py has changed. SQLAlchemy crashes on this.
        # We must normalize ALL statuses to the new 5 core values using raw SQL.
        
        status_updates = [
            ("review", ["matched", "tailored", "matching", "tailoring"]),
            ("applied", ["applying"]),
            ("rejected", ["match_failed"]),
            ("new", ["on_hold"]),
            ("help", ["manual_intervention"])
        ]
        
        for new_val, old_vals in status_updates:
            for old_val in old_vals:
                db.execute(text("UPDATE jobs SET status = :new WHERE LOWER(status) = :old"), 
                          {"new": new_val, "old": old_val})
                print(f"Status Fix: {old_val} -> {new_val}")

        # 2. Fix Region Discrepancy
        # Normalize anything with a comma (e.g., 'City, State') to 'United States' if not India
        # Also handle specific US state patterns
        us_states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
        
        # Normalize India first
        db.execute(text("UPDATE jobs SET location = 'India' WHERE LOWER(location) LIKE '%india%' OR LOWER(location) LIKE '%hyderabad%' OR LOWER(location) LIKE '%bangalore%' OR LOWER(location) LIKE '%bengaluru%'"))
        
        # Normalize everything else to United States if it matches US patterns
        for state in us_states:
            # Matches 'City, ST' or 'State'
            db.execute(text("UPDATE jobs SET location = 'United States' WHERE (location LIKE :pattern OR location = :state) AND location != 'India'"), 
                      {"pattern": f"%, {state}%", "state": state})

        # Catch-all for remaining specific US locations shown in screenshot
        us_keywords = ["united states", "usa", "remote", "washington", "orlando", "san francisco", "somerville", "redlands", "wilmington", "new york"]
        for kw in us_keywords:
            db.execute(text("UPDATE jobs SET location = 'United States' WHERE LOWER(location) LIKE :kw AND location != 'India'"), 
                      {"kw": f"%{kw}%"})

        db.commit()
        print("Final normalization and status fix complete.")
        
    except Exception as e:
        print(f"Error during final fix: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    final_fix()
