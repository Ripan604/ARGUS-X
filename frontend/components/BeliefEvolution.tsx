'use client';

import { useEffect, useRef, useState } from 'react';
import type { HistoryItem } from '@/types/argus';
import { posteriorColor } from '@/utils/posteriorDisplay';

function entropy(grid: number[][]): number { return -grid.flat().reduce((sum, p) => sum + (p > 0 ? p * Math.log2(p) : 0), 0); }

function MiniHeatmap({ grid }: { grid: number[][] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const context = ref.current?.getContext('2d'); if (!context) return;
    const maximum = Math.max(...grid.flat()), rows = grid.length, columns = grid[0].length;
    grid.forEach((row, y) => row.forEach((value, x) => { context.fillStyle = posteriorColor(value, maximum); context.fillRect(x * 160 / columns, y * 108 / rows, 160 / columns + 1, 108 / rows + 1); }));
  }, [grid]);
  return <canvas ref={ref} width={160} height={108} role="img" aria-label={`Posterior probability field with entropy ${entropy(grid).toFixed(2)} bits`} />;
}

export function BeliefEvolution({ history, initial }: { history: HistoryItem[]; initial: number[][] }) {
  const frames = [{ index: 0, grid: initial }, ...history.map((item) => ({ index: item.experiment_index, grid: item.posterior_after }))];
  const [active, setActive] = useState(0), [playing, setPlaying] = useState(false);
  const displayed = Math.min(active, frames.length - 1);
  useEffect(() => { if (!playing || frames.length < 2) return; const timer = window.setInterval(() => setActive((current) => current >= frames.length - 1 ? 0 : current + 1), 850); return () => window.clearInterval(timer); }, [playing, frames.length]);
  const selectedHistory = displayed > 0 ? history[displayed - 1] : null;
  return <div className="evolution-layout">
    <div><div className="timeline-controls"><button onClick={() => setPlaying((value) => !value)} disabled={frames.length < 2}>{playing ? 'PAUSE' : 'PLAY EVOLUTION'}</button><button onClick={() => { setPlaying(false); setActive(0); }}>RESET</button><input aria-label="Belief timeline" type="range" min="0" max={Math.max(0, frames.length - 1)} value={displayed} onChange={(event) => { setPlaying(false); setActive(Number(event.target.value)); }} /><b>t={displayed}</b></div><div className="timeline-focus"><MiniHeatmap grid={frames[displayed].grid} /><div><p className="eyebrow">SELECTED STATE</p><strong>{entropy(frames[displayed].grid).toFixed(3)} bits</strong><span>{selectedHistory ? `${selectedHistory.planner.action_type.toUpperCase()} · ${selectedHistory.parameters.waveform.replaceAll('_', ' ').toUpperCase()}` : 'UNIFORM PRIOR · BEFORE ACQUISITION'}</span><small>{selectedHistory ? `TX ${selectedHistory.parameters.source_x.toFixed(2)},${selectedHistory.parameters.source_y.toFixed(2)} → RX ${selectedHistory.parameters.receiver_x.toFixed(2)},${selectedHistory.parameters.receiver_y.toFixed(2)} · evidence ${Number(selectedHistory.diagnostics.evidence_weight ?? 0).toFixed(2)}` : 'Ground truth remains sealed.'}</small></div></div>
    <div className="evolution-filmstrip">
      {frames.map((frame, frameIndex) => <article key={frame.index} role="button" tabIndex={0} aria-label={`Show experiment ${frame.index}`} aria-pressed={frameIndex === displayed} className={frameIndex === displayed ? 'active-frame' : ''} onClick={() => { setPlaying(false); setActive(frameIndex); }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setPlaying(false); setActive(frameIndex); } }}><div><span>EXP {String(frame.index).padStart(2, '0')}</span><b>{entropy(frame.grid).toFixed(2)} bits</b></div><MiniHeatmap grid={frame.grid} /></article>)}
    </div>
    </div>
    <div className="entropy-trend">
      <p className="eyebrow">Entropy trajectory</p>
      <div className="bar-chart">{frames.map((frame) => { const normalized = entropy(frame.grid) / Math.log2(frame.grid.flat().length); return <div key={frame.index}><span style={{ height: `${normalized * 100}%` }} /><small>{frame.index}</small></div>; })}</div>
    </div>
  </div>;
}
