"""
Enhanced Match Probability Service for WC 2026 Simulation.

Algorithm: Ensemble of three components weighted at inference time:

1. **Bivariate Poisson (60%)** — Primary model.
   lambda_home/away driven by attack/defense strengths (WC-weighted), ELO difference,
   form index, and H2H goal averages.

2. **ELO Win Probability (25%)** — Classic ELO formula gives a clean signal for
   expected win/draw/loss that is calibrated across all international football.

3. **Rank & Form Adjustment (15%)** — Corrects for cases where ELO and Poisson disagree
   with recent form and FIFA rank positioning.

Referee/neutrality note: All WC 2026 matches are on neutral ground (USA/CAN/MEX),
so NO home-field advantage is added to the expected goals.
"""
import numpy as np
from scipy.stats import poisson
from typing import Dict, Any

from backend.database.repository import FootballRepository


class MatchProbabilityService:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _elo_win_prob(elo_h: float, elo_a: float) -> tuple[float, float, float]:
        """
        Convert ELO difference to (win, draw, loss) probability for the home team.
        Uses the standard ELO expected-score formula and distributes the remaining
        probability between win and draw proportionally.
        """
        # Expected score [0-1] for home team
        e = 1.0 / (1.0 + 10.0 ** ((elo_a - elo_h) / 400.0))
        # Draw probability is highest around e=0.5 and shrinks toward extremes
        draw_base = 0.28 * (1 - abs(e - 0.5) * 2)
        draw_p = max(0.08, min(0.32, draw_base))
        win_p = e * (1 - draw_p)
        loss_p = (1 - e) * (1 - draw_p)
        # Normalise
        total = win_p + draw_p + loss_p
        return win_p / total, draw_p / total, loss_p / total

    @staticmethod
    def _poisson_score_matrix(lambda_h: float, lambda_a: float, max_goals: int = 10):
        score_matrix = np.zeros((max_goals + 1, max_goals + 1))
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                score_matrix[i, j] = poisson.pmf(i, lambda_h) * poisson.pmf(j, lambda_a)
        return score_matrix

    @staticmethod
    def _probs_from_matrix(score_matrix) -> tuple[float, float, float]:
        home_win = float(np.sum(np.tril(score_matrix, k=-1).T))
        away_win = float(np.sum(np.triu(score_matrix, k=1).T))
        draw = float(np.sum(np.diag(score_matrix)))
        total = home_win + draw + away_win
        return home_win / total, draw / total, away_win / total

    # ------------------------------------------------------------------ #
    #  Main prediction method                                              #
    # ------------------------------------------------------------------ #

    def predict_match_outcome(self, match_id: str) -> Dict[str, Any]:
        """
        Predict win/draw/loss probabilities and expected goals for a match using
        an ensemble of Bivariate Poisson + ELO probability + form/rank adjustment.
        Returns a rich dict including confidence and breakdown of each component.
        """
        with self.repo.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT
                    home_team_id, away_team_id,
                    home_elo, away_elo,
                    home_attack_strength, away_attack_strength,
                    home_defense_strength, away_defense_strength,
                    elo_diff,
                    home_form_index, away_form_index,
                    home_wc_attack, away_wc_attack,
                    home_wc_defense, away_wc_defense,
                    home_squad_size, away_squad_size,
                    h2h_home_wins, h2h_away_wins, h2h_draws,
                    h2h_home_goals_avg, h2h_away_goals_avg
                FROM match_features WHERE match_id = ?
                """,
                [match_id]
            ).fetchone()

        if not res:
            return {
                "match_id": match_id,
                "home_win_prob": 0.38,
                "draw_prob": 0.28,
                "away_win_prob": 0.34,
                "expected_home_goals": 1.2,
                "expected_away_goals": 1.1,
                "message": "Fallback default probability (features not found)"
            }

        (home_team, away_team,
         h_elo, a_elo,
         h_att, a_att,
         h_def, a_def,
         elo_diff,
         h_form, a_form,
         h_wc_att, a_wc_att,
         h_wc_def, a_wc_def,
         h_squad, a_squad,
         h2h_hw, h2h_aw, h2h_d,
         h2h_hg, h2h_ag) = res

        # Fetch Average Player Ratings (Micro-level data)
        with self.repo.conn_factory(read_only=True) as conn:
            h_rating = conn.execute("SELECT AVG(base_rating) FROM players p JOIN squad_calls s ON p.player_id = s.player_id WHERE s.team_id = ?", [home_team]).fetchone()[0] or 70.0
            a_rating = conn.execute("SELECT AVG(base_rating) FROM players p JOIN squad_calls s ON p.player_id = s.player_id WHERE s.team_id = ?", [away_team]).fetchone()[0] or 70.0
        
        # Player rating delta factor (-0.2 to +0.2 roughly)
        player_edge = (h_rating - a_rating) / 100.0

        # -------------------------------------------------------------- #
        # 1. BIVARIATE POISSON COMPONENT                                  #
        # -------------------------------------------------------------- #
        # WC base goal rate per team per match
        base_goals_wc = 1.3

        # Blend overall vs WC-specific strengths (60% WC, 40% overall)
        h_blended_att = 0.6 * (h_wc_att or 1.0) + 0.4 * (h_att or 1.0)
        a_blended_att = 0.6 * (a_wc_att or 1.0) + 0.4 * (a_att or 1.0)
        h_blended_def = 0.6 * (h_wc_def or 1.0) + 0.4 * (h_def or 1.0)
        a_blended_def = 0.6 * (a_wc_def or 1.0) + 0.4 * (a_def or 1.0)

        # ELO-derived goal scaling factor (softened vs. previous implementation)
        elo_scale = elo_diff / 800.0   # ±200 ELO → ±25% goal scaling
        elo_factor_h = 1.0 + max(-0.4, min(0.4, elo_scale))
        elo_factor_a = 1.0 - max(-0.4, min(0.4, elo_scale))

        # Form adjustment: recent form (0-1) mapped to ±15% goal scaling
        # A team at 0.0 form loses 15%, at 1.0 gains 15%
        form_factor_h = 0.85 + 0.30 * (h_form or 0.5)
        form_factor_a = 0.85 + 0.30 * (a_form or 0.5)

        # Base lambda purely from attack/defense interaction
        lambda_h_base = base_goals_wc * h_blended_att * a_blended_def * elo_factor_h * form_factor_h
        lambda_a_base = base_goals_wc * a_blended_att * h_blended_def * elo_factor_a * form_factor_a

        # Head-to-head adjustment (blend if enough data: ≥3 meetings)
        h2h_total = (h2h_hw or 0) + (h2h_aw or 0) + (h2h_d or 0)
        h2h_weight = min(0.30, h2h_total * 0.06)  # max 30% h2h influence at 5+ meetings
        if h2h_total >= 3 and h2h_hg and h2h_ag:
            h2h_ratio = h2h_hg / h2h_ag if h2h_ag > 0 else 1.0
            # Blend: lambda leans toward historical ratio
            lambda_h = (1 - h2h_weight) * lambda_h_base + h2h_weight * (h2h_hg or 1.2)
            lambda_a = (1 - h2h_weight) * lambda_a_base + h2h_weight * (h2h_ag or 1.0)
        else:
            lambda_h = lambda_h_base
            lambda_a = lambda_a_base

        lambda_h = max(0.3, lambda_h)
        lambda_a = max(0.3, lambda_a)

        score_matrix = self._poisson_score_matrix(lambda_h, lambda_a)
        p_hw_poisson, p_d_poisson, p_aw_poisson = self._probs_from_matrix(score_matrix)

        # -------------------------------------------------------------- #
        # 2. ELO COMPONENT                                                #
        # -------------------------------------------------------------- #
        p_hw_elo, p_d_elo, p_aw_elo = self._elo_win_prob(h_elo or 1500, a_elo or 1500)

        # -------------------------------------------------------------- #
        # 3. RANK + FORM ADJUSTMENT COMPONENT                             #
        # -------------------------------------------------------------- #
        # Use form index difference as a soft signal
        form_delta = (h_form or 0.5) - (a_form or 0.5)       # range ≈ -1 to +1
        # Positive means home team is in better form
        # Squad depth: larger squad suggests more depth/fitness
        squad_delta = ((h_squad or 23) - (a_squad or 23)) / 23.0
        # H2H dominance
        h2h_edge = 0.0
        if h2h_total >= 3:
            h2h_edge = ((h2h_hw or 0) - (h2h_aw or 0)) / h2h_total  # range -1 to +1

        # Composite Edge blends macro (Form, H2H) with micro (Player Ratings, Squad Size)
        composite_edge = 0.35 * form_delta + 0.3 * player_edge + 0.25 * h2h_edge + 0.1 * squad_delta
        # Map composite edge to probability adjustment
        # edge ≈ +0.2 → +4% home win, -2% draw, -2% away win
        p_hw_adj = max(0.05, min(0.9, 0.38 + 0.20 * composite_edge))
        p_d_adj  = max(0.05, min(0.5, 0.28 - 0.05 * abs(composite_edge)))
        p_aw_adj = max(0.05, min(0.9, 1.0 - p_hw_adj - p_d_adj))
        # Normalise
        adj_total = p_hw_adj + p_d_adj + p_aw_adj
        p_hw_adj /= adj_total
        p_d_adj  /= adj_total
        p_aw_adj /= adj_total

        # -------------------------------------------------------------- #
        # ENSEMBLE WEIGHTS                                                 #
        # -------------------------------------------------------------- #
        W_POISSON = 0.60
        W_ELO     = 0.25
        W_ADJ     = 0.15

        home_win_prob = W_POISSON * p_hw_poisson + W_ELO * p_hw_elo + W_ADJ * p_hw_adj
        draw_prob     = W_POISSON * p_d_poisson  + W_ELO * p_d_elo  + W_ADJ * p_d_adj
        away_win_prob = W_POISSON * p_aw_poisson + W_ELO * p_aw_elo + W_ADJ * p_aw_adj

        # Final normalisation (should already sum to ~1, but guard against float drift)
        total = home_win_prob + draw_prob + away_win_prob
        home_win_prob /= total
        draw_prob     /= total
        away_win_prob /= total

        # Most likely scoreline from Poisson matrix
        most_likely_idx = tuple(np.unravel_index(np.argmax(score_matrix), score_matrix.shape))
        most_likely_score = f"{most_likely_idx[0]} - {most_likely_idx[1]}"

        # Confidence = how far the prediction is from a uniform 33/33/33 split
        max_p = max(home_win_prob, draw_prob, away_win_prob)
        confidence = round((max_p - 0.333) / 0.667 * 100, 1)  # 0–100 scale

        return {
            "match_id": match_id,
            "home_team_id": home_team,
            "away_team_id": away_team,
            "home_win_prob": round(home_win_prob, 4),
            "draw_prob":     round(draw_prob, 4),
            "away_win_prob": round(away_win_prob, 4),
            "expected_home_goals": round(float(lambda_h), 3),
            "expected_away_goals": round(float(lambda_a), 3),
            "most_likely_score": most_likely_score,
            "most_likely_score_prob": round(float(score_matrix[most_likely_idx]), 4),
            "confidence_pct": confidence,
            "components": {
                "poisson":  {"home_win": round(p_hw_poisson, 4), "draw": round(p_d_poisson, 4), "away_win": round(p_aw_poisson, 4)},
                "elo":      {"home_win": round(p_hw_elo, 4),     "draw": round(p_d_elo, 4),     "away_win": round(p_aw_elo, 4)},
                "form_adj": {"home_win": round(p_hw_adj, 4),     "draw": round(p_d_adj, 4),     "away_win": round(p_aw_adj, 4)},
            },
            "inputs": {
                "elo_diff": round(elo_diff or 0, 1),
                "home_form": round(h_form or 0.5, 3),
                "away_form": round(a_form or 0.5, 3),
                "h2h_meetings": h2h_total,
                "h2h_home_wins": h2h_hw or 0,
                "h2h_away_wins": h2h_aw or 0,
                "h2h_draws": h2h_d or 0,
            }
        }
