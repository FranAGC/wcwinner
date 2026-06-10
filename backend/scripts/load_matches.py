import sys
import os
from pathlib import Path
from datetime import date, timedelta

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.models.domain import Team, Match, TeamMatchStats

def populate_initial_data():
    repo = FootballRepository()

    print("Loading competitions and tournaments...")
    # Competitions
    repo.save_competition("WC", "FIFA World Cup", "International")
    repo.save_competition("FRIENDLY", "International Friendly", "International")
    
    # Tournaments
    repo.save_tournament("WC22", "WC", 2022, "Qatar")
    repo.save_tournament("WC26", "WC", 2026, "USA, Canada, Mexico")

    print("Loading teams...")
    # Main international teams
    teams = [
        # CONMEBOL
        Team(team_id="ARG", team_name="Argentina", team_code="ARG", confederation="CONMEBOL"),
        Team(team_id="BRA", team_name="Brazil", team_code="BRA", confederation="CONMEBOL"),
        Team(team_id="URU", team_name="Uruguay", team_code="URU", confederation="CONMEBOL"),
        Team(team_id="COL", team_name="Colombia", team_code="COL", confederation="CONMEBOL"),
        Team(team_id="ECU", team_name="Ecuador", team_code="ECU", confederation="CONMEBOL"),
        # UEFA
        Team(team_id="FRA", team_name="France", team_code="FRA", confederation="UEFA"),
        Team(team_id="ENG", team_name="England", team_code="ENG", confederation="UEFA"),
        Team(team_id="GER", team_name="Germany", team_code="GER", confederation="UEFA"),
        Team(team_id="ESP", team_name="Spain", team_code="ESP", confederation="UEFA"),
        Team(team_id="POR", team_name="Portugal", team_code="POR", confederation="UEFA"),
        Team(team_id="ITA", team_name="Italy", team_code="ITA", confederation="UEFA"),
        Team(team_id="NED", team_name="Netherlands", team_code="NED", confederation="UEFA"),
        Team(team_id="CRO", team_name="Croatia", team_code="CRO", confederation="UEFA"),
        Team(team_id="BEL", team_name="Belgium", team_code="BEL", confederation="UEFA"),
        # CONCACAF
        Team(team_id="USA", team_name="United States", team_code="USA", confederation="CONCACAF"),
        Team(team_id="MEX", team_name="Mexico", team_code="MEX", confederation="CONCACAF"),
        Team(team_id="CAN", team_name="Canada", team_code="CAN", confederation="CONCACAF"),
        # CAF
        Team(team_id="MAR", team_name="Morocco", team_code="MAR", confederation="CAF"),
        Team(team_id="SEN", team_name="Senegal", team_code="SEN", confederation="CAF"),
        # AFC
        Team(team_id="JPN", team_name="Japan", team_code="JPN", confederation="AFC"),
        Team(team_id="KOR", team_name="South Korea", team_code="KOR", confederation="AFC"),
        Team(team_id="AUS", team_name="Australia", team_code="AUS", confederation="AFC"),
    ]

    for team in teams:
        repo.save_team(team)

    print("Loading historical matches (World Cup 2022 representative sample)...")
    # Let's populate some key matches from WC 2022 with stats
    matches_data = [
        # Group Stage
        ("WC22_G1", "WC22", date(2022, 11, 20), "ECU", "QAT", 2, 0, "Group", "Completed",
         {"ECU": (2, 0.53, 6, 3, 4, 15, 1, 0, 1.2), "QAT": (0, 0.47, 5, 0, 1, 15, 3, 0, 0.3)}),
        ("WC22_G2", "WC22", date(2022, 11, 22), "ARG", "KSA", 1, 2, "Group", "Completed",
         {"ARG": (1, 0.70, 15, 6, 9, 7, 2, 0, 2.3), "KSA": (2, 0.30, 3, 2, 2, 21, 6, 0, 0.4)}),
        ("WC22_G3", "WC22", date(2022, 11, 22), "FRA", "AUS", 4, 1, "Group", "Completed",
         {"FRA": (4, 0.63, 23, 7, 8, 5, 0, 0, 4.0), "AUS": (1, 0.37, 4, 1, 1, 11, 3, 0, 0.5)}),
        ("WC22_G4", "WC22", date(2022, 11, 23), "ESP", "CRC", 7, 0, "Group", "Completed",
         {"ESP": (7, 0.82, 17, 8, 5, 8, 0, 0, 3.5), "CRC": (0, 0.18, 0, 0, 0, 12, 2, 0, 0.0)}),
        ("WC22_G5", "WC22", date(2022, 11, 23), "GER", "JPN", 1, 2, "Group", "Completed",
         {"GER": (1, 0.74, 26, 9, 6, 6, 0, 0, 3.1), "JPN": (2, 0.26, 12, 4, 6, 14, 0, 0, 1.4)}),
        ("WC22_G6", "WC22", date(2022, 11, 24), "BRA", "SRB", 2, 0, "Group", "Completed",
         {"BRA": (2, 0.59, 22, 8, 6, 7, 0, 0, 2.4), "SRB": (0, 0.41, 5, 0, 4, 12, 3, 0, 0.2)}),
        ("WC22_G7", "WC22", date(2022, 11, 26), "ARG", "MEX", 2, 0, "Group", "Completed",
         {"ARG": (2, 0.58, 5, 2, 4, 15, 1, 0, 0.3), "MEX": (0, 0.42, 4, 1, 2, 19, 4, 0, 0.2)}),
        ("WC22_G8", "WC22", date(2022, 11, 26), "FRA", "DEN", 2, 1, "Group", "Completed",
         {"FRA": (2, 0.48, 21, 7, 6, 4, 1, 0, 2.4), "DEN": (1, 0.52, 10, 3, 4, 9, 2, 0, 0.8)}),
        ("WC22_G9", "WC22", date(2022, 11, 27), "ESP", "GER", 1, 1, "Group", "Completed",
         {"ESP": (1, 0.64, 7, 3, 6, 13, 1, 0, 0.6), "GER": (1, 0.36, 11, 4, 5, 11, 3, 0, 1.3)}),
        ("WC22_G10", "WC22", date(2022, 11, 28), "BRA", "SUI", 1, 0, "Group", "Completed",
         {"BRA": (1, 0.54, 13, 5, 8, 10, 1, 0, 1.2), "SUI": (0, 0.46, 6, 0, 3, 17, 1, 0, 0.3)}),
         
        # Round of 16
        ("WC22_R16_1", "WC22", date(2022, 12, 3), "NED", "USA", 3, 1, "Round of 16", "Completed",
         {"NED": (3, 0.42, 11, 6, 4, 8, 2, 0, 1.7), "USA": (1, 0.58, 17, 8, 5, 5, 0, 0, 1.5)}),
        ("WC22_R16_2", "WC22", date(2022, 12, 3), "ARG", "AUS", 2, 1, "Round of 16", "Completed",
         {"ARG": (2, 0.61, 14, 5, 1, 8, 0, 0, 1.6), "AUS": (1, 0.39, 5, 1, 3, 15, 3, 0, 0.2)}),
        ("WC22_R16_3", "WC22", date(2022, 12, 4), "FRA", "POL", 3, 1, "Round of 16", "Completed",
         {"FRA": (3, 0.55, 16, 8, 7, 10, 0, 0, 2.1), "POL": (1, 0.45, 12, 3, 1, 8, 1, 0, 1.0)}),
        ("WC22_R16_4", "WC22", date(2022, 12, 5), "BRA", "KOR", 4, 1, "Round of 16", "Completed",
         {"BRA": (4, 0.53, 18, 9, 5, 8, 0, 0, 3.6), "KOR": (1, 0.47, 8, 6, 4, 11, 0, 0, 0.6)}),
        ("WC22_R16_5", "WC22", date(2022, 12, 6), "MAR", "ESP", 0, 0, "Round of 16", "Completed",
         {"MAR": (0, 0.23, 6, 2, 0, 11, 1, 0, 0.7), "ESP": (0, 0.77, 13, 1, 4, 14, 1, 0, 0.9)}), # Penalties MAR 3-0 ESP
         
        # Quarterfinals
        ("WC22_QF1", "WC22", date(2022, 12, 9), "CRO", "BRA", 1, 1, "Quarterfinals", "Completed",
         {"CRO": (1, 0.51, 9, 1, 3, 22, 2, 0, 0.6), "BRA": (1, 0.49, 21, 11, 7, 24, 3, 0, 2.6)}), # Penalties CRO 4-2 BRA
        ("WC22_QF2", "WC22", date(2022, 12, 9), "NED", "ARG", 2, 2, "Quarterfinals", "Completed",
         {"NED": (2, 0.52, 6, 2, 2, 30, 6, 0, 0.6), "ARG": (2, 0.48, 14, 5, 8, 18, 10, 0, 1.9)}), # Penalties ARG 4-3 NED
        ("WC22_QF3", "WC22", date(2022, 12, 10), "MAR", "POR", 1, 0, "Quarterfinals", "Completed",
         {"MAR": (1, 0.27, 9, 3, 3, 15, 3, 1, 1.4), "POR": (0, 0.73, 12, 3, 4, 9, 3, 0, 0.9)}),
        ("WC22_QF4", "WC22", date(2022, 12, 10), "ENG", "FRA", 1, 2, "Quarterfinals", "Completed",
         {"ENG": (1, 0.58, 16, 8, 5, 10, 1, 0, 2.4), "FRA": (2, 0.42, 8, 5, 2, 14, 3, 0, 0.9)}),
         
        # Semifinals
        ("WC22_SF1", "WC22", date(2022, 12, 13), "ARG", "CRO", 3, 0, "Semifinals", "Completed",
         {"ARG": (3, 0.39, 9, 7, 2, 8, 2, 0, 2.3), "CRO": (0, 0.61, 12, 3, 4, 8, 2, 0, 0.5)}),
        ("WC22_SF2", "WC22", date(2022, 12, 14), "FRA", "MAR", 2, 0, "Semifinals", "Completed",
         {"FRA": (2, 0.39, 14, 3, 2, 10, 0, 0, 2.0), "MAR": (0, 0.61, 13, 3, 3, 11, 3, 0, 0.9)}),
         
        # Final
        ("WC22_F", "WC22", date(2022, 12, 18), "ARG", "FRA", 3, 3, "Final", "Completed",
         {"ARG": (3, 0.54, 20, 10, 6, 26, 4, 0, 3.3), "FRA": (3, 0.46, 10, 5, 5, 19, 3, 0, 2.2)}) # Penalties ARG 4-2 FRA
    ]

    for match_id, tour_id, m_date, home, away, home_score, away_score, phase, status, stats_dict in matches_data:
        # Save match
        home_penalty = None
        away_penalty = None
        
        # Add penalty details for draws in knockout stages
        if match_id == "WC22_R16_5": # MAR-ESP
            home_penalty, away_penalty = 3, 0
        elif match_id == "WC22_QF1": # CRO-BRA
            home_penalty, away_penalty = 4, 2
        elif match_id == "WC22_QF2": # NED-ARG
            home_penalty, away_penalty = 3, 4
        elif match_id == "WC22_F": # ARG-FRA
            home_penalty, away_penalty = 4, 2

        # In DuckDB, if QAT or SRB are not in teams table, let's register them dynamically
        for t_id in [home, away]:
            if not repo.get_team_by_id(t_id):
                # Save team dummy
                dummy_team = Team(team_id=t_id, team_name=t_id, team_code=t_id, confederation="UEFA" if t_id in ["SRB", "DEN", "POL"] else "AFC" if t_id in ["QAT", "KSA"] else "CONCACAF" if t_id == "CRC" else "CAF")
                repo.save_team(dummy_team)

        match_model = Match(
            match_id=match_id, tournament_id=tour_id, match_date=m_date,
            home_team_id=home, away_team_id=away, home_score=home_score, away_score=away_score,
            home_penalty_score=home_penalty, away_penalty_score=away_penalty,
            match_phase=phase, status=status
        )
        repo.save_match(match_model)

        # Save stats
        for t_id, stats in stats_dict.items():
            goals, possession, shots, sot, corners, fouls, yc, rc, xg = stats
            stats_model = TeamMatchStats(
                match_id=match_id, team_id=t_id, goals=goals, possession=possession,
                shots=shots, shots_on_target=sot, corners=corners, fouls=fouls,
                yellow_cards=yc, red_cards=rc, expected_goals=xg
            )
            repo.save_team_match_stats(stats_model)

    print("Loading scheduled matches for World Cup 2026...")
    # Create some mock scheduled matches for WC2026 to show prediction flow
    # Since World Cup 2026 will start in June 2026, we will set them in June/July 2026
    start_date = date(2026, 6, 11)
    wc26_matches = [
        # Group A
        ("WC26_A1", "WC26", start_date, "USA", "COL", None, None, "Group", "Scheduled"),
        ("WC26_A2", "WC26", start_date + timedelta(days=1), "MEX", "ECU", None, None, "Group", "Scheduled"),
        ("WC26_A3", "WC26", start_date + timedelta(days=5), "USA", "ECU", None, None, "Group", "Scheduled"),
        ("WC26_A4", "WC26", start_date + timedelta(days=6), "MEX", "COL", None, None, "Group", "Scheduled"),
        # Group B
        ("WC26_B1", "WC26", start_date + timedelta(days=2), "ARG", "MAR", None, None, "Group", "Scheduled"),
        ("WC26_B2", "WC26", start_date + timedelta(days=2), "FRA", "JPN", None, None, "Group", "Scheduled"),
        ("WC26_B3", "WC26", start_date + timedelta(days=7), "ARG", "JPN", None, None, "Group", "Scheduled"),
        ("WC26_B4", "WC26", start_date + timedelta(days=7), "FRA", "MAR", None, None, "Group", "Scheduled"),
        # Group C
        ("WC26_C1", "WC26", start_date + timedelta(days=3), "BRA", "ENG", None, None, "Group", "Scheduled"),
        ("WC26_C2", "WC26", start_date + timedelta(days=3), "ESP", "SEN", None, None, "Group", "Scheduled"),
        ("WC26_C3", "WC26", start_date + timedelta(days=8), "BRA", "SEN", None, None, "Group", "Scheduled"),
        ("WC26_C4", "WC26", start_date + timedelta(days=8), "ESP", "ENG", None, None, "Group", "Scheduled"),
    ]

    for match_id, tour_id, m_date, home, away, home_score, away_score, phase, status in wc26_matches:
        match_model = Match(
            match_id=match_id, tournament_id=tour_id, match_date=m_date,
            home_team_id=home, away_team_id=away, home_score=home_score, away_score=away_score,
            home_penalty_score=None, away_penalty_score=None,
            match_phase=phase, status=status
        )
        repo.save_match(match_model)

    print(f"Data loading complete! Total matches: {len(repo.get_matches())}")

if __name__ == "__main__":
    populate_initial_data()
