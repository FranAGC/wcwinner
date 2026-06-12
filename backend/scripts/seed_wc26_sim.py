import sys
import os
from pathlib import Path
import duckdb

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.database.connection import get_db_path

def seed_wc26_sim():
    print("Resetting WC26_SIM parallel tournament matches from local CSV...")
    db_path = get_db_path()
    
    with duckdb.connect(db_path, read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        
        # 1. Delete all matches and stats related to WC26_SIM
        conn.execute("DELETE FROM team_match_stats WHERE match_id LIKE 'WC26_SIM_%'")
        conn.execute("DELETE FROM matches WHERE tournament_id = 'WC26_SIM'")
        
        # 2. Load the WC26 matches from CSV
        csv_path = os.path.abspath("backend/data/wc26_matches.csv")
        
        conn.execute(f"CREATE TEMP TABLE temp_wc26_sim AS SELECT * FROM read_csv_auto('{csv_path}')")
        
        # Convert empty strings to NULL to match database schema requirements
        conn.execute("UPDATE temp_wc26_sim SET home_team_id = NULL WHERE home_team_id = ''")
        conn.execute("UPDATE temp_wc26_sim SET away_team_id = NULL WHERE away_team_id = ''")
        
        # Replace 'WC26' with 'WC26_SIM'
        conn.execute("UPDATE temp_wc26_sim SET tournament_id = 'WC26_SIM'")
        conn.execute("UPDATE temp_wc26_sim SET match_id = REPLACE(match_id, 'WC26', 'WC26_SIM')")
        
        conn.execute("INSERT INTO matches SELECT * FROM temp_wc26_sim")
        conn.execute("DROP TABLE temp_wc26_sim")
        
        conn.execute("COMMIT")
        
        # Count the matches
        count = conn.execute("SELECT count(*) FROM matches WHERE tournament_id = 'WC26_SIM'").fetchone()[0]
        print(f"Successfully re-seeded {count} scheduled matches for WC26_SIM.")
        
    print("Recalculating tournament features and ELO for WC26_SIM...")
    from backend.simulations.tournament import TournamentSimulator
    sim = TournamentSimulator()
    sim.recalculate_tournament_features("WC26_SIM")
    print("WC26_SIM features recalculation complete.")

if __name__ == "__main__":
    seed_wc26_sim()
