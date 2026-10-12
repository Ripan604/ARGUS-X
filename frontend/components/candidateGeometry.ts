import type { ExperimentParameters } from '../types/argus.ts';

const numericParameters = ['source_x', 'source_y', 'receiver_x', 'receiver_y', 'frequency_start_hz', 'frequency_end_hz', 'amplitude', 'duration_s'] as const;

/** A route alone does not identify an experiment: excitation parameters must match too. */
export function sameCandidateExperiment(a: ExperimentParameters, b: ExperimentParameters): boolean {
  return a.waveform === b.waveform
    && numericParameters.every((key) => Number.isFinite(a[key]) && Number.isFinite(b[key]) && a[key] === b[key])
    && (a.phase_code ?? null) === (b.phase_code ?? null)
    && (a.code_length ?? null) === (b.code_length ?? null)
    && (a.sample_rate_hz ?? null) === (b.sample_rate_hz ?? null)
    && JSON.stringify(a.spectral_notches_hz ?? []) === JSON.stringify(b.spectral_notches_hz ?? []);
}

/** Share a zero-inclusive axis so negative utilities remain negative, not "better" bars. */
export function candidateScoreGeometry(value: number, values: number[]) {
  const finite = values.filter(Number.isFinite);
  const minimum = Math.min(0, ...finite);
  const maximum = Math.max(0, ...finite);
  const range = maximum - minimum;
  if (range === 0 || !Number.isFinite(value)) return { zero: 0, left: 0, width: 0, negative: value < 0 };
  const zero = 100 * -minimum / range;
  const end = Math.max(0, Math.min(100, 100 * (value - minimum) / range));
  return { zero, left: Math.min(zero, end), width: Math.abs(end - zero), negative: value < 0 };
}

/** Fit a physically proportioned panel into an SVG without changing its aspect ratio. */
export function candidatePanelGeometry(widthMm: number, heightMm: number, width: number, height: number, margin: number) {
  if (![widthMm, heightMm, width, height, margin].every(Number.isFinite)
    || widthMm <= 0 || heightMm <= 0 || margin < 0 || width <= margin * 2 || height <= margin * 2) return null;
  const scale = Math.min((width - margin * 2) / widthMm, (height - margin * 2) / heightMm);
  const panelWidth = widthMm * scale;
  const panelHeight = heightMm * scale;
  return { x: (width - panelWidth) / 2, y: (height - panelHeight) / 2, width: panelWidth, height: panelHeight };
}
