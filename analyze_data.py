import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from backend.database.repository import FootballRepository
import pandas as pd

repo = FootballRepository()

with repo.conn_factory(read_only=True) as conn:
    print("--- DATA QUALITY ANALYSIS ---")
    
    # 1. Team Features
    print("\n1. TEAM FEATURES")
    df_tf = conn.execute("SELECT * FROM team_features").df()
    print(df_tf.describe().to_string())
    print("\nMissing values:")
    print(df_tf.isnull().sum().to_string())
    
    # 2. Match Features
    print("\n2. MATCH FEATURES")
    df_mf = conn.execute("SELECT * FROM match_features").df()
    print(df_mf.describe().to_string())
    print("\nMissing values:")
    print(df_mf.isnull().sum().to_string())
    
    # 3. ELO History
    print("\n3. ELO HISTORY")
    df_elo = conn.execute("SELECT * FROM elo_history").df()
    print(f"Total records: {len(df_elo)}")
    print(df_elo.describe().to_string())
    print("\nMissing values:")
    print(df_elo.isnull().sum().to_string())

    # 4. Players and Squads
    print("\n4. PLAYERS & SQUADS")
    df_players = conn.execute("SELECT * FROM players").df()
    df_squads = conn.execute("SELECT * FROM squad_calls").df()
    print(f"Total players: {len(df_players)}")
    print(f"Total squad calls: {len(df_squads)}")
    print("\nPlayer Ratings Stats:")
    print(df_players['base_rating'].describe().to_string())
    print("\nMissing values in players:")
    print(df_players.isnull().sum().to_string())

