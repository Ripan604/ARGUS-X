import type { BenchmarkResult, ExperimentParameters, HistoryItem, MeasurementAnalysis, Preset, ResearchJob, SessionState } from '@/types/argus';

const CONFIGURED_API_URL = process.env.NEXT_PUBLIC_ARGUS_API_URL?.replace(/\/+$/, '');

export function resolveApiUrl(configured: string | undefined, hostname: string | undefined) {
  if (configured) return configured.replace(/\/+$/, '');
  return `http://${hostname || '127.0.0.1'}:8000`;
}

export function getApiUrl() {
  return resolveApiUrl(CONFIGURED_API_URL, typeof window === 'undefined' ? undefined : window.location.hostname);
}

function readableApiError(payload: string, status: number) {
  try {
    const parsed = JSON.parse(payload) as { detail?: string | Array<{ loc?: Array<string | number>; msg?: string }> };
    if (typeof parsed.detail === 'string') return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      const details = parsed.detail.map((item) => `${item.loc?.slice(1).join('.') || 'request'}: ${item.msg || 'invalid value'}`);
      if (details.length) return details.join('; ');
    }
  } catch {
    // Non-JSON error responses are shown verbatim below.
  }
  return payload || `ARGUS API returned ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiUrl()}${path}`, init);
  if (!response.ok) {
    throw new Error(readableApiError(await response.text(), response.status));
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
  plannerExplanation: (id: string) => request<Record<string, unknown>>(`/api/planner/explain?session_id=${encodeURIComponent(id)}`),
  inferenceUncertainty: (id: string) => request<Record<string, unknown>>(`/api/inference/uncertainty?session_id=${encodeURIComponent(id)}`),
  modelTrust: (id: string) => request<Record<string, unknown>>(`/api/model/trust?session_id=${encodeURIComponent(id)}`),
  oodStatus: (id: string) => request<Record<string, unknown>>(`/api/ood/status?session_id=${encodeURIComponent(id)}`),
  ledger: (id: string) => request<{ entries: Array<Record<string, unknown>> }>(`/api/ledger/${id}`),
  verifyLedger: (id: string) => request<{ status: string; valid: boolean; record_count: number; head_hash: string }>(`/api/ledger/${id}/verify`),
  exportBundle: async (id: string) => {
    const response = await fetch(`${getApiUrl()}/api/export/${id}`);
    if (!response.ok) throw new Error(await response.text());
    return response.blob();
  },
  jobs: () => request<{ jobs: ResearchJob[] }>('/api/research/jobs'),
  startJob: (job_type: ResearchJob['job_type'], parameters: Record<string, unknown> = {}) => request<ResearchJob>('/api/research/jobs', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ job_type, parameters }),
  }),
  cancelJob: (id: string) => request<ResearchJob>(`/api/research/jobs/${id}/cancel`, { method: 'POST' }),
  updateNoGoRegions: (id: string, regions: SessionState['no_go_regions']) => request<SessionState>(`/api/sessions/${id}/no-go-regions`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ regions }),
  }),
  humanDecision: (id: string, decision: 'accept' | 'modify' | 'reject', reason?: string) => request<{ state: SessionState }>(`/api/sessions/${id}/human-decision`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, reason }),
  }),
  emergencyStop: (id: string, reason: string) => request<SessionState>(`/api/sessions/${id}/emergency-stop`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }),
  }),
  releaseEmergencyStop: (id: string, reason: string) => request<SessionState>(`/api/sessions/${id}/emergency-stop/release`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason, acknowledgement: true }),
  }),
  assuranceStatus: (id: string) => request<Record<string, unknown>>(`/api/assurance/status?session_id=${encodeURIComponent(id)}`),
  registerProbe: (node_id: string, capabilities: Record<string, unknown>) => request<Record<string, unknown>>('/api/probe/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ node_id, node_type: 'phone', capabilities }),
  }),
  sendProbeMeasurement: (payload: Record<string, unknown>) => request<{ state: SessionState; quality: Record<string, unknown> }>('/api/probe/measurement', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }),
};
