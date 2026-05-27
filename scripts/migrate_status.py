import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal, engine

def migrate_statuses():
    db = SessionLocal()
    try:
        # We need to map old string values in the database to new ones
        # Mapping:
        # MATCHING, MATCHED, TAILORING, TAILORED -> review
        # APPLYING, APPLIED -> applied
        # MATCH_FAILED, REJECTED -> rejected
        # ON_HOLD -> new (or review, let's go with new)
        # MANUAL_INTERVENTION -> help
        
        mapping = {
            "MATCHING": "review",
            "MATCHED": "review",
            "TAILORING": "review",
            "TAILORED": "review",
            "APPLYING": "applied",
            "ON_HOLD": "new",
            "MANUAL_INTERVENTION": "help"
        }
        
        for old, new in mapping.items():
            # Using raw SQL to bypass Enum validation issues during transition
            db.execute(text(f"UPDATE jobs SET status = :new WHERE status = :old"), {"new": new, "old": old.lower()})
            print(f"Migrated {old.lower()} -> {new}")
            
        db.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_statuses()
