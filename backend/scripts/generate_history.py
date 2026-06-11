import os
import sys
from pathlib import Path
import urllib.request
import csv
from datetime import datetime, timedelta

# Add parent dir to path if we need to load db
sys.path.append(str(Path(__file__).resolve().parent.parent))

def compute_elo_and_rankings():
    print("Downloading results.csv from martj42 repository...")
    url = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        lines = [line.decode('utf-8') for line in response.readlines()]
    
    print(f"Downloaded {len(lines)} matches.")
    
    reader = csv.DictReader(lines)
    matches = list(reader)
    
    # Load our teams
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    teams_path = data_dir / 'teams.csv'
    
    if not teams_path.exists():
        print(f"teams.csv not found at {teams_path}")
        return
        
    our_teams = {}
    with open(teams_path, 'r', encoding='utf-8') as f:
        t_reader = csv.DictReader(f)
        for row in t_reader:
            our_teams[row['team_name']] = row['team_id']
            
    # Aliases for some teams
    aliases = {
        'United States': 'USA',
        'USA': 'USA',
        'Korea Republic': 'KOR',
        'South Korea': 'KOR',
        'Czech Republic': 'CZE',
        'Czechia': 'CZE',
        'DR Congo': 'COD',
        'Congo DR': 'COD',
        'Ivory Coast': 'CIV',
        "Côte d'Ivoire": 'CIV',
        'Cape Verde': 'CPV',
        'Curacao': 'CUW',
        'Curaçao': 'CUW',
        'Bosnia': 'BIH',
        'Bosnia and Herzegovina': 'BIH',
        'Iran': 'IRN',
    }
    
    def get_team_id(name):
        if name in our_teams:
            return our_teams[name]
        if name in aliases and aliases[name] in our_teams.values():
            return aliases[name]
        return None
        
    elos = {}
    
    # Sort matches chronologically
    matches.sort(key=lambda x: x['date'])
    
    # Data structures for snapshots
    # We will save monthly snapshots from 2000-01-01 to 2024-01-01
    snapshots = []
    current_snapshot_date = datetime(2000, 1, 1).date()
    
    print("Computing ELO ratings...")
    for m in matches:
        m_date = datetime.strptime(m['date'], '%Y-%m-%d').date()
        
        # Check if we crossed a snapshot boundary
        while m_date >= current_snapshot_date:
            if current_snapshot_date.year >= 2000:
                # Save snapshot
                snap = {
                    'date': current_snapshot_date.strftime('%Y-%m-%d'),
                    'ratings': {k: v for k, v in elos.items()}
                }
                snapshots.append(snap)
            # increment by 3 months to avoid huge files, or 1 month? Let's do 3 months (quarterly)
            month = current_snapshot_date.month + 3
            year = current_snapshot_date.year
            if month > 12:
                month -= 12
                year += 1
            current_snapshot_date = current_snapshot_date.replace(year=year, month=month, day=1)
            
        home = m['home_team']
        away = m['away_team']
        
        try:
            h_score = int(m['home_score'])
            a_score = int(m['away_score'])
        except ValueError:
            continue
            
        if home not in elos: elos[home] = 1500.0
        if away not in elos: elos[away] = 1500.0
        
        r_home = elos[home]
        r_away = elos[away]
        
        # ELO formula
        e_home = 1 / (10 ** ((r_away - r_home) / 400) + 1)
        e_away = 1 / (10 ** ((r_home - r_away) / 400) + 1)
        
        if h_score > a_score:
            s_home, s_away = 1.0, 0.0
        elif h_score < a_score:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5
            
        # K factor
        k = 30
        if m['tournament'] == 'FIFA World Cup':
            k = 60
        elif m['tournament'] in ['UEFA Euro', 'Copa América', 'African Cup of Nations']:
            k = 50
            
        # Goal difference multiplier
        gd = abs(h_score - a_score)
        if gd <= 1:
            g = 1.0
        elif gd == 2:
            g = 1.5
        else:
            g = (11 + gd) / 8.0
            
        elos[home] = r_home + k * g * (s_home - e_home)
        elos[away] = r_away + k * g * (s_away - e_away)

    # Save the final snapshot
    snap = {
        'date': current_snapshot_date.strftime('%Y-%m-%d'),
        'ratings': {k: v for k, v in elos.items()}
    }
    snapshots.append(snap)
    
    # Now generate CSVs
    print("Generating elo_history.csv and fifa_rankings.csv...")
    elo_rows = []
    fifa_rows = []
    
    for snap in snapshots:
        date_str = snap['date']
        ratings = snap['ratings']
        
        # Filter only our teams
        valid_ratings = []
        for team_name, elo in ratings.items():
            t_id = get_team_id(team_name)
            if t_id:
                valid_ratings.append((t_id, elo))
                
        # Sort valid ratings to generate rank
        valid_ratings.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (t_id, elo) in enumerate(valid_ratings, 1):
            elo_rows.append({
                'rating_date': date_str,
                'team_id': t_id,
                'elo_rating': round(elo, 2)
            })
            # Approximation for FIFA points based on ELO
            fifa_points = round((elo - 1000) * 1.5, 2)
            if fifa_points < 0: fifa_points = 0
            
            fifa_rows.append({
                'ranking_date': date_str,
                'team_id': t_id,
                'points': fifa_points,
                'rank': rank
            })
            
    elo_path = data_dir / 'elo_history.csv'
    fifa_path = data_dir / 'fifa_rankings.csv'
    
    with open(elo_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['rating_date', 'team_id', 'elo_rating'])
        writer.writeheader()
        writer.writerows(elo_rows)
        
    with open(fifa_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ranking_date', 'team_id', 'points', 'rank'])
        writer.writeheader()
        writer.writerows(fifa_rows)
        
    print(f"Successfully generated {len(elo_rows)} rows in elo_history.csv")
    print(f"Successfully generated {len(fifa_rows)} rows in fifa_rankings.csv")

if __name__ == "__main__":
    compute_elo_and_rankings()
