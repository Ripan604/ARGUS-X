'use client';

import { useEffect, useRef } from 'react';
import type { HistoryItem } from '@/types/argus';

function entropy(grid: number[][]): number { return -grid.flat().reduce((sum, p) => sum + (p > 0 ? p * Math.log2(p) : 0), 0); }

function MiniHeatmap({ grid }: { grid: number[][] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const context = ref.current?.getContext('2d'); if (!context) return;
    const maximum = Math.max(...grid.flat()), rows = grid.length, columns = grid[0].length;
    grid.forEach((row, y) => row.forEach((value, x) => { const t = Math.sqrt(value / maximum); context.fillStyle = `rgb(${Math.round(11 + 100 * t)},${Math.round(25 + 220 * t)},${Math.round(23 + 50 * (1 - t))})`; context.fillRect(x * 160 / columns, y * 108 / rows, 160 / columns + 1, 108 / rows + 1); }));
  }, [grid]);
  return <canvas ref={ref} width={160} height={108} />;
}

export function BeliefEvolution({ history, initial }: { history: HistoryItem[]; initial: number[][] }) {
  const frames = [{ index: 0, grid: initial }, ...history.map((item) => ({ index: item.experiment_index, grid: item.posterior_after }))];
  return <div className="evolution-layout">
    <div className="evolution-filmstrip">
      {frames.map((frame) => <article key={frame.index}><div><span>EXP {String(frame.index).padStart(2, '0')}</span><b>{entropy(frame.grid).toFixed(2)} bits</b></div><MiniHeatmap grid={frame.grid} /></article>)}
    </div>
    <div className="entropy-trend">
      <p className="eyebrow">Entropy trajectory</p>
      <div className="bar-chart">{frames.map((frame) => { const normalized = entropy(frame.grid) / Math.log2(frame.grid.flat().length); return <div key={frame.index}><span style={{ height: `${normalized * 100}%` }} /><small>{frame.index}</small></div>; })}</div>
    </div>
  </div>;
}
