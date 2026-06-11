"""
Tournament Simulator for WC 2026.

Improvements over previous version:
- Uses the full ensemble prediction (ELO + Poisson + Form/H2H) for all matches.
- Generates realistic match statistics correlated with expected goals:
  shots, shots on target, possession, fouls, cards — all scaled to xG.
- Penalty shootout uses ELO-weighted coin flip (unchanged).
- Group advancement correctly ranks all 12 groups.
"""
import random
import numpy as np
from datetime import date
from typing import List, Dict, Any, Tuple

from backend.database.repository import FootballRepository
from backend.models.domain import Match, TeamMatchStats
from backend.services.probability import MatchProbabilityService


class TournamentSimulator:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()
        self.prob_service = MatchProbabilityService(self.repo)

    # ------------------------------------------------------------------ #
    #  Realistic stat generation                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _generate_stats(team_id: str, match_id: str,
                        goals: int, xg: float,
                        opp_xg: float) -> TeamMatchStats:
        """
        Generate plausible match statistics correlated with expected goals.
        xg    — expected goals for this team
        opp_xg — expected goals for the opponent (used for possession estimate)
        """
        # Possession: proportional to attack pressure (xg-based proxy)
        total_xg = xg + opp_xg if (xg + opp_xg) > 0 else 2.0
        possession = round(max(0.32, min(0.68, xg / total_xg)), 2)

        # Shots: WC average ~12 per team; scale with xg
        shots = max(3, int(np.random.poisson(max(1, 12 * xg / 1.3))))
        shots_on_target = max(1, min(shots, int(np.random.poisson(max(1, shots * 0.38)))))
        corners = max(0, int(np.random.poisson(4 + 2 * xg)))
        fouls = max(6, int(np.random.poisson(13 - 2 * possession)))  # teams with low possession foul more
        yellow_cards = max(0, int(np.random.poisson(max(0.1, fouls * 0.12))))
        red_cards = 1 if random.random() < 0.04 else 0  # ~4% chance

        return TeamMatchStats(
            match_id=match_id,
            team_id=team_id,
            goals=goals,
            possession=possession,
            shots=shots,
            shots_on_target=shots_on_target,
            corners=corners,
            fouls=fouls,
            yellow_cards=yellow_cards,
            red_cards=red_cards,
            expected_goals=round(float(xg), 3)
        )

    # ------------------------------------------------------------------ #
    #  Single match simulation                                            #
    # ------------------------------------------------------------------ #

    def simulate_match_result(self, match: Match) -> Tuple[int, int, int | None, int | None]:
        """
        Simulates goals for a scheduled match.
        Returns (home_score, away_score, home_penalty, away_penalty).
        """
        prediction = self.prob_service.predict_match_outcome(match.match_id)
        lambda_h = prediction["expected_home_goals"]
        lambda_a = prediction["expected_away_goals"]

        # Draw from Poisson distribution
        home_score = int(np.random.poisson(lambda_h))
        away_score = int(np.random.poisson(lambda_a))

        home_penalty = None
        away_penalty = None

        # Handle ties in knockout stages
        if home_score == away_score and match.match_phase not in ("Group",):
            # Extra-time (30 min ≈ 25% of a full match)
            extra_h = int(np.random.poisson(lambda_h * 0.25))
            extra_a = int(np.random.poisson(lambda_a * 0.25))
            home_score += extra_h
            away_score += extra_a

            if home_score == away_score:
                # Penalty shootout — ELO gives slight edge
                h_elo = prediction.get("inputs", {}).get("elo_diff", 0)
                h_prob = 0.5 + h_elo / 2000.0
                h_prob = max(0.3, min(0.7, h_prob))
                if random.random() < h_prob:
                    home_penalty, away_penalty = 5, 4
                else:
                    home_penalty, away_penalty = 4, 5

        return home_score, away_score, home_penalty, away_penalty

    # ------------------------------------------------------------------ #
    #  Phase simulation                                                   #
    # ------------------------------------------------------------------ #

    def simulate_phase(self, tournament_id: str, phase: str) -> List[Dict[str, Any]]:
        """
        Finds all Scheduled matches for the given tournament + phase,
        simulates them, updates the DB, and returns results.
        """
        all_matches = self.repo.get_matches()
        phase_matches = [
            m for m in all_matches
            if m.tournament_id == tournament_id
            and m.match_phase.lower() == phase.lower()
            and m.status == "Scheduled"
        ]

        if not phase_matches:
            sim_matches = [
                m for m in all_matches
                if m.tournament_id == tournament_id
                and m.match_phase.lower() == phase.lower()
                and m.status == "Simulated"
            ]
            if sim_matches:
                return [{"match_id": m.match_id, "status": "Already Simulated"} for m in sim_matches]
            raise ValueError(
                f"No scheduled matches found for tournament {tournament_id} phase {phase}"
            )

        results = []
        for m in phase_matches:
            prediction = self.prob_service.predict_match_outcome(m.match_id)
            lambda_h = prediction["expected_home_goals"]
            lambda_a = prediction["expected_away_goals"]

            h_score, a_score, h_pen, a_pen = self.simulate_match_result(m)

            m.home_score = h_score
            m.away_score = a_score
            m.home_penalty_score = h_pen
            m.away_penalty_score = a_pen
            m.status = "Simulated"
            self.repo.save_match(m)

            # Generate realistic stats using the pre-computed xG lambdas
            h_stats = self._generate_stats(m.home_team_id, m.match_id, h_score, lambda_h, lambda_a)
            a_stats = self._generate_stats(m.away_team_id, m.match_id, a_score, lambda_a, lambda_h)
            self.repo.save_team_match_stats(h_stats)
            self.repo.save_team_match_stats(a_stats)

            winner = (
                m.home_team_id if (h_score > a_score or (h_pen and h_pen > a_pen))
                else m.away_team_id
            )
            results.append({
                "match_id": m.match_id,
                "home_team_id": m.home_team_id,
                "away_team_id": m.away_team_id,
                "home_score": h_score,
                "away_score": a_score,
                "home_penalty_score": h_pen,
                "away_penalty_score": a_pen,
                "winner": winner,
                "home_win_prob": prediction["home_win_prob"],
                "draw_prob": prediction["draw_prob"],
                "away_win_prob": prediction["away_win_prob"],
                "confidence_pct": prediction.get("confidence_pct"),
            })

        return results

    # ------------------------------------------------------------------ #
    #  Group → Knockout advancement                                       #
    # ------------------------------------------------------------------ #

    def advance_group_stage_to_knockout(self, tournament_id: str) -> List[Match]:
        """
        Calculates group stage standings across all 12 groups,
        ranks the top 4 group winners overall, and creates Semifinal matches.
        Tiebreakers: points → goal difference → goals for → ELO (last resort).
        """
        all_matches = self.repo.get_matches()
        group_matches = [
            m for m in all_matches
            if m.tournament_id == tournament_id and m.match_phase == "Group"
        ]

        if any(m.status == "Scheduled" for m in group_matches):
            raise ValueError(
                "Cannot advance: some group stage matches are still Scheduled and not simulated."
            )

        groups = {
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
            "Group L": ["ENG", "CRO", "GHA", "PAN"],
        }

        all_group_teams = [t for g in groups.values() for t in g]
        standings = {t: {"points": 0, "gf": 0, "ga": 0, "gd": 0} for t in all_group_teams}

        for m in group_matches:
            h, a = m.home_team_id, m.away_team_id
            hs, as_ = m.home_score or 0, m.away_score or 0

            if h not in standings or a not in standings:
                continue

            standings[h]["gf"] += hs
            standings[h]["ga"] += as_
            standings[h]["gd"] += (hs - as_)
            standings[a]["gf"] += as_
            standings[a]["ga"] += hs
            standings[a]["gd"] += (as_ - hs)

            if hs > as_:
                standings[h]["points"] += 3
            elif hs < as_:
                standings[a]["points"] += 3
            else:
                standings[h]["points"] += 1
                standings[a]["points"] += 1

        # Fetch ELOs for last-resort tiebreaker
        elo_map: Dict[str, float] = {}
        with self.repo.conn_factory(read_only=True) as conn:
            rows = conn.execute(
                """
                WITH rk AS (
                    SELECT team_id, elo_rating,
                           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY rating_date DESC) AS rn
                    FROM elo_history
                )
                SELECT team_id, elo_rating FROM rk WHERE rn = 1
                """
            ).fetchall()
            elo_map = {r[0]: r[1] for r in rows}

        def sort_key(t):
            s = standings[t]
            return (s["points"], s["gd"], s["gf"], elo_map.get(t, 1500.0))

        group_winners = []
        for g_name, g_teams in groups.items():
            sorted_teams = sorted(g_teams, key=sort_key, reverse=True)
            group_winners.append(sorted_teams[0])

        # Top 4 group winners overall → Semifinals
        top_4 = sorted(group_winners, key=sort_key, reverse=True)[:4]

        sf_matches = [
            Match(
                match_id=f"{tournament_id}_SF1",
                tournament_id=tournament_id,
                match_date=date(2026, 7, 5),
                home_team_id=top_4[0],
                away_team_id=top_4[1],
                match_phase="Semifinals",
                status="Scheduled",
            ),
            Match(
                match_id=f"{tournament_id}_SF2",
                tournament_id=tournament_id,
                match_date=date(2026, 7, 6),
                home_team_id=top_4[2],
                away_team_id=top_4[3],
                match_phase="Semifinals",
                status="Scheduled",
            ),
        ]

        # Pre-calculate features for the new semifinal matches so the predictor works immediately
        self._upsert_knockout_features(sf_matches)

        for m in sf_matches:
            self.repo.save_match(m)

        print(f"Generated Semifinals for {tournament_id}: {top_4}")
        return sf_matches

    # ------------------------------------------------------------------ #
    #  Semifinals → Final advancement                                     #
    # ------------------------------------------------------------------ #

    def advance_semifinals_to_final(self, tournament_id: str) -> List[Match]:
        all_matches = self.repo.get_matches()
        sf_matches = [
            m for m in all_matches
            if m.tournament_id == tournament_id and m.match_phase == "Semifinals"
        ]

        if any(m.status == "Scheduled" for m in sf_matches):
            raise ValueError("Cannot advance: some Semifinals are still Scheduled.")

        winners = []
        for m in sf_matches:
            hs, as_ = m.home_score or 0, m.away_score or 0
            if hs > as_:
                winners.append(m.home_team_id)
            elif as_ > hs:
                winners.append(m.away_team_id)
            else:
                if (m.home_penalty_score or 0) > (m.away_penalty_score or 0):
                    winners.append(m.home_team_id)
                else:
                    winners.append(m.away_team_id)

        final_match = Match(
            match_id=f"{tournament_id}_Final",
            tournament_id=tournament_id,
            match_date=date(2026, 7, 12),
            home_team_id=winners[0],
            away_team_id=winners[1],
            match_phase="Final",
            status="Scheduled",
        )

        self._upsert_knockout_features([final_match])
        self.repo.save_match(final_match)
        print(f"Generated Final for {tournament_id}: {winners[0]} vs {winners[1]}")
        return [final_match]

    # ------------------------------------------------------------------ #
    #  Helper: pre-calculate features for newly-created knockout matches  #
    # ------------------------------------------------------------------ #

    def _upsert_knockout_features(self, matches: List[Match]) -> None:
        """
        For freshly-created knockout matches (which don't yet have match_features rows),
        copy the relevant team features so the predictor can work immediately.
        """
        import polars as pl

        with self.repo.conn_factory(read_only=True) as conn:
            tf_rows = conn.execute(
                """
                SELECT team_id, elo, fifa_rank,
                       attack_strength, defense_strength,
                       form_index, wc_attack_strength, wc_defense_strength, squad_size
                FROM team_features
                """
            ).fetchall()
        tf = {r[0]: r[1:] for r in tf_rows}

        with self.repo.conn_factory(read_only=True) as conn:
            elo_rows = conn.execute(
                """
                WITH rk AS (
                    SELECT team_id, elo_rating,
                           ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY rating_date DESC) AS rn
                    FROM elo_history
                )
                SELECT team_id, elo_rating FROM rk WHERE rn = 1
                """
            ).fetchall()
        elo_map = {r[0]: r[1] for r in elo_rows}

        rows = []
        for m in matches:
            h, a = m.home_team_id, m.away_team_id
            h_tf = tf.get(h, (1500, 50, 1.0, 1.0, 0.5, 1.0, 1.0, 23))
            a_tf = tf.get(a, (1500, 50, 1.0, 1.0, 0.5, 1.0, 1.0, 23))
            h_elo = elo_map.get(h, h_tf[0])
            a_elo = elo_map.get(a, a_tf[0])
            rows.append((
                m.match_id, h, a,
                h_elo, a_elo,
                int(h_tf[1]), int(a_tf[1]),
                h_tf[2], a_tf[2],
                h_tf[3], a_tf[3],
                h_elo - a_elo, int(h_tf[1]) - int(a_tf[1]),
                h_tf[4], a_tf[4],
                h_tf[5], a_tf[5],
                h_tf[6], a_tf[6],
                int(h_tf[7]), int(a_tf[7]),
                0, 0, 0, 1.2, 1.0,  # no H2H data for new matches
            ))

        df = pl.DataFrame(rows, orient="row", schema=[
            "match_id", "home_team_id", "away_team_id",
            "home_elo", "away_elo", "home_fifa_rank", "away_fifa_rank",
            "home_attack_strength", "away_attack_strength",
            "home_defense_strength", "away_defense_strength",
            "elo_diff", "rank_diff",
            "home_form_index", "away_form_index",
            "home_wc_attack", "away_wc_attack",
            "home_wc_defense", "away_wc_defense",
            "home_squad_size", "away_squad_size",
            "h2h_home_wins", "h2h_away_wins", "h2h_draws",
            "h2h_home_goals_avg", "h2h_away_goals_avg",
        ])

        with self.repo.conn_factory(read_only=False) as conn:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("INSERT OR REPLACE INTO match_features SELECT * FROM df")
            conn.execute("COMMIT")
