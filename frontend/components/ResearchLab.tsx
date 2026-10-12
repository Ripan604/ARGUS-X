'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { argusApi } from '@/services/api';
import type { ResearchJob } from '@/types/argus';
import { ResearchEvidence } from '@/components/ResearchEvidence';

export function ResearchLab() {
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const mounted = useRef(false), mutating = useRef(false), activeJobs = useRef(false);
  const request = useRef<AbortController | null>(null);
  const refresh = useCallback(async (freshAfterMutation = false) => {
    if (!mounted.current || document.hidden) return;
    if (request.current && !request.current.signal.aborted && !freshAfterMutation) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    try {
      const result = await argusApi.jobs(controller.signal);
      if (mounted.current && request.current === controller && !controller.signal.aborted) {
        setJobs(result.jobs); setError(null);
        activeJobs.current = result.jobs.some(job => job.status === 'running' || job.status === 'queued');
      }
    } catch (reason) {
      if (mounted.current && request.current === controller && !controller.signal.aborted) setError(reason instanceof Error ? reason.message : String(reason));
    } finally { window.clearTimeout(timeout); if (request.current === controller) request.current = null; }
  }, []);
  useEffect(() => {
    mounted.current = true;
    let generation = 0, timer: number | undefined;
    const poll = async (version: number) => {
      await refresh();
      if (mounted.current && !document.hidden && version === generation) timer = window.setTimeout(() => { void poll(version); }, activeJobs.current ? 1500 : 10000);
    };
    const visibility = () => {
      generation++; window.clearTimeout(timer); request.current?.abort();
      if (!document.hidden) void poll(generation);
    };
    visibility(); document.addEventListener('visibilitychange', visibility);
    return () => { mounted.current = false; generation++; window.clearTimeout(timer); request.current?.abort(); document.removeEventListener('visibilitychange', visibility); };
  }, [refresh]);
  const start = async (type: ResearchJob['job_type'], overrides: Record<string, unknown> = {}) => {
    if (mutating.current) return;
    mutating.current = true;
    setError(null); setBusy(true);
    try {
      const parameters = type === 'calibration'
        ? { mode: 'quick', seed: 200 }
        : type === 'dataset_generation'
          ? { scale: 'tiny', seed: 71 }
          : type === 'surrogate_training'
            ? { samples: 240, query_count: 24, seed: 431 }
            : type === 'ablation'
              ? { cases: 2, seed: 300 }
              : type === 'demo_scenario'
                ? { cases: 4, seed: 17 }
              : { cases: 2, max_experiments: 5, seed: 100 };
      await argusApi.startJob(type, { ...parameters, ...overrides }); await refresh(true);
    } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { mutating.current = false; if (mounted.current) setBusy(false); }
  };
  const cancel = async (id: string) => {
    if (mutating.current) return;
    mutating.current = true;
    setBusy(true); setError(null);
    try { await argusApi.cancelJob(id); await refresh(true); }
    catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { mutating.current = false; if (mounted.current) setBusy(false); }
  };
  return <section className="secondary-page research-page"><div className="secondary-header"><div><p className="eyebrow">REPRODUCIBLE LOCAL SCIENCE</p><h1>Research and failure lab.</h1></div><span className="secondary-kpi">CPU-FIRST · SEALED TRUTHS · NO PAID SERVICE</span></div>
    <ResearchEvidence />
    <div className="research-actions"><button disabled={busy} onClick={() => start('benchmark')}>RUN QUICK BENCHMARK MATRIX<small>Nine planners · paired scenarios</small></button><button disabled={busy} onClick={() => start('calibration')}>RUN CALIBRATION CHECK<small>Coverage · rank · reliability</small></button><button disabled={busy} onClick={() => start('ablation')}>RUN MECHANISM ABLATION<small>Seven controlled removals</small></button><button disabled={busy} onClick={() => start('dataset_generation')}>GENERATE TINY RESPONSE BANK<small>Chunked · resumable · sealed truth</small></button><button disabled={busy} onClick={() => start('surrogate_training')}>ACTIVE-LEARN SURROGATE<small>Ensemble disagreement · sealed physics oracle</small></button><button disabled={busy} onClick={() => start('demo_scenario', { scenario: 'rival_hypotheses', seed: 17 })}>DEMO · RIVAL HYPOTHESES<small>Legitimate deterministic simulator trace</small></button><button disabled={busy} onClick={() => start('demo_scenario', { scenario: 'model_mismatch', seed: 17 })}>DEMO · MODEL MISMATCH<small>NEO versus naive paired ablation</small></button><button disabled={busy} onClick={() => start('demo_scenario', { scenario: 'measurement_compression', cases: 4, seed: 100 })}>DEMO · COMPRESSION<small>Paired seeds · shared stopping criterion</small></button></div>
    {error && <p className="error-banner">{error}</p>}
    <div className="job-table"><div><b>JOB</b><b>STATE</b><b>PROGRESS</b><b>RESULT</b></div>{jobs.length === 0 && <p className="empty-copy">No local research jobs have been submitted.</p>}{jobs.map((job) => <article key={job.id}><span><b>{job.job_type.replaceAll('_', ' ').toUpperCase()}</b><small>{job.id}</small></span><strong className={`job-${job.status}`}>{job.status.toUpperCase()}{(['queued', 'running'] as const).includes(job.status as 'queued' | 'running') && <button disabled={busy || job.cancellation_requested} onClick={() => cancel(job.id)}>{job.cancellation_requested ? 'CANCELLING' : 'CANCEL'}</button>}</strong><span><i><em style={{ width: `${Math.round(job.progress * 100)}%` }} /></i><small>{Math.round(job.progress * 100)}%</small></span><span>{job.error ? <small className="danger-copy">{job.error}</small> : job.result ? <details><summary>OPEN RESULT</summary><pre>{JSON.stringify(job.result, null, 2).slice(0, 12000)}</pre></details> : <small>Awaiting result</small>}</span></article>)}</div>
    <p className="research-disclaimer">All built-in studies are explicitly labeled simulated. The failure explorer preserves unsuccessful, overconfident and abstained runs; no result is hard-coded or presented as physical validation.</p>
  </section>;
}
