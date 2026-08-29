import type { BenchmarkResult, ExperimentParameters, HistoryItem, MeasurementAnalysis, Preset, SessionState } from '@/types/argus';

const API_URL = process.env.NEXT_PUBLIC_ARGUS_API_URL || 'http://127.0.0.1:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `ARGUS API returned ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const argusApi = {
  health: () => request<{ status: string }>('/health'),
  createSession: (
    preset: Preset,
    seed?: number,
    mode: 'simulation' | 'physical' = 'simulation',
    panelWidthMm = 600,
    panelHeightMm = 400,
  ) => request<SessionState>('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, preset, seed, panel_width_mm: panelWidthMm, panel_height_mm: panelHeightMm, grid_size: 20, max_experiments: 12 }),
  }),
  getSession: (id: string) => request<SessionState>(`/sessions/${id}`),
  runExperiment: (id: string, experiment?: ExperimentParameters) => request<{ state: SessionState; measurement: MeasurementAnalysis }>(`/sessions/${id}/experiments/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(experiment ? { experiment } : {}),
  }),
  uploadWav: async (id: string, file: Blob, experiment?: ExperimentParameters) => {
    const form = new FormData();
    form.append('file', file, 'argus-measurement.wav');
    if (experiment) form.append('experiment_json', JSON.stringify(experiment));
    return request<{ state: SessionState; measurement: MeasurementAnalysis }>(`/sessions/${id}/experiments/upload`, { method: 'POST', body: form });
  },
  connectDevice: (device: 'serial_probe' | 'microphone') => request<{ connected: boolean; last_error?: string }>('/devices/connect', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ device, baudrate: 115200 }),
  }),
  acquireDevice: (id: string, device: 'serial_probe' | 'microphone', experiment?: ExperimentParameters) => request<{ state: SessionState; measurement: MeasurementAnalysis }>(`/sessions/${id}/experiments/device`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ device, experiment }),
  }),
  history: (id: string) => request<{ experiments: HistoryItem[] }>(`/sessions/${id}/history`),
  reveal: (id: string) => request<SessionState>(`/sessions/${id}/reveal`, { method: 'POST' }),
  calibrate: (id: string) => request<Record<string, unknown>>(`/sessions/${id}/calibrate`, { method: 'POST' }),
  benchmarks: () => request<BenchmarkResult>('/benchmarks'),
};
