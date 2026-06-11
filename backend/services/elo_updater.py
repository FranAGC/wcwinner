"""
Service for updating Team ELO and Form Index after a match is completed or simulated.
"""
from typing import Optional
from datetime import timedelta
from backend.database.repository import FootballRepository
from backend.models.domain import Match, EloHistory

class EloUpdaterService:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()

    def update_after_match(self, match: Match) -> None:
        """
        Calculates and updates the ELO and Form Index for both teams after a match.
        """
        if not match.home_team_id or not match.away_team_id:
            return
        if match.home_score is None or match.away_score is None:
            return

        with self.repo.conn_factory(read_only=True) as conn:
            h_elo_res = conn.execute("SELECT elo_rating FROM elo_history WHERE team_id = ? ORDER BY rating_date DESC LIMIT 1", [match.home_team_id]).fetchone()
            a_elo_res = conn.execute("SELECT elo_rating FROM elo_history WHERE team_id = ? ORDER BY rating_date DESC LIMIT 1", [match.away_team_id]).fetchone()
            
            r_home = h_elo_res[0] if h_elo_res else 1500.0
            r_away = a_elo_res[0] if a_elo_res else 1500.0

            h_form_res = conn.execute("SELECT form_index FROM team_features WHERE team_id = ? ORDER BY as_of_date DESC LIMIT 1", [match.home_team_id]).fetchone()
            a_form_res = conn.execute("SELECT form_index FROM team_features WHERE team_id = ? ORDER BY as_of_date DESC LIMIT 1", [match.away_team_id]).fetchone()
            
            f_home = h_form_res[0] if h_form_res and h_form_res[0] is not None else 0.5
            f_away = a_form_res[0] if a_form_res and a_form_res[0] is not None else 0.5

        # ELO formula
        e_home = 1.0 / (10.0 ** ((r_away - r_home) / 400.0) + 1.0)
        e_away = 1.0 / (10.0 ** ((r_home - r_away) / 400.0) + 1.0)
        
        hs = match.home_score
        as_ = match.away_score
        h_pen = match.home_penalty_score or 0
        a_pen = match.away_penalty_score or 0

        # Match outcome for ELO and Form (penalty wins are technically draws in standard FIFA rules, 
        # but to keep momentum in the tournament, we'll give a slight edge to the penalty winner)
        if hs > as_:
            s_home, s_away = 1.0, 0.0
        elif hs < as_:
            s_home, s_away = 0.0, 1.0
        else:
            if h_pen > a_pen:
                s_home, s_away = 0.75, 0.5
            elif a_pen > h_pen:
                s_home, s_away = 0.5, 0.75
            else:
                s_home, s_away = 0.5, 0.5

        # K factor = 60 for World Cup
        k = 60.0
        
        # Goal difference multiplier
        gd = abs(hs - as_)
        if gd <= 1:
            g = 1.0
        elif gd == 2:
            g = 1.5
        else:
            g = (11.0 + float(gd)) / 8.0
            
        new_r_home = r_home + k * g * (s_home - e_home)
        new_r_away = r_away + k * g * (s_away - e_away)

        new_f_home = f_home * 0.7 + s_home * 0.3
        new_f_away = f_away * 0.7 + s_away * 0.3

        # We save the new rating effective the day AFTER the match, so it's ready for the next matches
        next_day = match.match_date + timedelta(days=1)

        elo_h = EloHistory(rating_date=next_day, team_id=match.home_team_id, elo_rating=new_r_home)
        elo_a = EloHistory(rating_date=next_day, team_id=match.away_team_id, elo_rating=new_r_away)
        
        self.repo.save_elo_rating(elo_h)
        self.repo.save_elo_rating(elo_a)

        # Update team_features by fetching latest, updating elo/form/date, and inserting
        with self.repo.conn_factory(read_only=False) as conn:
            # Home
            h_tf = conn.execute("SELECT * FROM team_features WHERE team_id = ? ORDER BY as_of_date DESC LIMIT 1", [match.home_team_id]).fetchone()
            if h_tf:
                conn.execute(
                    """
                    INSERT INTO team_features (
                        team_id, as_of_date, elo, fifa_rank, attack_strength, defense_strength,
                        avg_goals_scored, avg_goals_conceded, form_index, wc_attack_strength,
                        wc_defense_strength, squad_size, clean_sheet_rate, win_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (team_id, as_of_date) DO UPDATE SET
                        elo = EXCLUDED.elo, form_index = EXCLUDED.form_index
                    """,
                    [h_tf[0], next_day, new_r_home, h_tf[3], h_tf[4], h_tf[5], h_tf[6], h_tf[7], new_f_home, h_tf[9], h_tf[10], h_tf[11], h_tf[12], h_tf[13]]
                )
            
            # Away
            a_tf = conn.execute("SELECT * FROM team_features WHERE team_id = ? ORDER BY as_of_date DESC LIMIT 1", [match.away_team_id]).fetchone()
            if a_tf:
                conn.execute(
                    """
                    INSERT INTO team_features (
                        team_id, as_of_date, elo, fifa_rank, attack_strength, defense_strength,
                        avg_goals_scored, avg_goals_conceded, form_index, wc_attack_strength,
                        wc_defense_strength, squad_size, clean_sheet_rate, win_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (team_id, as_of_date) DO UPDATE SET
                        elo = EXCLUDED.elo, form_index = EXCLUDED.form_index
                    """,
                    [a_tf[0], next_day, new_r_away, a_tf[3], a_tf[4], a_tf[5], a_tf[6], a_tf[7], new_f_away, a_tf[9], a_tf[10], a_tf[11], a_tf[12], a_tf[13]]
                )
