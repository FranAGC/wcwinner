import sys
import os
from pathlib import Path
from datetime import date, datetime, timedelta
import httpx
import polars as pl

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.models.domain import Team

TEAM_NAME_MAP = {
    "Argentina": "ARG",
    "Brazil": "BRA",
    "Uruguay": "URU",
    "Colombia": "COL",
    "Ecuador": "ECU",
    "France": "FRA",
    "England": "ENG",
    "Germany": "GER",
    "Spain": "ESP",
    "Portugal": "POR",
    "Italy": "ITA",
    "Netherlands": "NED",
    "Croatia": "CRO",
    "Belgium": "BEL",
    "United States": "USA",
    "Mexico": "MEX",
    "Canada": "CAN",
    "Morocco": "MAR",
    "Senegal": "SEN",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Korea Republic": "KOR",
    "Australia": "AUS",
    
    # 26 New World Cup 2026 Teams
    "South Africa": "RSA",
    "Czech Republic": "CZE",
    "Czechia": "CZE",
    "Qatar": "QAT",
    "Switzerland": "SUI",
    "Haiti": "HAI",
    "Scotland": "SCO",
    "Paraguay": "PAR",
    "Turkey": "TUR",
    "Türkiye": "TUR",
    "Curaçao": "CUW",
    "Curacao": "CUW",
    "Ivory Coast": "CIV",
    "Côte d'Ivoire": "CIV",
    "Sweden": "SWE",
    "Tunisia": "TUN",
    "Egypt": "EGY",
    "Iran": "IRN",
    "New Zealand": "NZL",
    "Cape Verde": "CPV",
    "Cabo Verde": "CPV",
    "Saudi Arabia": "KSA",
    "Iraq": "IRQ",
    "Norway": "NOR",
    "Algeria": "ALG",
    "Austria": "AUT",
    "Jordan": "JOR",
    "Jamaica": "JAM",
    "Uzbekistan": "UZB",
    "Ghana": "GHA",
    "Panama": "PAN"
}

