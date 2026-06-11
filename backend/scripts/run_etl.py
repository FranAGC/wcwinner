import sys
import os
from pathlib import Path
import duckdb

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.connection import init_db, get_db_path

def run_pipeline():
    print("=== STARTING LOCAL DATABASE RESTORE PIPELINE ===")
    
    db_path = get_db_path()
    if os.path.exists(db_path):
        print(f"Removing old database file at {db_path}...")
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Warning: Could not remove old database file: {e}")
            
    print("\nStep 1: Initializing Schema...")
    init_db()
    
    print("\nStep 2: Restoring Tables from CSV files...")
    tables = ['teams', 'competitions', 'tournaments', 'matches', 'team_features', 'team_match_stats', 'elo_history', 'fifa_rankings']
    
    conn = duckdb.connect(db_path, read_only=False)
    conn.execute("BEGIN TRANSACTION")
    
    for t in tables:
        csv_path = os.path.abspath(f"backend/data/{t}.csv")
        if os.path.exists(csv_path):
            try:
                conn.execute(f"COPY {t} FROM '{csv_path}' (HEADER, DELIMITER ',')")
                print(f"  - Successfully restored {t}")
            except Exception as e:
                print(f"  - Error restoring {t}: {e}")
        else:
            print(f"  - Warning: Backup file {csv_path} not found.")
            
    conn.execute("COMMIT")
    conn.close()
    
    print("\nStep 3: Restoring WC26 Tournament Matches...")
    from backend.scripts.seed_wc26 import seed_wc26
    seed_wc26()
    
    print("\n=== RESTORE PIPELINE EXECUTION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_pipeline()
