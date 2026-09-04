'use client';

import { useEffect, useRef, useState } from 'react';
import type { SessionState } from '@/types/argus';

type Point = { x: number; y: number };

function solveLinear(matrix: number[][], values: number[]): number[] | null {
  const augmented = matrix.map((row, i) => [...row, values[i]]), n = values.length;
  for (let column = 0; column < n; column += 1) {
    let pivot = column; for (let row = column + 1; row < n; row += 1) if (Math.abs(augmented[row][column]) > Math.abs(augmented[pivot][column])) pivot = row;
    if (!Number.isFinite(augmented[pivot][column]) || Math.abs(augmented[pivot][column]) < 1e-10) return null;
    [augmented[column], augmented[pivot]] = [augmented[pivot], augmented[column]];
    const scale = augmented[column][column]; for (let j = column; j <= n; j += 1) augmented[column][j] /= scale;
    for (let row = 0; row < n; row += 1) if (row !== column) { const factor = augmented[row][column]; for (let j = column; j <= n; j += 1) augmented[row][j] -= factor * augmented[column][j]; }
  }
  const solution = augmented.map((row) => row[n]);
  return solution.every(Number.isFinite) ? solution : null;
}

function validQuadrilateral(points: Point[]): boolean {
  if (points.length !== 4 || points.some(({ x, y }) => !Number.isFinite(x) || !Number.isFinite(y))) return false;
  const crosses = points.map((point, index) => {
    const next = points[(index + 1) % 4], after = points[(index + 2) % 4];
    return (next.x - point.x) * (after.y - next.y) - (next.y - point.y) * (after.x - next.x);
  });
  const area = Math.abs(points.reduce((sum, point, index) => {
    const next = points[(index + 1) % 4];
    return sum + point.x * next.y - next.x * point.y;
  }, 0)) / 2;
  return area >= 1_000 && (crosses.every((value) => value > 1e-6) || crosses.every((value) => value < -1e-6));
}

function homography(points: Point[]): number[] | null {
  if (!validQuadrilateral(points)) return null;
  const sources = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }], matrix: number[][] = [], values: number[] = [];
  sources.forEach((source, i) => { const target = points[i]; matrix.push([source.x, source.y, 1, 0, 0, 0, -target.x * source.x, -target.x * source.y]); values.push(target.x); matrix.push([0, 0, 0, source.x, source.y, 1, -target.y * source.x, -target.y * source.y]); values.push(target.y); });
  return solveLinear(matrix, values);
}

function project(transform: number[], x: number, y: number): Point | null {
  const denominator = transform[6] * x + transform[7] * y + 1;
  if (!Number.isFinite(denominator) || Math.abs(denominator) < 1e-9) return null;
  const point = { x: (transform[0] * x + transform[1] * y + transform[2]) / denominator, y: (transform[3] * x + transform[4] * y + transform[5]) / denominator };
  return Number.isFinite(point.x) && Number.isFinite(point.y) ? point : null;
}

