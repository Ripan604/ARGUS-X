'use client';

import { useCallback, useEffect, useState } from 'react';
import { argusApi } from '@/services/api';
import { recordMicrophone } from '@/utils/audio';
import type { BenchmarkResult, HistoryItem, MeasurementAnalysis, Preset, SessionState } from '@/types/argus';

export function useArgusSession() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [measurement, setMeasurement] = useState<MeasurementAnalysis | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.resolve(window.localStorage.getItem('argus_last_session')).then((saved) => {
      if (active && saved) setLastSessionId(saved);
    });
    argusApi.health()
      .then(() => { if (active) setApiOnline(true); })
      .catch(() => { if (active) setApiOnline(false); });
    return () => { active = false; };
  }, []);

  const execute = useCallback(async <T,>(operation: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true); setError(null);
    try { return await operation(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unknown ARGUS error'); return undefined; }
    finally { setBusy(false); }
  }, []);

  const refreshHistory = useCallback(async (id: string) => {
    const result = await argusApi.history(id); setHistory(result.experiments);
  }, []);

  const create = (preset: Preset, mode: 'simulation' | 'physical' = 'simulation', panelWidthMm = 600, panelHeightMm = 400) => execute(async () => {
    const state = await argusApi.createSession(preset, undefined, mode, panelWidthMm, panelHeightMm);
    window.localStorage.setItem('argus_last_session', state.id); setLastSessionId(state.id); setApiOnline(true);
    setSession(state); setMeasurement(null); setHistory([]); return state;
  });
  const resume = () => lastSessionId && execute(async () => {
    const state = await argusApi.getSession(lastSessionId); const savedHistory = await argusApi.history(lastSessionId);
    setApiOnline(true); setSession(state); setHistory(savedHistory.experiments);
    setMeasurement(savedHistory.experiments.at(-1)?.features ?? null); return state;
  });
  const run = (manualContinue = false) => session && execute(async () => {
    const experiment = manualContinue ? session.recommendation.experiment : undefined;
    const result = await argusApi.runExperiment(session.id, experiment); setSession(result.state); setMeasurement(result.measurement); await refreshHistory(session.id); return result;
  });
  const upload = (file: Blob) => session && execute(async () => {
    const result = await argusApi.uploadWav(session.id, file, session.recommendation.experiment); setSession(result.state); setMeasurement(result.measurement); await refreshHistory(session.id); return result;
  });
  const capture = () => session && execute(async () => {
    const wav = await recordMicrophone(220); const result = await argusApi.uploadWav(session.id, wav, session.recommendation.experiment);
    setSession(result.state); setMeasurement(result.measurement); await refreshHistory(session.id); return result;
  });
  const acquireDevice = (device: 'serial_probe' | 'microphone') => session && execute(async () => {
    const connection = await argusApi.connectDevice(device);
    if (!connection.connected) throw new Error(connection.last_error || `${device} could not connect`);
    const result = await argusApi.acquireDevice(session.id, device, session.recommendation.experiment);
    setSession(result.state); setMeasurement(result.measurement); await refreshHistory(session.id); return result;
  });
  const reveal = () => session && execute(async () => { const state = await argusApi.reveal(session.id); setSession(state); return state; });
  const calibrate = () => session && execute(async () => { await argusApi.calibrate(session.id); const state = await argusApi.getSession(session.id); setSession(state); return state; });
  const loadBenchmarks = () => execute(async () => { const result = await argusApi.benchmarks(); setBenchmarks(result); return result; });
  const reset = () => { setSession(null); setMeasurement(null); setHistory([]); setError(null); };

  return { session, measurement, history, benchmarks, busy, error, apiOnline, lastSessionId, create, resume, run, upload, capture, acquireDevice, reveal, calibrate, loadBenchmarks, reset };
}
