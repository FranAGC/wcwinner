import sys
from pathlib import Path
from datetime import date, datetime
import httpx
import polars as pl

# Add the project directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository

def populate_players():
    repo = FootballRepository()
    print("Loading players and squad calls...")

    # 1. Get list of valid teams from our database
    valid_teams = {t.team_id for t in repo.get_teams()}
    if not valid_teams:
        print("No teams found. Run load_matches.py first.")
        return

    # 2. Download squads and players datasets
    print("Downloading squads dataset from GitHub...")
    squads_url = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/squads.csv"
    squads_df = pl.read_csv(squads_url)

    print("Downloading players dataset from GitHub...")
    players_url = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/players.csv"
    players_df = pl.read_csv(players_url)

    # 3. Join datasets to get player details and birth dates
    print("Joining and parsing players and squad calls...")
    joined_df = squads_df.join(players_df, on="player_id", how="left")

    # Filter to only contain target teams and tournaments from 2002 onwards
    target_tournaments = {"WC-2002", "WC-2006", "WC-2010", "WC-2014", "WC-2018", "WC-2022"}
    filtered_df = joined_df.filter(
        (pl.col("team_code").is_in(valid_teams)) &
        (pl.col("tournament_id").is_in(target_tournaments))
    )

    # 4. Standardize positions
    # Mapping of position codes/names to our standard categories
    pos_map = {
        "goalkeeper": "Goalkeeper",
        "defender": "Defender",
        "midfielder": "Midfielder",
        "forward": "Forward"
    }

    # 5. Extract and format Player records
    # Concatenate given_name and family_name
    filtered_df = filtered_df.with_columns(
        pl.concat_str(
            [pl.col("given_name").fill_null(""), pl.col("family_name").fill_null("")],
            separator=" "
        ).str.strip_chars().alias("player_name"),
        pl.col("position_name").str.to_lowercase().map_elements(lambda x: pos_map.get(x, "Midfielder"), return_dtype=pl.String).alias("standard_position"),
        pl.col("birth_date").str.strptime(pl.Date, format="%Y-%m-%d", strict=False)
    )

    # Find the unique list of players
    unique_players_df = filtered_df.unique(subset=["player_id"]).select([
        "player_id", "player_name", "birth_date", "standard_position"
    ])

    player_tuples = []
    for row in unique_players_df.iter_rows(named=True):
        b_date = row["birth_date"]
        # Format date as YYYY-MM-DD string or None
        b_date_str = b_date.strftime("%Y-%m-%d") if b_date is not None else None
        player_tuples.append((
            row["player_id"],
            row["player_name"],
            b_date_str,
            row["standard_position"],
            None # Club name is not in the squads dataset, setting to None
        ))

    # 6. Extract and format SquadCall records
    squad_calls_df = filtered_df.select([
        "tournament_id", "team_code", "player_id", "shirt_number"
    ]).unique(subset=["tournament_id", "team_code", "player_id"])

    call_tuples = []
    # Helper to map tournament ID
    def map_tour_id(tid: str) -> str:
        # e.g., WC-2022 -> WC22
        year_part = tid.split("-")[-1]
        return f"WC{year_part[-2:]}"

    for row in squad_calls_df.iter_rows(named=True):
        tour_id = map_tour_id(row["tournament_id"])
        call_tuples.append((
            tour_id,
            row["team_code"],
            row["player_id"],
            row["shirt_number"]
        ))

    # 7. Pre-populate anticipated WC 2026 rosters by cloning WC 2022 rosters
    # This ensures every team has a roster during WC 2026 simulation!
    wc22_calls = squad_calls_df.filter(pl.col("tournament_id") == "WC-2022")
    for row in wc22_calls.iter_rows(named=True):
        call_tuples.append((
            "WC26",
            row["team_code"],
            row["player_id"],
            row["shirt_number"]
        ))

    # 8. Save everything to the database in a single transaction using Polars integration
    print(f"Saving {len(player_tuples)} players and {len(call_tuples)} squad calls to DB...")
    
    players_df_save = pl.DataFrame(player_tuples, schema=[
        "player_id", "player_name", "birth_date", "position", "club"
    ])
    
    calls_df_save = pl.DataFrame(call_tuples, schema=[
        "tournament_id", "team_id", "player_id", "jersey_number"
    ])
    
    with repo.conn_factory(read_only=False) as conn:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("INSERT OR REPLACE INTO players SELECT * FROM players_df_save")
        conn.execute("INSERT OR REPLACE INTO squad_calls SELECT * FROM calls_df_save")
        conn.execute("COMMIT")

    print(f"Successfully loaded {len(player_tuples)} players and {len(call_tuples)} squad calls in bulk!")

if __name__ == "__main__":
    populate_players()
