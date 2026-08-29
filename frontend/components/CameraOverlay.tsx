'use client';

import { useEffect, useRef, useState } from 'react';
import type { SessionState } from '@/types/argus';

type Point = { x: number; y: number };

function solveLinear(matrix: number[][], values: number[]): number[] {
  const augmented = matrix.map((row, i) => [...row, values[i]]), n = values.length;
  for (let column = 0; column < n; column += 1) {
    let pivot = column; for (let row = column + 1; row < n; row += 1) if (Math.abs(augmented[row][column]) > Math.abs(augmented[pivot][column])) pivot = row;
    [augmented[column], augmented[pivot]] = [augmented[pivot], augmented[column]];
    const scale = augmented[column][column] || 1e-12; for (let j = column; j <= n; j += 1) augmented[column][j] /= scale;
    for (let row = 0; row < n; row += 1) if (row !== column) { const factor = augmented[row][column]; for (let j = column; j <= n; j += 1) augmented[row][j] -= factor * augmented[column][j]; }
  }
  return augmented.map((row) => row[n]);
}

function homography(points: Point[]): number[] | null {
  if (points.length !== 4) return null;
  const sources = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }], matrix: number[][] = [], values: number[] = [];
  sources.forEach((source, i) => { const target = points[i]; matrix.push([source.x, source.y, 1, 0, 0, 0, -target.x * source.x, -target.x * source.y]); values.push(target.x); matrix.push([0, 0, 0, source.x, source.y, 1, -target.y * source.x, -target.y * source.y]); values.push(target.y); });
  return solveLinear(matrix, values);
}

function project(transform: number[], x: number, y: number): Point { const denominator = transform[6] * x + transform[7] * y + 1; return { x: (transform[0] * x + transform[1] * y + transform[2]) / denominator, y: (transform[3] * x + transform[4] * y + transform[5]) / denominator }; }

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
      const markers = [project(transform, session.recommendation.experiment.source_x, session.recommendation.experiment.source_y), project(transform, session.status.mean_x, session.status.mean_y)];
      markers.forEach((point, index) => { context.strokeStyle = index ? '#f19554' : '#b7f55a'; context.lineWidth = 3; context.beginPath(); context.arc(point.x, point.y, index ? 15 : 22, 0, Math.PI * 2); context.stroke(); context.fillStyle = context.strokeStyle; context.fillText(index ? 'ESTIMATED DEFECT' : 'NEXT PROBE', point.x + 25, point.y); });
    }
  }, [points, session]);
  const click = (event: React.MouseEvent<HTMLCanvasElement>) => { if (points.length >= 4) return; const rect = event.currentTarget.getBoundingClientRect(); setPoints((current) => [...current, { x: (event.clientX - rect.left) * event.currentTarget.width / rect.width, y: (event.clientY - rect.top) * event.currentTarget.height / rect.height }]); };
  return <div className="camera-layout"><div className="camera-stage"><video ref={video} autoPlay playsInline muted /><canvas ref={canvas} width={960} height={540} onClick={click} />{!active && <button onClick={start}>ENABLE CAMERA</button>}</div><aside><p className="eyebrow">Planar homography · AR-lite</p><h3>Align the digital twin to the physical panel.</h3><ol><li>Enable the camera.</li><li>Click panel corners: top-left, top-right, bottom-right, bottom-left.</li><li>ARGUS projects its next probe and estimate into camera coordinates.</li></ol><div className="calibration-status">{points.length}/4 CORNERS CAPTURED</div>{points.length > 0 && <button className="ghost-button" onClick={() => setPoints([])}>RESET CORNERS</button>}{cameraError && <p className="error-text">{cameraError}</p>}</aside></div>;
}
