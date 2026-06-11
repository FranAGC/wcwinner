import sys
from pathlib import Path
from datetime import date, datetime
import polars as pl

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository

def rebuild_all_features():
    repo = FootballRepository()
    print("Rebuilding team and match features...")

    # 1. Load data
    teams = repo.get_teams()
    matches_df = repo.get_matches_df()
    
    # Get completed matches
    comp_matches = matches_df.filter(pl.col("status") == "Completed")
    
    # Calculate global averages of goals to normalize attack/defense strengths
    if len(comp_matches) > 0:
        total_goals = comp_matches["home_score"].sum() + comp_matches["away_score"].sum()
        global_avg_goals = total_goals / (2 * len(comp_matches))
    else:
        global_avg_goals = 1.2  # sensible fallback

    print(f"Global average goals per team per match: {global_avg_goals:.4f}")

    # We will build features as of 2026-06-10 (eve of WC 2026)
    as_of_date = date(2026, 6, 10)
    as_of_date_str = "2026-06-10"

    # Fetch all ELO ratings as of 2026-06-10 in bulk
    with repo.conn_factory(read_only=True) as conn:
        elo_rows = conn.execute(
            """
            SELECT team_id, elo_rating FROM elo_history
            WHERE rating_date = ?
            """,
            [as_of_date_str]
        ).fetchall()
        elo_map = {row[0]: row[1] for row in elo_rows}

    # Fetch all FIFA rankings as of 2026-06-10 in bulk
    with repo.conn_factory(read_only=True) as conn:
        rank_rows = conn.execute(
            """
            SELECT team_id, rank FROM fifa_rankings
            WHERE ranking_date = ?
            """,
            [as_of_date_str]
        ).fetchall()
        rank_map = {row[0]: row[1] for row in rank_rows}

    team_features_dict = {}
    team_features_tuples = []

    for team in teams:
        team_id = team.team_id
        
        # A. ELO
        elo = elo_map.get(team_id, 1500.0)

        # B. FIFA Rank
        rank = rank_map.get(team_id, 50)

        # C. Goal stats: Find matches played by team before as_of_date
        team_home_matches = comp_matches.filter((pl.col("home_team_id") == team_id) & (pl.col("match_date") <= as_of_date))
        team_away_matches = comp_matches.filter((pl.col("away_team_id") == team_id) & (pl.col("match_date") <= as_of_date))
        
        goals_scored = []
        goals_conceded = []
        points = [] # For form index (win=3, draw=1, loss=0)
        
        # Extract details chronologically
        team_all_matches = []
        for r in team_home_matches.iter_rows(named=True):
            team_all_matches.append((r["match_date"], r["home_score"], r["away_score"], "home"))
        for r in team_away_matches.iter_rows(named=True):
            team_all_matches.append((r["match_date"], r["away_score"], r["home_score"], "away"))
            
        # Sort by date
        team_all_matches.sort(key=lambda x: x[0])
        
        for _, scored, conceded, role in team_all_matches:
            goals_scored.append(scored)
            goals_conceded.append(conceded)
            if scored > conceded:
                points.append(3.0)
            elif scored < conceded:
                points.append(0.0)
            else:
                points.append(1.0)
                
        # Calculations
        if goals_scored:
            avg_scored = sum(goals_scored) / len(goals_scored)
            avg_conceded = sum(goals_conceded) / len(goals_conceded)
            attack_strength = avg_scored / global_avg_goals
            defense_strength = avg_conceded / global_avg_goals
            
            # Form index: last 5 matches, weighted (recent has higher weight)
            recent_points = points[-5:]
            weights = list(range(1, len(recent_points) + 1))
            weighted_points = sum(p * w for p, w in zip(recent_points, weights))
            total_weight = sum(weights)
            form_index = (weighted_points / total_weight) / 3.0 if total_weight > 0 else 0.5
        else:
            avg_scored = global_avg_goals
            avg_conceded = global_avg_goals
            attack_strength = 1.0
            defense_strength = 1.0
            form_index = 0.5
            
        team_features_tuples.append((
            team_id,
            as_of_date_str,
            elo,
            rank,
            attack_strength,
            defense_strength,
            avg_scored,
            avg_conceded,
            form_index
        ))

        # Keep a local mapping dict to easily build match features next
        team_features_dict[team_id] = {
            "elo": elo,
            "fifa_rank": rank,
            "attack_strength": attack_strength,
            "defense_strength": defense_strength
        }

    # Save all team features in bulk using Polars integration
    team_feats_df = pl.DataFrame(team_features_tuples, schema=[
        "team_id", "as_of_date", "elo", "fifa_rank", "attack_strength", "defense_strength",
        "avg_goals_scored", "avg_goals_conceded", "form_index"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO team_features SELECT * FROM team_feats_df")
        conn.execute("COMMIT")

    print(f"Successfully saved {len(team_features_tuples)} team features in bulk!")

    # 2. Build match_features for ALL matches (both completed and scheduled)
    all_matches = repo.get_matches()
    print(f"Rebuilding match_features for {len(all_matches)} matches...")
    
    match_features_tuples = []
    for m in all_matches:
        home_id = m.home_team_id
        away_id = m.away_team_id
        
        # Get feature values for both teams from dict
        h_feats = team_features_dict.get(home_id)
        a_feats = team_features_dict.get(away_id)
        
        # Fallback values if features are not found
        h_elo = h_feats["elo"] if h_feats else 1500.0
        a_elo = a_feats["elo"] if a_feats else 1500.0
        h_rank = h_feats["fifa_rank"] if h_feats else 50
        a_rank = a_feats["fifa_rank"] if a_feats else 50
        
        h_att = h_feats["attack_strength"] if h_feats else 1.0
        a_att = a_feats["attack_strength"] if a_feats else 1.0
        h_def = h_feats["defense_strength"] if h_feats else 1.0
        a_def = a_feats["defense_strength"] if a_feats else 1.0
        
        match_features_tuples.append((
            m.match_id,
            home_id,
            away_id,
            h_elo,
            a_elo,
            h_rank,
            a_rank,
            h_att,
            a_att,
            h_def,
            a_def,
            h_elo - a_elo,
            h_rank - a_rank
        ))

    # Save all match features in bulk using Polars integration
    match_feats_df = pl.DataFrame(match_features_tuples, schema=[
        "match_id", "home_team_id", "away_team_id", "home_elo", "away_elo",
        "home_fifa_rank", "away_fifa_rank", "home_attack_strength", "away_attack_strength",
        "home_defense_strength", "away_defense_strength", "elo_diff", "rank_diff"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO match_features SELECT * FROM match_feats_df")
        conn.execute("COMMIT")

    print(f"Successfully saved {len(match_features_tuples)} match features in bulk!")

if __name__ == "__main__":
    rebuild_all_features()
