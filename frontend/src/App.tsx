import React, { useEffect, useState, useMemo } from 'react';
import {
  Play,
  RotateCcw,
  Calendar,
  Layers,
  BarChart2,
  Info,
  Award,
  ChevronRight,
  Settings,
  Download
} from 'lucide-react';
import './App.css';
import { EloChart } from './charts/EloChart';
import { PredictionChart } from './charts/PredictionChart';
import { TournamentBracket } from './charts/TournamentBracket';

const API_URL = 'http://localhost:8000';

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
  ENG: 'gb-eng', CRO: 'hr', GHA: 'gh', PAN: 'pa',
  COD: 'cd', BIH: 'ba'
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
  confederation: string;
}

interface MatchStats {
  match_id: string;
  team_id: string;
  goals: number;
  possession?: number;
  shots?: number;
  shots_on_target?: number;
}

interface MatchDetail {
  match_id: string;
  tournament_id: string;
  match_date: string;
  home_team: Team;
  away_team: Team;
  home_score?: number;
  away_score?: number;
  home_penalty_score?: number;
  away_penalty_score?: number;
  match_phase: string;
  status: string;
  stats?: MatchStats[];
}

interface EloHistory {
  rating_date: string;
  team_id: string;
  elo_rating: number;
}

interface FifaRanking {
  ranking_date: string;
  team_id: string;
  points: number;
  rank: number;
}

