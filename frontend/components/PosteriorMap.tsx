'use client';

import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { HistoryItem, SessionState } from '@/types/argus';
import { containmentEllipse, posteriorColor } from '@/utils/posteriorDisplay';
import { gridCellAt, inspectGridCell, moveInspectionCell, panelMapGeometry, panelPointAt, physicalAxisTicks, restrictedRectangle, type GridCell } from '@/utils/heatmapGeometry';
import { summarizePosterior } from '@/utils/posteriorReview';
import { initialMapGesture, transitionMapGesture, type MapGestureEvent } from '@/utils/mapGestures';
import styles from './HeatmapCanvas.module.css';

interface Props { session: SessionState; history: HistoryItem[]; disabled?: boolean; active?: boolean; selectedCell?: GridCell; onSelectCell?: (cell: GridCell) => void; onNoGoChange?: (regions: SessionState['no_go_regions']) => void }

export function PosteriorMap({ session, history, onNoGoChange, disabled = false, active = true, selectedCell, onSelectCell }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [localCell, setLocalCell] = useState<GridCell>({ row: 0, column: 0 });
  const cell = selectedCell ?? localCell;
  const setCell = (next: GridCell) => { setLocalCell(next); onSelectCell?.(next); };
  const [keyboardReadout, setKeyboardReadout] = useState('');
  const [layers, setLayers] = useState({ history: true, hypotheses: true, radius: true, next: true });
  const descriptionId = useId();
  const geometry = useMemo(() => panelMapGeometry(session.panel.width_m, session.panel.height_m), [session.panel.width_m, session.panel.height_m]);
  const grid = session.posterior, rows = Array.isArray(grid) ? grid.length : 0;
  const columns = Array.isArray(grid) && Array.isArray(grid[0]) ? grid[0].length : 0;
  const valid = useMemo(() => {
    if (!Array.isArray(grid) || !grid.length || !Array.isArray(grid[0])) return false;
    const width = grid[0].length;
    if (!width || grid.length * width > 65536) return false;
    // Array.from visits sparse slots that Array.every/flat would skip.
    return Array.from(grid).every(row => Array.isArray(row) && row.length === width
      && Array.from(row).every(value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1))
      && summarizePosterior(grid) !== null;
  }, [grid]);
  const inspection = useMemo(() => valid ? inspectGridCell(grid, cell, session.panel.width_m, session.panel.height_m) : null, [valid, grid, cell, session.panel.width_m, session.panel.height_m]);
  const blocked = disabled || !active || session.safety.emergency_stop.latched || !onNoGoChange || !valid;
  const contextKey = JSON.stringify([session.id, disabled, active, session.safety.emergency_stop.latched,
    Boolean(onNoGoChange), valid, session.panel.width_m, session.panel.height_m, session.no_go_regions]);
  const [gesture, setGesture] = useState(() => initialMapGesture(contextKey));
  const gestureRef = useRef(gesture);
  // Guarded prop-derived reset runs before committing a changed lifecycle.
  // Overlay preferences and the selected cell remain independent of this state.
  if (gesture.contextKey !== contextKey) setGesture(initialMapGesture(contextKey));
  const drawing = gesture.contextKey === contextKey && gesture.editing && !blocked;
  const visibleDraft = drawing ? gesture.draft : null;
  useLayoutEffect(() => {
    const pointerId = gestureRef.current.draft?.pointerId;
    gestureRef.current = initialMapGesture(contextKey);
    const canvas = ref.current;
    if (pointerId !== undefined && canvas?.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
  }, [contextKey]);
  useEffect(() => {
    const canvas = ref.current, ctx = canvas?.getContext('2d'); if (!canvas || !ctx || !valid || !active) return;
    const { width, height, left, top, fieldWidth, fieldHeight, widthMm, heightMm } = geometry;
    const px = (x: number) => left + x * fieldWidth, py = (y: number) => top + y * fieldHeight;
    ctx.clearRect(0, 0, width, height); ctx.fillStyle = '#091522'; ctx.fillRect(left, top, fieldWidth, fieldHeight);
    const maximum = grid.reduce((peak, row) => row.reduce((value, cell) => Math.max(value, cell), peak), 0);
    grid.forEach((row, y) => row.forEach((value, x) => { ctx.fillStyle = posteriorColor(value, maximum); ctx.fillRect(px(x / columns), py(y / rows), fieldWidth / columns + .3, fieldHeight / rows + .3); }));
    ctx.save(); ctx.beginPath(); ctx.rect(left, top, fieldWidth, fieldHeight); ctx.clip();
    ctx.lineWidth = .65; ctx.strokeStyle = '#aadff91a';
    for (let i = 1; i < 10; i++) { ctx.beginPath(); ctx.moveTo(px(i / 10), top); ctx.lineTo(px(i / 10), py(1)); ctx.moveTo(left, py(i / 10)); ctx.lineTo(px(1), py(i / 10)); ctx.stroke(); }
    if (layers.history) history.forEach(item => { const e = item.parameters; ctx.strokeStyle = '#b7d2e16c'; ctx.lineWidth = 1; ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.moveTo(px(e.source_x), py(e.source_y)); ctx.lineTo(px(e.receiver_x), py(e.receiver_y)); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#b9d4e1'; ctx.font = '10px monospace'; ctx.fillText(String(item.experiment_index), px(e.source_x) + 6, py(e.source_y) - 6); });
    const drawRegion = (region: SessionState['no_go_regions'][number], provisional = false) => { const x = px(region.x_min), y = py(region.y_min), w = (region.x_max - region.x_min) * fieldWidth, h = (region.y_max - region.y_min) * fieldHeight; ctx.fillStyle = '#efaf6833'; ctx.fillRect(x, y, w, h); ctx.strokeStyle = '#efbd80'; ctx.lineWidth = 1.5; ctx.setLineDash(provisional ? [4, 3] : []); ctx.strokeRect(x, y, w, h); ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y + h); ctx.moveTo(x + w, y); ctx.lineTo(x, y + h); ctx.strokeStyle = '#e6b47a55'; ctx.stroke(); ctx.fillStyle = '#f9d5a6'; ctx.font = '10px monospace'; ctx.fillText(provisional ? 'AREA PREVIEW' : region.label.toUpperCase(), x + 5, y + 14); };
    session.no_go_regions.forEach(region => drawRegion(region));
    if (visibleDraft) { const preview = restrictedRectangle(visibleDraft.start, visibleDraft.end, session.no_go_regions.length); if (preview) drawRegion(preview, true); }
    if (layers.radius) { const containment = session.status.posterior_containment, ellipse = containmentEllipse(containment.radius90_mm, session.panel.width_m, session.panel.height_m, fieldWidth, fieldHeight); if (ellipse) { ctx.strokeStyle = '#f0c498'; ctx.setLineDash([6, 5]); ctx.lineWidth = 1.6; ctx.beginPath(); ctx.ellipse(px(containment.reference_x), py(containment.reference_y), ellipse.x, ellipse.y, 0, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); } }
    if (layers.hypotheses) session.status.integrity_assessment.candidate_regions.slice(0, 3).forEach(candidate => { ctx.strokeStyle = '#f0c498'; ctx.lineWidth = 1.2; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.arc(px(candidate.x), py(candidate.y), 15, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#ffdaa3'; ctx.font = '10px monospace'; ctx.fillText(`H${candidate.rank}`, px(candidate.x) + 18, py(candidate.y) - 8); });
    if (session.revealed && session.ground_truth) { const truth = session.ground_truth; ctx.strokeStyle = '#fb947b'; ctx.lineWidth = 2; ctx.setLineDash([7, 4]); ctx.beginPath(); ctx.ellipse(px(truth.center_x), py(truth.center_y), truth.radius_x * fieldWidth, truth.radius_y * fieldHeight, 0, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); ctx.fillStyle = '#fb947b'; ctx.font = '11px monospace'; ctx.fillText('REVEALED TRUTH', px(truth.center_x) + 12, py(truth.center_y) - 16); }
    if (inspection) { ctx.strokeStyle = '#a8efd5'; ctx.lineWidth = 1.3; ctx.strokeRect(px(cell.column / columns), py(cell.row / rows), fieldWidth / columns, fieldHeight / rows); ctx.setLineDash([2, 4]); ctx.strokeStyle = '#c4b6f099'; ctx.beginPath(); ctx.moveTo(px(inspection.x), top); ctx.lineTo(px(inspection.x), py(1)); ctx.stroke(); ctx.strokeStyle = '#8ad8f199'; ctx.beginPath(); ctx.moveTo(left, py(inspection.y)); ctx.lineTo(px(1), py(inspection.y)); ctx.stroke(); ctx.setLineDash([]); }
    ctx.restore();
    const label = (text: string, x: number, y: number, color: string) => { ctx.font = 'bold 10px monospace'; const labelWidth = ctx.measureText(text).width; const lx = Math.max(left + 4, Math.min(px(1) - labelWidth - 4, x)), ly = Math.max(top + 14, Math.min(py(1) - 6, y)); ctx.fillStyle = '#091522df'; ctx.fillRect(lx - 3, ly - 11, labelWidth + 6, 15); ctx.fillStyle = color; ctx.fillText(text, lx, ly); };
    if (layers.next) { const e = session.recommendation.experiment; ctx.strokeStyle = '#dbf2fd'; ctx.lineWidth = 1.4; ctx.setLineDash([5, 5]); ctx.beginPath(); ctx.moveTo(px(e.source_x), py(e.source_y)); ctx.lineTo(px(e.receiver_x), py(e.receiver_y)); ctx.stroke(); ctx.setLineDash([]); for (const [x, y, text, color] of [[e.source_x, e.source_y, 'TX', '#85ddff'], [e.receiver_x, e.receiver_y, 'RX', '#ffc98f']] as const) { ctx.beginPath(); ctx.arc(px(x), py(y), 9, 0, Math.PI * 2); ctx.fillStyle = '#0a1b2ed9'; ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke(); ctx.beginPath(); ctx.arc(px(x), py(y), 3, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); label(text, px(x) + 13, py(y) - 10, color); } }
    const mx = px(session.status.map_x), my = py(session.status.map_y); ctx.fillStyle = '#f5faff'; ctx.beginPath(); ctx.arc(mx, my, 3.5, 0, Math.PI * 2); ctx.fill(); label('MAP', mx + 9, my + 16, '#f5faff');
    ctx.strokeStyle = '#88b4d077'; ctx.lineWidth = 1; ctx.strokeRect(left, top, fieldWidth, fieldHeight); ctx.fillStyle = '#9fbcd2'; ctx.font = '11px monospace'; ctx.textAlign = 'center';
    for (const value of physicalAxisTicks(fieldWidth)) { const x = px(value); ctx.beginPath(); ctx.moveTo(x, py(1) + 2); ctx.lineTo(x, py(1) + 7); ctx.stroke(); ctx.fillText((value * widthMm).toFixed(0), x, py(1) + 22); }
    ctx.fillText('X / mm', left + fieldWidth / 2, height - 8); ctx.textAlign = 'right';
    for (const value of physicalAxisTicks(fieldHeight)) { const y = py(value); ctx.beginPath(); ctx.moveTo(left - 2, y); ctx.lineTo(left - 7, y); ctx.stroke(); ctx.fillText((value * heightMm).toFixed(0), left - 11, y + 4); }
    ctx.save(); ctx.translate(11, top + fieldHeight / 2); ctx.rotate(-Math.PI / 2); ctx.textAlign = 'center'; ctx.fillText('Y / mm', 0, 0); ctx.restore(); ctx.textAlign = 'left';
  }, [session, history, grid, geometry, rows, columns, valid, layers, inspection, cell, visibleDraft, active]);
  const pointAt = (event: React.PointerEvent<HTMLCanvasElement>, clamp = false) => { const box = event.currentTarget.getBoundingClientRect(); return panelPointAt((event.clientX - box.left) * geometry.width / box.width, (event.clientY - box.top) * geometry.height / box.height, geometry, clamp); };
  const updateGesture = (event: MapGestureEvent) => {
    const result = transitionMapGesture(gestureRef.current, event);
    if (result.state !== gestureRef.current) { gestureRef.current = result.state; setGesture(result.state); }
    return result;
  };
  const releasePointer = (pointerId: number | undefined) => {
    const canvas = ref.current;
    if (pointerId !== undefined && canvas?.hasPointerCapture(pointerId)) canvas.releasePointerCapture(pointerId);
  };
  const cancelDraft = (leaveEditing = false) => {
    const pointerId = gestureRef.current.draft?.pointerId;
    updateGesture({ type: 'cancel', contextKey, leaveEditing });
    releasePointer(pointerId);
  };
  if (!valid) return <p className={styles.error} role="alert">The posterior grid is invalid. Refresh the session to inspect its latest saved field.</p>;
  return <div className={styles.root}>
    <div className={styles.controls}><fieldset><legend>Overlays</legend>{([['history', 'Recorded paths'], ['hypotheses', 'Hypotheses'], ['radius', 'R90'], ['next', 'Next probe']] as const).map(([key, label]) => <label key={key}><input type="checkbox" checked={layers[key]} onChange={event => setLayers(current => ({ ...current, [key]: event.target.checked }))} />{label}</label>)}</fieldset></div>
    <div className={styles.frame}><canvas ref={ref} width={geometry.width} height={geometry.height} className={`${styles.canvas} ${drawing ? styles.editing : ''}`} tabIndex={0} role="img" aria-label="Inspect posterior cells on the physical panel" aria-describedby={descriptionId} aria-keyshortcuts="ArrowLeft ArrowRight ArrowUp ArrowDown Home End Escape"
      onPointerDown={event => {
        if (!active || event.button !== 0 || gestureRef.current.draft) return;
        const point = pointAt(event); if (!point) return;
        event.currentTarget.focus(); const next = gridCellAt(point, rows, columns); if (next) setCell(next);
        if (!drawing) return;
        const result = updateGesture({ type: 'down', contextKey, pointerId: event.pointerId, point, blocked });
        if (result.state.draft?.pointerId === event.pointerId) {
          try { event.currentTarget.setPointerCapture(event.pointerId); }
          catch { cancelDraft(true); }
        }
      }}
      onPointerMove={event => {
        if (!active) return;
        const current = gestureRef.current.draft;
        if (current && current.pointerId !== event.pointerId) return;
        const point = pointAt(event, drawing && Boolean(current)); if (!point) return;
        const next = gridCellAt(point, rows, columns); if (next && (next.row !== cell.row || next.column !== cell.column)) setCell(next);
        if (drawing && current) updateGesture({ type: 'move', contextKey, pointerId: event.pointerId, point, blocked });
      }}
      onPointerUp={event => {
        if (gestureRef.current.draft?.pointerId !== event.pointerId) return;
        const result = updateGesture({ type: 'up', contextKey, pointerId: event.pointerId, point: pointAt(event, true), blocked: blocked || !drawing });
        releasePointer(event.pointerId);
        if (!result.completed || !onNoGoChange || blocked || !drawing) return;
        const region = restrictedRectangle(result.completed.start, result.completed.end, session.no_go_regions.length);
        if (region) onNoGoChange([...session.no_go_regions, region]);
      }}
      onPointerCancel={event => {
        if (gestureRef.current.draft?.pointerId !== event.pointerId) return;
        updateGesture({ type: 'cancel', contextKey, pointerId: event.pointerId, leaveEditing: true });
        releasePointer(event.pointerId);
      }}
      onLostPointerCapture={event => {
        if (event.currentTarget.hasPointerCapture(event.pointerId) || gestureRef.current.draft?.pointerId !== event.pointerId) return;
        updateGesture({ type: 'cancel', contextKey, pointerId: event.pointerId, leaveEditing: true });
      }}
      onKeyDown={event => {
        if (!active || event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'Escape') {
          if (gestureRef.current.editing || gestureRef.current.draft) { event.preventDefault(); cancelDraft(true); }
          return;
        }
        const next = moveInspectionCell(cell, event.key, rows, columns);
        if (next) { event.preventDefault(); setCell(next); const value = inspectGridCell(grid, next, session.panel.width_m, session.panel.height_m); if (value) setKeyboardReadout(`Cell ${next.column + 1}, ${next.row + 1}. X ${value.xMm.toFixed(1)}, Y ${value.yMm.toFixed(1)} millimeters. ${(value.probability * 100).toFixed(4)} percent probability mass.`); }
      }} /></div>
    <p className={styles.srOnly} role="status">{keyboardReadout}</p>
    <div className={styles.inspection} aria-live="off"><span>CELL {cell.column + 1}, {cell.row + 1}</span><strong>X {inspection?.xMm.toFixed(1) ?? '—'} <small>mm</small></strong><strong>Y {inspection?.yMm.toFixed(1) ?? '—'} <small>mm</small></strong><strong className={styles.probability}>{inspection ? (inspection.probability * 100).toFixed(4) : '—'}% <small>mass</small></strong></div>
    <div className={styles.legend}><span><i className={styles.source} />Next transmitter</span><span><i className={styles.receiver} />Next receiver</span><span><i className={styles.hypothesis} />Hypothesis</span><span><i className={styles.restriction} />Exclusion zone</span><span><small>LOW</small><span className={styles.scale} /><small>PEAK</small></span></div>
    {onNoGoChange && <div className={styles.editBar}><button type="button" aria-pressed={!drawing} onClick={() => cancelDraft(true)}>Inspect cells</button><button type="button" className={styles.editSelected} aria-pressed={drawing} disabled={blocked} onClick={() => { cancelDraft(); updateGesture({ type: 'mode', contextKey, editing: !drawing, blocked }); }}>Draw exclusion zone</button><button type="button" disabled={blocked || !session.no_go_regions.length} onClick={() => { if (!blocked) { cancelDraft(true); onNoGoChange([]); } }}>Clear zones ({session.no_go_regions.length})</button><p>{drawing ? 'Drag a rectangle; Escape cancels.' : blocked ? 'Region editing is currently unavailable.' : 'Drawing changes the planner’s allowed region.'}</p></div>}
    <p className={styles.instructions} id={descriptionId}>Hover or tap to inspect a cell. Focus the map and use arrow keys to move, Home or End for corner cells. <b>Origin: upper-left.</b> Brightness is relative to this field’s peak; the readout is probability mass at the cell centre. R90 = {session.status.posterior_containment.radius90_mm.toFixed(1)} mm; coverage is not field calibrated.</p>
  </div>;
}
