import duckdb
import polars as pl
from typing import List, Optional, Dict, Any
from datetime import date
from backend.database.connection import get_connection
from backend.models.domain import Team, Match, TeamMatchStats, FifaRanking, EloHistory, TeamFeatures, MatchFeatures, Player, SquadCall

class FootballRepository:
    def __init__(self, conn_factory=get_connection):
        self.conn_factory = conn_factory

    # --- TEAM OPERATIONS ---
    def get_teams(self) -> List[Team]:
        """Get all teams as Pydantic models."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute("SELECT team_id, team_name, team_code, confederation FROM teams").fetchall()
            return [Team(team_id=r[0], team_name=r[1], team_code=r[2], confederation=r[3]) for r in res]

    def get_teams_df(self) -> pl.DataFrame:
        """Get all teams as a Polars DataFrame."""
        with self.conn_factory(read_only=True) as conn:
            return conn.query("SELECT * FROM teams").pl()

    def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get a team by ID."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                "SELECT team_id, team_name, team_code, confederation FROM teams WHERE team_id = ?", 
                [team_id]
            ).fetchone()
            if res:
                return Team(team_id=res[0], team_name=res[1], team_code=res[2], confederation=res[3])
            return None

    def save_team(self, team: Team) -> None:
        """Save a single team (upsert)."""
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO teams (team_id, team_name, team_code, confederation) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT (team_id) DO NOTHING
                """,
                [team.team_id, team.team_name, team.team_code, team.confederation]
            )

    # --- MATCH OPERATIONS ---
    def get_matches(self) -> List[Match]:
        """Get all matches as Pydantic models."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT match_id, tournament_id, match_date, home_team_id, away_team_id, 
                       home_score, away_score, home_penalty_score, away_penalty_score, 
                       match_phase, status 
                FROM matches
                ORDER BY match_date ASC
                """
            ).fetchall()
            return [
                Match(
                    match_id=r[0], tournament_id=r[1], match_date=r[2], 
                    home_team_id=r[3], away_team_id=r[4], home_score=r[5], 
                    away_score=r[6], home_penalty_score=r[7], away_penalty_score=r[8], 
                    match_phase=r[9], status=r[10]
                ) for r in res
            ]

    def get_matches_df(self) -> pl.DataFrame:
        """Get all matches as a Polars DataFrame."""
        with self.conn_factory(read_only=True) as conn:
            return conn.query("SELECT * FROM matches ORDER BY match_date ASC").pl()

    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get a single match by ID."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT match_id, tournament_id, match_date, home_team_id, away_team_id, 
                       home_score, away_score, home_penalty_score, away_penalty_score, 
                       match_phase, status 
                FROM matches WHERE match_id = ?
                """,
                [match_id]
            ).fetchone()
            if res:
                return Match(
                    match_id=res[0], tournament_id=res[1], match_date=res[2], 
                    home_team_id=res[3], away_team_id=res[4], home_score=res[5], 
                    away_score=res[6], home_penalty_score=res[7], away_penalty_score=res[8], 
                    match_phase=res[9], status=res[10]
                )
            return None

    def save_match(self, m: Match) -> None:
        """Save a single match (upsert)."""
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO matches (
                    match_id, tournament_id, match_date, home_team_id, away_team_id, 
                    home_score, away_score, home_penalty_score, away_penalty_score, 
                    match_phase, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (match_id) DO UPDATE SET
                    tournament_id = EXCLUDED.tournament_id,
                    match_date = EXCLUDED.match_date,
                    home_team_id = EXCLUDED.home_team_id,
                    away_team_id = EXCLUDED.away_team_id,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    home_penalty_score = EXCLUDED.home_penalty_score,
                    away_penalty_score = EXCLUDED.away_penalty_score,
                    match_phase = EXCLUDED.match_phase,
                    status = EXCLUDED.status
                """,
                [m.match_id, m.tournament_id, m.match_date, m.home_team_id, m.away_team_id,
                 m.home_score, m.away_score, m.home_penalty_score, m.away_penalty_score,
                 m.match_phase, m.status]
            )

    # --- COMPETITION & TOURNAMENT OPERATIONS ---
    def save_competition(self, comp_id: str, name: str, comp_type: str) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO competitions (competition_id, competition_name, competition_type)
                VALUES (?, ?, ?) ON CONFLICT DO NOTHING
                """,
                [comp_id, name, comp_type]
            )

    def save_tournament(self, tour_id: str, comp_id: str, year: int, host: str) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO tournaments (tournament_id, competition_id, year, host_country)
                VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING
                """,
                [tour_id, comp_id, year, host]
            )

    # --- TEAM MATCH STATS ---
    def get_match_stats(self, match_id: str) -> List[TeamMatchStats]:
        """Get match statistics for both teams in a match."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT match_id, team_id, goals, possession, shots, shots_on_target, 
                       corners, fouls, yellow_cards, red_cards, expected_goals
                FROM team_match_stats WHERE match_id = ?
                """,
                [match_id]
            ).fetchall()
            return [
                TeamMatchStats(
                    match_id=r[0], team_id=r[1], goals=r[2], possession=r[3],
                    shots=r[4], shots_on_target=r[5], corners=r[6], fouls=r[7],
                    yellow_cards=r[8], red_cards=r[9], expected_goals=r[10]
                ) for r in res
            ]

    def save_team_match_stats(self, stats: TeamMatchStats) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO team_match_stats (
                    match_id, team_id, goals, possession, shots, shots_on_target,
                    corners, fouls, yellow_cards, red_cards, expected_goals
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (match_id, team_id) DO UPDATE SET
                    goals = EXCLUDED.goals,
                    possession = EXCLUDED.possession,
                    shots = EXCLUDED.shots,
                    shots_on_target = EXCLUDED.shots_on_target,
                    corners = EXCLUDED.corners,
                    fouls = EXCLUDED.fouls,
                    yellow_cards = EXCLUDED.yellow_cards,
                    red_cards = EXCLUDED.red_cards,
                    expected_goals = EXCLUDED.expected_goals
                """,
                [stats.match_id, stats.team_id, stats.goals, stats.possession, stats.shots,
                 stats.shots_on_target, stats.corners, stats.fouls, stats.yellow_cards,
                 stats.red_cards, stats.expected_goals]
            )

    # --- FIFA RANKINGS ---
    def get_latest_rankings(self) -> List[FifaRanking]:
        """Get the latest ranking for each team."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                WITH ranked AS (
                    SELECT ranking_date, team_id, points, rank,
                           ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY ranking_date DESC) as rn
                    FROM fifa_rankings
                )
                SELECT ranking_date, team_id, points, rank
                FROM ranked WHERE rn = 1
                ORDER BY rank ASC
                """
            ).fetchall()
            return [FifaRanking(ranking_date=r[0], team_id=r[1], points=r[2], rank=r[3]) for r in res]

    def get_latest_rankings_df(self) -> pl.DataFrame:
        with self.conn_factory(read_only=True) as conn:
            return conn.query(
                """
                WITH ranked AS (
                    SELECT ranking_date, team_id, points, rank,
                           ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY ranking_date DESC) as rn
                    FROM fifa_rankings
                )
                SELECT ranking_date, team_id, points, rank
                FROM ranked WHERE rn = 1
                ORDER BY rank ASC
                """
            ).pl()

    def save_fifa_ranking(self, r: FifaRanking) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO fifa_rankings (ranking_date, team_id, points, rank)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (ranking_date, team_id) DO UPDATE SET
                    points = EXCLUDED.points,
                    rank = EXCLUDED.rank
                """,
                [r.ranking_date, r.team_id, r.points, r.rank]
            )

    # --- ELO HISTORY ---
    def get_latest_elo(self) -> List[EloHistory]:
        """Get the latest ELO rating for all teams."""
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                WITH ranked AS (
                    SELECT rating_date, team_id, elo_rating,
                           ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY rating_date DESC) as rn
                    FROM elo_history
                )
                SELECT rating_date, team_id, elo_rating
                FROM ranked WHERE rn = 1
                ORDER BY elo_rating DESC
                """
            ).fetchall()
            return [EloHistory(rating_date=r[0], team_id=r[1], elo_rating=r[2]) for r in res]

    def get_latest_elo_df(self) -> pl.DataFrame:
        with self.conn_factory(read_only=True) as conn:
            return conn.query(
                """
                WITH ranked AS (
                    SELECT rating_date, team_id, elo_rating,
                           ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY rating_date DESC) as rn
                    FROM elo_history
                )
                SELECT rating_date, team_id, elo_rating
                FROM ranked WHERE rn = 1
                ORDER BY elo_rating DESC
                """
            ).pl()

    def get_elo_history_df(self, team_id: str) -> pl.DataFrame:
        """Get ELO rating history for a specific team."""
        with self.conn_factory(read_only=True) as conn:
            return conn.query(
                "SELECT * FROM elo_history WHERE team_id = ? ORDER BY rating_date ASC",
                [team_id]
            ).pl()

    def save_elo_rating(self, e: EloHistory) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO elo_history (rating_date, team_id, elo_rating)
                VALUES (?, ?, ?)
                ON CONFLICT (rating_date, team_id) DO UPDATE SET
                    elo_rating = EXCLUDED.elo_rating
                """,
                [e.rating_date, e.team_id, e.elo_rating]
            )

    # --- FEATURES ---
    def save_team_features(self, f: TeamFeatures) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO team_features (
                    team_id, as_of_date, elo, fifa_rank, attack_strength,
                    defense_strength, avg_goals_scored, avg_goals_conceded, form_index,
                    wc_attack_strength, wc_defense_strength, squad_size, clean_sheet_rate, win_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (team_id, as_of_date) DO UPDATE SET
                    elo = EXCLUDED.elo,
                    fifa_rank = EXCLUDED.fifa_rank,
                    attack_strength = EXCLUDED.attack_strength,
                    defense_strength = EXCLUDED.defense_strength,
                    avg_goals_scored = EXCLUDED.avg_goals_scored,
                    avg_goals_conceded = EXCLUDED.avg_goals_conceded,
                    form_index = EXCLUDED.form_index,
                    wc_attack_strength = EXCLUDED.wc_attack_strength,
                    wc_defense_strength = EXCLUDED.wc_defense_strength,
                    squad_size = EXCLUDED.squad_size,
                    clean_sheet_rate = EXCLUDED.clean_sheet_rate,
                    win_rate = EXCLUDED.win_rate
                """,
                [f.team_id, f.as_of_date, f.elo, f.fifa_rank, f.attack_strength,
                 f.defense_strength, f.avg_goals_scored, f.avg_goals_conceded, f.form_index,
                 f.wc_attack_strength, f.wc_defense_strength, f.squad_size,
                 f.clean_sheet_rate, f.win_rate]
            )

    def save_match_features(self, f: MatchFeatures) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO match_features (
                    match_id, home_team_id, away_team_id, home_elo, away_elo,
                    home_fifa_rank, away_fifa_rank, home_attack_strength, away_attack_strength,
                    home_defense_strength, away_defense_strength, elo_diff, rank_diff,
                    home_form_index, away_form_index,
                    home_wc_attack, away_wc_attack, home_wc_defense, away_wc_defense,
                    home_squad_size, away_squad_size,
                    h2h_home_wins, h2h_away_wins, h2h_draws,
                    h2h_home_goals_avg, h2h_away_goals_avg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (match_id) DO UPDATE SET
                    home_elo = EXCLUDED.home_elo,
                    away_elo = EXCLUDED.away_elo,
                    home_fifa_rank = EXCLUDED.home_fifa_rank,
                    away_fifa_rank = EXCLUDED.away_fifa_rank,
                    home_attack_strength = EXCLUDED.home_attack_strength,
                    away_attack_strength = EXCLUDED.away_attack_strength,
                    home_defense_strength = EXCLUDED.home_defense_strength,
                    away_defense_strength = EXCLUDED.away_defense_strength,
                    elo_diff = EXCLUDED.elo_diff,
                    rank_diff = EXCLUDED.rank_diff,
                    home_form_index = EXCLUDED.home_form_index,
                    away_form_index = EXCLUDED.away_form_index,
                    home_wc_attack = EXCLUDED.home_wc_attack,
                    away_wc_attack = EXCLUDED.away_wc_attack,
                    home_wc_defense = EXCLUDED.home_wc_defense,
                    away_wc_defense = EXCLUDED.away_wc_defense,
                    home_squad_size = EXCLUDED.home_squad_size,
                    away_squad_size = EXCLUDED.away_squad_size,
                    h2h_home_wins = EXCLUDED.h2h_home_wins,
                    h2h_away_wins = EXCLUDED.h2h_away_wins,
                    h2h_draws = EXCLUDED.h2h_draws,
                    h2h_home_goals_avg = EXCLUDED.h2h_home_goals_avg,
                    h2h_away_goals_avg = EXCLUDED.h2h_away_goals_avg
                """,
                [f.match_id, f.home_team_id, f.away_team_id, f.home_elo, f.away_elo,
                 f.home_fifa_rank, f.away_fifa_rank, f.home_attack_strength, f.away_attack_strength,
                 f.home_defense_strength, f.away_defense_strength, f.elo_diff, f.rank_diff,
                 f.home_form_index, f.away_form_index,
                 f.home_wc_attack, f.away_wc_attack, f.home_wc_defense, f.away_wc_defense,
                 f.home_squad_size, f.away_squad_size,
                 f.h2h_home_wins, f.h2h_away_wins, f.h2h_draws,
                 f.h2h_home_goals_avg, f.h2h_away_goals_avg]
            )
            
    # --- PLAYERS & SQUAD CALLS ---
    def save_player(self, p: Player) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO players (player_id, player_name, birth_date, position, club)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    birth_date = EXCLUDED.birth_date,
                    position = EXCLUDED.position,
                    club = EXCLUDED.club
                """,
                [p.player_id, p.player_name, p.birth_date, p.position, p.club]
            )

    def save_squad_call(self, sc: SquadCall) -> None:
        with self.conn_factory(read_only=False) as conn:
            conn.execute(
                """
                INSERT INTO squad_calls (tournament_id, team_id, player_id, jersey_number)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (tournament_id, team_id, player_id) DO UPDATE SET
                    jersey_number = EXCLUDED.jersey_number
                """,
                [sc.tournament_id, sc.team_id, sc.player_id, sc.jersey_number]
            )
            
    def get_squad_players(self, tournament_id: str, team_id: str) -> List[Dict[str, Any]]:
        with self.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT p.player_id, p.player_name, p.birth_date, p.position, p.club, sc.jersey_number
                FROM squad_calls sc
                JOIN players p ON sc.player_id = p.player_id
                WHERE sc.tournament_id = ? AND sc.team_id = ?
                ORDER BY sc.jersey_number ASC
                """,
                [tournament_id, team_id]
            ).fetchall()
            return [
                {
                    "player_id": r[0],
                    "player_name": r[1],
                    "birth_date": r[2],
                    "position": r[3],
                    "club": r[4],
                    "jersey_number": r[5]
                } for r in res
            ]
