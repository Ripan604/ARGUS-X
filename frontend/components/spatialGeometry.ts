/** Coordinates of a circle in physical millimeters, not normalized panel distance. */
export function physicalCircle(cx: number, cy: number, radiusMm: number, widthMm: number, heightMm: number, segments = 120) {
  if (![cx, cy, radiusMm, widthMm, heightMm].every(Number.isFinite)
    || widthMm <= 0 || heightMm <= 0 || radiusMm < 0
    || !Number.isInteger(segments) || segments < 3 || segments > 2048) return [];
  return Array.from({ length: segments + 1 }, (_, index) => { const angle = index / segments * Math.PI * 2; return { x: cx + Math.cos(angle) * radiusMm / widthMm, y: cy + Math.sin(angle) * radiusMm / heightMm }; });
}
export function normalizedRelief(posterior: number[][] | undefined) {
  if (!posterior?.length || !posterior[0]?.length
    || posterior.some((row) => row.length !== posterior[0].length || row.some((value) => !Number.isFinite(value) || value < 0))) return null;
  const peak = Math.max(...posterior.flat());
  return posterior.map((row) => row.map((value) => peak > 0 ? Math.max(0, value) / peak : 0));
}