interface PredictionData {
  match_id: string;
  home_team_id: string;
  away_team_id: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  expected_home_goals: number;
  expected_away_goals: number;
  most_likely_score: string;
  most_likely_score_prob: number;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'matches' | 'rankings' | 'standings' | 'config'>('matches');
  const [teams, setTeams] = useState<Team[]>([]);
  const [matches, setMatches] = useState<MatchDetail[]>([]);
  const [eloRankings, setEloRankings] = useState<EloHistory[]>([]);
  const [fifaRankings, setFifaRankings] = useState<FifaRanking[]>([]);
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [predictionAlgorithm, setPredictionAlgorithm] = useState<'ensemble' | 'mcmf'>('ensemble');

  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phaseFilter, setPhaseFilter] = useState<string>('All');
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);

  const teamToEmoji: Record<string, string> = {
    MEX: '🇲🇽', RSA: '🇿🇦', KOR: '🇰🇷', CZE: '🇨🇿',
    CAN: '🇨🇦', BIH: '🇧🇦', QAT: '🇶🇦', SUI: '🇨🇭',
    BRA: '🇧🇷', MAR: '🇲🇦', HAI: '🇭🇹', SCO: '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    USA: '🇺🇸', PAR: '🇵🇾', AUS: '🇦🇺', TUR: '🇹🇷',
    GER: '🇩🇪', CUW: '🇨🇼', CIV: '🇨🇮', ECU: '🇪🇨',
    NED: '🇳🇱', JPN: '🇯🇵', SWE: '🇸🇪', TUN: '🇹🇳',
    BEL: '🇧🇪', EGY: '🇪🇬', IRN: '🇮🇷', NZL: '🇳🇿',
    ESP: '🇪🇸', CPV: '🇨🇻', KSA: '🇸🇦', URU: '🇺🇾',
    FRA: '🇫🇷', SEN: '🇸🇳', IRQ: '🇮🇶', NOR: '🇳🇴',
    ARG: '🇦🇷', ALG: '🇩🇿', AUT: '🇦🇹', JOR: '🇯🇴',
    POR: '🇵🇹', COD: '🇨🇩', UZB: '🇺🇿', COL: '🇨🇴',
    ENG: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', CRO: '🇭🇷', GHA: '🇬🇭', PAN: '🇵🇦'
  };

  const [isBracketVisible, setIsBracketVisible] = useState(false);

  // Mappings
  const teamsMap = useMemo(() => {
    return teams.reduce((acc, t) => {
      acc[t.team_id] = t.team_name;
      return acc;
    }, {} as Record<string, string>);
  }, [teams]);

  const fetchAllData = async (shouldResetSelected = false) => {
    try {
      setLoading(true);
      setError(null);

      const [teamsRes, matchesRes, eloRes, fifaRes] = await Promise.all([
        fetch(`${API_URL}/teams`).then(r => r.json()),
        fetch(`${API_URL}/matches?tournament_id=WC26`).then(r => r.json()),
        fetch(`${API_URL}/elo`).then(r => r.json()),
        fetch(`${API_URL}/ranking`).then(r => r.json())
      ]);

      setTeams(teamsRes);
      setMatches(matchesRes);
      setEloRankings(eloRes);
      setFifaRankings(fifaRes);

      if (shouldResetSelected) {
        setSelectedMatchId(null);
        setPrediction(null);
      }
    } catch (err: any) {
      console.error(err);
      setError('Error al conectar con la API. Asegúrese de que el servidor FastAPI esté corriendo.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleSelectMatch = async (matchId: string) => {
    setSelectedMatchId(matchId);
    setPrediction(null);
    try {
      const res = await fetch(`${API_URL}/predict/${matchId}?algorithm=${predictionAlgorithm}`);
      if (!res.ok) throw new Error('No se pudo obtener la predicción');
      const data = await res.json();
      setPrediction(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSimulatePhase = async (phase: string) => {
    try {
      setSimulating(true);
      const res = await fetch(`${API_URL}/simulate/phase?tournament_id=WC26&phase=${phase}&algorithm=${predictionAlgorithm}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Error en simulación');
      }
      await fetchAllData();
      if (selectedMatchId) {
        handleSelectMatch(selectedMatchId);
      }
    } catch (err: any) {
      alert(`Error en simulación: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleAdvanceTournament = async (currentPhase: string) => {
    try {
      setSimulating(true);
      const res = await fetch(`${API_URL}/simulate/advance?tournament_id=WC26&current_phase=${currentPhase}&algorithm=${predictionAlgorithm}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Error al avanzar de fase');
      }
      await fetchAllData();
    } catch (err: any) {
      alert(`Error al avanzar: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleResetWc26 = async () => {
    if (!confirm('¿Está seguro de que desea reiniciar los partidos del torneo WC26 al estado inicial?')) {
      return;
    }
    try {
      setSimulating(true);
      const res = await fetch(`${API_URL}/reset/wc26`, { method: 'POST' });
      if (!res.ok) throw new Error('Error al reiniciar base de datos de WC26');
      await fetchAllData(true);
      alert('Torneo WC26 restablecido correctamente a Fase de Grupos.');
    } catch (err: any) {
      alert(`Error al reiniciar: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleResetAll = async () => {
    if (!confirm('ADVERTENCIA: Esto borrará TODOS los datos y volverá a descargar y procesar todo el historial mundial. Puede tomar varios minutos. ¿Desea continuar?')) {
      return;
    }
    try {
      setSimulating(true);
      const res = await fetch(`${API_URL}/reset/all`, { method: 'POST' });
      if (!res.ok) throw new Error('Error al restaurar base de datos completa');
      await fetchAllData(true);
      alert('Base de datos histórica restablecida correctamente.');
    } catch (err: any) {
      alert(`Error crítico al restaurar BD: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const handleDownloadCSV = () => {
    const validMatches = matches.filter(m => m.status === 'Simulated' || m.status === 'Completed');

    // Define phase order for grouping/sorting
    const phaseOrder: Record<string, number> = {
      'Group': 1,
      'Round of 32': 2,
      'Round of 16': 3,
      'Quarterfinals': 4,
      'Semifinals': 5,
      'Final': 6
    };

    // Sort by phase then date
    const sortedMatches = [...validMatches].sort((a, b) => {
      const phaseDiff = (phaseOrder[a.match_phase] || 99) - (phaseOrder[b.match_phase] || 99);
      if (phaseDiff !== 0) return phaseDiff;
      return new Date(a.match_date).getTime() - new Date(b.match_date).getTime();
    });

    // Generate CSV
    const headers = ['Fecha', 'Fase', 'Local', 'Goles Local', 'Goles Visitante', 'Visitante', 'Penales Local', 'Penales Visitante', 'Estado'];
    const rows = sortedMatches.map(m => [
      m.match_date,
      m.match_phase,
      m.home_team?.team_name || 'TBD',
      m.home_score !== undefined ? m.home_score : '',
      m.away_score !== undefined ? m.away_score : '',
      m.away_team?.team_name || 'TBD',
      m.home_penalty_score !== undefined && m.home_penalty_score !== null ? m.home_penalty_score : '',
      m.away_penalty_score !== undefined && m.away_penalty_score !== null ? m.away_penalty_score : '',
      m.status
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob(['\\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' }); // Added BOM for Excel
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'resultados_wc26.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Determine current phase status for simulation panel
  const groupMatches = matches.filter(m => m.match_phase === 'Group');
  const r32Matches = matches.filter(m => m.match_phase === 'Round of 32');
  const r16Matches = matches.filter(m => m.match_phase === 'Round of 16');
  const qfMatches = matches.filter(m => m.match_phase === 'Quarterfinals');
  const sfMatches = matches.filter(m => m.match_phase === 'Semifinals');
  const finalMatches = matches.filter(m => m.match_phase === 'Final');

  const groupsCompleted = groupMatches.length > 0 && groupMatches.every(m => m.status === 'Simulated' || m.status === 'Completed');
  const r32Exists = r32Matches.length > 0 && r32Matches.some(m => m.home_team && m.away_team);
  const r32Completed = r32Exists && r32Matches.every(m => m.status === 'Simulated' || m.status === 'Completed');
  const r16Exists = r16Matches.length > 0 && r16Matches.some(m => m.home_team && m.away_team);
  const r16Completed = r16Exists && r16Matches.every(m => m.status === 'Simulated' || m.status === 'Completed');
  const qfExists = qfMatches.length > 0 && qfMatches.some(m => m.home_team && m.away_team);
  const qfCompleted = qfExists && qfMatches.every(m => m.status === 'Simulated' || m.status === 'Completed');
  const sfExists = sfMatches.length > 0 && sfMatches.some(m => m.home_team && m.away_team);
  const sfCompleted = sfExists && sfMatches.every(m => m.status === 'Simulated' || m.status === 'Completed');
  const finalExists = finalMatches.length > 0 && finalMatches.some(m => m.home_team && m.away_team);
  const finalCompleted = finalExists && finalMatches.every(m => m.status === 'Simulated' || m.status === 'Completed');

  // Compute standings
  const standings = useMemo(() => {
    const groups: Record<string, string[]> = {
      'Grupo A': ['MEX', 'RSA', 'KOR', 'CZE'],
      'Grupo B': ['CAN', 'BIH', 'QAT', 'SUI'],
      'Grupo C': ['BRA', 'MAR', 'HAI', 'SCO'],
      'Grupo D': ['USA', 'PAR', 'AUS', 'TUR'],
      'Grupo E': ['GER', 'CUW', 'CIV', 'ECU'],
      'Grupo F': ['NED', 'JPN', 'SWE', 'TUN'],
      'Grupo G': ['BEL', 'EGY', 'IRN', 'NZL'],
      'Grupo H': ['ESP', 'CPV', 'KSA', 'URU'],
      'Grupo I': ['FRA', 'SEN', 'IRQ', 'NOR'],
      'Grupo J': ['ARG', 'ALG', 'AUT', 'JOR'],
      'Grupo K': ['POR', 'COD', 'UZB', 'COL'],
      'Grupo L': ['ENG', 'CRO', 'GHA', 'PAN']
    };

    const initialStats = () => ({ pg: 0, pe: 0, pp: 0, gf: 0, ga: 0, gd: 0, pts: 0 });
    const stats: Record<string, ReturnType<typeof initialStats>> = {};

    // Initialize
    Object.values(groups).flat().forEach(t => {
      stats[t] = initialStats();
    });

    // Process group matches
    groupMatches.forEach(m => {
      const h = m.home_team?.team_id;
      const a = m.away_team?.team_id;
      const hs = m.home_score;
      const as_ = m.away_score;

      if (!h || !a) return; // Safely handle missing teams

      if (hs === undefined || as_ === undefined || hs === null || as_ === null) return; // Not simulated yet

      stats[h].gf += hs;
      stats[h].ga += as_;
      stats[h].gd += (hs - as_);
      stats[a].gf += as_;
      stats[a].ga += hs;
      stats[a].gd += (as_ - hs);

      if (hs > as_) {
        stats[h].pg += 1;
        stats[h].pts += 3;
        stats[a].pp += 1;
      } else if (hs < as_) {
        stats[a].pg += 1;
        stats[a].pts += 3;
        stats[h].pp += 1;
      } else {
        stats[h].pe += 1;
        stats[h].pts += 1;
        stats[a].pe += 1;
        stats[a].pts += 1;
      }
    });

    // Format standings
    const formatted: Record<string, Array<{ team_id: string; team_name: string; pts: number; gd: number; gf: number; ga: number; pg: number; pe: number; pp: number }>> = {};

    Object.entries(groups).forEach(([gName, gTeams]) => {
      formatted[gName] = gTeams.map(tId => ({
        team_id: tId,
        team_name: teamsMap[tId] || tId,
        ...stats[tId]
      })).sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
    });

    return formatted;
  }, [groupMatches, teamsMap]);

  // Filtered matches
  const filteredMatches = useMemo(() => {
    if (phaseFilter === 'All') return matches;
    return matches.filter(m => m.match_phase === phaseFilter);
  }, [matches, phaseFilter]);

  // Selected match detail helper
  const selectedMatch = useMemo(() => {
    if (!selectedMatchId) return null;
    return matches.find(m => m.match_id === selectedMatchId) || null;
  }, [selectedMatchId, matches]);

  return (
    <div className="app-container">
      <header>
        <div className="logo-section">
          <h1>🏆 WC <span>Winner</span> 2026</h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Plataforma de Predicción Probabilística Basada en ELO & Poisson Bivariado
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="glass-panel" style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Motor Lógico:</span>
            <select 
              value={predictionAlgorithm}
              onChange={(e) => {
                setPredictionAlgorithm(e.target.value as 'ensemble' | 'mcmf');
                if (selectedMatchId) handleSelectMatch(selectedMatchId); // refresh
              }}
              style={{
                background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid var(--border-color)', 
                borderRadius: '4px', padding: '4px 8px', fontSize: '0.85rem', outline: 'none', cursor: 'pointer'
              }}
            >
              <option value="ensemble">Ensemble Estadístico (Poisson + ELO)</option>
              <option value="mcmf">Monte Carlo Match Flow (MCMF)</option>
            </select>
          </div>
          <div className="glass-panel" style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
            <span className={`pulse-indicator ${groupsCompleted ? (finalCompleted ? 'simulated' : 'live') : 'scheduled'}`}></span>
            <span style={{ color: 'var(--text-secondary)' }}>
              Estado: {groupsCompleted ? (finalCompleted ? 'Completado' : 'Fases Eliminatorias') : 'Fase de Grupos'}
            </span>
          </div>
          <button onClick={handleResetWc26} className="glow-btn" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#ef4444', boxShadow: 'none' }} disabled={simulating}>
            <RotateCcw size={16} /> Reiniciar BD
          </button>
        </div>
      </header>

      {error && (
        <div className="glass-panel" style={{ padding: '16px', borderColor: '#ef4444', color: '#fca5a5', marginBottom: '24px' }}>
          <p>{error}</p>
        </div>
      )}

      {loading && !simulating ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
          <div style={{ border: '3px solid var(--bg-tertiary)', borderTop: '3px solid var(--accent-neon)', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite' }} />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <>
          <div className="tab-nav">
            <button className={`tab-btn ${activeTab === 'matches' ? 'active' : ''}`} onClick={() => setActiveTab('matches')}>
              <Layers size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} /> Partidos y Simulación
            </button>
            <button className={`tab-btn ${activeTab === 'standings' ? 'active' : ''}`} onClick={() => setActiveTab('standings')}>
              <BarChart2 size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} /> Clasificación de Grupos
            </button>
            <button className={`tab-btn ${activeTab === 'rankings' ? 'active' : ''}`} onClick={() => setActiveTab('rankings')}>
              <Award size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} /> Rankings ELO & FIFA
            </button>
            <button className={`tab-btn ${activeTab === 'config' ? 'active' : ''}`} onClick={() => setActiveTab('config')}>
              <Settings size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} /> Configuración
            </button>
          </div>

          <div className="grid-layout">

            {/* LEFT SIDE: Active tab view */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

              {/* Tab 1: Matches & Simulation */}
              {activeTab === 'matches' && (
                <>
                  {/* Simulation flow controller */}
                  <div className="glass-panel" style={{ padding: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                      <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: '#fff', margin: 0 }}>
                        Panel de Simulación de Fases
                      </h2>
                      <button className="glow-btn" onClick={handleDownloadCSV} style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
                        <Download size={14} style={{ marginRight: '6px' }} /> Exportar CSV
                      </button>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>

                      {/* Step 1: Group Stage */}
                      <div className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderColor: groupsCompleted ? 'rgba(0, 255, 170, 0.2)' : 'var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Paso 1</span>
                        </div>
                        <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Fase de Grupos</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px' }} onClick={() => handleSimulatePhase('Group')} disabled={groupsCompleted || simulating}>
                            <Play size={14} /> Simular
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #00f0ff, #0077ff)' }} onClick={() => handleAdvanceTournament('Group')} disabled={!groupsCompleted || r32Exists || simulating}>
                            <ChevronRight size={14} /> Avanzar
                          </button>
                        </div>
                      </div>

                      {/* Step 2: R32 */}
                      <div className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderColor: r32Completed ? 'rgba(0, 255, 170, 0.2)' : 'var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Paso 2</span>
                        </div>
                        <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>16avos</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px' }} onClick={() => handleSimulatePhase('Round of 32')} disabled={!r32Exists || r32Completed || simulating}>
                            <Play size={14} /> Simular
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #00f0ff, #0077ff)' }} onClick={() => handleAdvanceTournament('Round of 32')} disabled={!r32Completed || r16Exists || simulating}>
                            <ChevronRight size={14} /> Avanzar
                          </button>
                        </div>
                      </div>

                      {/* Step 3: R16 */}
                      <div className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderColor: r16Completed ? 'rgba(0, 255, 170, 0.2)' : 'var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Paso 3</span>
                        </div>
                        <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Octavos</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px' }} onClick={() => handleSimulatePhase('Round of 16')} disabled={!r16Exists || r16Completed || simulating}>
                            <Play size={14} /> Simular
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #00f0ff, #0077ff)' }} onClick={() => handleAdvanceTournament('Round of 16')} disabled={!r16Completed || qfExists || simulating}>
                            <ChevronRight size={14} /> Avanzar
                          </button>
                        </div>
                      </div>

                      {/* Step 4: QF */}
                      <div className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderColor: qfCompleted ? 'rgba(0, 255, 170, 0.2)' : 'var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Paso 4</span>
                        </div>
                        <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Cuartos</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px' }} onClick={() => handleSimulatePhase('Quarterfinals')} disabled={!qfExists || qfCompleted || simulating}>
                            <Play size={14} /> Simular
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #00f0ff, #0077ff)' }} onClick={() => handleAdvanceTournament('Quarterfinals')} disabled={!qfCompleted || sfExists || simulating}>
                            <ChevronRight size={14} /> Avanzar
                          </button>
                        </div>
                      </div>

                      {/* Step 5: SF & Final */}
                      <div className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderColor: finalExists ? 'rgba(0, 255, 170, 0.2)' : 'var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Paso 5</span>
                        </div>
                        <h3 style={{ fontSize: '1rem', marginBottom: '12px' }}>Semis y Final</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px' }} onClick={() => handleSimulatePhase('Semifinals')} disabled={!sfExists || sfCompleted || simulating}>
                            <Play size={14} /> Simular Semis
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #00f0ff, #0077ff)' }} onClick={() => handleAdvanceTournament('Semifinals')} disabled={!sfCompleted || finalExists || simulating}>
                            <ChevronRight size={14} /> Avanzar
                          </button>
                          <button className="glow-btn" style={{ width: '100%', justifyContent: 'center', padding: '8px', background: 'linear-gradient(135deg, #ffd700, #ff8800)', color: '#000' }} onClick={() => handleSimulatePhase('Final')} disabled={!finalExists || finalCompleted || simulating}>
                            <Play size={14} /> Gran Final
                          </button>
                        </div>
                      </div>

                    </div>
                  </div>

                </>
              )}

              {/* Tab 2: Standings */}
              {activeTab === 'standings' && (
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', marginBottom: '20px', color: '#fff', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                    Clasificación en Tiempo Real de Grupos
                  </h2>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    {Object.entries(standings).map(([groupName, groupTeams]) => (
                      <div key={groupName} className="glass-panel" style={{ padding: '16px', background: 'rgba(255,255,255,0.01)' }}>
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '12px', color: 'var(--accent-cyan)' }}>{groupName}</h3>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                              <th style={{ padding: '8px' }}>Equipo</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>PTS</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>PG</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>PE</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>PP</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>GF</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>GA</th>
                              <th style={{ padding: '8px', textAlign: 'center' }}>DG</th>
                            </tr>
                          </thead>
                          <tbody>
                            {groupTeams.map((team, idx) => (
                              <tr key={team.team_id} style={{ borderBottom: idx < 3 ? '1px solid rgba(255,255,255,0.03)' : 'none', background: idx < 2 ? 'rgba(0, 255, 170, 0.01)' : 'transparent' }}>
                                <td 
                                  style={{ padding: '10px 8px', fontWeight: idx < 2 ? 600 : 400, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                                  onClick={() => setSelectedTeamId(team.team_id)}
                                  className="team-row-hover"
                                >
                                  <span style={{ fontSize: '0.8rem', color: idx < 2 ? 'var(--accent-neon)' : 'var(--text-muted)' }}>{idx + 1}</span>
                                  <span style={{ display: 'flex', alignItems: 'center' }}>
                                    {getFlagUrl(team.team_id) ? <img src={getFlagUrl(team.team_id)!} alt="" width="16" height="12" /> : '🏳️ '}
                                  </span>
                                  {team.team_name}
                                </td>
                                <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold', color: idx < 2 ? 'var(--accent-neon)' : 'var(--text-primary)' }}>{team.pts}</td>
                                <td style={{ padding: '8px', textAlign: 'center' }}>{team.pg}</td>
                                <td style={{ padding: '8px', textAlign: 'center' }}>{team.pe}</td>
                                <td style={{ padding: '8px', textAlign: 'center' }}>{team.pp}</td>
                                <td style={{ padding: '8px', textAlign: 'center' }}>{team.gf}</td>
                                <td style={{ padding: '8px', textAlign: 'center' }}>{team.ga}</td>
                                <td style={{ padding: '8px', textAlign: 'center', color: team.gd > 0 ? 'var(--accent-neon)' : team.gd < 0 ? '#ef4444' : 'var(--text-primary)' }}>
                                  {team.gd > 0 ? `+${team.gd}` : team.gd}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab 3: Rankings */}
              {activeTab === 'rankings' && (
                <>
                  {/* Interactive Plotly ELO Chart */}
                  <div className="glass-panel" style={{ padding: '20px' }}>
                    <EloChart eloData={eloRankings} teamsMap={teamsMap} />
                  </div>

                  {/* List of ELO and FIFA Rankings side-by-side */}
                  {eloRankings.length === 0 && fifaRankings.length === 0 ? (
                    <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
                      <Info size={40} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
                      <h3 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '8px' }}>Base de datos histórica vacía</h3>
                      <p style={{ color: 'var(--text-secondary)' }}>
                        Actualmente no hay datos cargados de Rankings ELO o FIFA. <br /><br />
                        Por favor, ve a la sección <strong>Configuración Avanzada</strong> y ejecuta la <strong>Restauración Base de Datos Completa</strong> para rellenar los datos.
                      </p>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>

                      {/* ELO List */}
                      <div className="glass-panel" style={{ padding: '16px' }}>
                        <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                          Ranking ELO Completo
                        </h3>
                        <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                          <table style={{ width: '100%', fontSize: '0.85rem' }}>
                            <tbody>
                              {eloRankings.map((r, i) => (
                                <tr key={r.team_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                                  <td style={{ padding: '6px' }}>{i + 1}. {teamToEmoji[r.team_id] || ''} {teamsMap[r.team_id] || r.team_id}</td>
                                  <td style={{ padding: '6px', textAlign: 'right', fontWeight: 600, color: 'var(--accent-neon)' }}>{Math.round(r.elo_rating)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* FIFA List */}
                      <div className="glass-panel" style={{ padding: '16px' }}>
                        <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '6px' }}>
                          Clasificación Mundial FIFA
                        </h3>
                        <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                          <table style={{ width: '100%', fontSize: '0.85rem' }}>
                            <tbody>
                              {fifaRankings.map((r) => (
                                <tr key={r.team_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                                  <td style={{ padding: '6px' }}>{r.rank}. {teamToEmoji[r.team_id] || ''} {teamsMap[r.team_id] || r.team_id}</td>
                                  <td style={{ padding: '6px', textAlign: 'right', fontWeight: 600, color: 'var(--accent-cyan)' }}>{Math.round(r.points)} pts</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                    </div>
                  )}
                </>
              )}

            </div>

            {/* RIGHT SIDE: Sidebar detail (Context-sensitive Match prediction panel) */}
            {(activeTab === 'matches' || activeTab === 'standings') && (
              <div className="glass-panel" style={{ padding: '20px', height: 'fit-content' }}>
                {activeTab === 'matches' && (
                  <>
                    {!selectedMatch ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        <Info size={40} style={{ color: 'var(--text-muted)', marginBottom: '12px' }} />
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '6px', color: '#fff' }}>Análisis Probabilístico</h3>
                        <p style={{ fontSize: '0.85rem', maxWidth: '280px' }}>
                          Seleccione cualquier partido del calendario para ver las estadísticas probabilísticas del modelo y el análisis detallado.
                        </p>
                      </div>
                    ) : (
                      <div>
                        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', color: '#fff', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginBottom: '16px' }}>
                          Análisis: {selectedMatch.home_team?.team_name || 'TBD'} vs {selectedMatch.away_team?.team_name || 'TBD'}
                        </h3>

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px' }}>
                          <div style={{ textAlign: 'center', width: '45%' }}>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{selectedMatch.home_team?.team_name || 'TBD'}</span>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '6px' }}>
                              <span style={{ fontSize: '0.75rem', padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: '4px', color: 'var(--accent-cyan)' }}>
                                ELO: {selectedMatch.home_team ? Math.round(eloRankings.find(r => r.team_id === selectedMatch.home_team?.team_id)?.elo_rating || 1500) : '---'}
                              </span>
                              <span style={{ fontSize: '0.75rem', padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: '4px', color: 'var(--accent-gold)' }}>
                                FIFA: #{selectedMatch.home_team ? (fifaRankings.find(r => r.team_id === selectedMatch.home_team?.team_id)?.rank || '?') : '---'}
                              </span>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>VS</div>

                          <div style={{ textAlign: 'center', width: '45%' }}>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{selectedMatch.away_team?.team_name || 'TBD'}</span>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '6px' }}>
                              <span style={{ fontSize: '0.75rem', padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: '4px', color: 'var(--accent-cyan)' }}>
                                ELO: {selectedMatch.away_team ? Math.round(eloRankings.find(r => r.team_id === selectedMatch.away_team?.team_id)?.elo_rating || 1500) : '---'}
                              </span>
                              <span style={{ fontSize: '0.75rem', padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: '4px', color: 'var(--accent-gold)' }}>
                                FIFA: #{selectedMatch.away_team ? (fifaRankings.find(r => r.team_id === selectedMatch.away_team?.team_id)?.rank || '?') : '---'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {(selectedMatch.status === 'Simulated' || selectedMatch.status === 'Completed') && selectedMatch.stats && (
                          <div className="glass-panel" style={{ padding: '12px', marginBottom: '16px', background: 'rgba(255,255,255,0.01)' }}>
                            <h4 style={{ fontSize: '0.9rem', marginBottom: '8px', color: selectedMatch.status === 'Completed' ? '#4ade80' : 'var(--accent-gold)' }}>
                              {selectedMatch.status === 'Completed' ? 'Estadísticas del Partido' : 'Estadísticas de la Simulación'}
                            </h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.8rem' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Goles Marcados:</span>
                                <span style={{ fontWeight: 600 }}>{selectedMatch.home_score} - {selectedMatch.away_score}</span>
                              </div>
                              {selectedMatch.home_penalty_score !== null && (
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                  <span>Penaltis:</span>
                                  <span style={{ fontWeight: 600 }}>{selectedMatch.home_penalty_score} - {selectedMatch.away_penalty_score}</span>
                                </div>
                              )}
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span>Estado:</span>
                                <span style={{ color: selectedMatch.status === 'Completed' ? '#4ade80' : 'var(--accent-gold)' }}>
                                  {selectedMatch.status === 'Completed' ? 'Completado (Real)' : 'Simulado'}
                                </span>
                              </div>
                            </div>
                          </div>
                        )}

                        {selectedMatch.status === 'Scheduled' && (
                          <>
                            {prediction ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--accent-neon)' }}>
                                  Algoritmo utilizado: {predictionAlgorithm === 'ensemble' ? 'Ensemble Estadístico' : 'Monte Carlo Match Flow'}
                                </div>
                                {/* Prediction donut chart */}
                                <PredictionChart
                                  homeName={selectedMatch.home_team?.team_name || 'TBD'}
                                  awayName={selectedMatch.away_team?.team_name || 'TBD'}
                                  homeWinProb={prediction.home_win_prob}
                                  drawProb={prediction.draw_prob}
                                  awayWinProb={prediction.away_win_prob}
                                />

                                {/* Probability numeric summary */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', textAlign: 'center' }}>
                                  <div className="glass-panel" style={{ padding: '8px', background: 'rgba(0, 240, 255, 0.05)' }}>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{selectedMatch.home_team?.team_code || 'L'} Gana</span>
                                    <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '4px' }}>
                                      {Math.round(prediction.home_win_prob * 100)}%
                                    </p>
                                  </div>
                                  <div className="glass-panel" style={{ padding: '8px', background: 'rgba(255, 255, 255, 0.02)' }}>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Empate</span>
                                    <p style={{ fontSize: '1rem', fontWeight: 700, color: '#9ca3af', marginTop: '4px' }}>
                                      {Math.round(prediction.draw_prob * 100)}%
                                    </p>
                                  </div>
                                  <div className="glass-panel" style={{ padding: '8px', background: 'rgba(0, 255, 170, 0.05)' }}>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{selectedMatch.away_team?.team_code || 'V'} Gana</span>
                                    <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-neon)', marginTop: '4px' }}>
                                      {Math.round(prediction.away_win_prob * 100)}%
                                    </p>
                                  </div>
                                </div>

                                {/* Poisson Expected Goals & Scoreline */}
                                <div className="glass-panel" style={{ padding: '14px', background: 'rgba(255,255,255,0.01)' }}>
                                  <h4 style={{ fontSize: '0.9rem', color: '#fff', marginBottom: '8px' }}>Expectativas de Goles (Modelo Poisson)</h4>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                      <span>Goles Esperados {selectedMatch.home_team?.team_code || 'L'}:</span>
                                      <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{prediction.expected_home_goals.toFixed(2)}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                      <span>Goles Esperados {selectedMatch.away_team?.team_code || 'V'}:</span>
                                      <span style={{ fontWeight: 600, color: 'var(--accent-neon)' }}>{prediction.expected_away_goals.toFixed(2)}</span>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '6px', marginTop: '4px' }}>
                                      <span style={{ fontWeight: 600 }}>Marcador Más Probable:</span>
                                      <span style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>
                                        {prediction.most_likely_score ? `${prediction.most_likely_score} (${Math.round(prediction.most_likely_score_prob * 100)}%)` : 'N/A'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '150px' }}>
                                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Cargando predicciones del modelo...</span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </>
                )}

                {activeTab === 'standings' && (
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', color: '#fff', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px', marginBottom: '16px' }}>
                      Partidos Jugados: {selectedTeamId ? (teamsMap[selectedTeamId] || selectedTeamId) : 'Seleccione un equipo'}
                    </h3>
                    {!selectedTeamId ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '200px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                        <Info size={40} style={{ color: 'var(--text-muted)', marginBottom: '12px' }} />
                        <p style={{ fontSize: '0.85rem' }}>Haga clic en un equipo de la tabla para ver sus partidos.</p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {matches
                          .filter(m => m.home_team?.team_id === selectedTeamId || m.away_team?.team_id === selectedTeamId)
                          .sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())
                          .length === 0 ? (
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textAlign: 'center', marginTop: '20px' }}>No hay partidos registrados todavía.</p>
                        ) : matches
                          .filter(m => m.home_team?.team_id === selectedTeamId || m.away_team?.team_id === selectedTeamId)
                          .sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())
                          .map(m => {
                            const isHome = m.home_team?.team_id === selectedTeamId;
                            const opponentName = isHome ? m.away_team?.team_name : m.home_team?.team_name;
                            const opponentId = isHome ? m.away_team?.team_id : m.home_team?.team_id;
                            const ourScore = isHome ? m.home_score : m.away_score;
                            const theirScore = isHome ? m.away_score : m.home_score;
                            
                            let resultColor = 'var(--text-secondary)';
                            let resultText = 'Pendiente';
                            
                            if (m.status === 'Completed' || m.status === 'Simulated') {
                              if (ourScore !== undefined && theirScore !== undefined) {
                                if (ourScore > theirScore) {
                                  resultColor = 'var(--accent-neon)';
                                  resultText = 'Victoria';
                                } else if (ourScore < theirScore) {
                                  resultColor = '#ef4444';
                                  resultText = 'Derrota';
                                } else {
                                  resultColor = '#9ca3af';
                                  resultText = 'Empate';
                                }
                              }
                            }

                            return (
                              <div key={m.match_id} style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                                    {m.match_date} - {m.match_phase}
                                  </span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
                                    <span style={{ color: resultColor, fontWeight: 'bold', width: '60px', display: 'inline-block' }}>{resultText}</span>
                                    vs {opponentId && getFlagUrl(opponentId) ? <img src={getFlagUrl(opponentId)!} alt="" width="16" height="12" /> : '🏳️'} {opponentName}
                                  </div>
                                </div>
                                {(ourScore !== undefined && theirScore !== undefined) && (
                                  <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: resultColor }}>
                                    {isHome ? `${ourScore} - ${theirScore}` : `${theirScore} - ${ourScore}`}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            {/* Tab 4: Config */}
            {activeTab === 'config' && (
              <div className="glass-panel" style={{ padding: '24px', gridColumn: '1 / -1' }}>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '20px', color: '#fff', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  Configuración Avanzada
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div className="glass-panel" style={{ padding: '20px', background: 'rgba(239, 68, 68, 0.05)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                    <h3 style={{ fontSize: '1.2rem', color: '#ef4444', marginBottom: '12px' }}>Restaurar Base de Datos Completa (Local CSV)</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                      Esta acción borrará absolutamente <strong>todos</strong> los datos de la base de datos actual y la restaurará rápidamente a partir de los respaldos locales CSV (incluyendo histórico, ELOs y estadísticas pre-calculadas).
                      <br /><br />
                      <strong>Aviso:</strong> Esta operación perderá cualquier progreso de simulación actual.
                    </p>
                    <button onClick={handleResetAll} className="glow-btn" style={{ background: '#ef4444', color: '#fff', border: 'none', padding: '10px 20px', fontWeight: 'bold' }} disabled={simulating}>
                      <RotateCcw size={18} style={{ marginRight: '8px' }} />
                      Ejecutar Restauración Completa
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
          {/* Full width Matches list (Calendario de Partidos) */}
          {activeTab === 'matches' && (
            <div style={{ marginTop: '24px' }}>
              {/* Matches list */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: '#fff' }}>
                    Calendario de Partidos
                  </h2>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {['All', 'Group', 'Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Final'].map(f => {
                      let label = f === 'All' ? 'Todos' : f === 'Group' ? 'Grupos' : f === 'Round of 32' ? '16avos' : f === 'Round of 16' ? 'Octavos' : f === 'Quarterfinals' ? 'Cuartos' : f === 'Semifinals' ? 'Semis' : 'Final';
                      return (
                        <button
                          key={f}
                          style={{ padding: '4px 10px', borderRadius: '6px', border: '1px solid var(--border-color)', background: phaseFilter === f ? 'var(--bg-tertiary)' : 'transparent', color: phaseFilter === f ? 'var(--accent-neon)' : 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.8rem' }}
                          onClick={() => setPhaseFilter(f)}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <button
                    className="glow-btn"
                    onClick={() => setIsBracketVisible(!isBracketVisible)}
                    style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
                  >
                    <Layers size={18} style={{ marginRight: '8px' }} />
                    {isBracketVisible ? 'Ocultar Cuadro del Torneo' : 'Ver Cuadro del Torneo (Knockout Bracket)'}
                  </button>
                </div>

                {isBracketVisible && (
                  <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border-color)', marginBottom: '16px', overflowX: 'auto' }}>
                    <TournamentBracket matches={matches} />
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '550px', overflowY: 'auto', paddingRight: '4px', marginTop: '16px' }}>
                  {filteredMatches.length === 0 ? (
                    <p style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
                      No hay partidos disponibles para esta fase. Avance en la simulación.
                    </p>
                  ) : (
                    filteredMatches.map(m => {
                      const isSelected = m.match_id === selectedMatchId;
                      return (
                        <div
                          key={m.match_id}
                          className="glass-panel"
                          style={{
                            padding: '14px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            cursor: 'pointer',
                            background: isSelected ? 'rgba(0, 255, 170, 0.04)' : 'var(--glass-bg)',
                            borderColor: isSelected ? 'var(--accent-neon)' : 'var(--glass-border)'
                          } as React.CSSProperties}
                          onClick={() => handleSelectMatch(m.match_id)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '30%' }}>
                            <Calendar size={14} style={{ color: 'var(--text-muted)' }} />
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.match_date}</span>
                              <span style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>{m.match_phase}</span>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', width: '50%' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '40%', justifyContent: 'flex-end' }}>
                              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{m.home_team?.team_name || 'TBD'}</span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.home_team?.team_code || '---'}</span>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--bg-primary)', padding: '4px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', minWidth: '60px', justifyContent: 'center' }}>
                              {m.status === 'Scheduled' ? (
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>VS</span>
                              ) : (
                                <>
                                  <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--accent-neon)' }}>{m.home_score}</span>
                                  <span style={{ color: 'var(--text-muted)' }}>-</span>
                                  <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--accent-neon)' }}>{m.away_score}</span>
                                </>
                              )}
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '40%' }}>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.away_team?.team_code || '---'}</span>
                              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{m.away_team?.team_name || 'TBD'}</span>
                            </div>
                          </div>

                          <div style={{ width: '20%', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '8px' }}>
                            {m.home_penalty_score !== null && m.home_penalty_score !== undefined && (
                              <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', marginRight: '6px' }}>
                                (Pen: {m.home_penalty_score}-{m.away_penalty_score})
                              </span>
                            )}
                            <span style={{
                              fontSize: '0.7rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background: m.status === 'Completed' ? (m.tournament_id === 'WC26' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(255,255,255,0.05)') : m.status === 'Simulated' ? 'rgba(255,215,0,0.1)' : 'rgba(0,240,255,0.1)',
                              color: m.status === 'Completed' ? (m.tournament_id === 'WC26' ? '#4ade80' : 'var(--text-secondary)') : m.status === 'Simulated' ? 'var(--accent-gold)' : 'var(--accent-cyan)'
                            }}>
                              {m.status === 'Completed' ? (m.tournament_id === 'WC26' ? 'Real' : 'Histórico') : m.status === 'Simulated' ? 'Simulado' : 'Predicción'}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {simulating && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(8, 11, 17, 0.8)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ border: '3px solid var(--bg-tertiary)', borderTop: '3px solid var(--accent-neon)', borderRadius: '50%', width: '50px', height: '50px', animation: 'spin 1s linear infinite', marginBottom: '16px' }} />
          <p style={{ fontFamily: 'var(--font-display)', color: '#fff', fontSize: '1.1rem' }}>Procesando simulación en base de datos...</p>
        </div>
      )}

    </div>
  );
}
