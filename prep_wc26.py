import pandas as pd
import os

def create_wc26_csv():
    # Load matches.csv
    df = pd.read_csv('backend/data/matches.csv')
    
    # Extract WC26 matches
    wc26_df = df[df['tournament_id'] == 'WC26'].copy()
    
    # Remove WC26 from matches.csv
    df_no_wc26 = df[df['tournament_id'] != 'WC26']
    df_no_wc26.to_csv('backend/data/matches.csv', index=False)
    
    # Prepare knockout matches templates
    knockout_matches = []
    
    phases = {
        'Round of 32': (16, '2026-06-28', 'R32'),
        'Round of 16': (8, '2026-07-02', 'R16'),
        'Quarterfinals': (4, '2026-07-05', 'QF'),
        'Semifinals': (2, '2026-07-08', 'SF'),
        'Final': (1, '2026-07-19', 'F')
    }
    
    for phase_name, (count, dt, prefix) in phases.items():
        for i in range(1, count + 1):
            knockout_matches.append({
                'match_id': f'WC26_{prefix}_M{i}',
                'tournament_id': 'WC26',
                'match_date': dt,
                'home_team_id': '',
                'away_team_id': '',
                'home_score': '',
                'away_score': '',
                'home_penalty_score': '',
                'away_penalty_score': '',
                'match_phase': phase_name,
                'status': 'Scheduled'
            })
            
    ko_df = pd.DataFrame(knockout_matches)
    
    # Combine
    final_wc26_df = pd.concat([wc26_df, ko_df], ignore_index=True)
    final_wc26_df.to_csv('backend/data/wc26_matches.csv', index=False)
    print("Created wc26_matches.csv and removed WC26 from matches.csv")

if __name__ == '__main__':
    create_wc26_csv()
