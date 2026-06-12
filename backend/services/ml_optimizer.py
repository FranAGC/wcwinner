import numpy as np
import random
from typing import List, Dict, Any, Tuple
from backend.database.repository import FootballRepository
from backend.simulations.tournament import TournamentSimulator

class GeneticOptimizer:
    def __init__(self, repo: FootballRepository, prob_service, simulator: TournamentSimulator):
        self.repo = repo
        self.prob_service = prob_service
        self.simulator = simulator
        
        # Default Weights (Genes)
        # [w_elo, w_att, w_form, w_h2h, w_squad, w_rating]
        self.best_weights = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    def set_weights(self, weights: List[float]):
        self.best_weights = weights

    def get_weights(self) -> List[float]:
        return self.best_weights

    def get_real_matches(self) -> List[Any]:
        # Returns matches from WC26 that have been completed
        matches = self.repo.get_matches()
        return [m for m in matches if m.tournament_id == "WC26" and m.status == "Completed"]
        
    def _calculate_fitness(self, weights: List[float], real_matches: List[Any]) -> float:
        """
        Simulate all real matches using ATA and the given weights,
        then calculate Mean Absolute Error (MAE) of goals.
        Returns a fitness score (lower MAE -> higher fitness, so we return negative MAE).
        """
        if not real_matches:
            return 0.0
            
        total_error = 0.0
        
        for m in real_matches:
            # Predict with ATA using current weights
            pred = self.prob_service.predict_match_outcome(m.match_id, algorithm="ata", ata_weights=weights)
            pred_h_goals = pred["expected_home_goals"]
            pred_a_goals = pred["expected_away_goals"]
            
            real_h_goals = m.home_score
            real_a_goals = m.away_score
            
            # MAE of goals
            total_error += abs(pred_h_goals - real_h_goals) + abs(pred_a_goals - real_a_goals)
            
        mae = total_error / (len(real_matches) * 2)
        return -mae # Negative because higher fitness is better

    def run_generation(self, population_size=10, generations=3) -> Dict[str, Any]:
        real_matches = self.get_real_matches()
        if not real_matches:
            return {"status": "error", "message": "No hay partidos reales (WC26 completados) para entrenar el algoritmo."}
            
        num_genes = 6
        population = [
            [random.uniform(0.1, 2.0) for _ in range(num_genes)]
            for _ in range(population_size)
        ]
        
        # Add current best as one of the population to not lose progress
        population[0] = self.best_weights.copy()
        
        best_fitness = -999.0
        best_individual = self.best_weights
        
        for gen in range(generations):
            fitness_scores = [(ind, self._calculate_fitness(ind, real_matches)) for ind in population]
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            best_individual = fitness_scores[0][0]
            best_fitness = fitness_scores[0][1]
            
            # Selection (Top 50%)
            survivors = [x[0] for x in fitness_scores[:population_size//2]]
            
            # Crossover and Mutation to fill the rest
            new_population = survivors.copy()
            while len(new_population) < population_size:
                parent1 = random.choice(survivors)
                parent2 = random.choice(survivors)
                
                # Crossover
                child = []
                for i in range(num_genes):
                    if random.random() > 0.5:
                        child.append(parent1[i])
                    else:
                        child.append(parent2[i])
                        
                # Mutation (10% chance)
                for i in range(num_genes):
                    if random.random() < 0.1:
                        child[i] *= random.uniform(0.8, 1.2)
                        
                new_population.append(child)
                
            population = new_population
            
        self.best_weights = best_individual
        return {
            "status": "success",
            "message": "Entrenamiento genético completado.",
            "generations": generations,
            "best_weights": best_individual,
            "fitness_mae": round(abs(best_fitness), 3)
        }

    def compare_real_vs_simulated(self) -> Dict[str, Any]:
        """
        Compare WC26 (Real) vs WC26_SIM (Simulated)
        """
        matches = self.repo.get_matches()
        real_matches = {m.match_id: m for m in matches if m.tournament_id == "WC26" and m.status == "Completed"}
        sim_matches = {m.match_id.replace("WC26_SIM", "WC26"): m for m in matches if m.tournament_id == "WC26_SIM" and m.status == "Completed"}
        
        if not real_matches:
            return {"error": "No hay resultados reales (WC26 completados) para comparar."}
            
        if not sim_matches:
            return {"error": "No hay resultados simulados (WC26_SIM completados) para comparar. Simula la fase paralela primero."}
            
        common_matches = set(real_matches.keys()).intersection(set(sim_matches.keys()))
        
        if not common_matches:
            return {"error": "No hay coincidencia de partidos entre el torneo real y el simulado."}
            
        total_error = 0
        correct_outcomes = 0 # W/D/L match
        
        details = []
        for match_id in common_matches:
            rm = real_matches[match_id]
            sm = sim_matches[match_id]
            
            mae_match = abs(rm.home_score - sm.home_score) + abs(rm.away_score - sm.away_score)
            total_error += mae_match
            
            def get_outcome(h, a):
                if h > a: return 'H'
                elif a > h: return 'A'
                return 'D'
                
            if get_outcome(rm.home_score, rm.away_score) == get_outcome(sm.home_score, sm.away_score):
                correct_outcomes += 1
                
            details.append({
                "match_id": match_id,
                "home": rm.home_team_id,
                "away": rm.away_team_id,
                "real_score": f"{rm.home_score}-{rm.away_score}",
                "sim_score": f"{sm.home_score}-{sm.away_score}"
            })
            
        return {
            "total_matches_compared": len(common_matches),
            "mae_goals": round(total_error / (len(common_matches) * 2), 3),
            "outcome_accuracy_pct": round((correct_outcomes / len(common_matches)) * 100, 1),
            "details": details
        }
