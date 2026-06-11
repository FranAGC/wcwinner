import sys
import os
from pathlib import Path
import duckdb

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.database.connection import get_db_path

def seed_wc26():
    print("Resetting WC26 tournament matches from local CSV...")
    db_path = get_db_path()
    
    with duckdb.connect(db_path, read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        
        # 1. Delete all matches and stats related to WC26
        conn.execute("DELETE FROM team_match_stats WHERE match_id LIKE 'WC26_%'")
        conn.execute("DELETE FROM matches WHERE tournament_id = 'WC26'")
        
        # 2. Load the WC26 matches from CSV
        csv_path = os.path.abspath("backend/data/wc26_matches.csv")
        
        # We need to correctly handle empty strings as NULL for home/away teams in CSV
        # DuckDB handles this cleanly with COPY if we specify options, or we can use a temp table
        conn.execute(f"CREATE TEMP TABLE temp_wc26 AS SELECT * FROM read_csv_auto('{csv_path}')")
        
        # Convert empty strings to NULL to match database schema requirements
        conn.execute("""
            UPDATE temp_wc26 
            SET home_team_id = NULL WHERE home_team_id = '';
        """)
        conn.execute("""
            UPDATE temp_wc26 
            SET away_team_id = NULL WHERE away_team_id = '';
        """)
        
        conn.execute("INSERT INTO matches SELECT * FROM temp_wc26")
        conn.execute("DROP TABLE temp_wc26")
        
        conn.execute("COMMIT")
        
        # Count the matches
        count = conn.execute("SELECT count(*) FROM matches WHERE tournament_id = 'WC26'").fetchone()[0]
        print(f"Successfully re-seeded {count} scheduled matches for WC26.")

if __name__ == "__main__":
    seed_wc26()
