import sqlite3
import os

def migrate_db():
    db_path = os.path.join("data", "jobs.db")
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List of columns to add
    new_columns = [
        ("seniority", "VARCHAR(50)"),
        ("tech_stack", "TEXT"),
        ("ats_type", "VARCHAR(50)"),
        ("is_active", "INTEGER DEFAULT 1")
    ]
    
    for col_name, col_type in new_columns:
        try:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
