'use client';

import { useId, useMemo } from 'react';
import type { SessionState } from '@/types/argus';
import type { GridCell } from '@/utils/heatmapGeometry';
import { posteriorProfiles, profileCsv } from '@/utils/posteriorProfiles';
import './posterior-profiles.css';

function SliceChart({ axis, points, extent, peak, selected, onSelect }: {
  axis: 'X' | 'Y'; points: { coordinateMm: number; probability: number }[]; extent: number;
  peak: number; selected: number; onSelect: (index: number) => void;
}) {
  const gradientId = useId();
  const x = (mm: number) => 49 + mm / extent * 329, y = (mass: number) => 133 - mass / peak * 105;
  const path = points.map((point, index) => `${index ? 'L' : 'M'} ${x(point.coordinateMm)} ${y(point.probability)}`).join(' ');
  const selectedPoint = points[selected];
  return <div className={`posterior-slice posterior-slice-${axis.toLowerCase()}`}>
    <div className="posterior-slice-heading"><span>{axis === 'X' ? 'HORIZONTAL SLICE' : 'VERTICAL SLICE'}</span><b>{axis} · {selectedPoint.coordinateMm.toFixed(1)} <small>mm</small></b></div>
    <svg viewBox="0 0 400 170" role="img" aria-label={`${axis} slice. Selected position ${selectedPoint.coordinateMm.toFixed(1)} millimeters, ${(selectedPoint.probability * 100).toFixed(4)} percent cell probability. Both charts share a maximum of ${(peak * 100).toFixed(4)} percent.`}>
      <defs><linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1"><stop stopColor="currentColor" stopOpacity=".28" /><stop offset="1" stopColor="currentColor" stopOpacity=".015" /></linearGradient></defs>
      {[0, .5, 1].map(fraction => <g key={fraction}><path d={`M 49 ${y(peak * fraction)} H 378`} stroke="#a2c9df1c" strokeDasharray={fraction ? '3 5' : undefined} /><text x="41" y={y(peak * fraction) + 3} textAnchor="end" fill="#8faec2" fontSize="8">{(peak * fraction * 100).toFixed(peak < .001 ? 3 : 2)}</text></g>)}
      <text x="49" y="13" fill="#8faec2" fontSize="8">CELL MASS / %</text>
      <path d={`${path} L ${x(points[points.length - 1].coordinateMm)} 133 L ${x(points[0].coordinateMm)} 133 Z`} fill={`url(#${gradientId})`} />
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d={`M ${x(selectedPoint.coordinateMm)} 26 V 133`} stroke="currentColor" strokeOpacity=".6" strokeDasharray="3 4" />
      <circle cx={x(selectedPoint.coordinateMm)} cy={y(selectedPoint.probability)} r="4" fill="currentColor" stroke="#0d1b2a" strokeWidth="2" />
      {[0, .5, 1].map(fraction => <text key={fraction} x={x(extent * fraction)} y="153" textAnchor="middle" fill="#8faec2" fontSize="9">{(extent * fraction).toFixed(0)}</text>)}
      <text x="213" y="168" textAnchor="middle" fill="#8faec2" fontSize="8">{axis} POSITION / mm</text>
    </svg>
    <label className="posterior-slice-control"><span>Move along {axis}</span><input aria-label={`Selected ${axis} cell`} aria-valuetext={`${selectedPoint.coordinateMm.toFixed(1)} millimeters`} type="range" min="0" max={points.length - 1} step="1" value={selected} onChange={event => onSelect(Number(event.target.value))} /><output>{selected + 1} / {points.length}</output></label>
  </div>;
}

export function PosteriorProfiles({ session, cell, onSelect }: { session: SessionState; cell: GridCell; onSelect: (cell: GridCell) => void }) {
  const widthMm = session.panel.width_m * 1000, heightMm = session.panel.height_m * 1000;
  const profiles = useMemo(() => posteriorProfiles(session.posterior, cell, widthMm, heightMm), [session.posterior, cell, widthMm, heightMm]);
  if (!profiles) return <p className="posterior-profile-unavailable" role="status">Profiles require a valid, normalized posterior and a cell inside the grid.</p>;
  const snapToMap = () => onSelect({ row: Math.min(profiles.rows - 1, Math.max(0, Math.floor(session.status.map_y * profiles.rows))), column: Math.min(profiles.columns - 1, Math.max(0, Math.floor(session.status.map_x * profiles.columns))) });
  const exportProfile = () => {
    const url = URL.createObjectURL(new Blob([profileCsv(profiles)], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `argus-profiles-${session.id.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 60)}-observation-${session.status.experiment_count}.csv`;
    anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <section className="posterior-profiles" aria-label="Linked posterior inspection">
    <header><div><p className="eyebrow">LINKED INSPECTION / CELL {cell.column + 1}, {cell.row + 1}</p><h3>Explore the probability landscape.</h3><p>Move the crosshair in 2D or use the sliders. The same location is highlighted in 3D.</p></div><div className="posterior-profile-actions"><button onClick={snapToMap}>Inspect MAP</button><button onClick={exportProfile}>Export slices <span aria-hidden="true">↗</span></button></div></header>
    <div className="posterior-profiles-grid"><div className="posterior-selected-readout"><p>INSPECTED CELL</p><strong>{(profiles.probability * 100).toFixed(4)}<small>% mass</small></strong><dl><div><dt>X</dt><dd>{profiles.xMm.toFixed(1)} mm</dd></div><div><dt>Y</dt><dd>{profiles.yMm.toFixed(1)} mm</dd></div><div><dt>Relative to peak</dt><dd>{(profiles.probability / profiles.peak * 100).toFixed(1)}%</dd></div></dl><span><i />Crosshair = inspection location</span></div><SliceChart axis="X" points={profiles.horizontal} extent={widthMm} peak={profiles.peak} selected={cell.column} onSelect={column => onSelect({ ...cell, column })} /><SliceChart axis="Y" points={profiles.vertical} extent={heightMm} peak={profiles.peak} selected={cell.row} onSelect={row => onSelect({ ...cell, row })} /></div>
    <p className="posterior-profile-note">Both profiles use the same vertical scale: the current posterior’s peak cell mass. These are exact row and column slices, not summed marginals or physical cross-sections through the material.</p>
  </section>;
}
