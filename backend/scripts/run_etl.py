import sys
import os
from pathlib import Path

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.connection import init_db, get_db_path
from backend.scripts.load_matches import populate_initial_data
from backend.scripts.load_rankings import populate_rankings
from backend.scripts.load_players import populate_players
from backend.scripts.calculate_elo import calculate_and_save_elo
from backend.scripts.rebuild_features import rebuild_all_features

def run_pipeline():
    print("=== STARTING FOOTBALL PROBABILITY SYSTEM ETL PIPELINE ===")
    
    db_path = get_db_path()
    if os.path.exists(db_path):
        print(f"Removing old database file at {db_path}...")
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Warning: Could not remove old database file: {e}")
            
    print("\nStep 1: Initializing Database...")
    init_db()
    
    print("\nStep 2: Loading Matches...")
    populate_initial_data()
    
    print("\nStep 3: Loading FIFA Rankings...")
    populate_rankings()
    
    print("\nStep 4: Loading Players...")
    populate_players()
    
    print("\nStep 5: Calculating ELO History...")
    calculate_and_save_elo()
    
    print("\nStep 6: Rebuilding Features...")
    rebuild_all_features()
    
    print("\n=== PIPELINE EXECUTION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_pipeline()
