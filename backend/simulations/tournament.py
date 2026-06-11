"""
Tournament Simulator for WC 2026.

Full bracket:
  Group stage (72) → Round of 32 (32) → Round of 16 (16) →
  Quarterfinals (8) → Semifinals (4) → Final (1)

Advancement rules (real WC2026):
  - Top 2 from each of 12 groups = 24 teams
  - 8 best 3rd-place teams = 8 teams
  - Total 32 teams in Round of 32
"""
import random
import numpy as np
from datetime import date
from typing import List, Dict, Any, Tuple

from backend.database.repository import FootballRepository
from backend.models.domain import Match, TeamMatchStats
from backend.services.probability import MatchProbabilityService

# Official WC2026 group composition (same as load_matches.py)
GROUPS: Dict[str, List[str]] = {
    "A": ["MEX", "RSA", "KOR", "CZE"],
    "B": ["CAN", "ITA", "QAT", "SUI"],
    "C": ["BRA", "MAR", "HAI", "SCO"],
    "D": ["USA", "PAR", "AUS", "TUR"],
    "E": ["GER", "CUW", "CIV", "ECU"],
    "F": ["NED", "JPN", "SWE", "TUN"],
    "G": ["BEL", "EGY", "IRN", "NZL"],
    "H": ["ESP", "CPV", "KSA", "URU"],
    "I": ["FRA", "SEN", "IRQ", "NOR"],
    "J": ["ARG", "ALG", "AUT", "JOR"],
    "K": ["POR", "JAM", "UZB", "COL"],
    "L": ["ENG", "CRO", "GHA", "PAN"],
}

# Round of 32 official bracket seeding (FIFA 2026 format):
# Group winners and runners-up are paired according to the draw
# We pair them as: W_A vs R_B, W_B vs R_A, W_C vs R_D, etc.
R32_BRACKET = [
    ("A", "B", 1),  # match 1:  W_A vs R_B
    ("B", "A", 2),  # match 2:  W_B vs R_A
    ("C", "D", 3),
    ("D", "C", 4),
    ("E", "F", 5),
    ("F", "E", 6),
    ("G", "H", 7),
    ("H", "G", 8),
    ("I", "J", 9),
    ("J", "I", 10),
    ("K", "L", 11),
    ("L", "K", 12),
    # 4 best 3rd-place teams vs the 4 worst R2 spots — simplified pairing
    ("3rd_best", "none", 13),
    ("3rd_2nd",  "none", 14),
    ("3rd_3rd",  "none", 15),
    ("3rd_4th",  "none", 16),
]

# Knockout phase dates (approximate, following WC2026 schedule)
PHASE_DATES = {
    "Round of 32":    date(2026, 6, 28),
    "Round of 16":    date(2026, 7, 2),
    "Quarterfinals":  date(2026, 7, 5),
    "Semifinals":     date(2026, 7, 8),
    "Final":          date(2026, 7, 19),
}


