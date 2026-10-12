import type { BenchmarkResult, ExperimentParameters, HistoryItem, MeasurementAnalysis, Preset, ResearchJob, SessionState } from '@/types/argus';
import type { ProbeTimingCalibration } from '@/utils/probeCalibration';

const CONFIGURED_API_URL = process.env.NEXT_PUBLIC_ARGUS_API_URL?.replace(/\/+$/, '');
const CONFIGURED_API_PORT = process.env.NEXT_PUBLIC_ARGUS_API_PORT || '8000';
const TOKEN_STORAGE_KEY = 'argus_access_token';
let tabToken = '';

export function setApiToken(value: string) {
  const token = value.trim();
  if (token && !/^[A-Za-z0-9._~-]{32,256}$/.test(token)) throw new Error('Enter the complete access key from the ARGUS launcher.');
  if (typeof window === 'undefined') throw new Error('Access keys can only be set in a browser tab.');
  tabToken = token;
  try {
    if (token) window.sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify({ api: getApiUrl(), token }));
    else window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch { /* A blocked storage API keeps the key only in this page's memory. */ }
}

export function getApiToken(): string {
  if (typeof window === 'undefined') return '';
  try {
    const stored = JSON.parse(window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || 'null') as { api?: string; token?: string } | null;
    if (stored?.api === getApiUrl() && typeof stored.token === 'string' && /^[A-Za-z0-9._~-]{32,256}$/.test(stored.token)) return stored.token;
  } catch { /* Storage is optional; never expose a key through a URL or public env var. */ }
  return tabToken;
}

export function authorizedRequestInit(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  const token = getApiToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

export function getWebSocketProtocols(): string[] {
  const token = getApiToken();
  return token ? ['argus', `argus-token.${token}`] : ['argus'];
}

export function resolveApiUrl(configured: string | undefined, hostname: string | undefined, port = '8000') {
  if (configured) {
    const url = new URL(configured);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('ARGUS API must be an HTTP(S) address without URL credentials, query, or fragment.');
    return configured.replace(/\/+$/, '');
  }
  if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) throw new Error('Invalid ARGUS API port');
  const host = hostname || '127.0.0.1';
  return `http://${host.includes(':') && !host.startsWith('[') ? `[${host}]` : host}:${port}`;
}

export function getApiUrl() {
  return resolveApiUrl(CONFIGURED_API_URL, typeof window === 'undefined' ? undefined : window.location.hostname, CONFIGURED_API_PORT);
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
  const response = await fetch(`${getApiUrl()}${path}`, authorizedRequestInit(init));
  if (!response.ok) {
    throw new Error(readableApiError(await response.text(), response.status));
  }
  return response.json() as Promise<T>;
}

export const argusApi = {
  ledgerCheckpoint: (id: string) => request<Record<string, unknown>>(`/api/ledger/${id}/checkpoint`),
  health: async (signal?: AbortSignal) => {
    const response = await request<{ status: string; service?: string; authentication_required?: boolean; network_mode?: string }>('/health', { signal });
    if (response.status !== 'ok' || response.service !== 'argus') throw new Error('This API address is serving another application. Check the ARGUS API port.');
    return response;
  },
  createSession: (
    preset: Preset,
    seed?: number,
    mode: 'simulation' | 'physical' = 'simulation',
    panelWidthMm = 600,
    panelHeightMm = 400,
    nuisanceAwareDesign = false,
    riskCalibrationDesign = false,
  ) => request<SessionState>('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, preset, seed, panel_width_mm: panelWidthMm, panel_height_mm: panelHeightMm, grid_size: 20, max_experiments: 12, enable_nuisance_aware_design: nuisanceAwareDesign, enable_risk_calibration_design: riskCalibrationDesign }),
  }),
  getSession: (id: string) => request<SessionState>(`/sessions/${id}`),
  runExperiment: (id: string, experiment?: ExperimentParameters) => request<{ state: SessionState; measurement: MeasurementAnalysis }>(`/sessions/${id}/experiments/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(experiment ? { experiment } : {}),
  }),
  uploadWav: async (id: string, file: Blob, experiment?: ExperimentParameters, sensorMetadata?: Record<string, unknown>) => {
    const form = new FormData();
    form.append('file', file, 'argus-measurement.wav');
    if (experiment) form.append('experiment_json', JSON.stringify(experiment));
    if (sensorMetadata) form.append('sensor_metadata_json', JSON.stringify(sensorMetadata));
    return request<{ state: SessionState; measurement: MeasurementAnalysis }>(`/sessions/${id}/experiments/upload`, { method: 'POST', body: form });
  },
  connectDevice: (device: 'serial_probe' | 'microphone', timingCalibration?: ProbeTimingCalibration) => request<{ connected: boolean; last_error?: string; arrival_likelihood_supported?: boolean }>('/devices/connect', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ device, baudrate: 115200, ...(timingCalibration ? { timing_calibration: timingCalibration } : {}) }),
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
    const response = await fetch(`${getApiUrl()}/api/export/${id}`, authorizedRequestInit());
    if (!response.ok) throw new Error(await response.text());
    return response.blob();
  },
  jobs: (signal?: AbortSignal) => request<{ jobs: ResearchJob[] }>('/api/research/jobs', { signal }),
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
