'use client';

import { useState } from 'react';
import { NarrativeTwin } from './NarrativeTwin';
import { HeatmapCanvas } from './HeatmapCanvas';
import { PosteriorProfiles } from './PosteriorProfiles';
import type { GridCell } from '@/utils/heatmapGeometry';
import type { HistoryItem, SessionState } from '@/types/argus';
import './spatial-observatory.css';

type View = '3d' | '2d' | 'split';
const VIEWS: { id: View; label: string; icon: string }[] = [
  { id: '3d', label: '3D surface', icon: '◇' },
  { id: '2d', label: '2D inspection', icon: '▦' },
  { id: 'split', label: 'Split view', icon: '◫' },
];

export function SpatialObservatory({ session, history, disabled, onNoGoChange }: {
  session: SessionState;
  history: HistoryItem[];
  disabled: boolean;
  onNoGoChange: (regions: SessionState['no_go_regions']) => void;
}) {
  const [view, setView] = useState<View>('3d');
  const [expanded, setExpanded] = useState(false);
  const [selectedCell, setSelectedCell] = useState<GridCell>(() => ({ row: Math.min(session.posterior.length - 1, Math.max(0, Math.floor(session.status.map_y * session.posterior.length))), column: Math.min(session.posterior[0].length - 1, Math.max(0, Math.floor(session.status.map_x * session.posterior[0].length))) }));
  const { status, panel } = session;
  const widthMm = panel.width_m * 1000, heightMm = panel.height_m * 1000;
  const containment = status.posterior_containment;
  const radii = [...containment.probabilities].sort((a, b) => a.radius_mm - b.radius_mm);
  return <section className={`spatial-observatory ${expanded ? 'observatory-expanded' : ''}`} aria-labelledby="spatial-observatory-title">
    <header className="observatory-heading">
      <div><p className="eyebrow">SPATIAL OBSERVATORY / CURRENT POSTERIOR</p><h2 id="spatial-observatory-title">See the shape of uncertainty.</h2></div>
      <span className="observatory-snapshot">{session.mode === 'physical' ? 'PHYSICAL SESSION' : 'SIMULATION'}<i />{String(status.experiment_count).padStart(2, '0')} OBSERVATIONS</span>
    </header>
    <div className="observatory-toolbar">
      <div className="observatory-modes" role="group" aria-label="Spatial visualization mode">{VIEWS.map(item => <button key={item.id} aria-pressed={view === item.id} onClick={() => setView(item.id)}><span aria-hidden="true">{item.icon}</span>{item.label}</button>)}</div>
      {view !== '2d' && <button className="observatory-expand" aria-pressed={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? 'Standard height' : 'Expand scene'}<span aria-hidden="true">{expanded ? '↙' : '↗'}</span></button>}
    </div>
    <div className={`observatory-body observatory-${view}`}>
      <div className="observatory-views">
        <div className="observatory-surface" hidden={view === '2d'}><NarrativeTwin key={session.id} session={session} history={history} presentation="hero" active={view !== '2d'} selectedCell={selectedCell} onSelectCell={setSelectedCell} /></div>
        <div className="observatory-planar" hidden={view === '3d'}><div className="observatory-planar-heading"><strong>Planar inspection</strong><span>PHYSICAL COORDINATES / mm</span></div><HeatmapCanvas session={session} history={history} disabled={disabled} active={view !== '3d'} selectedCell={selectedCell} onSelectCell={setSelectedCell} onNoGoChange={onNoGoChange} /></div>
      </div>
      <aside className="observatory-inspector" aria-label="Posterior field readout">
        <p className="eyebrow">FIELD READOUT</p>
        <div className="observatory-map-label"><i />MAP LOCATION<span>MODEL ESTIMATE</span></div>
        <div className="observatory-coordinates"><div><span>X</span><strong>{(status.map_x * widthMm).toFixed(1)}</strong><small>mm</small></div><div><span>Y</span><strong>{(status.map_y * heightMm).toFixed(1)}</strong><small>mm</small></div></div>
        <dl className="observatory-field-facts"><div><dt>Panel extent</dt><dd>{widthMm.toFixed(0)} × {heightMm.toFixed(0)} mm</dd></div><div><dt>Cell spacing</dt><dd>{containment.grid_cell_width_mm.toFixed(1)} × {containment.grid_cell_height_mm.toFixed(1)} mm</dd></div><div><dt>Peak cell mass</dt><dd>{(status.peak_probability * 100).toFixed(2)}%</dd></div><div><dt>Recorded paths</dt><dd>{history.length}</dd></div></dl>
        <div className="observatory-mass"><h3>Mass around the MAP</h3><p>Accumulated posterior within each radius</p>{radii.map(item => <div className="observatory-mass-row" key={item.radius_mm}><span>{item.radius_mm} <small>mm</small></span><div><i style={{ width: `${Math.min(100, Math.max(0, item.probability * 100))}%` }} /></div><b>{(item.probability * 100).toFixed(1)}%</b></div>)}</div>
        <p className="observatory-interpretation">The surface rises with relative probability. It represents uncertainty in location; its height does not estimate defect depth. Radius coverage is not field calibrated.</p>
      </aside>
    </div>
    <PosteriorProfiles session={session} cell={selectedCell} onSelect={setSelectedCell} />
    <footer className="observatory-footer"><span><i />SAME POSTERIOR IN EVERY VIEW</span><p>{view === '3d' ? 'Orbit the camera, or choose Inspect surface to select a cell directly in 3D. Arrow keys follow the selected interaction mode.' : 'Inspect individual cells and path geometry. Exclusion-zone editing requires an explicit drawing action.'}</p></footer>
  </section>;
}