def populate_initial_data():
    repo = FootballRepository()

    print("Loading competitions and tournaments...")
    # Competitions
    competitions = [
        ("WC", "FIFA World Cup", "International"),
        ("FRIENDLY", "International Friendly", "International"),
        ("COPA_AMERICA", "Copa América", "Continental"),
        ("EURO", "UEFA Euro", "Continental"),
        ("OTHER", "Other Tournament", "International")
    ]
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.executemany(
            """
            INSERT OR REPLACE INTO competitions (competition_id, competition_name, competition_type)
            VALUES (?, ?, ?)
            """,
            competitions
        )
        conn.execute("COMMIT")
    
    # We will collect unique tournaments to insert them in bulk
    unique_tournaments = {
        ("WC22", "WC", 2022, "Qatar"),
        ("WC26", "WC", 2026, "USA, Canada, Mexico"),
        ("FRIENDLY", "FRIENDLY", 2026, "Worldwide")
    }

    print("Loading teams...")
    teams = [
        Team(team_id="ARG", team_name="Argentina", team_code="ARG", confederation="CONMEBOL"),
        Team(team_id="BRA", team_name="Brazil", team_code="BRA", confederation="CONMEBOL"),
        Team(team_id="URU", team_name="Uruguay", team_code="URU", confederation="CONMEBOL"),
        Team(team_id="COL", team_name="Colombia", team_code="COL", confederation="CONMEBOL"),
        Team(team_id="ECU", team_name="Ecuador", team_code="ECU", confederation="CONMEBOL"),
        Team(team_id="FRA", team_name="France", team_code="FRA", confederation="UEFA"),
        Team(team_id="ENG", team_name="England", team_code="ENG", confederation="UEFA"),
        Team(team_id="GER", team_name="Germany", team_code="GER", confederation="UEFA"),
        Team(team_id="ESP", team_name="Spain", team_code="ESP", confederation="UEFA"),
        Team(team_id="POR", team_name="Portugal", team_code="POR", confederation="UEFA"),
        Team(team_id="ITA", team_name="Italy", team_code="ITA", confederation="UEFA"),
        Team(team_id="NED", team_name="Netherlands", team_code="NED", confederation="UEFA"),
        Team(team_id="CRO", team_name="Croatia", team_code="CRO", confederation="UEFA"),
        Team(team_id="BEL", team_name="Belgium", team_code="BEL", confederation="UEFA"),
        Team(team_id="USA", team_name="United States", team_code="USA", confederation="CONCACAF"),
        Team(team_id="MEX", team_name="Mexico", team_code="MEX", confederation="CONCACAF"),
        Team(team_id="CAN", team_name="Canada", team_code="CAN", confederation="CONCACAF"),
        Team(team_id="MAR", team_name="Morocco", team_code="MAR", confederation="CAF"),
        Team(team_id="SEN", team_name="Senegal", team_code="SEN", confederation="CAF"),
        Team(team_id="JPN", team_name="Japan", team_code="JPN", confederation="AFC"),
        Team(team_id="KOR", team_name="South Korea", team_code="KOR", confederation="AFC"),
        Team(team_id="AUS", team_name="Australia", team_code="AUS", confederation="AFC"),
        
        # 26 New World Cup 2026 Teams
        Team(team_id="RSA", team_name="South Africa", team_code="RSA", confederation="CAF"),
        Team(team_id="CZE", team_name="Czechia", team_code="CZE", confederation="UEFA"),
        Team(team_id="QAT", team_name="Qatar", team_code="QAT", confederation="AFC"),
        Team(team_id="SUI", team_name="Switzerland", team_code="SUI", confederation="UEFA"),
        Team(team_id="HAI", team_name="Haiti", team_code="HAI", confederation="CONACAF"),
        Team(team_id="SCO", team_name="Scotland", team_code="SCO", confederation="UEFA"),
        Team(team_id="PAR", team_name="Paraguay", team_code="PAR", confederation="CONMEBOL"),
        Team(team_id="TUR", team_name="Turkey", team_code="TUR", confederation="UEFA"),
        Team(team_id="CUW", team_name="Curaçao", team_code="CUW", confederation="CONACAF"),
        Team(team_id="CIV", team_name="Ivory Coast", team_code="CIV", confederation="CAF"),
        Team(team_id="SWE", team_name="Sweden", team_code="SWE", confederation="UEFA"),
        Team(team_id="TUN", team_name="Tunisia", team_code="TUN", confederation="CAF"),
        Team(team_id="EGY", team_name="Egypt", team_code="EGY", confederation="CAF"),
        Team(team_id="IRN", team_name="Iran", team_code="IRN", confederation="AFC"),
        Team(team_id="NZL", team_name="New Zealand", team_code="NZL", confederation="OFC"),
        Team(team_id="CPV", team_name="Cape Verde", team_code="CPV", confederation="CAF"),
        Team(team_id="KSA", team_name="Saudi Arabia", team_code="KSA", confederation="AFC"),
        Team(team_id="IRQ", team_name="Iraq", team_code="IRQ", confederation="AFC"),
        Team(team_id="NOR", team_name="Norway", team_code="NOR", confederation="UEFA"),
        Team(team_id="ALG", team_name="Algeria", team_code="ALG", confederation="CAF"),
        Team(team_id="AUT", team_name="Austria", team_code="AUT", confederation="UEFA"),
        Team(team_id="JOR", team_name="Jordan", team_code="JOR", confederation="AFC"),
        Team(team_id="JAM", team_name="Jamaica", team_code="JAM", confederation="CONACAF"),
        Team(team_id="UZB", team_name="Uzbekistan", team_code="UZB", confederation="AFC"),
        Team(team_id="GHA", team_name="Ghana", team_code="GHA", confederation="CAF"),
        Team(team_id="PAN", team_name="Panama", team_code="PAN", confederation="CONACAF")
    ]

    for team in teams:
        repo.save_team(team)

    print("Downloading historical matches and shootouts from GitHub...")
    matches_tuples = []
    stats_tuples = []
    
    try:
        res_matches = httpx.get("https://raw.githubusercontent.com/martj42/international_results/master/results.csv")
        res_shootouts = httpx.get("https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv")
        
        if res_matches.status_code != 200 or res_shootouts.status_code != 200:
            raise Exception("Failed to download datasets from GitHub.")
            
        print("Parsing historical matches...")
        matches_df = pl.read_csv(res_matches.content, null_values=["NA", "null", ""])
        shootouts_df = pl.read_csv(res_shootouts.content, null_values=["NA", "null", ""])
        
        # Build shootouts dict
        shootouts_dict = {}
        for row in shootouts_df.iter_rows(named=True):
            shootouts_dict[(row["date"], row["home_team"], row["away_team"])] = row["winner"]
            
        # Parse date and filter to >= 2000-01-01 and non-null scores
        matches_df = matches_df.with_columns(
            pl.col("date").str.to_date("%Y-%m-%d")
        ).filter(
            (pl.col("date") >= date(2000, 1, 1)) &
            (pl.col("home_score").is_not_null()) &
            (pl.col("away_score").is_not_null())
        )
        
        # Optimize by filtering for our target 22 teams in Polars first
        target_team_names = list(TEAM_NAME_MAP.keys())
        matches_df = matches_df.filter(
            pl.col("home_team").is_in(target_team_names) &
            pl.col("away_team").is_in(target_team_names)
        )
        
        print(f"Filtered to {len(matches_df)} target-team matches since 2000.")
        
        print("Starting parsing loop...")
        for idx, row in enumerate(matches_df.iter_rows(named=True)):
            if idx % 1000 == 0:
                print(f"Parsed {idx} rows...")
            h_name = row["home_team"]
            a_name = row["away_team"]
            
            h_code = TEAM_NAME_MAP[h_name]
            a_code = TEAM_NAME_MAP[a_name]
            
            m_date = row["date"]
            m_date_str = m_date.strftime("%Y-%m-%d")
            
            home_score = row["home_score"]
            away_score = row["away_score"]
            
            shootout_winner = shootouts_dict.get((m_date_str, h_name, a_name))
            home_penalty = None
            away_penalty = None
            if shootout_winner:
                if shootout_winner == h_name:
                    home_penalty, away_penalty = 4, 3
                else:
                    home_penalty, away_penalty = 3, 4
            
            tourn_name = row["tournament"]
            country_name = row["country"] or "Unknown"
            if tourn_name == "FIFA World Cup":
                comp_id = "WC"
                tour_id = f"WC{m_date.year % 100:02d}"
                unique_tournaments.add((tour_id, comp_id, m_date.year, country_name))
                phase = "World Cup Group" if "Group" in (row["city"] or "") else "World Cup Knockout"
            elif tourn_name == "Friendly":
                comp_id = "FRIENDLY"
                tour_id = "FRIENDLY"
                phase = "Friendly"
            elif "Copa América" in tourn_name:
                comp_id = "COPA_AMERICA"
                tour_id = f"CA{m_date.year}"
                unique_tournaments.add((tour_id, comp_id, m_date.year, country_name))
                phase = "Copa America"
            elif "UEFA Euro" in tourn_name:
                comp_id = "EURO"
                tour_id = f"EURO{m_date.year}"
                unique_tournaments.add((tour_id, comp_id, m_date.year, country_name))
                phase = "UEFA Euro"
            else:
                comp_id = "OTHER"
                tour_id = "OTHER_HIST"
                unique_tournaments.add((tour_id, comp_id, 2000, "Worldwide"))
                phase = tourn_name[:50]
            
            match_id = f"HIST_{h_code}_{a_code}_{m_date_str.replace('-', '')}"
            
            matches_tuples.append((
                match_id, tour_id, m_date_str, h_code, a_code,
                home_score, away_score, home_penalty, away_penalty,
                phase, "Completed"
            ))
            
            # Stats tuples
            stats_tuples.append((
                match_id, h_code, home_score, 0.50, 12, 4, 4, 12, 1, 0, float(home_score)
            ))
            stats_tuples.append((
                match_id, a_code, away_score, 0.50, 12, 4, 4, 12, 1, 0, float(away_score)
            ))
        print("Parsing loop finished successfully!")
                
    except Exception as e:
        print(f"Warning: Failed to load massive dataset from GitHub ({e}). Using basic fallback.")
        pass

    print("Adding scheduled WC2026 matches...")

    # Add scheduled matches for World Cup 2026 (complete 3-match group stage for Groups A to L)
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
    
    completed_results = {
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
        
        for m_idx, (h, a, m_date, match_num) in enumerate(matchups):
            grp_code = group_name.replace("Group ", "")
            match_id = f"WC26_{grp_code}{match_num}"
            
            res = completed_results.get((h, a)) or completed_results.get((a, h))
            if res:
                if res == completed_results.get((a, h)):
                    h_score, a_score = res[1], res[0]
                else:
                    h_score, a_score = res[0], res[1]
                status = "Completed"
            else:
                h_score, a_score = None, None
                status = "Scheduled"
                
            wc26_matches.append((
                match_id, "WC26", m_date, h, a, h_score, a_score, "Group", status
            ))

    for m_id, tour_id, m_date, home, away, home_score, away_score, phase, status in wc26_matches:
        m_date_str = m_date.strftime("%Y-%m-%d")
        matches_tuples.append((
            m_id, tour_id, m_date_str, home, away, home_score, away_score,
            None, None, phase, status
        ))
        if status == "Completed":
            stats_tuples.append((
                m_id, home, home_score, 0.55, 14, 5, 5, 10, 1, 0, float(home_score)
            ))
            stats_tuples.append((
                m_id, away, away_score, 0.45, 10, 3, 3, 12, 2, 0, float(away_score)
            ))

    # Bulk save to DB in a single transaction using Polars integration
    print(f"Saving {len(matches_tuples)} matches and {len(stats_tuples)} stats to DB...")
    
    tournaments_df = pl.DataFrame(list(unique_tournaments), schema=[
        "tournament_id", "competition_id", "year", "host_country"
    ])
    
    matches_df_save = pl.DataFrame(matches_tuples, schema=[
        "match_id", "tournament_id", "match_date", "home_team_id", "away_team_id",
        "home_score", "away_score", "home_penalty_score", "away_penalty_score",
        "match_phase", "status"
    ])
    
    stats_df_save = pl.DataFrame(stats_tuples, schema=[
        "match_id", "team_id", "goals", "possession", "shots", "shots_on_target",
        "corners", "fouls", "yellow_cards", "red_cards", "expected_goals"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO tournaments SELECT * FROM tournaments_df")
        conn.execute("INSERT OR REPLACE INTO matches SELECT * FROM matches_df_save")
        conn.execute("INSERT OR REPLACE INTO team_match_stats SELECT * FROM stats_df_save")
        conn.execute("COMMIT")

    print(f"Successfully loaded {len(matches_tuples)} total matches in bulk!")

if __name__ == "__main__":
    populate_initial_data()
