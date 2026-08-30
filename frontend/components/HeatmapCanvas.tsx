'use client';

import { useEffect, useRef, useState } from 'react';
import type { HistoryItem, SessionState } from '@/types/argus';

interface Props { session: SessionState; history: HistoryItem[]; onNoGoChange?: (regions: SessionState['no_go_regions']) => void; }

function probabilityColor(value: number, max: number): string {
  const t = Math.min(1, Math.sqrt(value / Math.max(max, 1e-12)));
  const r = Math.round(13 + 170 * Math.max(0, t - 0.72) / 0.28);
  const g = Math.round(34 + 211 * t);
  const b = Math.round(29 + 61 * (1 - t));
  return `rgb(${r},${g},${b})`;
}

export function HeatmapCanvas({ session, history, onNoGoChange }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [editing, setEditing] = useState(false), [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  useEffect(() => {
    const canvas = ref.current; if (!canvas) return;
    const context = canvas.getContext('2d'); if (!context) return;
    const width = canvas.width, height = canvas.height;
    const padding = 24, fieldWidth = width - padding * 2, fieldHeight = height - padding * 2;
    context.clearRect(0, 0, width, height); context.fillStyle = '#07100d'; context.fillRect(0, 0, width, height);
    const grid = session.posterior, rows = grid.length, columns = grid[0].length;
    const maximum = Math.max(...grid.flat());
    grid.forEach((row, y) => row.forEach((value, x) => {
      context.fillStyle = probabilityColor(value, maximum);
      context.globalAlpha = 0.28 + Math.min(0.72, Math.sqrt(value / maximum) * 0.72);
      context.fillRect(padding + x * fieldWidth / columns + .5, padding + y * fieldHeight / rows + .5, fieldWidth / columns - 1, fieldHeight / rows - 1);
    }));
    context.globalAlpha = 1; context.strokeStyle = '#40554d'; context.lineWidth = 2; context.strokeRect(padding, padding, fieldWidth, fieldHeight);
    session.no_go_regions.forEach((region) => { context.fillStyle = '#ff715d22'; context.strokeStyle = '#ff715d'; context.lineWidth = 2; context.fillRect(padding + region.x_min * fieldWidth, padding + region.y_min * fieldHeight, (region.x_max - region.x_min) * fieldWidth, (region.y_max - region.y_min) * fieldHeight); context.strokeRect(padding + region.x_min * fieldWidth, padding + region.y_min * fieldHeight, (region.x_max - region.x_min) * fieldWidth, (region.y_max - region.y_min) * fieldHeight); context.fillStyle = '#ff8c78'; context.font = '10px monospace'; context.fillText(region.label.toUpperCase(), padding + region.x_min * fieldWidth + 5, padding + region.y_min * fieldHeight + 14); });
    history.forEach((item, index) => {
      const e = item.parameters;
      context.strokeStyle = '#62756d'; context.globalAlpha = .5; context.lineWidth = 1;
      context.beginPath(); context.moveTo(padding + e.source_x * fieldWidth, padding + e.source_y * fieldHeight);
      context.lineTo(padding + e.receiver_x * fieldWidth, padding + e.receiver_y * fieldHeight); context.stroke();
      context.globalAlpha = 1; context.fillStyle = '#94a79f'; context.font = '12px monospace';
      context.fillText(String(index + 1), padding + e.source_x * fieldWidth + 5, padding + e.source_y * fieldHeight - 5);
    });
    const drawMarker = (x: number, y: number, label: string, color: string, radius = 11) => {
      const px = padding + x * fieldWidth, py = padding + y * fieldHeight;
      context.strokeStyle = color; context.lineWidth = 2; context.beginPath(); context.arc(px, py, radius, 0, Math.PI * 2); context.stroke();
      context.fillStyle = color; context.font = 'bold 11px monospace'; context.fillText(label, px + radius + 4, py + 4);
      context.beginPath(); context.moveTo(px - 18, py); context.lineTo(px + 18, py); context.moveTo(px, py - 18); context.lineTo(px, py + 18); context.stroke();
    };
    const next = session.recommendation.experiment;
    session.status.integrity_assessment.candidate_regions.slice(0, 3).forEach((candidate, index) => {
      const px = padding + candidate.x * fieldWidth, py = padding + candidate.y * fieldHeight;
      context.save(); context.setLineDash([4, 4]); context.strokeStyle = index === 0 ? '#f19554' : '#83a99a'; context.lineWidth = 1.5;
      context.beginPath(); context.arc(px, py, 19 + index * 3, 0, Math.PI * 2); context.stroke(); context.setLineDash([]);
      context.fillStyle = index === 0 ? '#f19554' : '#a1b4ac'; context.font = 'bold 10px monospace'; context.fillText(`H${candidate.rank}`, px + 23, py - 8); context.restore();
    });
    drawMarker(next.source_x, next.source_y, 'NEXT SOURCE', '#b7f55a', 14);
    drawMarker(next.receiver_x, next.receiver_y, 'R', '#e8f3ee', 9);
    const covariance = session.status.covariance;
    if (covariance?.length === 2) {
      const a = covariance[0][0], b = covariance[0][1], d = covariance[1][1];
      const trace = a + d, root = Math.sqrt(Math.max(0, (a - d) ** 2 + 4 * b * b));
      const l1 = Math.max((trace + root) / 2, 1e-6), l2 = Math.max((trace - root) / 2, 1e-6);
      const angle = .5 * Math.atan2(2 * b, a - d);
      context.save(); context.translate(padding + session.status.mean_x * fieldWidth, padding + session.status.mean_y * fieldHeight); context.rotate(angle);
      context.strokeStyle = '#f19554'; context.setLineDash([6, 6]); context.lineWidth = 1.5;
      context.beginPath(); context.ellipse(0, 0, 1.5 * Math.sqrt(l1) * fieldWidth, 1.5 * Math.sqrt(l2) * fieldHeight, 0, 0, Math.PI * 2); context.stroke(); context.restore(); context.setLineDash([]);
    }
    if (session.ground_truth) {
      const truth = session.ground_truth;
      context.save(); context.translate(padding + truth.center_x * fieldWidth, padding + truth.center_y * fieldHeight);
      context.strokeStyle = '#ff765f'; context.lineWidth = 3; context.setLineDash([9, 5]);
      context.beginPath(); context.ellipse(0, 0, truth.radius_x * fieldWidth, truth.radius_y * fieldHeight, 0, 0, Math.PI * 2); context.stroke();
      context.fillStyle = '#ff765f'; context.font = 'bold 12px monospace'; context.fillText('GROUND TRUTH', 14, -14); context.restore(); context.setLineDash([]);
    }
  }, [session, history]);
  const coordinate = (event: React.PointerEvent<HTMLCanvasElement>) => { const canvas = event.currentTarget, rectangle = canvas.getBoundingClientRect(); const px = (event.clientX - rectangle.left) * canvas.width / rectangle.width, py = (event.clientY - rectangle.top) * canvas.height / rectangle.height; return { x: Math.max(0, Math.min(1, (px - 24) / (canvas.width - 48))), y: Math.max(0, Math.min(1, (py - 24) / (canvas.height - 48))) }; };
  const finishRegion = (event: React.PointerEvent<HTMLCanvasElement>) => { if (!editing || !dragStart || !onNoGoChange) return; const end = coordinate(event); setDragStart(null); const xMin = Math.min(dragStart.x, end.x), xMax = Math.max(dragStart.x, end.x), yMin = Math.min(dragStart.y, end.y), yMax = Math.max(dragStart.y, end.y); if (xMax - xMin < 0.02 || yMax - yMin < 0.02) return; onNoGoChange([...session.no_go_regions, { x_min: xMin, y_min: yMin, x_max: xMax, y_max: yMax, label: `no-go ${session.no_go_regions.length + 1}` }]); };
  return <><canvas ref={ref} width={900} height={590} className={`heatmap-canvas ${editing ? 'drawing-no-go' : ''}`} aria-label="Posterior defect probability with recommended source and receiver positions" onPointerDown={(event) => { if (editing) { event.currentTarget.setPointerCapture(event.pointerId); setDragStart(coordinate(event)); } }} onPointerUp={finishRegion} /><div className="no-go-toolbar"><button className={editing ? 'active' : ''} onClick={() => setEditing((value) => !value)}>{editing ? 'DRAG A RESTRICTED RECTANGLE' : 'DRAW NO-GO REGION'}</button><button onClick={() => onNoGoChange?.([])} disabled={!session.no_go_regions.length}>CLEAR {session.no_go_regions.length || ''}</button></div></>;
}
