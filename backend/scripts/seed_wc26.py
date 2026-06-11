import sys
from pathlib import Path
from datetime import date, timedelta
import polars as pl

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository

def seed_wc26():
    repo = FootballRepository()
    
    print("Resetting WC26 tournament matches...")
    
    # 1. Delete all matches and stats related to WC26
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("DELETE FROM team_match_stats WHERE match_id LIKE 'WC26_%'")
        conn.execute("DELETE FROM matches WHERE tournament_id = 'WC26'")
        conn.execute("COMMIT")
        
    # 2. Define WC26 official-like group structure and scheduled matches
    start_date = date(2026, 6, 11)
    groups_config = {
        "Group A": ["MEX", "RSA", "KOR", "CZE"],
        "Group B": ["CAN", "ITA", "QAT", "SUI"],
        "Group C": ["BRA", "MAR", "HAI", "SCO"],
        "Group D": ["USA", "PAR", "AUS", "TUR"],
        "Group E": ["GER", "CUW", "CIV", "ECU"],
        "Group F": ["NED", "JPN", "SWE", "TUN"],
        "Group G": ["BEL", "EGY", "IRN", "NZL"],
        "Group H": ["ESP", "CPV", "KSA", "URU"],
        "Group I": ["FRA", "SEN", "IRQ", "NOR"],
        "Group J": ["ARG", "ALG", "AUT", "JOR"],
        "Group K": ["POR", "JAM", "UZB", "COL"],
        "Group L": ["ENG", "CRO", "GHA", "PAN"]
    }
    
    wc26_matches = []
    
    for g_idx, (group_name, teams_list) in enumerate(groups_config.items()):
        t1, t2, t3, t4 = teams_list
        md1_date = start_date + timedelta(days=(g_idx // 3))
        md2_date = start_date + timedelta(days=6 + (g_idx // 3))
        md3_date = start_date + timedelta(days=12 + (g_idx // 3))
        
        matchups = [
            (t1, t2, md1_date, 1),
            (t3, t4, md1_date, 2),
            (t1, t3, md2_date, 3),
            (t2, t4, md2_date, 4),
            (t1, t4, md3_date, 5),
            (t2, t3, md3_date, 6)
        ]
        
        for h, a, m_date, match_num in matchups:
            grp_code = group_name.replace("Group ", "")
            match_id = f"WC26_{grp_code}{match_num}"
            
            wc26_matches.append((
                match_id, "WC26", m_date.strftime("%Y-%m-%d"), h, a, None, None, None, None, "Group", "Scheduled"
            ))
            
    matches_df_save = pl.DataFrame(wc26_matches, schema=[
        "match_id", "tournament_id", "match_date", "home_team_id", "away_team_id",
        "home_score", "away_score", "home_penalty_score", "away_penalty_score",
        "match_phase", "status"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT INTO matches SELECT * FROM matches_df_save")
        conn.execute("COMMIT")
        
    print(f"Successfully re-seeded {len(wc26_matches)} scheduled group matches for WC26.")

if __name__ == "__main__":
    seed_wc26()
