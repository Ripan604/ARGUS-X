'use client';

import { useEffect, useRef } from 'react';
import type { MeasurementAnalysis } from '@/types/argus';

function LinePlot({ x, y, color = '#b7f55a', label }: { x: number[]; y: number[]; color?: string; label: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current, context = canvas?.getContext('2d'); if (!canvas || !context || y.length < 2) return;
    const width = canvas.width, height = canvas.height, pad = 28;
    context.fillStyle = '#08110e'; context.fillRect(0, 0, width, height); context.strokeStyle = '#263732'; context.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) { const py = pad + i * (height - pad * 2) / 4; context.beginPath(); context.moveTo(pad, py); context.lineTo(width - pad, py); context.stroke(); }
    const min = Math.min(...y), max = Math.max(...y), span = max - min || 1;
    context.strokeStyle = color; context.lineWidth = 1.6; context.beginPath();
    y.forEach((value, index) => { const px = pad + index / (y.length - 1) * (width - pad * 2); const py = height - pad - (value - min) / span * (height - pad * 2); if (index) context.lineTo(px, py); else context.moveTo(px, py); }); context.stroke();
    context.fillStyle = '#71847c'; context.font = '10px monospace'; context.fillText(x[0]?.toFixed(3) ?? '0', pad, height - 8); context.fillText(x.at(-1)?.toFixed(3) ?? '', width - 65, height - 8);
  }, [x, y, color]);
  return <div className="plot-frame"><span>{label}</span><canvas ref={ref} width={720} height={210} /></div>;
}

function SpectrogramPlot({ analysis }: { analysis: MeasurementAnalysis }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current, context = canvas?.getContext('2d'); if (!canvas || !context) return;
    const matrix = analysis.spectrogram_db; if (!matrix.length || !matrix[0]?.length) return;
    const values = matrix.flat(), low = Math.min(...values), high = Math.max(...values), rows = matrix.length, columns = matrix[0].length;
    context.fillStyle = '#08110e'; context.fillRect(0, 0, canvas.width, canvas.height);
    matrix.forEach((row, y) => row.forEach((value, x) => {
      const t = (value - low) / (high - low || 1); context.fillStyle = `rgb(${Math.round(14 + 180 * t)},${Math.round(35 + 210 * t)},${Math.round(45 + 20 * (1 - t))})`;
      context.fillRect(x * canvas.width / columns, canvas.height - (y + 1) * canvas.height / rows, canvas.width / columns + 1, canvas.height / rows + 1);
    }));
  }, [analysis]);
  return <div className="plot-frame"><span>TIME–FREQUENCY ENERGY</span><canvas ref={ref} width={720} height={210} /></div>;
}

export function SignalPlots({ analysis }: { analysis: MeasurementAnalysis | null }) {
  if (!analysis) return <div className="empty-analysis"><b>NO SIGNAL ACQUIRED</b><p>Run the recommended experiment or upload a WAV measurement to inspect its waveform, spectrum, and extracted features.</p></div>;
  return <>
    <div className="plot-grid">
      <LinePlot x={analysis.time_s} y={analysis.waveform} label="TIME RESPONSE · SECONDS" />
      <LinePlot x={analysis.fft_frequency_hz} y={analysis.fft_power} color="#f19554" label="FFT POWER · HZ" />
      <SpectrogramPlot analysis={analysis} />
    </div>
    <div className="feature-grid">
      {Object.entries(analysis.features).map(([name, value]) => <div key={name}><small>{name.replaceAll('_', ' ')}</small><strong>{Math.abs(value) >= 100 ? value.toFixed(1) : value.toFixed(4)}</strong></div>)}
    </div>
  </>;
}
