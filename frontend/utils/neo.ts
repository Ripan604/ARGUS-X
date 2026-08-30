export function clamp01(value: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
}

export function percent(value: number, digits = 0): string {
  return `${(clamp01(value) * 100).toFixed(digits)}%`;
}

export function typedValue(record: Record<string, unknown> | undefined, key: string, fallback = 0): number {
  const value = record?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function responseDelayMilliseconds(prediction: Record<string, unknown>): number | null {
  const mean = prediction.mean;
  if (!Array.isArray(mean) || typeof mean[0] !== 'number') return null;
  return mean[0] * 1000;
}

