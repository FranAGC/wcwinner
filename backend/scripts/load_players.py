import sys
from pathlib import Path
from datetime import date

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.models.domain import Player, SquadCall

def populate_players():
    repo = FootballRepository()
    print("Loading players and squad calls...")

    # Key players
    players_data = [
        # Argentina
        ("ARG_1", "Lionel Messi", date(1987, 6, 24), "Forward", "Inter Miami CF"),
        ("ARG_2", "Lautaro Martínez", date(1997, 8, 22), "Forward", "Inter Milan"),
        ("ARG_3", "Rodrigo De Paul", date(1994, 5, 24), "Midfielder", "Atlético Madrid"),
        ("ARG_4", "Emiliano Martínez", date(1992, 9, 2), "Goalkeeper", "Aston Villa"),
        # France
        ("FRA_1", "Kylian Mbappé", date(1998, 12, 20), "Forward", "Real Madrid"),
        ("FRA_2", "Antoine Griezmann", date(1991, 3, 21), "Forward", "Atlético Madrid"),
        ("FRA_3", "Aurélien Tchouaméni", date(2000, 1, 27), "Midfielder", "Real Madrid"),
        ("FRA_4", "Mike Maignan", date(1995, 7, 3), "Goalkeeper", "AC Milan"),
        # Brazil
        ("BRA_1", "Vinícius Júnior", date(2000, 7, 12), "Forward", "Real Madrid"),
        ("BRA_2", "Rodrygo", date(2001, 1, 9), "Forward", "Real Madrid"),
        ("BRA_3", "Bruno Guimarães", date(1997, 11, 16), "Midfielder", "Newcastle United"),
        ("BRA_4", "Alisson Becker", date(1992, 10, 2), "Goalkeeper", "Liverpool"),
        # England
        ("ENG_1", "Harry Kane", date(1993, 7, 28), "Forward", "Bayern Munich"),
        ("ENG_2", "Jude Bellingham", date(2003, 6, 29), "Midfielder", "Real Madrid"),
        ("ENG_3", "Bukayo Saka", date(2001, 9, 5), "Forward", "Arsenal"),
        ("ENG_4", "Jordan Pickford", date(1994, 3, 7), "Goalkeeper", "Everton"),
        # USA
        ("USA_1", "Christian Pulisic", date(1998, 9, 18), "Forward", "AC Milan"),
        ("USA_2", "Weston McKennie", date(1998, 8, 28), "Midfielder", "Juventus"),
        ("USA_3", "Tyler Adams", date(1999, 2, 14), "Midfielder", "Bournemouth"),
        ("USA_4", "Matt Turner", date(1994, 6, 24), "Goalkeeper", "Crystal Palace"),
    ]

    for p_id, name, b_date, pos, club in players_data:
        player = Player(
            player_id=p_id,
            player_name=name,
            birth_date=b_date,
            position=pos,
            club=club
        )
        repo.save_player(player)

    # Squad Calls for WC2022 and WC2026
    squads_data = [
        # WC 2022 Calls
        ("WC22", "ARG", "ARG_1", 10),
        ("WC22", "ARG", "ARG_2", 22),
        ("WC22", "ARG", "ARG_3", 7),
        ("WC22", "ARG", "ARG_4", 23),
        
        ("WC22", "FRA", "FRA_1", 10),
        ("WC22", "FRA", "FRA_2", 7),
        ("WC22", "FRA", "FRA_3", 8),
        
        ("WC22", "BRA", "BRA_1", 20),
        ("WC22", "BRA", "BRA_4", 1),
        
        ("WC22", "ENG", "ENG_1", 9),
        ("WC22", "ENG", "ENG_4", 1),
        
        ("WC22", "USA", "USA_1", 10),
        ("WC22", "USA", "USA_2", 8),
        ("WC22", "USA", "USA_3", 4),
        ("WC22", "USA", "USA_4", 1),

        # WC 2026 Calls (anticipated)
        ("WC26", "ARG", "ARG_1", 10),
        ("WC26", "ARG", "ARG_2", 22),
        ("WC26", "ARG", "ARG_3", 7),
        ("WC26", "ARG", "ARG_4", 23),
        
        ("WC26", "FRA", "FRA_1", 10),
        ("WC26", "FRA", "FRA_3", 8),
        ("WC26", "FRA", "FRA_4", 1),
        
        ("WC26", "BRA", "BRA_1", 10),
        ("WC26", "BRA", "BRA_2", 11),
        ("WC26", "BRA", "BRA_3", 5),
        ("WC26", "BRA", "BRA_4", 1),
        
        ("WC26", "ENG", "ENG_1", 9),
        ("WC26", "ENG", "ENG_2", 10),
        ("WC26", "ENG", "ENG_3", 7),
        ("WC26", "ENG", "ENG_4", 1),
        
        ("WC26", "USA", "USA_1", 10),
        ("WC26", "USA", "USA_2", 8),
        ("WC26", "USA", "USA_3", 4),
        ("WC26", "USA", "USA_4", 1),
    ]

    for tour_id, team_id, player_id, jersey in squads_data:
        # Check if team and player exist
        if not repo.get_team_by_id(team_id):
            continue
        
        call = SquadCall(
            tournament_id=tour_id,
            team_id=team_id,
            player_id=player_id,
            jersey_number=jersey
        )
        repo.save_squad_call(call)

    print("Players and squad calls loaded successfully!")

if __name__ == "__main__":
    populate_players()