export function CameraOverlay({ session }: { session: SessionState }) {
  const video = useRef<HTMLVideoElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const [points, setPoints] = useState<Point[]>([]), [cameraError, setCameraError] = useState('');
  const [active, setActive] = useState(false);
  const start = async () => { try { const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }); if (video.current) video.current.srcObject = stream; setActive(true); setCameraError(''); } catch (error) { setCameraError(error instanceof Error ? error.message : 'Camera permission failed'); } };
  useEffect(() => () => { const stream = video.current?.srcObject as MediaStream | null; stream?.getTracks().forEach((track) => track.stop()); }, []);
  useEffect(() => {
    const overlay = canvas.current; if (!overlay) return; const context = overlay.getContext('2d'); if (!context) return;
    context.clearRect(0, 0, overlay.width, overlay.height); context.lineWidth = 2; context.strokeStyle = '#b7f55a'; context.fillStyle = '#b7f55a'; context.font = '12px monospace';
    points.forEach((point, index) => { context.beginPath(); context.arc(point.x, point.y, 7, 0, Math.PI * 2); context.stroke(); context.fillText(['TL', 'TR', 'BR', 'BL'][index], point.x + 10, point.y - 8); });
    if (points.length > 1) { context.beginPath(); context.moveTo(points[0].x, points[0].y); points.slice(1).forEach((point) => context.lineTo(point.x, point.y)); if (points.length === 4) context.closePath(); context.stroke(); }
    const transform = homography(points); if (transform) {
      const rows = session.posterior.length, columns = session.posterior[0]?.length ?? 0, maximum = Math.max(...session.posterior.flat());
      session.posterior.forEach((row, y) => row.forEach((value, x) => {
        const corners = [project(transform, x / columns, y / rows), project(transform, (x + 1) / columns, y / rows), project(transform, (x + 1) / columns, (y + 1) / rows), project(transform, x / columns, (y + 1) / rows)];
        if (corners.some((corner) => corner === null)) return;
        const projected = corners as Point[];
        context.beginPath(); context.moveTo(projected[0].x, projected[0].y); projected.slice(1).forEach((corner) => context.lineTo(corner.x, corner.y)); context.closePath(); context.fillStyle = `rgba(183,245,90,${0.34 * Math.sqrt(value / Math.max(maximum, 1e-12))})`; context.fill();
      }));
      const source = project(transform, session.recommendation.experiment.source_x, session.recommendation.experiment.source_y);
      const receiver = project(transform, session.recommendation.experiment.receiver_x, session.recommendation.experiment.receiver_y);
      const estimate = project(transform, session.status.mean_x, session.status.mean_y);
      if (!source || !receiver || !estimate) return;
      context.strokeStyle = '#eaf4ef88'; context.lineWidth = 2; context.setLineDash([7, 6]); context.beginPath(); context.moveTo(source.x, source.y); context.lineTo(receiver.x, receiver.y); context.stroke(); context.setLineDash([]);
      const covariance = session.status.covariance; const scale90 = Math.sqrt(4.605); const xEdge = project(transform, Math.min(1, session.status.mean_x + scale90 * Math.sqrt(Math.max(0, covariance[0]?.[0] ?? 0))), session.status.mean_y); const yEdge = project(transform, session.status.mean_x, Math.min(1, session.status.mean_y + scale90 * Math.sqrt(Math.max(0, covariance[1]?.[1] ?? 0))));
      if (xEdge && yEdge) { context.strokeStyle = '#f19554'; context.lineWidth = 2; context.beginPath(); context.ellipse(estimate.x, estimate.y, Math.max(12, Math.hypot(xEdge.x - estimate.x, xEdge.y - estimate.y)), Math.max(12, Math.hypot(yEdge.x - estimate.x, yEdge.y - estimate.y)), 0, 0, Math.PI * 2); context.stroke(); }
      [[source, 'SOURCE', '#b7f55a'], [receiver, 'RECEIVER', '#65c6ff'], [estimate, 'SUSPECTED REGION', '#f19554']].forEach(([rawPoint, label, color]) => { const point = rawPoint as Point; context.strokeStyle = String(color); context.lineWidth = 3; context.beginPath(); context.arc(point.x, point.y, label === 'SUSPECTED REGION' ? 15 : 21, 0, Math.PI * 2); context.stroke(); context.fillStyle = String(color); context.fillText(String(label), point.x + 24, point.y); });
    }
  }, [points, session]);
  const click = (event: React.MouseEvent<HTMLCanvasElement>) => { if (points.length >= 4) return; const rect = event.currentTarget.getBoundingClientRect(); setPoints((current) => [...current, { x: (event.clientX - rect.left) * event.currentTarget.width / rect.width, y: (event.clientY - rect.top) * event.currentTarget.height / rect.height }]); };
  const registrationError = points.length === 4 && homography(points) === null
    ? 'Corner geometry is degenerate or out of order. Reset and tap TL, TR, BR, BL.'
    : '';
  return <div className="camera-layout"><div className="camera-stage"><video ref={video} autoPlay playsInline muted /><canvas ref={canvas} width={960} height={540} onClick={click} />{!active && <button onClick={start}>ENABLE CAMERA</button>}</div><aside><p className="eyebrow">Planar homography / AR-lite</p><h3>Align the digital twin to the physical panel.</h3><ol><li>Enable the camera.</li><li>Click panel corners: top-left, top-right, bottom-right, bottom-left.</li><li>ARGUS projects its next probe and estimate into camera coordinates.</li></ol><div className="calibration-status">{points.length}/4 CORNERS CAPTURED</div>{points.length > 0 && <button className="ghost-button" onClick={() => setPoints([])}>RESET CORNERS</button>}{(cameraError || registrationError) && <p className="error-text">{cameraError || registrationError}</p>}</aside></div>;
}
