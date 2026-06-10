import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface PredictionChartProps {
  homeName: string;
  awayName: string;
  homeWinProb: number;
  drawProb: number;
  awayWinProb: number;
}

export const PredictionChart: React.FC<PredictionChartProps> = ({
  homeName,
  awayName,
  homeWinProb,
  drawProb,
  awayWinProb
}) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    const data: any[] = [
      {
        values: [
          Math.round(homeWinProb * 100),
          Math.round(drawProb * 100),
          Math.round(awayWinProb * 100)
        ],
        labels: [`Victoria ${homeName}`, 'Empate', `Victoria ${awayName}`],
        type: 'pie',
        hole: 0.6,
        marker: {
          colors: ['#00f0ff', '#1f2937', '#00ffaa']
        },
        hoverinfo: 'label+percent',
        textinfo: 'percent',
        textposition: 'inside',
        insidetextorientation: 'radial'
      }
    ];

    const layout: any = {
      showlegend: true,
      legend: {
        orientation: 'h',
        x: 0,
        y: -0.1,
        font: {
          family: 'Outfit, sans-serif',
          color: '#9ca3af',
          size: 11
        }
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { t: 10, b: 50, l: 10, r: 10 },
      width: 300,
      height: 300,
      autosize: true
    };

    const config: any = {
      responsive: true,
      displayModeBar: false
    };

    Plotly.newPlot(chartRef.current, data, layout, config);

    return () => {
      if (chartRef.current) {
        Plotly.purge(chartRef.current);
      }
    };
  }, [homeName, awayName, homeWinProb, drawProb, awayWinProb]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      <div ref={chartRef} style={{ width: '100%', maxWidth: '300px', height: '300px' }} />
    </div>
  );
};
