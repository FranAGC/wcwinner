import os
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import date

from backend.database.repository import FootballRepository
from backend.models.domain import Team, Match, FifaRanking, EloHistory, MatchDetail, TeamMatchStats
from backend.services.probability import MatchProbabilityService
from backend.simulations.tournament import TournamentSimulator

app = FastAPI(
    title="Football Probability API",
    description="API for World Cup 2026 probabilistic analysis and match predictions",
    version="1.0.0"
)

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = FootballRepository()
prob_service = MatchProbabilityService(repo)
simulator = TournamentSimulator(repo)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Football Probability API. World Cup 2026 Ready."}

@app.get("/teams", response_model=List[Team])
def get_teams():
    """Retrieve all teams registered in the system."""
    try:
        return repo.get_teams()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/team/{team_id}", response_model=Team)
def get_team(team_id: str):
    """Retrieve details of a specific team by its ID (e.g. ARG, FRA)."""
    team = repo.get_team_by_id(team_id.upper())
    if not team:
        raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
    return team

@app.get("/matches", response_model=List[MatchDetail])
def get_matches(
    tournament_id: Optional[str] = Query(None, description="Filter matches by tournament, e.g. WC26"),
    status: Optional[str] = Query(None, description="Filter matches by status, e.g. Completed, Scheduled, Simulated")
):
    """Retrieve matches, optionally filtered by tournament and status, with team details and statistics."""
    try:
        matches = repo.get_matches()
        
        # Apply filters
        if tournament_id:
            matches = [m for m in matches if m.tournament_id.upper() == tournament_id.upper()]
        if status:
            matches = [m for m in matches if m.status.lower() == status.lower()]

        # Pre-fetch all teams in bulk
        all_teams = repo.get_teams()
        teams_dict = {t.team_id: t for t in all_teams}

        # Pre-fetch all stats in bulk
        stats_dict = {}
        with repo.conn_factory(read_only=True) as conn:
            stats_rows = conn.execute(
                """
                SELECT match_id, team_id, goals, possession, shots, shots_on_target, 
                       corners, fouls, yellow_cards, red_cards, expected_goals
                FROM team_match_stats
                """
            ).fetchall()
            for r in stats_rows:
                m_id = r[0]
                stat_obj = TeamMatchStats(
                    match_id=r[0], team_id=r[1], goals=r[2], possession=r[3],
                    shots=r[4], shots_on_target=r[5], corners=r[6], fouls=r[7],
                    yellow_cards=r[8], red_cards=r[9], expected_goals=r[10]
                )
                if m_id not in stats_dict:
                    stats_dict[m_id] = []
                stats_dict[m_id].append(stat_obj)

        # Enhance matches with Team details and Match stats
        detailed_matches = []
        for m in matches:
            home_team = teams_dict.get(m.home_team_id)
            away_team = teams_dict.get(m.away_team_id)
            
            # Fetch stats if completed or simulated
            stats = None
            if m.status in ["Completed", "Simulated"]:
                stats = stats_dict.get(m.match_id)
                
            detailed_matches.append(MatchDetail(
                match_id=m.match_id,
                tournament_id=m.tournament_id,
                match_date=m.match_date,
                home_team=home_team,
                away_team=away_team,
                home_score=m.home_score,
                away_score=m.away_score,
                home_penalty_score=m.home_penalty_score,
                away_penalty_score=m.away_penalty_score,
                match_phase=m.match_phase,
                status=m.status,
                stats=stats
            ))
        return detailed_matches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ranking", response_model=List[FifaRanking])
def get_rankings():
    """Retrieve the latest FIFA ranking for all teams."""
    try:
        return repo.get_latest_rankings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/elo", response_model=List[EloHistory])
def get_elo():
    """Retrieve the latest ELO ratings for all teams."""
    try:
        return repo.get_latest_elo()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PROBABILITY & SIMULATION ENDPOINTS ---

@app.get("/predict/{match_id}")
def get_match_prediction(match_id: str):
    """
    Get win/draw/loss probabilities, expected goals, most likely scoreline,
    confidence, H2H context, and form breakdown for a match.
    """
    prediction = prob_service.predict_match_outcome(match_id)
    if not prediction:
        raise HTTPException(status_code=404, detail=f"Prediction features for match {match_id} not found")
    return prediction

@app.get("/team/{team_id}/features")
def get_team_features(team_id: str):
    """
    Retrieve the full computed feature set for a team: ELO, FIFA rank,
    attack/defense strengths (overall + WC), form index, squad size, etc.
    """
    with repo.conn_factory(read_only=True) as conn:
        res = conn.execute(
            """
            SELECT team_id, as_of_date, elo, fifa_rank,
                   attack_strength, defense_strength,
                   avg_goals_scored, avg_goals_conceded, form_index,
                   wc_attack_strength, wc_defense_strength,
                   squad_size, clean_sheet_rate, win_rate
            FROM team_features WHERE team_id = ?
            ORDER BY as_of_date DESC LIMIT 1
            """,
            [team_id.upper()]
        ).fetchone()
    if not res:
        raise HTTPException(status_code=404, detail=f"No features found for team {team_id}")
    keys = [
        "team_id", "as_of_date", "elo", "fifa_rank",
        "attack_strength", "defense_strength",
        "avg_goals_scored", "avg_goals_conceded", "form_index",
        "wc_attack_strength", "wc_defense_strength",
        "squad_size", "clean_sheet_rate", "win_rate"
    ]
    return dict(zip(keys, res))

@app.post("/simulate/phase")
def simulate_phase(
    tournament_id: str = Query(..., description="Tournament ID, e.g. WC26"),
    phase: str = Query(..., description="Phase to simulate, e.g. Group, Semifinals, Final")
):
    """Simulate all scheduled matches of a specific phase and save results to the DB."""
    try:
        results = simulator.simulate_phase(tournament_id, phase)
        return {"message": f"Successfully simulated phase {phase}", "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/simulate/advance")
def advance_tournament(
    tournament_id: str = Query(..., description="Tournament ID, e.g. WC26"),
    current_phase: str = Query(..., description="Current phase that just finished, e.g. Group, Semifinals")
):
    """Generate matchups for the next phase based on the finished phase's results."""
    try:
        if current_phase.lower() == "group":
            new_matches = simulator.advance_group_stage_to_knockout(tournament_id)
            return {"message": "Advanced Group Stage to Semifinals", "scheduled_matches": new_matches}
        elif current_phase.lower() == "semifinals":
            new_matches = simulator.advance_semifinals_to_final(tournament_id)
            return {"message": "Advanced Semifinals to Final", "scheduled_matches": new_matches}
        else:
            raise HTTPException(status_code=400, detail=f"Advancing from phase '{current_phase}' is not supported or it is the Final.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/reset")
def reset_database():
    """Reset the database to the initial clean state by executing the run_etl.py pipeline."""
    try:
        from backend.scripts.run_etl import run_pipeline
        run_pipeline()
        return {"message": "Database successfully reset to initial state"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
