import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface EloChartProps {
  eloData: Array<{ team_id: string; elo_rating: number }>;
  teamsMap: Record<string, string>;
}

export const EloChart: React.FC<EloChartProps> = ({ eloData, teamsMap }) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current || eloData.length === 0) return;

    // Take top 15 teams
    const topTeams = eloData.slice(0, 15);
    const xData = topTeams.map(d => teamsMap[d.team_id] || d.team_id);
    const yData = topTeams.map(d => d.elo_rating);

    const trace: any = {
      x: xData,
      y: yData,
      type: 'bar',
      marker: {
        color: yData.map(v => v > 1700 ? '#00f0ff' : '#00ffaa'),
        opacity: 0.85,
        line: {
          color: '#080b11',
          width: 1.5
        }
      },
      hovertemplate: '<b>%{x}</b><br>Rating ELO: %{y:.1f}<extra></extra>'
    };

    const layout: any = {
      title: {
        text: 'Top 15 Ranking ELO Global',
        font: {
          family: 'Space Grotesk, sans-serif',
          size: 16,
          color: '#f3f4f6'
        }
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      xaxis: {
        tickfont: {
          color: '#9ca3af',
          family: 'Outfit, sans-serif'
        },
        gridcolor: 'rgba(255,255,255,0.05)',
        zeroline: false
      },
      yaxis: {
        title: {
          text: 'Puntos ELO',
          font: { color: '#9ca3af' }
        },
        tickfont: {
          color: '#9ca3af',
          family: 'Outfit, sans-serif'
        },
        gridcolor: 'rgba(255,255,255,0.05)',
        zeroline: false,
        range: [1300, Math.max(...yData) + 50]
      },
      margin: { t: 50, b: 60, l: 60, r: 20 },
      autosize: true
    };

    const config: any = {
      responsive: true,
      displayModeBar: false
    };

    Plotly.newPlot(chartRef.current, [trace], layout, config);

    // Cleanup on unmount or re-render
    return () => {
      if (chartRef.current) {
        Plotly.purge(chartRef.current);
      }
    };
  }, [eloData, teamsMap]);

  return (
    <div style={{ width: '100%', height: '350px', position: 'relative' }}>
      <div ref={chartRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
};
