import sys
from pathlib import Path
import pytest
from datetime import date

# Add project root to python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.database.repository import FootballRepository
from backend.services.probability import MatchProbabilityService
from backend.simulations.tournament import TournamentSimulator

def test_probability_prediction():
    repo = FootballRepository()
    service = MatchProbabilityService(repo)
    
    # WC26_A1 = first match of Group A (MEX vs RSA)
    prediction = service.predict_match_outcome("WC26_A1")
    assert prediction is not None
    assert "home_win_prob" in prediction
    assert "away_win_prob" in prediction
    assert "draw_prob" in prediction
    assert 0.0 <= prediction["home_win_prob"] <= 1.0
    assert 0.0 <= prediction["away_win_prob"] <= 1.0
    assert 0.0 <= prediction["draw_prob"] <= 1.0
    # Probabilities should sum to approximately 1.0 (allow slight rounding from round())
    total = prediction["home_win_prob"] + prediction["away_win_prob"] + prediction["draw_prob"]
    assert abs(total - 1.0) < 1e-3
    # New fields from enhanced predictor
    assert "confidence_pct" in prediction
    assert "components" in prediction
    assert "inputs" in prediction
    assert "most_likely_score" in prediction

def test_tournament_simulation_e2e():
    # Reset the DB to a clean state so the simulation starts fresh
    from backend.scripts.run_etl import run_pipeline
    run_pipeline()

    repo = FootballRepository()
    simulator = TournamentSimulator(repo)
    
    # 1. Simulate Group Stage
    results_group = simulator.simulate_phase("WC26", "Group")
    assert len(results_group) > 0
    # Each result should have a winner
    for r in results_group:
        assert "winner" in r
        assert r["home_score"] is not None
        assert r["away_score"] is not None
        
    # 2. Advance Group to Semifinals
    sf_matches = simulator.advance_group_stage_to_knockout("WC26")
    assert len(sf_matches) == 2
    assert sf_matches[0].match_phase == "Semifinals"
    assert sf_matches[0].status == "Scheduled"
    
    # 3. Simulate Semifinals
    results_sf = simulator.simulate_phase("WC26", "Semifinals")
    assert len(results_sf) == 2
    
    # 4. Advance Semifinals to Final
    final_matches = simulator.advance_semifinals_to_final("WC26")
    assert len(final_matches) == 1
    assert final_matches[0].match_phase == "Final"
    assert final_matches[0].status == "Scheduled"
    
    # 5. Simulate Final
    results_final = simulator.simulate_phase("WC26", "Final")
    assert len(results_final) == 1
    assert results_final[0]["winner"] is not None
