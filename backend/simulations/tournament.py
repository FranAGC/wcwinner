import random
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple

from backend.database.repository import FootballRepository
from backend.models.domain import Match, TeamMatchStats
from backend.services.probability import MatchProbabilityService

class TournamentSimulator:
    def __init__(self, repo: FootballRepository = None):
        self.repo = repo or FootballRepository()
        self.prob_service = MatchProbabilityService(self.repo)

    def simulate_match_result(self, match: Match) -> Tuple[int, int, int, int]:
        """
        Simulates goals for a scheduled match.
        Returns (home_score, away_score, home_penalty, away_penalty).
        """
        # Get expected lambda goals
        prediction = self.prob_service.predict_match_outcome(match.match_id)
        lambda_h = prediction["expected_home_goals"]
        lambda_a = prediction["expected_away_goals"]
        
        # Draw from Poisson distribution
        home_score = int(np.random.poisson(lambda_h))
        away_score = int(np.random.poisson(lambda_a))
        
        home_penalty = None
        away_penalty = None
        
        # Handle ties in knockout stages (anything other than Group phase)
        if home_score == away_score and match.match_phase != "Group":
            # 120' extra time simulation (simple add-on of goals)
            extra_h = int(np.random.poisson(lambda_h * 0.25))
            extra_a = int(np.random.poisson(lambda_a * 0.25))
            home_score += extra_h
            away_score += extra_a
            
            # If still tied, simulate penalty shootout
            if home_score == away_score:
                # ELO advantage can slightly tilt penalty shootout (e.g. composure)
                h_elo = prediction.get("home_elo", 1500.0)
                a_elo = prediction.get("away_elo", 1500.0)
                h_prob = 0.5 + (h_elo - a_elo) / 2000.0
                h_prob = max(0.3, min(0.7, h_prob))
                
                # Penalty scores (e.g., typical 4-3, 5-4 etc)
                if random.random() < h_prob:
                    home_penalty, away_penalty = 5, 4
                else:
                    home_penalty, away_penalty = 4, 5
                    
        return home_score, away_score, home_penalty, away_penalty

    def simulate_phase(self, tournament_id: str, phase: str) -> List[Dict[str, Any]]:
        """
        Finds all scheduled matches for the given tournament and phase,
        simulates them, updates the database, and returns the results.
        """
        # 1. Fetch all matches of this phase in scheduled status
        all_matches = self.repo.get_matches()
        phase_matches = [
            m for m in all_matches 
            if m.tournament_id == tournament_id 
            and m.match_phase.lower() == phase.lower() 
            and m.status == "Scheduled"
        ]
        
        if not phase_matches:
            # Maybe already simulated? Check if simulated ones exist
            sim_matches = [
                m for m in all_matches 
                if m.tournament_id == tournament_id 
                and m.match_phase.lower() == phase.lower() 
                and m.status == "Simulated"
            ]
            if sim_matches:
                print(f"Phase {phase} has already been simulated.")
                return [{"match_id": m.match_id, "status": "Already Simulated"} for m in sim_matches]
            raise ValueError(f"No scheduled matches found for tournament {tournament_id} phase {phase}")

        results = []
        for m in phase_matches:
            h_score, a_score, h_pen, a_pen = self.simulate_match_result(m)
            
            # Update Match model
            m.home_score = h_score
            m.away_score = a_score
            m.home_penalty_score = h_pen
            m.away_penalty_score = a_pen
            m.status = "Simulated"
            self.repo.save_match(m)
            
            # Save statistics
            h_stats = TeamMatchStats(
                match_id=m.match_id, team_id=m.home_team_id, goals=h_score,
                possession=0.5, shots=10, shots_on_target=4, corners=4, fouls=12,
                yellow_cards=1, red_cards=0, expected_goals=h_score * 0.9
            )
            a_stats = TeamMatchStats(
                match_id=m.match_id, team_id=m.away_team_id, goals=a_score,
                possession=0.5, shots=10, shots_on_target=4, corners=4, fouls=12,
                yellow_cards=1, red_cards=0, expected_goals=a_score * 0.9
            )
            self.repo.save_team_match_stats(h_stats)
            self.repo.save_team_match_stats(a_stats)
            
            results.append({
                "match_id": m.match_id,
                "home_team_id": m.home_team_id,
                "away_team_id": m.away_team_id,
                "home_score": h_score,
                "away_score": a_score,
                "home_penalty_score": h_pen,
                "away_penalty_score": a_pen,
                "winner": m.home_team_id if (h_score > a_score or (h_pen and h_pen > a_pen)) else m.away_team_id
            })
            
        return results

    def advance_group_stage_to_knockout(self, tournament_id: str) -> List[Match]:
        """
        Calculates group stage standings, decides who advances,
        and schedules the first knockout round (e.g. Round of 16 for WC 2026/2022).
        For simplicity, we will simulate a standard 4-team group advancement (top 2 advance).
        Let's pair them: Group A Winner vs Group B Runner-up, etc.
        """
        # Fetch all matches in group stage for the tournament
        all_matches = self.repo.get_matches()
        group_matches = [
            m for m in all_matches 
            if m.tournament_id == tournament_id 
            and m.match_phase == "Group"
        ]
        
        # Verify all are simulated or completed
        if any(m.status == "Scheduled" for m in group_matches):
            raise ValueError("Cannot advance: some group stage matches are still scheduled and not simulated.")

        # Calculate points and goal difference per team
        # We need to know which team belongs to which group.
        # In our load_matches.py:
        # Group A: USA, COL, MEX, ECU
        # Group B: ARG, MAR, FRA, JPN
        # Group C: BRA, ENG, ESP, SEN
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
            "Group L": ["ENG", "CRO", "GHA", "PAN"]
        }
        
        standings = {t: {"points": 0, "gf": 0, "ga": 0, "gd": 0} for g in groups.values() for t in g}
        
        for m in group_matches:
            h = m.home_team_id
            a = m.away_team_id
            hs = m.home_score
            as_ = m.away_score
            
            if h not in standings or a not in standings:
                continue # Skip teams not in our target groups
                
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
                
        # Rank groups
        group_winners = []
        for g_name, g_teams in groups.items():
            # Sort teams in this group
            sorted_teams = sorted(
                g_teams,
                key=lambda t: (standings[t]["points"], standings[t]["gd"], standings[t]["gf"]),
                reverse=True
            )
            group_winners.append(sorted_teams[0])
            
        # Select the top 4 group winners overall to advance to Semifinals
        top_4_winners = sorted(
            group_winners,
            key=lambda t: (standings[t]["points"], standings[t]["gd"], standings[t]["gf"]),
            reverse=True
        )[:4]
        
        semifinalists = top_4_winners
        
        # Schedule Semifinals
        # Match 1: Winner A vs Winner B
        # Match 2: Winner C vs Best Runner-up
        sf_matches = [
            Match(
                match_id=f"{tournament_id}_SF1",
                tournament_id=tournament_id,
                match_date=date(2026, 7, 5),
                home_team_id=semifinalists[0],
                away_team_id=semifinalists[1],
                match_phase="Semifinals",
                status="Scheduled"
            ),
            Match(
                match_id=f"{tournament_id}_SF2",
                tournament_id=tournament_id,
                match_date=date(2026, 7, 6),
                home_team_id=semifinalists[2],
                away_team_id=semifinalists[3],
                match_phase="Semifinals",
                status="Scheduled"
            )
        ]
        
        for m in sf_matches:
            self.repo.save_match(m)
            
        print(f"Generated Semifinals matches for {tournament_id}!")
        return sf_matches

    def advance_semifinals_to_final(self, tournament_id: str) -> List[Match]:
        # Fetch Semifinals matches
        all_matches = self.repo.get_matches()
        sf_matches = [
            m for m in all_matches 
            if m.tournament_id == tournament_id 
            and m.match_phase == "Semifinals"
        ]
        
        if any(m.status == "Scheduled" for m in sf_matches):
            raise ValueError("Cannot advance: some Semifinals matches are still scheduled and not simulated.")
            
        # Determine winners
        winners = []
        for m in sf_matches:
            if m.home_score > m.away_score:
                winners.append(m.home_team_id)
            elif m.home_score < m.away_score:
                winners.append(m.away_team_id)
            else:
                # Penalties
                if m.home_penalty_score > m.away_penalty_score:
                    winners.append(m.home_team_id)
                else:
                    winners.append(m.away_team_id)
                    
        # Schedule Final
        final_match = Match(
            match_id=f"{tournament_id}_Final",
            tournament_id=tournament_id,
            match_date=date(2026, 7, 12),
            home_team_id=winners[0],
            away_team_id=winners[1],
            match_phase="Final",
            status="Scheduled"
        )
        self.repo.save_match(final_match)
        print(f"Generated Final match for {tournament_id}!")
        return [final_match]
