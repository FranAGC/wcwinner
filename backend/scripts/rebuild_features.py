import sys
from pathlib import Path
from datetime import date, datetime
import polars as pl
import numpy as np

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository

def rebuild_all_features():
    repo = FootballRepository()
    print("Rebuilding team and match features (enhanced)...")

    # 1. Load data
    teams = repo.get_teams()
    matches_df = repo.get_matches_df()
    
    # Get completed matches
    comp_matches = matches_df.filter(pl.col("status") == "Completed")
    
    # Separate WC-only completed matches for tournament-specific features
    wc_matches = comp_matches.filter(
        pl.col("tournament_id").str.starts_with("WC") | pl.col("match_phase").str.contains("World Cup")
    )
    
    # Calculate global averages of goals to normalize attack/defense strengths
    if len(comp_matches) > 0:
        total_goals = comp_matches["home_score"].sum() + comp_matches["away_score"].sum()
        global_avg_goals = total_goals / (2 * len(comp_matches))
    else:
        global_avg_goals = 1.2  # sensible fallback

    if len(wc_matches) > 0:
        wc_total_goals = wc_matches["home_score"].sum() + wc_matches["away_score"].sum()
        wc_avg_goals = wc_total_goals / (2 * len(wc_matches))
    else:
        wc_avg_goals = 1.3  # WC slightly higher than overall

    print(f"Global avg goals/team/match: {global_avg_goals:.4f} | WC only: {wc_avg_goals:.4f}")

    # Build a head-to-head lookup dict from all completed matches
    # Key: frozenset of two teams, value: list of (date, home, away, h_score, a_score)
    h2h_records: dict = {}
    for row in comp_matches.iter_rows(named=True):
        h = row["home_team_id"]
        a = row["away_team_id"]
        key = tuple(sorted([h, a]))
        if key not in h2h_records:
            h2h_records[key] = []
        h2h_records[key].append((row["match_date"], h, a, row["home_score"], row["away_score"]))

    # We will build features as of 2026-06-10 (eve of WC 2026)
    as_of_date = date(2026, 6, 10)
    as_of_date_str = "2026-06-10"

    # Fetch all ELO ratings as of 2026-06-10 in bulk
    with repo.conn_factory(read_only=True) as conn:
        elo_rows = conn.execute(
            "SELECT team_id, elo_rating FROM elo_history WHERE rating_date = ?",
            [as_of_date_str]
        ).fetchall()
        elo_map = {row[0]: row[1] for row in elo_rows}

    # Fetch all FIFA rankings as of 2026-06-10 in bulk
    with repo.conn_factory(read_only=True) as conn:
        rank_rows = conn.execute(
            "SELECT team_id, rank FROM fifa_rankings WHERE ranking_date = ?",
            [as_of_date_str]
        ).fetchall()
        rank_map = {row[0]: row[1] for row in rank_rows}
        
        # Also try latest available ranking if exact date not found
        if not rank_map:
            rank_rows = conn.execute(
                """
                WITH ranked AS (
                    SELECT team_id, rank,
                           ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY ranking_date DESC) as rn
                    FROM fifa_rankings
                )
                SELECT team_id, rank FROM ranked WHERE rn = 1
                """
            ).fetchall()
            rank_map = {row[0]: row[1] for row in rank_rows}

    # Fetch squad sizes for WC26 per team
    with repo.conn_factory(read_only=True) as conn:
        squad_rows = conn.execute(
            "SELECT team_id, COUNT(player_id) as sz FROM squad_calls WHERE tournament_id = 'WC26' GROUP BY team_id"
        ).fetchall()
        squad_size_map = {row[0]: row[1] for row in squad_rows}

    team_features_dict = {}
    team_features_tuples = []

    for team in teams:
        team_id = team.team_id
        
        # A. ELO
        elo = elo_map.get(team_id, 1500.0)

        # B. FIFA Rank
        rank = rank_map.get(team_id, 50)

        # C. Squad size
        squad_size = squad_size_map.get(team_id, 23)  # default to 23 if missing

        # D. Goal stats from ALL completed matches
        team_home = comp_matches.filter(pl.col("home_team_id") == team_id)
        team_away = comp_matches.filter(pl.col("away_team_id") == team_id)
        
        all_matches_data = []
        for r in team_home.iter_rows(named=True):
            all_matches_data.append((r["match_date"], r["home_score"], r["away_score"]))
        for r in team_away.iter_rows(named=True):
            all_matches_data.append((r["match_date"], r["away_score"], r["home_score"]))
        all_matches_data.sort(key=lambda x: x[0])

        goals_scored = [m[1] for m in all_matches_data]
        goals_conceded = [m[2] for m in all_matches_data]
        results = []
        for gs, gc in zip(goals_scored, goals_conceded):
            if gs > gc:
                results.append(3.0)
            elif gs < gc:
                results.append(0.0)
            else:
                results.append(1.0)

        n = len(all_matches_data)
        if n > 0:
            avg_scored = sum(goals_scored) / n
            avg_conceded = sum(goals_conceded) / n
            attack_strength = avg_scored / global_avg_goals
            defense_strength = avg_conceded / global_avg_goals
            
            # Exponential decay form index (recent matches count more)
            # decay factor: most recent match = weight 1.0, older = exponential decay
            recent = all_matches_data[-10:]  # last 10 matches max
            n_recent = len(recent)
            decay = 0.85
            weights = np.array([decay ** (n_recent - 1 - i) for i in range(n_recent)])
            points_recent = np.array([results[-(n_recent - i)] for i in range(n_recent)])
            form_index = float(np.dot(weights, points_recent[::-1]) / (weights.sum() * 3.0))
            
            # Clean sheet rate
            clean_sheets = sum(1 for gc in goals_conceded if gc == 0)
            clean_sheet_rate = clean_sheets / n
            
            # Win rate
            wins = sum(1 for gs, gc in zip(goals_scored, goals_conceded) if gs > gc)
            win_rate = wins / n
        else:
            avg_scored = global_avg_goals
            avg_conceded = global_avg_goals
            attack_strength = 1.0
            defense_strength = 1.0
            form_index = 0.5
            clean_sheet_rate = 0.25
            win_rate = 0.33

        # E. World Cup specific attack/defense strength
        wc_home = wc_matches.filter(pl.col("home_team_id") == team_id)
        wc_away = wc_matches.filter(pl.col("away_team_id") == team_id)
        
        wc_scored = []
        wc_conceded = []
        for r in wc_home.iter_rows(named=True):
            wc_scored.append(r["home_score"])
            wc_conceded.append(r["away_score"])
        for r in wc_away.iter_rows(named=True):
            wc_scored.append(r["away_score"])
            wc_conceded.append(r["home_score"])
        
        if wc_scored:
            wc_attack = (sum(wc_scored) / len(wc_scored)) / wc_avg_goals
            wc_defense = (sum(wc_conceded) / len(wc_conceded)) / wc_avg_goals
        else:
            # Fall back to overall but with WC regression toward mean
            wc_attack = attack_strength * 0.7 + 1.0 * 0.3
            wc_defense = defense_strength * 0.7 + 1.0 * 0.3
            
        team_features_tuples.append((
            team_id, as_of_date_str, elo, rank,
            attack_strength, defense_strength,
            avg_scored, avg_conceded, form_index,
            wc_attack, wc_defense, squad_size,
            clean_sheet_rate, win_rate
        ))

        team_features_dict[team_id] = {
            "elo": elo,
            "fifa_rank": rank,
            "attack_strength": attack_strength,
            "defense_strength": defense_strength,
            "form_index": form_index,
            "wc_attack": wc_attack,
            "wc_defense": wc_defense,
            "squad_size": squad_size,
        }

    # Save all team features in bulk
    team_feats_df = pl.DataFrame(team_features_tuples, orient="row", schema=[
        "team_id", "as_of_date", "elo", "fifa_rank",
        "attack_strength", "defense_strength",
        "avg_goals_scored", "avg_goals_conceded", "form_index",
        "wc_attack_strength", "wc_defense_strength", "squad_size",
        "clean_sheet_rate", "win_rate"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO team_features SELECT * FROM team_feats_df")
        conn.execute("COMMIT")

    print(f"Successfully saved {len(team_features_tuples)} enhanced team features!")

    # 2. Build match_features for ALL matches with H2H data
    all_matches = repo.get_matches()
    print(f"Rebuilding match_features for {len(all_matches)} matches (with H2H)...")
    
    match_features_tuples = []
    for m in all_matches:
        home_id = m.home_team_id
        away_id = m.away_team_id
        
        h_feats = team_features_dict.get(home_id, {})
        a_feats = team_features_dict.get(away_id, {})
        
        h_elo = h_feats.get("elo", 1500.0)
        a_elo = a_feats.get("elo", 1500.0)
        h_rank = h_feats.get("fifa_rank", 50)
        a_rank = a_feats.get("fifa_rank", 50)
        h_att = h_feats.get("attack_strength", 1.0)
        a_att = a_feats.get("attack_strength", 1.0)
        h_def = h_feats.get("defense_strength", 1.0)
        a_def = a_feats.get("defense_strength", 1.0)
        h_form = h_feats.get("form_index", 0.5)
        a_form = a_feats.get("form_index", 0.5)
        h_wc_att = h_feats.get("wc_attack", 1.0)
        a_wc_att = a_feats.get("wc_attack", 1.0)
        h_wc_def = h_feats.get("wc_defense", 1.0)
        a_wc_def = a_feats.get("wc_defense", 1.0)
        h_squad = h_feats.get("squad_size", 23)
        a_squad = a_feats.get("squad_size", 23)

        # Head-to-head features (last 10 historical meetings)
        key = tuple(sorted([home_id, away_id]))
        h2h_list = h2h_records.get(key, [])
        # Keep only last 10 meetings chronologically
        h2h_list = sorted(h2h_list, key=lambda x: x[0])[-10:]
        
        h2h_home_wins = 0
        h2h_away_wins = 0
        h2h_draws = 0
        h2h_home_goals = []
        h2h_away_goals = []
        
        for (_, ht, at, hs, as_) in h2h_list:
            if ht == home_id:
                hg, ag = hs, as_
            else:
                hg, ag = as_, hs
            h2h_home_goals.append(hg)
            h2h_away_goals.append(ag)
            if hg > ag:
                h2h_home_wins += 1
            elif ag > hg:
                h2h_away_wins += 1
            else:
                h2h_draws += 1

        h2h_home_goals_avg = float(np.mean(h2h_home_goals)) if h2h_home_goals else 1.2
        h2h_away_goals_avg = float(np.mean(h2h_away_goals)) if h2h_away_goals else 1.0
        
        match_features_tuples.append((
            m.match_id, home_id, away_id,
            h_elo, a_elo, h_rank, a_rank,
            h_att, a_att, h_def, a_def,
            h_elo - a_elo, h_rank - a_rank,
            h_form, a_form,
            h_wc_att, a_wc_att,
            h_wc_def, a_wc_def,
            h_squad, a_squad,
            h2h_home_wins, h2h_away_wins, h2h_draws,
            h2h_home_goals_avg, h2h_away_goals_avg
        ))

    # Save all match features in bulk
    match_feats_df = pl.DataFrame(match_features_tuples, orient="row", schema=[
        "match_id", "home_team_id", "away_team_id",
        "home_elo", "away_elo", "home_fifa_rank", "away_fifa_rank",
        "home_attack_strength", "away_attack_strength",
        "home_defense_strength", "away_defense_strength",
        "elo_diff", "rank_diff",
        "home_form_index", "away_form_index",
        "home_wc_attack", "away_wc_attack",
        "home_wc_defense", "away_wc_defense",
        "home_squad_size", "away_squad_size",
        "h2h_home_wins", "h2h_away_wins", "h2h_draws",
        "h2h_home_goals_avg", "h2h_away_goals_avg"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO match_features SELECT * FROM match_feats_df")
        conn.execute("COMMIT")

    print(f"Successfully saved {len(match_features_tuples)} enhanced match features!")

if __name__ == "__main__":
    rebuild_all_features()
