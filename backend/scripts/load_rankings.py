import sys
from pathlib import Path
from datetime import date

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.models.domain import FifaRanking

def populate_rankings():
    repo = FootballRepository()
    print("Loading FIFA rankings...")

    # Define some rankings before WC2022 (circa Oct/Nov 2022) and in 2026
    rankings_data = [
        # --- Pre-World Cup 2022 (Oct 2022) ---
        (date(2022, 10, 6), "BRA", 1841.3, 1),
        (date(2022, 10, 6), "BEL", 1816.7, 2),
        (date(2022, 10, 6), "ARG", 1773.8, 3),
        (date(2022, 10, 6), "FRA", 1759.7, 4),
        (date(2022, 10, 6), "ENG", 1728.4, 5),
        (date(2022, 10, 6), "ITA", 1726.1, 6),
        (date(2022, 10, 6), "ESP", 1715.2, 7),
        (date(2022, 10, 6), "NED", 1694.5, 8),
        (date(2022, 10, 6), "POR", 1676.5, 9),
        (date(2022, 10, 6), "DEN", 1666.5, 10),
        (date(2022, 10, 6), "GER", 1650.2, 11),
        (date(2022, 10, 6), "CRO", 1645.6, 12),
        (date(2022, 10, 6), "MEX", 1644.8, 13),
        (date(2022, 10, 6), "URU", 1638.7, 14),
        (date(2022, 10, 6), "USA", 1627.4, 16),
        (date(2022, 10, 6), "COL", 1611.2, 17),
        (date(2022, 10, 6), "SEN", 1584.3, 18),
        (date(2022, 10, 6), "MAR", 1563.5, 22),
        (date(2022, 10, 6), "JPN", 1559.5, 24),
        (date(2022, 10, 6), "KOR", 1530.3, 28),
        (date(2022, 10, 6), "ECU", 1464.3, 44),
        (date(2022, 10, 6), "QAT", 1439.8, 50),
        (date(2022, 10, 6), "KSA", 1437.7, 51),
        
        # --- Pre-World Cup 2026 (June 2026, mock/current approximation) ---
        (date(2026, 6, 1), "ARG", 1860.5, 1),
        (date(2026, 6, 1), "FRA", 1840.2, 2),
        (date(2026, 6, 1), "BEL", 1795.3, 3),
        (date(2026, 6, 1), "BRA", 1788.1, 4),
        (date(2026, 6, 1), "ENG", 1785.4, 5),
        (date(2026, 6, 1), "POR", 1750.6, 6),
        (date(2026, 6, 1), "NED", 1742.3, 7),
        (date(2026, 6, 1), "ESP", 1730.1, 8),
        (date(2026, 6, 1), "ITA", 1724.5, 9),
        (date(2026, 6, 1), "CRO", 1720.0, 10),
        (date(2026, 6, 1), "USA", 1690.4, 11),
        (date(2026, 6, 1), "COL", 1675.2, 12),
        (date(2026, 6, 1), "MAR", 1668.5, 13),
        (date(2026, 6, 1), "URU", 1665.2, 14),
        (date(2026, 6, 1), "GER", 1655.4, 15),
        (date(2026, 6, 1), "JPN", 1628.7, 16),
        (date(2026, 6, 1), "MEX", 1625.3, 17),
        (date(2026, 6, 1), "SEN", 1620.1, 18),
        (date(2026, 6, 1), "KOR", 1588.2, 22),
        (date(2026, 6, 1), "ECU", 1535.4, 30),
        (date(2026, 6, 1), "QAT", 1502.1, 42),
        (date(2026, 6, 1), "KSA", 1445.6, 55),
    ]

    for r_date, team_id, points, rank in rankings_data:
        # Check if team exists (to prevent foreign key violation)
        if not repo.get_team_by_id(team_id):
            print(f"Skipping ranking for unknown team: {team_id}")
            continue
        
        ranking = FifaRanking(
            ranking_date=r_date,
            team_id=team_id,
            points=points,
            rank=rank
        )
        repo.save_fifa_ranking(ranking)

    print("FIFA rankings loaded successfully!")

if __name__ == "__main__":
    populate_rankings()