class TournamentSimulator:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()
        self.prob_service = MatchProbabilityService(self.repo)

    # ------------------------------------------------------------------ #
    #  Stat generation (correlated with xG)                               #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generate_stats(team_id: str, match_id: str,
                        goals: int, xg: float, opp_xg: float) -> TeamMatchStats:
        total_xg = xg + opp_xg if (xg + opp_xg) > 0 else 2.0
        possession = round(max(0.32, min(0.68, xg / total_xg)), 2)
        shots = max(3, int(np.random.poisson(max(1, 12 * xg / 1.3))))
        shots_on_target = max(1, min(shots, int(np.random.poisson(max(1, shots * 0.38)))))
        corners = max(0, int(np.random.poisson(4 + 2 * xg)))
        fouls = max(6, int(np.random.poisson(13 - 2 * possession)))
        yellow_cards = max(0, int(np.random.poisson(max(0.1, fouls * 0.12))))
        red_cards = 1 if random.random() < 0.04 else 0
        return TeamMatchStats(
            match_id=match_id, team_id=team_id, goals=goals,
            possession=possession, shots=shots, shots_on_target=shots_on_target,
            corners=corners, fouls=fouls, yellow_cards=yellow_cards, red_cards=red_cards,
            expected_goals=round(float(xg), 3)
        )

    # ------------------------------------------------------------------ #
    #  Single match simulation                                            #
    # ------------------------------------------------------------------ #
    def simulate_match_result(self, match: Match) -> Tuple[int, int, int | None, int | None]:
        prediction = self.prob_service.predict_match_outcome(match.match_id)
        lambda_h = prediction["expected_home_goals"]
        lambda_a = prediction["expected_away_goals"]

        home_score = int(np.random.poisson(lambda_h))
        away_score = int(np.random.poisson(lambda_a))
        home_penalty = away_penalty = None

        # Ties only matter in knockout phases
        if home_score == away_score and match.match_phase not in ("Group",):
            extra_h = int(np.random.poisson(lambda_h * 0.25))
            extra_a = int(np.random.poisson(lambda_a * 0.25))
            home_score += extra_h
            away_score += extra_a

            if home_score == away_score:
                elo_diff = prediction.get("inputs", {}).get("elo_diff", 0)
                h_prob = max(0.3, min(0.7, 0.5 + elo_diff / 2000.0))
                if random.random() < h_prob:
                    home_penalty, away_penalty = 5, 4
                else:
                    home_penalty, away_penalty = 4, 5

        return home_score, away_score, home_penalty, away_penalty

    # ------------------------------------------------------------------ #
    #  Phase simulation (generic)                                         #
    # ------------------------------------------------------------------ #
    def simulate_phase(self, tournament_id: str, phase: str) -> List[Dict[str, Any]]:
        all_matches = self.repo.get_matches()
        phase_matches = [
            m for m in all_matches
            if m.tournament_id == tournament_id
            and m.match_phase.lower() == phase.lower()
            and m.status == "Scheduled"
        ]

        if not phase_matches:
            sim = [m for m in all_matches
                   if m.tournament_id == tournament_id
                   and m.match_phase.lower() == phase.lower()
                   and m.status == "Simulated"]
            if sim:
                return [{"match_id": m.match_id, "status": "Already Simulated"} for m in sim]
            raise ValueError(f"No scheduled matches for {tournament_id} phase {phase}")

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

            h_stats = self._generate_stats(m.home_team_id, m.match_id, h_score, lambda_h, lambda_a)
            a_stats = self._generate_stats(m.away_team_id, m.match_id, a_score, lambda_a, lambda_h)
            self.repo.save_team_match_stats(h_stats)
            self.repo.save_team_match_stats(a_stats)

            winner = (m.home_team_id if (h_score > a_score or (h_pen and h_pen > a_pen))
                      else m.away_team_id)
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
    #  Internal: Compute group standings                                  #
    # ------------------------------------------------------------------ #
    def _compute_group_standings(self, tournament_id: str) -> Dict[str, List[Dict]]:
        """Returns standings per group, sorted by pts/gd/gf/elo."""
        all_matches = self.repo.get_matches()
        group_matches = [m for m in all_matches
                         if m.tournament_id == tournament_id and m.match_phase == "Group"]

        elo_map = self._get_elo_map()
        all_group_teams = [t for g in GROUPS.values() for t in g]
        stats = {t: {"pts": 0, "gf": 0, "ga": 0, "gd": 0} for t in all_group_teams}

        for m in group_matches:
            h, a = m.home_team_id, m.away_team_id
            hs, as_ = m.home_score or 0, m.away_score or 0
            if h not in stats or a not in stats:
                continue
            stats[h]["gf"] += hs; stats[h]["ga"] += as_; stats[h]["gd"] += (hs - as_)
            stats[a]["gf"] += as_; stats[a]["ga"] += hs;  stats[a]["gd"] += (as_ - hs)
            if hs > as_:   stats[h]["pts"] += 3
            elif as_ > hs: stats[a]["pts"] += 3
            else:          stats[h]["pts"] += 1; stats[a]["pts"] += 1

        def sort_key(t):
            s = stats[t]
            return (s["pts"], s["gd"], s["gf"], elo_map.get(t, 1500.0))

        result = {}
        for grp, teams in GROUPS.items():
            sorted_teams = sorted(teams, key=sort_key, reverse=True)
            result[grp] = [{"team_id": t, "rank": i + 1, **stats[t]} for i, t in enumerate(sorted_teams)]
        return result

    def _get_elo_map(self) -> Dict[str, float]:
        with self.repo.conn_factory(read_only=True) as conn:
            rows = conn.execute(
                """WITH rk AS (SELECT team_id, elo_rating,
                                      ROW_NUMBER() OVER(PARTITION BY team_id ORDER BY rating_date DESC) AS rn
                               FROM elo_history)
                   SELECT team_id, elo_rating FROM rk WHERE rn=1"""
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def _winner_of(self, match: Match) -> str:
        hs, as_ = match.home_score or 0, match.away_score or 0
        if hs > as_: return match.home_team_id
        if as_ > hs: return match.away_team_id
        if (match.home_penalty_score or 0) > (match.away_penalty_score or 0): return match.home_team_id
        return match.away_team_id

    # ------------------------------------------------------------------ #
    #  Group → Round of 32                                                #
    # ------------------------------------------------------------------ #
    def advance_group_stage_to_round32(self, tournament_id: str) -> List[Match]:
        all_matches = self.repo.get_matches()
        grp_matches = [m for m in all_matches
                       if m.tournament_id == tournament_id and m.match_phase == "Group"]
        if any(m.status == "Scheduled" for m in grp_matches):
            raise ValueError("Cannot advance: some group matches are still Scheduled.")

        standings = self._compute_group_standings(tournament_id)

        # Top 2 per group (24 teams)
        winners   = {g: standings[g][0]["team_id"] for g in GROUPS}
        runners   = {g: standings[g][1]["team_id"] for g in GROUPS}
        # 3rd-place teams ranked by pts/gd/gf/elo, best 8 advance
        elo_map = self._get_elo_map()
        third_place = []
        for g, s in standings.items():
            t3 = s[2]
            third_place.append((t3["team_id"], t3["pts"], t3["gd"], t3["gf"],
                                 elo_map.get(t3["team_id"], 1500.0)))
        third_place.sort(key=lambda x: (x[1], x[2], x[3], x[4]), reverse=True)
        best_thirds = [t[0] for t in third_place[:8]]

        # Schedule 32 knockout matches
        # Official WC2026 R32 pairing (simplified symmetric bracket):
        # Pairs: W_A-R_B, W_C-R_D, W_E-R_F, W_G-R_H, W_I-R_J, W_K-R_L
        #        W_B-R_A, W_D-R_C, W_F-R_E, W_H-R_G, W_J-R_I, W_L-R_K
        # The 8 best 3rd-place vs positions TBD (fill into remaining slots)
        r32_pairings_winners = [
            (winners["A"], runners["B"]), (winners["C"], runners["D"]),
            (winners["E"], runners["F"]), (winners["G"], runners["H"]),
            (winners["I"], runners["J"]), (winners["K"], runners["L"]),
            (winners["B"], runners["A"]), (winners["D"], runners["C"]),
            (winners["F"], runners["E"]), (winners["H"], runners["G"]),
            (winners["J"], runners["I"]), (winners["L"], runners["K"]),
        ]
        # Best thirds fill remaining 4 spots paired with 4 lowest-seeded group winners
        lower_winners = sorted(
            [winners["C"], winners["D"], winners["I"], winners["J"]],
            key=lambda t: elo_map.get(t, 1500.0)
        )
        third_pairings = list(zip(lower_winners, best_thirds[:4]))

        all_pairings = r32_pairings_winners + third_pairings   # 16 matches

        match_date = PHASE_DATES["Round of 32"]
        new_matches = []
        for i, (h, a) in enumerate(all_pairings, 1):
            m = Match(
                match_id=f"{tournament_id}_R32_M{i}",
                tournament_id=tournament_id,
                match_date=match_date,
                home_team_id=h,
                away_team_id=a,
                match_phase="Round of 32",
                status="Scheduled",
            )
            new_matches.append(m)

        self._upsert_knockout_features(new_matches)
        for m in new_matches:
            self.repo.save_match(m)
        print(f"Scheduled {len(new_matches)} Round of 32 matches for {tournament_id}")
        return new_matches

    # ------------------------------------------------------------------ #
    #  Generic: advance a phase by picking winners                        #
    # ------------------------------------------------------------------ #
    def _advance_knockout_phase(self, tournament_id: str,
                                 from_phase: str, to_phase: str,
                                 match_prefix: str) -> List[Match]:
        all_matches = self.repo.get_matches()
        from_matches = [m for m in all_matches
                        if m.tournament_id == tournament_id and m.match_phase == from_phase]
        if not from_matches:
            raise ValueError(f"No {from_phase} matches found.")
        if any(m.status == "Scheduled" for m in from_matches):
            raise ValueError(f"Cannot advance: some {from_phase} matches are still Scheduled.")

        # Sort by match_id to maintain consistent bracket ordering
        from_matches.sort(key=lambda m: m.match_id)
        winners = [self._winner_of(m) for m in from_matches]

        # Pair winners sequentially: match1_winner vs match2_winner, etc.
        new_matches = []
        match_date = PHASE_DATES[to_phase]
        for i in range(0, len(winners), 2):
            if i + 1 >= len(winners):
                break
            h, a = winners[i], winners[i + 1]
            m = Match(
                match_id=f"{tournament_id}_{match_prefix}{i // 2 + 1}",
                tournament_id=tournament_id,
                match_date=match_date,
                home_team_id=h,
                away_team_id=a,
                match_phase=to_phase,
                status="Scheduled",
            )
            new_matches.append(m)

        self._upsert_knockout_features(new_matches)
        for m in new_matches:
            self.repo.save_match(m)
        print(f"Scheduled {len(new_matches)} {to_phase} matches for {tournament_id}")
        return new_matches

    def advance_round32_to_round16(self, tournament_id: str) -> List[Match]:
        return self._advance_knockout_phase(tournament_id, "Round of 32", "Round of 16", "R16_M")

    def advance_round16_to_quarterfinals(self, tournament_id: str) -> List[Match]:
        return self._advance_knockout_phase(tournament_id, "Round of 16", "Quarterfinals", "QF_M")

    def advance_quarterfinals_to_semifinals(self, tournament_id: str) -> List[Match]:
        return self._advance_knockout_phase(tournament_id, "Quarterfinals", "Semifinals", "SF_M")

    def advance_semifinals_to_final(self, tournament_id: str) -> List[Match]:
        return self._advance_knockout_phase(tournament_id, "Semifinals", "Final", "Final_M")

    # ------------------------------------------------------------------ #
    #  Pre-calculate features for new knockout matches                    #
    # ------------------------------------------------------------------ #
    def _upsert_knockout_features(self, matches: List[Match]) -> None:
        import polars as pl
        with self.repo.conn_factory(read_only=True) as conn:
            tf_rows = conn.execute(
                """SELECT team_id, elo, fifa_rank,
                          attack_strength, defense_strength,
                          form_index, wc_attack_strength, wc_defense_strength, squad_size
                   FROM team_features"""
            ).fetchall()
        tf = {r[0]: r[1:] for r in tf_rows}
        elo_map = self._get_elo_map()

        rows = []
        for m in matches:
            h, a = m.home_team_id, m.away_team_id
            ht = tf.get(h, (1500, 50, 1.0, 1.0, 0.5, 1.0, 1.0, 23))
            at = tf.get(a, (1500, 50, 1.0, 1.0, 0.5, 1.0, 1.0, 23))
            h_elo = elo_map.get(h, ht[0])
            a_elo = elo_map.get(a, at[0])
            rows.append((
                m.match_id, h, a,
                h_elo, a_elo, int(ht[1]), int(at[1]),
                ht[2], at[2], ht[3], at[3],
                h_elo - a_elo, int(ht[1]) - int(at[1]),
                ht[4], at[4],
                ht[5], at[5], ht[6], at[6],
                int(ht[7]), int(at[7]),
                0, 0, 0, 1.2, 1.0,
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
