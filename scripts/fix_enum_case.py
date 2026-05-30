import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal

def fix_enum_case():
    db = SessionLocal()
    try:
        # Map lowercase DB strings to uppercase Enum member names
        # REJECTED, REVIEW, APPLIED, NEW, HELP
        mapping = {
            "new": "NEW",
            "review": "REVIEW",
            "applied": "APPLIED",
            "rejected": "REJECTED",
            "help": "HELP"
        }
        
        for low, up in mapping.items():
            db.execute(text("UPDATE jobs SET status = :up WHERE status = :low"), {"up": up, "low": low})
            print(f"Case Fix: {low} -> {up}")
            
        db.commit()
        print("Enum case fix complete.")
    except Exception as e:
        print(f"Fix failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_enum_case()
