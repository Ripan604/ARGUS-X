'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { HistoryItem, SessionState } from '@/types/argus';
import { inspectGridCell, moveInspectionCell, type GridCell } from '@/utils/heatmapGeometry';
import { normalizedRelief, panelProjection, physicalCircle, pickPosteriorCell, projectedReliefFaces, reliefNormal, wrapAzimuth, type ProjectedPoint } from './spatialGeometry';
import { useSceneMotion } from './SpatialWorld';
import './spatial-scene.css';

const DEFAULT_CAMERA = { azimuth: -27, elevation: 38, zoom: 1 };
const EMPTY_HISTORY: HistoryItem[] = [];

export function SpatialScene({ session, history = EMPTY_HISTORY, presentation = 'embedded', active = true, selectedCell, onSelectCell }: {
  session?: SessionState; history?: HistoryItem[]; presentation?: 'embedded' | 'hero'; active?: boolean; selectedCell?: GridCell; onSelectCell?: (cell: GridCell) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null), stageRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: number; x: number; y: number; azimuth: number; elevation: number } | null>(null);
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const [paths, setPaths] = useState(true), [ring, setRing] = useState(true), [grid, setGrid] = useState(true);
  const [waves, setWaves] = useState(!session);
  const [interaction, setInteraction] = useState<'orbit' | 'inspect'>('orbit');
  const [inspectionAnnouncement, setInspectionAnnouncement] = useState('');
  const inspecting = interaction === 'inspect' && Boolean(session && onSelectCell);
  const inspection = session && selectedCell ? inspectGridCell(session.posterior, selectedCell, session.panel.width_m, session.panel.height_m) : null;
  const { paused } = useSceneMotion();
  const hintId = useId();
  useEffect(() => {
    const current = drag.current;
    drag.current = null;
    const canvas = canvasRef.current?.parentElement;
    if (current && canvas?.hasPointerCapture(current.id)) canvas.releasePointerCapture(current.id);
  }, [active, interaction]);
  useEffect(() => {
    const canvas = canvasRef.current, stage = stageRef.current, ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !stage) return;
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    const widthMm = (session?.panel.width_m ?? .6) * 1000, heightMm = (session?.panel.height_m ?? .4) * 1000;
    const field = normalizedRelief(session?.posterior), rows = field?.length ?? 17, columns = field?.[0]?.length ?? 25;
    const experiment = session?.recommendation.experiment;
    const source = { x: experiment?.source_x ?? .16, y: experiment?.source_y ?? .72 };
    const receiver = { x: experiment?.receiver_x ?? .84, y: experiment?.receiver_y ?? .22 };
    let width = 1, height = 1, frame = 0, last = 0, time = 0, visible = true;
    const draw = () => {
      if (!active || width < 2 || height < 2) return;
      ctx.clearRect(0, 0, width, height);
      const { project, aspectX, aspectY } = panelProjection({ widthMm, heightMm, viewportWidth: Math.max(width, 1), viewportHeight: Math.max(height, 1), azimuthDeg: camera.azimuth, elevationDeg: camera.elevation, zoom: camera.zoom });
      const polygon = (points: ProjectedPoint[], fill: string | CanvasGradient, stroke?: string) => {
        ctx.beginPath(); points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.closePath();
        ctx.fillStyle = fill; ctx.fill(); if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = .65; ctx.stroke(); }
      };
      const line = (points: ProjectedPoint[], color: string, thickness = 1) => {
        ctx.beginPath(); points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.strokeStyle = color; ctx.lineWidth = thickness; ctx.stroke();
      };
      const label = (text: string, p: ProjectedPoint, color: string, dx = 10, dy = -9) => {
        ctx.font = '10px ui-monospace, monospace';
        const textWidth = ctx.measureText(text).width;
        const x = Math.max(8, Math.min(width - textWidth - 8, p.x + dx)), y = Math.max(15, Math.min(height - 28, p.y + dy));
        ctx.fillStyle = '#091625dc'; ctx.fillRect(x - 4, y - 11, textWidth + 8, 17); ctx.fillStyle = color; ctx.fillText(text, x, y);
      };
      // A physical-aspect floor and schematic thickness anchor the probability relief.
      const corners = [[0, 0], [1, 0], [1, 1], [0, 1]];
      ctx.save(); ctx.shadowColor = '#02080fc0'; ctx.shadowBlur = 24; ctx.shadowOffsetY = 10;
      polygon(corners.map(([x, y]) => project(x, y, -.05)), '#030b1580');
      ctx.restore();
      const sides = corners.map((a, i) => {
        const b = corners[(i + 1) % 4], points = [project(...a as [number, number]), project(...b as [number, number]), project(b[0], b[1], -.032), project(a[0], a[1], -.032)];
        return { points, depth: points.reduce((sum, p) => sum + p.depth, 0) / 4 };
      }).sort((a, b) => a.depth - b.depth);
      for (const side of sides) polygon(side.points, '#12283d', '#6a9bb34d');
      const lightOrigin = project(0, 0), lightEnd = project(1, 1);
      const panelFinish = ctx.createLinearGradient(lightOrigin.x, lightOrigin.y, lightEnd.x, lightEnd.y);
      panelFinish.addColorStop(0, '#173344'); panelFinish.addColorStop(1, '#0b1b28');
      polygon(corners.map(([x, y]) => project(x, y)), panelFinish, '#9ccddd66');
      if (field) field.forEach((row, r) => row.forEach((value, c) => {
        polygon([[c / columns, r / rows], [(c + 1) / columns, r / rows], [(c + 1) / columns, (r + 1) / rows], [c / columns, (r + 1) / rows]].map(([x, y]) => project(x, y, .001)), `rgba(116,211,236,${.025 + Math.sqrt(value) * .24})`);
      }));
      if (grid) for (let i = 0; i <= 10; i++) {
        line([project(i / 10, 0, .002), project(i / 10, 1, .002)], '#85bddb22');
        line([project(0, i / 10, .002), project(1, i / 10, .002)], '#85bddb22');
      }
      if (field) {
        const cellHeight = (r: number, c: number) => field[Math.min(rows - 1, r)][Math.min(columns - 1, c)] * .23;
        for (const cell of projectedReliefFaces(field, project)) {
          const r = cell.row, c = cell.column;
          const normal = reliefNormal((cellHeight(r, c + 1) - cellHeight(r, c)) * columns, (cellHeight(r + 1, c) - cellHeight(r, c)) * rows, aspectX, aspectY);
          const light = .65 + .35 * Math.max(0, normal.x * -.4 + normal.y * -.5 + normal.z * .76);
          const warm = Math.pow(cell.value, 2.3);
          const red = (28 + cell.value * 65 + warm * 150) * light, green = (76 + cell.value * 122) * light, blue = (112 + cell.value * 96 - warm * 68) * light;
          polygon(cell.points, `rgb(${red},${green},${blue})`, grid ? `rgba(162,223,246,${.10 + cell.value * .23})` : undefined);
        }
      }
      // Linked row/column traces use the exact same samples as the profile charts.
      if (field && selectedCell && selectedCell.row >= 0 && selectedCell.row < rows && selectedCell.column >= 0 && selectedCell.column < columns) {
        const { row, column } = selectedCell, x = (column + .5) / columns, y = (row + .5) / rows;
        line(field[row].map((value, c) => project((c + .5) / columns, y, value * .23 + .003)), '#8ad8f1', 1.8);
        line(field.map((values, r) => project(x, (r + .5) / rows, values[column] * .23 + .004)), '#c4b6f0', 1.8);
        const point = project(x, y, field[row][column] * .23 + .009);
        ctx.strokeStyle = '#a8efd5'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(point.x, point.y, 7, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = '#a8efd5'; ctx.beginPath(); ctx.arc(point.x, point.y, 2, 0, Math.PI * 2); ctx.fill();
      }
      // Floor overlays stay legible as projected annotations; they are not depth measurements.
      session?.no_go_regions.forEach(region => {
        const points = [[region.x_min, region.y_min], [region.x_max, region.y_min], [region.x_max, region.y_max], [region.x_min, region.y_max]].map(([x, y]) => project(x, y, .006));
        polygon(points, '#ed99652a', '#ecac7ca0');
        line([points[0], points[2]], '#ecac7c66'); line([points[1], points[3]], '#ecac7c66');
      });
      const clippedCircle = (cx: number, cy: number, radius: number, color: string) => {
        let segment: ProjectedPoint[] = [];
        for (const p of physicalCircle(cx, cy, radius, widthMm, heightMm)) {
          if (p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1) segment.push(project(p.x, p.y, .008));
          else { if (segment.length > 1) line(segment, color, 1.4); segment = []; }
        }
        if (segment.length > 1) line(segment, color, 1.4);
      };
      if (paths) {
        ctx.setLineDash([2, 5]);
        history.forEach(item => { const e = item.parameters; line([project(e.source_x, e.source_y, .009), project(e.receiver_x, e.receiver_y, .009)], '#8cbacf50'); });
        ctx.setLineDash([5, 5]); line([project(source.x, source.y, .014), project(receiver.x, receiver.y, .014)], '#d9eaf6aa', 1.5); ctx.setLineDash([]);
      }
      if (session && ring) {
        const containment = session.status.posterior_containment;
        ctx.setLineDash([5, 5]); clippedCircle(containment.reference_x, containment.reference_y, containment.radius90_mm, '#f3c18dae'); ctx.setLineDash([]);
      }
      if (waves) for (let i = 0; i < 3; i++) {
        const progress = (time * .12 + i / 3) % 1;
        clippedCircle(source.x, source.y, progress * Math.max(widthMm, heightMm) * .8, `rgba(143,215,247,${(1 - progress) * .28})`);
      }
      for (const [point, text, color] of [[source, 'TX', '#85ddff'], [receiver, 'RX', '#ffc98f']] as const) {
        const base = project(point.x, point.y, .008), top = project(point.x, point.y, .075);
        line([base, top], `${color}aa`, 1.6); ctx.strokeStyle = color; ctx.beginPath(); ctx.arc(base.x, base.y, 7, 0, Math.PI * 2); ctx.stroke();
        ctx.shadowColor = color; ctx.shadowBlur = 14; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(top.x, top.y, 4, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
        label(session ? `NEXT ${text}` : text, top, color, 10, text === 'TX' ? -8 : 15);
      }
      if (session && field) {
        const x = session.status.map_x, y = session.status.map_y;
        const r = Math.min(rows - 1, Math.max(0, Math.floor(y * rows))), c = Math.min(columns - 1, Math.max(0, Math.floor(x * columns)));
        const base = project(x, y, .01), top = project(x, y, field[r][c] * .23 + .028);
        ctx.setLineDash([2, 3]); line([base, top], '#e5f4ff9c'); ctx.setLineDash([]);
        ctx.beginPath(); ctx.arc(top.x, top.y, 4, 0, Math.PI * 2); ctx.fillStyle = '#f3faff'; ctx.fill();
        label('MAP', top, '#f3faff');
      }
      const x1 = project(0, 1.11, -.032), x2 = project(1, 1.11, -.032), y1 = project(-.09, 0, -.032), y2 = project(-.09, 1, -.032);
      line([x1, x2], '#89aac461'); line([y1, y2], '#89aac461');
      const xGraduated = width >= 460 && Math.hypot(x2.x - x1.x, x2.y - x1.y) >= 220;
      const yGraduated = width >= 460 && Math.hypot(y2.x - y1.x, y2.y - y1.y) >= 220;
      const tickLabel = (text: string, point: ProjectedPoint, dx: number, dy: number) => {
        ctx.font = '10px ui-monospace, monospace'; ctx.fillStyle = '#96b0c1';
        const x = point.x + dx, y = point.y + dy;
        if (x < 8 || x + ctx.measureText(text).width > width - 8 || y < 14 || y > height - 28) return;
        ctx.fillText(text, x, y);
      };
      for (const fraction of [.25, .5, .75]) {
        if (xGraduated) {
          const point = project(fraction, 1.11, -.032);
          line([point, project(fraction, 1.125, -.032)], '#89aac480');
          tickLabel((fraction * widthMm).toFixed(0), point, -8, 15);
        }
        if (yGraduated) {
          const point = project(-.09, fraction, -.032);
          line([point, project(-.105, fraction, -.032)], '#89aac480');
          tickLabel((fraction * heightMm).toFixed(0), point, -31, 3);
        }
      }
      label(`X · ${widthMm.toFixed(0)} mm`, { ...x1, x: (x1.x + x2.x) / 2, y: (x1.y + x2.y) / 2 }, '#b0c8d5', -25, xGraduated ? 34 : 18);
      label(`Y · ${heightMm.toFixed(0)} mm`, yGraduated ? y1 : { ...y1, x: (y1.x + y2.x) / 2, y: (y1.y + y2.y) / 2 }, '#b0c8d5', -50, yGraduated ? -23 : -10);
      label('0,0', project(0, 0), '#6e93ad', -20, -15);
    };
    const tick = (now: number) => { if (now - last >= 33) { time += .033; draw(); last = now; } frame = requestAnimationFrame(tick); };
    const sync = () => { cancelAnimationFrame(frame); draw(); if (active && waves && visible && !paused && !preference.matches && !document.hidden) frame = requestAnimationFrame(tick); };
    const resize = new ResizeObserver(([entry]) => { width = entry.contentRect.width; height = entry.contentRect.height; const ratio = Math.min(devicePixelRatio || 1, 2); canvas.width = Math.max(1, Math.round(width * ratio)); canvas.height = Math.max(1, Math.round(height * ratio)); ctx.setTransform(ratio, 0, 0, ratio, 0, 0); draw(); });
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    resize.observe(canvas); observer.observe(stage); sync(); preference.addEventListener('change', sync); document.addEventListener('visibilitychange', sync);
    return () => { cancelAnimationFrame(frame); resize.disconnect(); observer.disconnect(); preference.removeEventListener('change', sync); document.removeEventListener('visibilitychange', sync); };
  }, [session, history, camera, grid, paths, ring, waves, paused, active, selectedCell]);

  const endDrag = () => { drag.current = null; };
  const select = (cell: GridCell) => {
    if (!session || !onSelectCell) return;
    const value = inspectGridCell(session.posterior, cell, session.panel.width_m, session.panel.height_m);
    if (!value) return;
    onSelectCell(cell);
    setInspectionAnnouncement(`Cell ${cell.column + 1}, ${cell.row + 1}. X ${value.xMm.toFixed(1)}, Y ${value.yMm.toFixed(1)} millimeters. ${(value.probability * 100).toFixed(4)} percent probability mass.`);
  };
  return <section className={`narrative-twin spatial-scene spatial-scene--${presentation} ${session ? 'session-twin' : 'landing-twin'}`} ref={stageRef} aria-label={session ? 'Live posterior in three dimensions' : 'Illustrative acoustic experiment'}>
    <div className="scene-heading"><div><i /><div><strong>{session ? 'Probability surface' : 'The experiment, in space'}</strong><small>{session ? 'RELATIVE POSTERIOR / 3D PROJECTION' : 'ILLUSTRATIVE SENSING GEOMETRY'}</small></div></div><span>INTERACTIVE 3D</span></div>
    {session && onSelectCell && <div className="scene-interaction" role="group" aria-label="3D interaction mode"><button type="button" aria-pressed={!inspecting} onClick={() => setInteraction('orbit')}>Orbit camera</button><button type="button" aria-pressed={inspecting} onClick={() => setInteraction('inspect')}>Inspect surface</button><p>{inspecting ? 'Tap the surface to link a cell to both slices.' : 'Drag the scene to change the camera angle.'}</p></div>}
    <div className={`scene-viewport spatial-canvas-wrap ${inspecting ? 'scene-viewport--inspect' : ''}`} role="group" aria-label={inspecting ? 'Inspect cells on the 3D probability surface' : 'Orbit the 3D panel'} aria-describedby={hintId} tabIndex={0}
      onPointerDown={event => {
        if (!active || event.button !== 0 || drag.current || !event.isPrimary) return;
        event.currentTarget.focus();
        if (inspecting && session) {
          const box = event.currentTarget.getBoundingClientRect();
          const cell = pickPosteriorCell(session.posterior, { widthMm: session.panel.width_m * 1000, heightMm: session.panel.height_m * 1000, viewportWidth: box.width, viewportHeight: box.height, azimuthDeg: camera.azimuth, elevationDeg: camera.elevation, zoom: camera.zoom }, event.clientX - box.left, event.clientY - box.top);
          if (cell) select(cell);
          return;
        }
        try { event.currentTarget.setPointerCapture(event.pointerId); }
        catch { return; }
        drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, azimuth: camera.azimuth, elevation: camera.elevation };
      }}
      onPointerMove={event => { const start = drag.current; if (!start || start.id !== event.pointerId) return; setCamera(current => ({ ...current, azimuth: wrapAzimuth(start.azimuth + (event.clientX - start.x) * .45), elevation: Math.min(90, Math.max(0, start.elevation - (event.clientY - start.y) * .35)) })); }}
      onPointerUp={event => { if (drag.current?.id !== event.pointerId) return; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); endDrag(); }} onPointerCancel={event => { if (drag.current?.id === event.pointerId) endDrag(); }} onLostPointerCapture={event => { if (drag.current?.id === event.pointerId) endDrag(); }}
      onKeyDown={event => {
        if (!active || event.ctrlKey || event.metaKey || event.altKey) return;
        if (inspecting && session) {
          if (event.key === 'Escape') { event.preventDefault(); setInteraction('orbit'); return; }
          const cell = selectedCell ?? { row: 0, column: 0 };
          const next = moveInspectionCell(cell, event.key, session.posterior.length, session.posterior[0]?.length ?? 0);
          if (next) { event.preventDefault(); select(next); return; }
        }
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '=', '-', 'Home'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'Home') setCamera(DEFAULT_CAMERA);
        else setCamera(current => ({ azimuth: wrapAzimuth(current.azimuth + (event.key === 'ArrowLeft' ? -5 : event.key === 'ArrowRight' ? 5 : 0)), elevation: Math.min(90, Math.max(0, current.elevation + (event.key === 'ArrowUp' ? 5 : event.key === 'ArrowDown' ? -5 : 0))), zoom: Math.min(1.6, Math.max(.6, current.zoom + (event.key === '+' || event.key === '=' ? .1 : event.key === '-' ? -.1 : 0))) }));
      }}>
      <canvas ref={canvasRef} className="scene-canvas" role="img" aria-label={session ? `Posterior relief: MAP at X ${(session.status.map_x * session.panel.width_m * 1000).toFixed(1)}, Y ${(session.status.map_y * session.panel.height_m * 1000).toFixed(1)} millimeters. Height represents probability relative to the current peak, not physical depth.` : 'An illustrative 600 by 400 millimeter flat panel with a transmitter and receiver; no defect is inferred.'} />
      <div className="scene-camera-readout"><span>AZ <b>{camera.azimuth.toFixed(0)}°</b> / EL <b>{camera.elevation.toFixed(0)}°</b></span><span>{camera.zoom.toFixed(1)}× VIEW</span></div>
      {session && <div className="scene-height-scale"><i /><div><b>1.0</b><span>p / pₘₐₓ</span><b>0</b></div></div>}
      <div className="scene-caption"><span>{inspecting ? 'TAP TO INSPECT' : 'DRAG TO ORBIT'}</span><span>{session ? 'HEIGHT = RELATIVE PROBABILITY' : 'NO DEFECT ESTIMATE BEFORE EVIDENCE'}</span></div>
      <p className="scene-keyboard-hint" id={hintId}>{inspecting ? 'Tap a visible surface cell, or use arrow keys to move through the grid. Home and End select corner cells. Escape returns to camera orbit. Plus and minus zoom.' : 'Arrow keys rotate the camera. Plus and minus zoom. Home restores the isometric view.'}</p>
    </div>
    {session && onSelectCell && <div className="scene-inspection-readout"><span>LINKED CELL {inspection ? `${inspection.column + 1}, ${inspection.row + 1}` : '—'}</span><strong>X {inspection?.xMm.toFixed(1) ?? '—'} <small>mm</small></strong><strong>Y {inspection?.yMm.toFixed(1) ?? '—'} <small>mm</small></strong><strong>{inspection ? (inspection.probability * 100).toFixed(4) : '—'}% <small>mass</small></strong></div>}
    <p className="scene-keyboard-hint" role="status">{inspectionAnnouncement}</p>
    <div className="scene-console"><div className="scene-presets" role="group" aria-label="Camera presets"><button aria-pressed={camera.azimuth === -27 && camera.elevation === 38} onClick={() => setCamera(current => ({ ...current, azimuth: -27, elevation: 38 }))}>Isometric</button><button aria-pressed={camera.azimuth === 0 && camera.elevation === 90} onClick={() => setCamera(current => ({ ...current, azimuth: 0, elevation: 90 }))}>Top</button><button aria-pressed={camera.azimuth === 0 && camera.elevation === 0} onClick={() => setCamera(current => ({ ...current, azimuth: 0, elevation: 0 }))}>Front</button><button className="scene-reset" onClick={() => setCamera(DEFAULT_CAMERA)}>Reset view</button></div>
      <div className="scene-toggles"><label><input type="checkbox" checked={paths} onChange={e => setPaths(e.target.checked)} />Paths</label>{session && <label><input type="checkbox" checked={ring} onChange={e => setRing(e.target.checked)} />R90</label>}<label><input type="checkbox" checked={grid} onChange={e => setGrid(e.target.checked)} />Grid</label><label><input type="checkbox" checked={waves} onChange={e => setWaves(e.target.checked)} />Illustrative rings</label></div>
      <div className="scene-sliders"><label>AZIMUTH<output>{camera.azimuth.toFixed(0)}°</output><input aria-label="3D camera azimuth" type="range" min="-180" max="180" value={camera.azimuth} onChange={e => setCamera(current => ({ ...current, azimuth: Number(e.target.value) }))} /></label><label>ELEVATION<output>{camera.elevation.toFixed(0)}°</output><input aria-label="3D camera elevation" type="range" min="0" max="90" value={camera.elevation} onChange={e => setCamera(current => ({ ...current, elevation: Number(e.target.value) }))} /></label><label>ZOOM<output>{camera.zoom.toFixed(1)}×</output><input aria-label="3D camera zoom" type="range" min=".6" max="1.6" step=".05" value={camera.zoom} onChange={e => setCamera(current => ({ ...current, zoom: Number(e.target.value) }))} /></label></div>
    </div>
    <div className="scene-legend"><span><i className="tx" />{session ? 'Next transmitter' : 'Transmitter'}</span><span><i className="rx" />{session ? 'Next receiver' : 'Receiver'}</span>{session && <><span><i className="map" />MAP estimate</span><span><i className="history" />Recorded paths</span><span><i className="ring" />R90 boundary</span></>}{selectedCell && <><span><i className="x-slice" />X slice</span><span><i className="y-slice" />Y slice</span></>}</div>
    <p className="scene-science-note">{session ? 'Surface height shows relative cell probability. The dashed R90 boundary uses posterior mass and physical dimensions; its coverage is not field calibrated. ' : 'The panel illustrates the sensing concept. '}<strong>Animated excitation rings are illustrative, not measured waves.</strong>{session && ' Panel thickness is schematic.'}</p>
  </section>;
}
