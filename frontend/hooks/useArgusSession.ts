'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { argusApi } from '@/services/api';
import { recordMicrophone } from '@/utils/audio';
import { SessionOperationFence, reconcileOwnedRead, runningOperation, settleOwnedTask } from '@/utils/sessionOperations';
import type { OperationTicket, SessionOperation } from '@/utils/sessionOperations';
import type { BenchmarkResult, HistoryItem, MeasurementAnalysis, Preset, SessionState } from '@/types/argus';
import type { ProbeTimingCalibration } from '@/utils/probeCalibration';

interface OperationContext {
  ticket: OperationTicket;
  current: () => boolean;
  partial: (message: string) => void;
}

const readableError = (reason: unknown) => reason instanceof Error ? reason.message : 'Unknown ARGUS error';

export function useArgusSession() {
  const [ownership] = useState(() => new SessionOperationFence());
  const [session, setRawSession] = useState<SessionState | null>(null);
  const sessionRef = useRef<SessionState | null>(null);
  const [measurement, setMeasurement] = useState<MeasurementAnalysis | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [operation, setOperation] = useState<SessionOperation | null>(null);
  const operationRef = useRef<SessionOperation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [authenticationRequired, setAuthenticationRequired] = useState(false);
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const lastSessionIdRef = useRef<string | null>(null);

  const publishOperation = useCallback((next: SessionOperation | null) => {
    operationRef.current = next;
    setOperation(next);
  }, []);

  const applySession = useCallback((next: SessionState | null) => {
    const state = next ? { ...next, safety: { ...next.safety,
      emergency_stop: ownership.mergeSafety(next.id, next.safety.emergency_stop) } } : null;
    sessionRef.current = state;
    setRawSession(state);
  }, [ownership]);

  useEffect(() => {
    ownership.mount();
    let active = true;
    const storageTimer = window.setTimeout(() => {
      try {
        const saved = window.localStorage.getItem('argus_last_session');
        if (active && saved) { lastSessionIdRef.current = saved; setLastSessionId(saved); }
      } catch { /* Storage can be disabled in restricted browser contexts. */ }
    }, 0);
    let checkingHealth = false;
    let healthController: AbortController | undefined;
    const checkHealth = async () => {
      if (checkingHealth || document.hidden) return;
      checkingHealth = true;
      const controller = new AbortController();
      healthController = controller;
      const timeout = window.setTimeout(() => controller.abort(), 5_000);
      try {
        const health = await argusApi.health(controller.signal);
        if (active) { setApiOnline(true); setAuthenticationRequired(Boolean(health.authentication_required)); }
      } catch { if (active) setApiOnline(false); }
      finally { window.clearTimeout(timeout); checkingHealth = false; }
    };
    void checkHealth();
    const healthTimer = window.setInterval(checkHealth, 12_000);
    document.addEventListener('visibilitychange', checkHealth);
    return () => {
      active = false;
      ownership.dispose();
      window.clearTimeout(storageTimer);
      window.clearInterval(healthTimer);
      document.removeEventListener('visibilitychange', checkHealth);
      healthController?.abort();
    };
  }, [ownership]);

  const execute = useCallback(async <T,>(label: string, work: (context: OperationContext) => Promise<T>,
    replace = false): Promise<T | undefined> => {
    const ticket = replace ? ownership.beginReplacement(label) : ownership.begin(label);
    if (!ticket) return undefined;
    if (replace) { applySession(null); setMeasurement(null); setHistory([]); }
    publishOperation(runningOperation(ticket));
    setBusy(ownership.isBusy); setError(null); setWarning(null);
    let partialDetail: string | undefined;
    const context: OperationContext = { ticket, current: () => ownership.owns(ticket),
      partial: (message) => { if (ownership.owns(ticket)) partialDetail = message; } };
    const outcome = await settleOwnedTask(ownership, ticket, () => work(context));
    if (outcome.status === 'stale') return undefined;
    const displayed = operationRef.current?.id === ticket.id;
    if (displayed) {
      const detail = outcome.status === 'failed' ? readableError(outcome.error) : partialDetail;
      publishOperation({ ...runningOperation(ticket), sessionId: ownership.sessionId, finishedAt: Date.now(),
        status: outcome.status === 'failed' ? 'failed' : partialDetail ? 'partial' : 'succeeded', ...(detail ? { detail } : {}) });
      if (outcome.status === 'failed') setError(detail || 'Unknown ARGUS error');
    }
    if (outcome.status === 'succeeded' && partialDetail) setWarning(partialDetail);
    ownership.finish(ticket);
    if (ownership.isMounted) setBusy(ownership.isBusy);
    return outcome.status === 'succeeded' ? outcome.value : undefined;
  }, [ownership, applySession, publishOperation]);

  const commitState = useCallback((context: OperationContext, state: SessionState) => {
    if (!ownership.checkResponse(context.ticket, state.id)) return false;
    applySession(state);
    return true;
  }, [ownership, applySession]);

  const refreshHistory = useCallback(async (id: string, context: OperationContext, successLabel: string,
    restoreMeasurement = false) => {
    if (!context.current()) return;
    const followup = await reconcileOwnedRead(ownership, context.ticket, () => argusApi.history(id), (result) => {
      if (ownership.sessionId !== id) return;
      setHistory(result.experiments);
      if (restoreMeasurement) setMeasurement(result.experiments.at(-1)?.features ?? null);
    });
    if (followup.status === 'partial') context.partial(`${successLabel}; history could not refresh: ${readableError(followup.error)}`);
  }, [ownership]);

  const requireAcquisition = (context: OperationContext, id: string) => {
    if (!context.current()) return false;
    if (!ownership.allowsAcquisition(context.ticket) || sessionRef.current?.safety.emergency_stop.latched) {
      throw new Error('Emergency stop blocks acquisition. No next acquisition request was dispatched.');
    }
    return ownership.checkResponse(context.ticket, id);
  };

  const create = (preset: Preset, mode: 'simulation' | 'physical' = 'simulation', panelWidthMm = 600,
    panelHeightMm = 400, nuisanceAwareDesign = false, riskCalibrationDesign = false) => execute('Create session', async (context) => {
    const state = await argusApi.createSession(preset, undefined, mode, panelWidthMm, panelHeightMm, nuisanceAwareDesign, riskCalibrationDesign);
    if (!ownership.adopt(context.ticket, state.id)) return undefined;
    try { window.localStorage.setItem('argus_last_session', state.id); } catch { /* Optional convenience only. */ }
    lastSessionIdRef.current = state.id; setLastSessionId(state.id); setApiOnline(true);
    applySession(state); return state;
  }, true);

  const resume = () => {
    const id = lastSessionIdRef.current;
    if (!id) return undefined;
    return execute('Resume session', async (context) => {
      const state = await argusApi.getSession(id);
      if (!context.current()) return undefined;
      if (state.id !== id) throw new Error('Engine response belongs to a different saved session; it was not applied.');
      if (!ownership.adopt(context.ticket, id)) return undefined;
      setApiOnline(true); applySession(state);
      await refreshHistory(id, context, 'Session resumed', true);
      return state;
    }, true);
  };

  const run = (manualContinue = false) => {
    const current = sessionRef.current;
    return current && execute('Run experiment', async (context) => {
      if (!requireAcquisition(context, current.id)) return undefined;
      const experiment = manualContinue ? current.recommendation.experiment : undefined;
      const result = await argusApi.runExperiment(current.id, experiment);
      if (!commitState(context, result.state)) return undefined;
      setMeasurement(result.measurement);
      await refreshHistory(current.id, context, 'Measurement recorded'); return result;
    });
  };

  const upload = (file: Blob) => {
    const current = sessionRef.current;
    return current && execute('Analyze WAV', async (context) => {
      if (!requireAcquisition(context, current.id)) return undefined;
      const result = await argusApi.uploadWav(current.id, file, current.recommendation.experiment);
      if (!commitState(context, result.state)) return undefined;
      setMeasurement(result.measurement);
      await refreshHistory(current.id, context, 'Measurement recorded'); return result;
    });
  };

  const capture = () => {
    const current = sessionRef.current;
    return current && execute('Capture microphone', async (context) => {
      if (!requireAcquisition(context, current.id)) return undefined;
      const wav = await recordMicrophone(220);
      if (!requireAcquisition(context, current.id)) return undefined;
      const result = await argusApi.uploadWav(current.id, wav, current.recommendation.experiment);
      if (!commitState(context, result.state)) return undefined;
      setMeasurement(result.measurement);
      await refreshHistory(current.id, context, 'Measurement recorded'); return result;
    });
  };

  const acquireDevice = (device: 'serial_probe' | 'microphone', timingCalibration?: ProbeTimingCalibration) => {
    const current = sessionRef.current;
    return current && execute(device === 'serial_probe' ? 'Acquire serial probe' : 'Acquire microphone', async (context) => {
      if (!requireAcquisition(context, current.id)) return undefined;
      if (device === 'serial_probe' && !timingCalibration) throw new Error('Load a device-specific operator timing/drive calibration record before serial acquisition.');
      const connection = await argusApi.connectDevice(device, timingCalibration);
      if (!requireAcquisition(context, current.id)) return undefined;
      if (!connection.connected) throw new Error(connection.last_error || `${device} could not connect`);
      if (device === 'serial_probe' && !connection.arrival_likelihood_supported) throw new Error('This probe has no supported v2 frame and operator timing/drive calibration.');
      const result = await argusApi.acquireDevice(current.id, device, current.recommendation.experiment);
      if (!commitState(context, result.state)) return undefined;
      setMeasurement(result.measurement);
      await refreshHistory(current.id, context, 'Measurement recorded'); return result;
    });
  };

  const reveal = () => {
    const current = sessionRef.current;
    return current && execute('Reveal simulation truth', async (context) => {
      const state = await argusApi.reveal(current.id); return commitState(context, state) ? state : undefined;
    });
  };

  const calibrate = () => {
    const current = sessionRef.current;
    return current && execute('Calibrate session', async (context) => {
      if (!requireAcquisition(context, current.id)) return undefined;
      await argusApi.calibrate(current.id);
      if (!context.current()) return undefined;
      try {
        const state = await argusApi.getSession(current.id); return commitState(context, state) ? state : undefined;
      } catch (reason) { context.partial(`Calibration acknowledged; state could not refresh: ${readableError(reason)}`); return undefined; }
    });
  };

  const loadBenchmarks = () => execute('Load benchmarks', async (context) => {
    const result = await argusApi.benchmarks(); if (context.current()) setBenchmarks(result); return result;
  });

  const setNoGoRegions = (regions: SessionState['no_go_regions']) => {
    const current = sessionRef.current;
    return current && execute('Update placement exclusions', async (context) => {
      const state = await argusApi.updateNoGoRegions(current.id, regions); return commitState(context, state) ? state : undefined;
    });
  };

  const emergencyStop = async (reason: string) => {
    const current = sessionRef.current;
    if (!current) return undefined;
    const ticket = ownership.beginSafety('stop', 'Acknowledge emergency stop');
    if (!ticket) return undefined;
    publishOperation(runningOperation(ticket)); setBusy(ownership.isBusy); setError(null); setWarning(null);
    try {
      const state = await argusApi.emergencyStop(current.id, reason);
      if (!ownership.acknowledgeSafety(ticket, state.id, state.safety.emergency_stop)) {
        if (ownership.ownsSafety(ticket)) throw new Error('Engine safety acknowledgment is older than the displayed safety state. Refresh the session before proceeding.');
        return undefined;
      }
      applySession(state);
      if (operationRef.current?.id === ticket.id) publishOperation({ ...runningOperation(ticket),
        status: 'succeeded', finishedAt: Date.now(), detail: 'Engine acknowledged the emergency stop.' });
      return ownership.ownsSafety(ticket) ? state : undefined;
    } catch (reason) {
      if (ownership.ownsSafety(ticket)) {
        const detail = readableError(reason);
        setError(detail); publishOperation({ ...runningOperation(ticket), status: 'failed', finishedAt: Date.now(), detail });
      }
      return undefined;
    } finally {
      ownership.finishSafety(ticket);
      if (ownership.isMounted) setBusy(ownership.isBusy);
    }
  };

  const releaseEmergencyStop = (reason: string) => {
    const current = sessionRef.current;
    return current && execute('Release emergency stop', async (context) => {
      const ticket = ownership.beginSafety('release', 'Release emergency stop');
      if (!ticket) return undefined;
      try {
        const state = await argusApi.releaseEmergencyStop(current.id, reason);
        if (!context.current()) return undefined;
        if (!ownership.acknowledgeSafety(ticket, state.id, state.safety.emergency_stop)) {
          if (ownership.ownsSafety(ticket)) throw new Error('Engine safety acknowledgment is older than the displayed safety state. Refresh the session before proceeding.');
          return undefined;
        }
        applySession(state); return state;
      } finally { ownership.finishSafety(ticket); }
    });
  };

  const refreshSession = () => {
    const current = sessionRef.current;
    return current && execute('Refresh session', async (context) => {
      const state = await argusApi.getSession(current.id);
      if (!commitState(context, state)) return undefined;
      await refreshHistory(current.id, context, 'Session state refreshed', true); return state;
    });
  };

  const reset = () => {
    const pending = ownership.isBusy;
    ownership.reset(); applySession(null); setMeasurement(null); setHistory([]); setError(null);
    setWarning(pending ? 'Earlier requests may still finish on the engine; their results will not replace this workspace.' : null);
    publishOperation(null); setBusy(false);
  };

  return { session, measurement, history, benchmarks, busy, operation, error, warning, apiOnline, authenticationRequired,
    lastSessionId, create, resume, run, upload, capture, acquireDevice, reveal, calibrate, loadBenchmarks,
    setNoGoRegions, emergencyStop, releaseEmergencyStop, refreshSession, reset };
}
