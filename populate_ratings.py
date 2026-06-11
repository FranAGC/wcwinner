import os
import sys
from pathlib import Path
import duckdb
import random

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

def populate_ratings():
    db_path = 'football_probability.duckdb'
    conn = duckdb.connect(db_path, read_only=False)
    
    print("Assigning base ratings to players...")
    # Get team ELOs to base the ratings on
    team_elos = conn.execute("SELECT team_id, MAX(elo_rating) FROM elo_history GROUP BY team_id").fetchall()
    elo_dict = {t: elo for t, elo in team_elos}
    
    # Get all squad calls
    calls = conn.execute("SELECT team_id, player_id FROM squad_calls").fetchall()
    
    # Calculate a rating for each player
    # Base ELO 1500 -> ~70 rating. ELO 2000 -> ~88 rating.
    player_ratings = []
    for team_id, player_id in calls:
        elo = elo_dict.get(team_id, 1500)
        # linear mapping: rating = 40 + elo * 0.024
        base_rating = min(96.0, max(50.0, 40.0 + (elo * 0.023)))
        
        # Add random variance between -5 and +5
        variance = random.uniform(-6.0, 6.0)
        final_rating = round(base_rating + variance, 1)
        player_ratings.append((final_rating, player_id))
        
    # Update players table
    conn.execute("BEGIN TRANSACTION")
    conn.executemany("UPDATE players SET base_rating = ? WHERE player_id = ?", player_ratings)
    conn.execute("COMMIT")
    
    print(f"Updated {len(player_ratings)} players with base ratings.")
    
    print("Exporting tables to CSV backups...")
    os.makedirs('backend/data', exist_ok=True)
    tables = ['teams', 'competitions', 'tournaments', 'matches', 'team_features', 'team_match_stats', 'players', 'player_match_stats', 'squad_calls']
    for t in tables:
        try:
            conn.execute(f"COPY (SELECT * FROM {t}) TO 'backend/data/{t}.csv' (HEADER, DELIMITER ',')")
            print(f"  - Exported {t}")
        except Exception as e:
            print(f"  - Error exporting {t}: {e}")
            
    conn.close()

if __name__ == '__main__':
    populate_ratings()
