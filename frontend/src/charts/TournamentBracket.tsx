import React from 'react';

const fifaToIso: Record<string, string> = {
  MEX: 'mx', RSA: 'za', KOR: 'kr', CZE: 'cz',
  CAN: 'ca', ITA: 'it', QAT: 'qa', SUI: 'ch',
  BRA: 'br', MAR: 'ma', HAI: 'ht', SCO: 'gb-sct',
  USA: 'us', PAR: 'py', AUS: 'au', TUR: 'tr',
  GER: 'de', CUW: 'cw', CIV: 'ci', ECU: 'ec',
  NED: 'nl', JPN: 'jp', SWE: 'se', TUN: 'tn',
  BEL: 'be', EGY: 'eg', IRN: 'ir', NZL: 'nz',
  ESP: 'es', CPV: 'cv', KSA: 'sa', URU: 'uy',
  FRA: 'fr', SEN: 'sn', IRQ: 'iq', NOR: 'no',
  ARG: 'ar', ALG: 'dz', AUT: 'at', JOR: 'jo',
  POR: 'pt', JAM: 'jm', UZB: 'uz', COL: 'co',
  ENG: 'gb-eng', CRO: 'hr', GHA: 'gh', PAN: 'pa'
};

const getFlagUrl = (fifaCode: string) => {
  const iso = fifaToIso[fifaCode];
  if (!iso) return null;
  return `https://flagcdn.com/16x12/${iso}.png`;
};

interface Team {
  team_id: string;
  team_name: string;
  team_code: string;
}

interface MatchDetail {
  match_id: string;
  home_team: Team | null;
  away_team: Team | null;
  home_score?: number;
  away_score?: number;
  home_penalty_score?: number;
  away_penalty_score?: number;
  match_phase: string;
  status: string;
}

interface TournamentBracketProps {
  matches: MatchDetail[];
}

export const TournamentBracket: React.FC<TournamentBracketProps> = ({ matches }) => {
  // Group matches by phase
  const getPhaseMatches = (phase: string) => {
    return matches.filter(m => m.match_phase === phase).sort((a, b) => a.match_id.localeCompare(b.match_id));
  };

  const r32 = getPhaseMatches("Round of 32");
  const r16 = getPhaseMatches("Round of 16");
  const qf = getPhaseMatches("Quarterfinals");
  const sf = getPhaseMatches("Semifinals");
  const final = getPhaseMatches("Final");

  if (r32.length === 0) {
    return null;
  }

  const renderMatch = (m: MatchDetail) => {
    const isPlayed = m.status === 'Completed' || m.status === 'Simulated';
    const hScore = isPlayed ? m.home_score : '-';
    const aScore = isPlayed ? m.away_score : '-';
    
    let hWinner = false;
    let aWinner = false;
    if (isPlayed && m.home_score !== undefined && m.away_score !== undefined) {
      if (m.home_score > m.away_score) hWinner = true;
      else if (m.away_score > m.home_score) aWinner = true;
      else if (m.home_penalty_score !== undefined && m.away_penalty_score !== undefined) {
        if (m.home_penalty_score > m.away_penalty_score) hWinner = true;
        else aWinner = true;
      }
    }

    return (
      <div 
        key={m.match_id} 
        style={{ 
          background: 'rgba(255,255,255,0.02)', 
          border: '1px solid var(--border-color)', 
          borderRadius: '4px', 
          padding: '4px',
          width: '120px',
          fontSize: '0.75rem',
          margin: '4px 0',
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: hWinner ? 'bold' : 'normal', color: hWinner ? '#fff' : 'var(--text-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {m.home_team && getFlagUrl(m.home_team.team_code) && <img src={getFlagUrl(m.home_team.team_code)!} alt="" width="16" height="12" />}
            {m.home_team?.team_code || 'TBD'}
          </div>
          <span>{hScore} {m.home_penalty_score !== null && m.home_penalty_score !== undefined ? `(${m.home_penalty_score})` : ''}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: aWinner ? 'bold' : 'normal', color: aWinner ? '#fff' : 'var(--text-secondary)', marginTop: '2px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {m.away_team && getFlagUrl(m.away_team.team_code) && <img src={getFlagUrl(m.away_team.team_code)!} alt="" width="16" height="12" />}
            {m.away_team?.team_code || 'TBD'}
          </div>
          <span>{aScore} {m.away_penalty_score !== null && m.away_penalty_score !== undefined ? `(${m.away_penalty_score})` : ''}</span>
        </div>
      </div>
    );
  };

  return (
    <div style={{ marginTop: '20px', overflowX: 'auto', paddingBottom: '20px' }}>
      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', marginBottom: '16px', color: '#fff', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
        Cuadro del Torneo (Knockout Bracket)
      </h2>
      <div style={{ display: 'flex', gap: '20px', minWidth: '800px', padding: '10px' }}>
        {/* R32 */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-around', flex: 1 }}>
          <h3 style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>16avos</h3>
          {r32.map(renderMatch)}
        </div>
        {/* R16 */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-around', flex: 1 }}>
          <h3 style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>Octavos</h3>
          {r16.map(renderMatch)}
        </div>
        {/* QF */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-around', flex: 1 }}>
          <h3 style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>Cuartos</h3>
          {qf.map(renderMatch)}
        </div>
        {/* SF */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-around', flex: 1 }}>
          <h3 style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>Semifinales</h3>
          {sf.map(renderMatch)}
        </div>
        {/* Final */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-around', flex: 1 }}>
          <h3 style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-gold)' }}>Final</h3>
          {final.map(renderMatch)}
        </div>
      </div>
    </div>
  );
};
