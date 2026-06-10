import sys
from pathlib import Path
from datetime import date, datetime
import polars as pl

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.models.domain import TeamFeatures, MatchFeatures

def rebuild_all_features():
    repo = FootballRepository()
    print("Rebuilding team and match features...")

    # 1. Load data
    teams = repo.get_teams()
    matches_df = repo.get_matches_df()
    
    # Get completed matches
    comp_matches = matches_df.filter(pl.col("status") == "Completed")
    
    # Calculate global averages of goals to normalize attack/defense strengths
    # Each match has a home and away score, so 2 team-performances per match
    if len(comp_matches) > 0:
        total_goals = comp_matches["home_score"].sum() + comp_matches["away_score"].sum()
        global_avg_goals = total_goals / (2 * len(comp_matches))
    else:
        global_avg_goals = 1.2  # sensible fallback

    print(f"Global average goals per team per match: {global_avg_goals:.4f}")

    # We will build features as of 2026-06-10 (eve of WC 2026)
    as_of_date = date(2026, 6, 10)

    team_features_dict = {}

    for team in teams:
        team_id = team.team_id
        
        # A. ELO: Find latest ELO as of 2026-06-10
        with repo.conn_factory(read_only=True) as conn:
            elo_res = conn.execute(
                """
                SELECT elo_rating FROM elo_history
                WHERE team_id = ? AND rating_date <= ?
                ORDER BY rating_date DESC LIMIT 1
                """,
                [team_id, as_of_date]
            ).fetchone()
            elo = elo_res[0] if elo_res else 1500.0

        # B. FIFA Rank: Find latest FIFA rank as of 2026-06-10
        with repo.conn_factory(read_only=True) as conn:
            rank_res = conn.execute(
                """
                SELECT rank FROM fifa_rankings
                WHERE team_id = ? AND ranking_date <= ?
                ORDER BY ranking_date DESC LIMIT 1
                """,
                [team_id, as_of_date]
            ).fetchone()
            rank = rank_res[0] if rank_res else 50

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
            # Defaults for teams with no prior matches in DB
            avg_scored = global_avg_goals
            avg_conceded = global_avg_goals
            attack_strength = 1.0
            defense_strength = 1.0
            form_index = 0.5
            
        tf = TeamFeatures(
            team_id=team_id,
            as_of_date=as_of_date,
            elo=elo,
            fifa_rank=rank,
            attack_strength=attack_strength,
            defense_strength=defense_strength,
            avg_goals_scored=avg_scored,
            avg_goals_conceded=avg_conceded,
            form_index=form_index
        )
        repo.save_team_features(tf)
        team_features_dict[team_id] = tf

    print("Team features successfully updated in team_features!")

    # 2. Build match_features for ALL matches (both completed and scheduled)
    all_matches = repo.get_matches()
    print(f"Rebuilding match_features for {len(all_matches)} matches...")
    
    for m in all_matches:
        home_id = m.home_team_id
        away_id = m.away_team_id
        
        # Get feature values for both teams
        h_feats = team_features_dict.get(home_id)
        a_feats = team_features_dict.get(away_id)
        
        # Fallback values if features are not found
        h_elo = h_feats.elo if h_feats else 1500.0
        a_elo = a_feats.elo if a_feats else 1500.0
        h_rank = h_feats.fifa_rank if h_feats else 50
        a_rank = a_feats.fifa_rank if a_feats else 50
        
        h_att = h_feats.attack_strength if h_feats else 1.0
        a_att = a_feats.attack_strength if a_feats else 1.0
        h_def = h_feats.defense_strength if h_feats else 1.0
        a_def = a_feats.defense_strength if a_feats else 1.0
        
        mf = MatchFeatures(
            match_id=m.match_id,
            home_team_id=home_id,
            away_team_id=away_id,
            home_elo=h_elo,
            away_elo=a_elo,
            home_fifa_rank=h_rank,
            away_fifa_rank=a_rank,
            home_attack_strength=h_att,
            away_attack_strength=a_att,
            home_defense_strength=h_def,
            away_defense_strength=a_def,
            elo_diff=h_elo - a_elo,
            rank_diff=h_rank - a_rank
        )
        repo.save_match_features(mf)

    print("Match features successfully updated in match_features!")

if __name__ == "__main__":
    rebuild_all_features()
