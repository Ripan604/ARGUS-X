/** Descriptive metrics of a recorded discrete posterior; never a coverage certificate. */
export interface PosteriorSummary {
  rows: number; columns: number; values: number[]; entropyBits: number;
  effectiveCells: number; area90Fraction: number; mass90: number; threshold90: number;
  map: { x: number; y: number }; mean: { x: number; y: number };
}

export function summarizePosterior(grid: number[][]): PosteriorSummary | null {
  const rows = grid.length, columns = grid[0]?.length ?? 0;
  if (!rows || !columns || rows * columns > 65536 || grid.some(row => row.length !== columns)) return null;
  const values = grid.flat();
  if (values.some(p => !Number.isFinite(p) || p < 0 || p > 1)) return null;
  const total = values.reduce((sum, p) => sum + p, 0);
  if (Math.abs(total - 1) > 1e-5) return null;
  // Only floating-point normalization drift is removed. Invalid mass is rejected above.
  const normalized = values.map(p => p / total);
  const sorted = [...normalized].sort((a, b) => b - a);
  let cumulative = 0, threshold90 = 1;
  for (const p of sorted) { cumulative += p; threshold90 = p; if (cumulative >= .9 - 1e-12) break; }
  // Include every cell tied at the boundary; a uniform field must show the entire panel.
  const selected = normalized.filter(p => p >= threshold90);
  const mapIndex = normalized.indexOf(sorted[0]);
  let meanX = 0, meanY = 0, entropyBits = 0;
  normalized.forEach((p, index) => {
    meanX += p * ((index % columns) + .5) / columns;
    meanY += p * (Math.floor(index / columns) + .5) / rows;
    if (p > 0) entropyBits -= p * Math.log2(p);
  });
  return { rows, columns, values: normalized, entropyBits, effectiveCells: 2 ** entropyBits,
    threshold90, area90Fraction: selected.length / normalized.length,
    mass90: selected.reduce((sum, p) => sum + p, 0),
    map: { x: ((mapIndex % columns) + .5) / columns, y: (Math.floor(mapIndex / columns) + .5) / rows },
    mean: { x: meanX, y: meanY } };
}

export function comparePosteriors(before: number[][], after: number[][], widthMm: number, heightMm: number) {
  const previous = summarizePosterior(before), current = summarizePosterior(after);
  if (!previous || !current || previous.rows !== current.rows || previous.columns !== current.columns
    || ![widthMm, heightMm].every(v => Number.isFinite(v) && v > 0)) return null;
  let jsBits = 0, totalVariation = 0;
  previous.values.forEach((p, i) => {
    const q = current.values[i], m = (p + q) / 2;
    if (p > 0) jsBits += .5 * p * Math.log2(p / m);
    if (q > 0) jsBits += .5 * q * Math.log2(q / m);
    totalVariation += .5 * Math.abs(p - q);
  });
  return { previous, current, jsBits: Math.max(0, jsBits), totalVariation,
    entropyChangeBits: current.entropyBits - previous.entropyBits,
    meanShiftMm: Math.hypot((current.mean.x - previous.mean.x) * widthMm, (current.mean.y - previous.mean.y) * heightMm),
    delta: current.values.map((p, i) => p - previous.values[i]) };
}
