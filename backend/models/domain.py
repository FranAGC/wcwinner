from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

# --- Team Models ---
class TeamBase(BaseModel):
    team_id: str = Field(..., description="Unique ID for the team, e.g., 'ARG'")
    team_name: str = Field(..., description="Display name of the team")
    team_code: str = Field(..., description="Three-letter FIFA country code, e.g., 'ARG'")
    confederation: str = Field(..., description="Confederation, e.g., 'CONMEBOL', 'UEFA'")

class TeamCreate(TeamBase):
    pass

class Team(TeamBase):
    class Config:
        from_attributes = True

# --- Competition Models ---
class CompetitionBase(BaseModel):
    competition_id: str
    competition_name: str
    competition_type: str

class Competition(CompetitionBase):
    class Config:
        from_attributes = True

# --- Tournament Models ---
class TournamentBase(BaseModel):
    tournament_id: str
    competition_id: str
    year: int
    host_country: str

class Tournament(TournamentBase):
    class Config:
        from_attributes = True

# --- Match Models ---
class MatchBase(BaseModel):
    match_id: str
    tournament_id: str
    match_date: date
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_penalty_score: Optional[int] = None
    away_penalty_score: Optional[int] = None
    match_phase: str  # e.g., Group, Round of 32, Round of 16, Quarterfinals, Semifinals, Final
    status: str       # Completed, Scheduled, Simulated

class MatchCreate(MatchBase):
    pass

class Match(MatchBase):
    class Config:
        from_attributes = True

# --- Team Match Stats Models ---
class TeamMatchStatsBase(BaseModel):
    match_id: str
    team_id: str
    goals: int
    possession: Optional[float] = None
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    corners: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None
    expected_goals: Optional[float] = None

class TeamMatchStats(TeamMatchStatsBase):
    class Config:
        from_attributes = True

# --- FIFA Rankings Models ---
class FifaRankingBase(BaseModel):
    ranking_date: date
    team_id: str
    points: float
    rank: int

class FifaRanking(FifaRankingBase):
    class Config:
        from_attributes = True

# --- ELO History Models ---
class EloHistoryBase(BaseModel):
    rating_date: date
    team_id: str
    elo_rating: float

class EloHistory(EloHistoryBase):
    class Config:
        from_attributes = True

# --- Player Models ---
class PlayerBase(BaseModel):
    player_id: str
    player_name: str
    birth_date: Optional[date] = None
    position: Optional[str] = None
    club: Optional[str] = None

class Player(PlayerBase):
    class Config:
        from_attributes = True

# --- Player Match Stats Models ---
class PlayerMatchStatsBase(BaseModel):
    match_id: str
    player_id: str
    team_id: str
    minutes_played: int
    goals: int = 0
    assists: int = 0
    shots: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: Optional[float] = None

class PlayerMatchStats(PlayerMatchStatsBase):
    class Config:
        from_attributes = True

# --- Squad Calls Models ---
class SquadCallBase(BaseModel):
    tournament_id: str
    team_id: str
    player_id: str
    jersey_number: Optional[int] = None

class SquadCall(SquadCallBase):
    class Config:
        from_attributes = True

# --- Team Features Models ---
class TeamFeaturesBase(BaseModel):
    team_id: str
    as_of_date: date
    elo: float
    fifa_rank: int
    attack_strength: Optional[float] = None
    defense_strength: Optional[float] = None
    avg_goals_scored: Optional[float] = None
    avg_goals_conceded: Optional[float] = None
    form_index: Optional[float] = None          # Exponentially-weighted recent form (0-1)
    wc_attack_strength: Optional[float] = None  # Attack in WC matches only
    wc_defense_strength: Optional[float] = None # Defense in WC matches only
    squad_size: Optional[int] = None            # WC squad size
    clean_sheet_rate: Optional[float] = None    # Rate of clean sheets
    win_rate: Optional[float] = None            # Overall win rate

class TeamFeatures(TeamFeaturesBase):
    class Config:
        from_attributes = True

# --- Match Features Models ---
class MatchFeaturesBase(BaseModel):
    match_id: str
    home_team_id: str
    away_team_id: str
    home_elo: Optional[float] = None
    away_elo: Optional[float] = None
    home_fifa_rank: Optional[int] = None
    away_fifa_rank: Optional[int] = None
    home_attack_strength: Optional[float] = None
    away_attack_strength: Optional[float] = None
    home_defense_strength: Optional[float] = None
    away_defense_strength: Optional[float] = None
    elo_diff: Optional[float] = None
    rank_diff: Optional[int] = None
    home_form_index: Optional[float] = None
    away_form_index: Optional[float] = None
    home_wc_attack: Optional[float] = None
    away_wc_attack: Optional[float] = None
    home_wc_defense: Optional[float] = None
    away_wc_defense: Optional[float] = None
    home_squad_size: Optional[int] = None
    away_squad_size: Optional[int] = None
    h2h_home_wins: Optional[int] = None
    h2h_away_wins: Optional[int] = None
    h2h_draws: Optional[int] = None
    h2h_home_goals_avg: Optional[float] = None
    h2h_away_goals_avg: Optional[float] = None

class MatchFeatures(MatchFeaturesBase):
    class Config:
        from_attributes = True

# --- Combined API response models ---
class MatchDetail(BaseModel):
    match_id: str
    tournament_id: str
    match_date: date
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_penalty_score: Optional[int] = None
    away_penalty_score: Optional[int] = None
    match_phase: str
    status: str
    stats: Optional[List[TeamMatchStats]] = None
