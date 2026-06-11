import sys
from pathlib import Path
from datetime import date, datetime
import polars as pl

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository

def calculate_and_save_elo():
    repo = FootballRepository()
    print("Calculating ELO history for all teams...")

    # 1. Get all teams
    teams = repo.get_teams()
    if not teams:
        print("No teams found in database. Run load_matches.py first.")
        return

    # 2. Get FIFA rankings to initialize ELOs
    rankings_df = repo.get_latest_rankings_df()
    
    # Map team_id -> initial ELO (using FIFA points or default to 1500)
    current_elos = {}
    initial_date = date(2022, 11, 1)
    
    elo_tuples = []

    for team in teams:
        team_id = team.team_id
        # Try to find FIFA points
        points_row = rankings_df.filter(pl.col("team_id") == team_id)
        if len(points_row) > 0:
            # FIFA points align well with ELO scale (1400-1860)
            initial_elo = float(points_row["points"][0])
        else:
            initial_elo = 1500.0
        
        current_elos[team_id] = initial_elo
        
        # Save initial ELO
        initial_date_str = initial_date.strftime("%Y-%m-%d")
        elo_tuples.append((initial_date_str, team_id, initial_elo))

    # 3. Get all completed matches in chronological order
    matches_df = repo.get_matches_df()
    completed_matches = matches_df.filter(pl.col("status") == "Completed").sort("match_date")

    print(f"Processing {len(completed_matches)} completed matches...")

    # ELO parameters
    K_FACTOR_WC = 60      # World Cup matches have high importance
    K_FACTOR_DEFAULT = 30

    for row in completed_matches.iter_rows(named=True):
        match_date = row["match_date"]
        # Convert date to string format for insertion
        if isinstance(match_date, (date, datetime)):
            match_date_str = match_date.strftime("%Y-%m-%d")
        else:
            match_date_str = str(match_date)

        home = row["home_team_id"]
        away = row["away_team_id"]
        h_score = row["home_score"]
        a_score = row["away_score"]
        phase = row["match_phase"]

        # Ensure teams are in current_elos
        if home not in current_elos:
            current_elos[home] = 1500.0
        if away not in current_elos:
            current_elos[away] = 1500.0

        r_home = current_elos[home]
        r_away = current_elos[away]

        # Expected scores
        e_home = 1.0 / (1.0 + 10.0 ** ((r_away - r_home) / 400.0))
        e_away = 1.0 / (1.0 + 10.0 ** ((r_home - r_away) / 400.0))

        # Actual scores
        if h_score > a_score:
            s_home, s_away = 1.0, 0.0
        elif h_score < a_score:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        # Determine K-factor
        k = K_FACTOR_WC if "World Cup" in (phase or "") or "Cup" in (phase or "") else K_FACTOR_DEFAULT

        # Update ELOs
        new_r_home = r_home + k * (s_home - e_home)
        new_r_away = r_away + k * (s_away - e_away)

        current_elos[home] = new_r_home
        current_elos[away] = new_r_away

        # Save to database list
        elo_tuples.append((match_date_str, home, new_r_home))
        elo_tuples.append((match_date_str, away, new_r_away))

    # Also save a current ELO entry for the eve of WC 2026 (e.g. 2026-06-10) to make sure it's up to date
    pre_wc26_date_str = "2026-06-10"
    for team_id, elo_val in current_elos.items():
        elo_tuples.append((pre_wc26_date_str, team_id, elo_val))

    # Save all ELO history records in bulk inside a single transaction using Polars integration
    elo_df_save = pl.DataFrame(elo_tuples, schema=[
        "rating_date", "team_id", "elo_rating"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO elo_history SELECT * FROM elo_df_save")
        conn.execute("COMMIT")

    print(f"ELO calculation completed and successfully saved {len(elo_tuples)} history records in bulk!")

if __name__ == "__main__":
    calculate_and_save_elo()
