-- Schema creation for Football Probability system (World Cup 2026)
-- Note: Foreign key REFERENCES constraints are omitted to support DuckDB updates/upserts

-- 1. Teams Table
CREATE TABLE IF NOT EXISTS teams (
    team_id VARCHAR PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    team_code VARCHAR UNIQUE NOT NULL, -- e.g. ARG, BRA, USA
    confederation VARCHAR NOT NULL     -- e.g. CONMEBOL, UEFA, CONCACAF, CAF, AFC, OFC
);

-- 2. Competitions Table
CREATE TABLE IF NOT EXISTS competitions (
    competition_id VARCHAR PRIMARY KEY,
    competition_name VARCHAR NOT NULL,
    competition_type VARCHAR NOT NULL  -- e.g. International, Continental
);

-- 3. Tournaments Table
CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id VARCHAR PRIMARY KEY,
    competition_id VARCHAR,
    year INTEGER NOT NULL,
    host_country VARCHAR NOT NULL
);

-- 4. Matches Table
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR PRIMARY KEY,
    tournament_id VARCHAR,
    match_date DATE NOT NULL,
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_score INTEGER,
    away_score INTEGER,
    home_penalty_score INTEGER,
    away_penalty_score INTEGER,
    match_phase VARCHAR NOT NULL,     -- e.g. Group, Round of 32, Round of 16, Quarterfinals, Semifinals, Final
    status VARCHAR NOT NULL           -- e.g. Completed, Scheduled, Simulated
);

-- 5. Team Match Stats Table
CREATE TABLE IF NOT EXISTS team_match_stats (
    match_id VARCHAR,
    team_id VARCHAR,
    goals INTEGER NOT NULL,
    possession DOUBLE,
    shots INTEGER,
    shots_on_target INTEGER,
    corners INTEGER,
    fouls INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    expected_goals DOUBLE,
    PRIMARY KEY (match_id, team_id)
);

-- 6. FIFA Rankings Table
CREATE TABLE IF NOT EXISTS fifa_rankings (
    ranking_date DATE NOT NULL,
    team_id VARCHAR,
    points DOUBLE NOT NULL,
    rank INTEGER NOT NULL,
    PRIMARY KEY (ranking_date, team_id)
);

-- 7. ELO History Table
CREATE TABLE IF NOT EXISTS elo_history (
    rating_date DATE NOT NULL,
    team_id VARCHAR,
    elo_rating DOUBLE NOT NULL,
    PRIMARY KEY (rating_date, team_id)
);

-- 8. Players Table
CREATE TABLE IF NOT EXISTS players (
    player_id VARCHAR PRIMARY KEY,
    player_name VARCHAR NOT NULL,
    birth_date DATE,
    position VARCHAR,                 -- e.g. Goalkeeper, Defender, Midfielder, Forward
    club VARCHAR,
    base_rating DOUBLE DEFAULT 70.0   -- Overall player rating (1-100)
);

-- 9. Player Match Stats Table
CREATE TABLE IF NOT EXISTS player_match_stats (
    match_id VARCHAR,
    player_id VARCHAR,
    team_id VARCHAR,
    minutes_played INTEGER NOT NULL,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    shots INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    rating DOUBLE,
    PRIMARY KEY (match_id, player_id)
);

-- 10. Squad Calls Table
CREATE TABLE IF NOT EXISTS squad_calls (
    tournament_id VARCHAR,
    team_id VARCHAR,
    player_id VARCHAR,
    jersey_number INTEGER,
    PRIMARY KEY (tournament_id, team_id, player_id)
);

-- 11. Team Features Table (for ML/Probability model input)
CREATE TABLE IF NOT EXISTS team_features (
    team_id VARCHAR,
    as_of_date DATE NOT NULL,
    elo DOUBLE NOT NULL,
    fifa_rank INTEGER NOT NULL,
    attack_strength DOUBLE,
    defense_strength DOUBLE,
    avg_goals_scored DOUBLE,
    avg_goals_conceded DOUBLE,
    form_index DOUBLE,               -- Exponentially weighted recent form (0-1)
    wc_attack_strength DOUBLE,       -- Attack strength in World Cup matches only
    wc_defense_strength DOUBLE,      -- Defense strength in World Cup matches only
    squad_size INTEGER,              -- Number of players in WC26 squad
    clean_sheet_rate DOUBLE,         -- Rate of clean sheets in recent completed matches
    win_rate DOUBLE,                 -- Overall win rate from completed matches
    PRIMARY KEY (team_id, as_of_date)
);

-- 12. Match Features Table (pre-calculated match features)
CREATE TABLE IF NOT EXISTS match_features (
    match_id VARCHAR PRIMARY KEY,
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_elo DOUBLE,
    away_elo DOUBLE,
    home_fifa_rank INTEGER,
    away_fifa_rank INTEGER,
    home_attack_strength DOUBLE,
    away_attack_strength DOUBLE,
    home_defense_strength DOUBLE,
    away_defense_strength DOUBLE,
    elo_diff DOUBLE,
    rank_diff INTEGER,
    home_form_index DOUBLE,
    away_form_index DOUBLE,
    home_wc_attack DOUBLE,
    away_wc_attack DOUBLE,
    home_wc_defense DOUBLE,
    away_wc_defense DOUBLE,
    home_squad_size INTEGER,
    away_squad_size INTEGER,
    h2h_home_wins INTEGER,           -- Head-to-head wins for home team (last 10 meetings)
    h2h_away_wins INTEGER,           -- Head-to-head wins for away team (last 10 meetings)
    h2h_draws INTEGER,               -- Head-to-head draws (last 10 meetings)
    h2h_home_goals_avg DOUBLE,       -- Average goals scored by home team in H2H
    h2h_away_goals_avg DOUBLE        -- Average goals scored by away team in H2H
);
