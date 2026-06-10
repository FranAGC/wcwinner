import numpy as np
from scipy.stats import poisson
from typing import Dict, Tuple, Any

from backend.database.repository import FootballRepository
from backend.models.domain import MatchFeatures

class MatchProbabilityService:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()

    def predict_match_outcome(self, match_id: str) -> Dict[str, Any]:
        """
        Predicts match probabilities (win, draw, loss) and expected goals
        using a bivariate Poisson model based on team attack/defense strengths.
        """
        # Fetch match features
        with self.repo.conn_factory(read_only=True) as conn:
            res = conn.execute(
                """
                SELECT home_team_id, away_team_id, home_elo, away_elo,
                       home_attack_strength, away_attack_strength,
                       home_defense_strength, away_defense_strength
                FROM match_features WHERE match_id = ?
                """,
                [match_id]
            ).fetchone()
            
        if not res:
            # Fallback if features are not pre-calculated
            return {
                "match_id": match_id,
                "home_win_prob": 0.38,
                "draw_prob": 0.28,
                "away_win_prob": 0.34,
                "expected_home_goals": 1.2,
                "expected_away_goals": 1.1,
                "message": "Fallback default probability (features not found)"
            }
            
        home_team, away_team, h_elo, a_elo, h_att, a_att, h_def, a_def = res
        
        # Base goals
        # In World Cup tournaments, typical average goals per team per match is ~1.3
        base_goals = 1.3
        
        # Expected lambda (goals) for home and away
        # Adjusted by ELO difference as well
        elo_diff = h_elo - a_elo
        elo_factor_home = 1.0 + (elo_diff / 1000.0) # E.g., +200 ELO increases expected goals by 20%
        elo_factor_away = 1.0 - (elo_diff / 1000.0)
        
        lambda_home = max(0.2, base_goals * h_att * a_def * elo_factor_home)
        lambda_away = max(0.2, base_goals * a_att * h_def * elo_factor_away)
        
        # Calculate probabilities for scores up to 10 goals
        max_goals = 10
        score_matrix = np.zeros((max_goals + 1, max_goals + 1))
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                # Poisson probability of home scoring i and away scoring j
                score_matrix[i, j] = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
                
        # Calculate outcomes
        home_win_prob = float(np.sum(np.triu(score_matrix, k=1).T)) # i > j
        away_win_prob = float(np.sum(np.tril(score_matrix, k=-1).T)) # i < j
        draw_prob = float(np.sum(np.diag(score_matrix)))             # i == j
        
        # Normalize to ensure they sum to exactly 1.0
        total_prob = home_win_prob + draw_prob + away_win_prob
        home_win_prob /= total_prob
        draw_prob /= total_prob
        away_win_prob /= total_prob
        
        # Find most likely scoreline
        most_likely_idx = np.unravel_index(np.argmax(score_matrix), score_matrix.shape)
        most_likely_score = f"{most_likely_idx[0]} - {most_likely_idx[1]}"
        
        return {
            "match_id": match_id,
            "home_team_id": home_team,
            "away_team_id": away_team,
            "home_win_prob": home_win_prob,
            "draw_prob": draw_prob,
            "away_win_prob": away_win_prob,
            "expected_home_goals": float(lambda_home),
            "expected_away_goals": float(lambda_away),
            "most_likely_score": most_likely_score,
            "most_likely_score_prob": float(score_matrix[most_likely_idx])
        }
