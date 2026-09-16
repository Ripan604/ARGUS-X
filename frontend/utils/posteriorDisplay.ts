/** Shared posterior palette, scaled to the largest cell for visibility, not calibration. */
export function posteriorColor(value: number, maximum: number): string {
  const strength = Math.sqrt(Math.max(0, Math.min(1,
    Number.isFinite(value) && Number.isFinite(maximum) && maximum > 0 ? value / maximum : 0)));
  const low = [13, 25, 40], high = [119, 219, 235];
  return `rgb(${low.map((channel, index) => Math.round(channel + (high[index] - channel) * strength)).join(',')})`;
}

/** Fit a physical rectangle inside the drawing buffer without distorting its aspect. */
export function panelCanvasSize(widthM: number, heightM: number) {
  if (!Number.isFinite(widthM) || !Number.isFinite(heightM) || widthM <= 0 || heightM <= 0) {
    throw new RangeError('Panel dimensions must be finite and positive.');
  }
  const scale = Math.min(852 / widthM, 542 / heightM);
  return { width: Math.round(widthM * scale) + 48, height: Math.round(heightM * scale) + 48 };
}

/** A physical circle becomes an ellipse when x and y have different pixel scales. */
export function containmentEllipse(radiusMm: number, widthM: number, heightM: number, fieldWidth: number, fieldHeight: number) {
  if (![radiusMm, widthM, heightM, fieldWidth, fieldHeight].every(Number.isFinite)
    || radiusMm < 0 || widthM <= 0 || heightM <= 0 || fieldWidth <= 0 || fieldHeight <= 0) return null;
  return { x: radiusMm / (1_000 * widthM) * fieldWidth, y: radiusMm / (1_000 * heightM) * fieldHeight };
}
