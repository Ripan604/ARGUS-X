'use client';

import { useCallback, useEffect, useState } from 'react';
import { argusApi } from '@/services/api';
import type { ResearchJob } from '@/types/argus';

export function ResearchLab() {
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(() => argusApi.jobs().then((result) => setJobs(result.jobs)).catch((reason) => setError(reason instanceof Error ? reason.message : String(reason))), []);
  useEffect(() => { refresh(); const timer = window.setInterval(refresh, 1500); return () => window.clearInterval(timer); }, [refresh]);
  const start = async (type: ResearchJob['job_type'], overrides: Record<string, unknown> = {}) => {
    setError(null);
    try {
      const parameters = type === 'calibration' ? { mode: 'quick', seed: 200 } : type === 'dataset_generation' ? { scale: 'tiny', seed: 71 } : type === 'surrogate_training' ? { samples: 240, query_count: 24, seed: 431 } : { cases: 2, max_experiments: 5, seed: 100 };
      await argusApi.startJob(type, { ...parameters, ...overrides }); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };
  return <section className="secondary-page research-page"><div className="secondary-header"><div><p className="eyebrow">REPRODUCIBLE LOCAL SCIENCE</p><h1>Research and failure lab.</h1></div><span className="secondary-kpi">CPU-FIRST · SEALED TRUTHS · NO PAID SERVICE</span></div>
    <div className="research-actions"><button onClick={() => start('benchmark')}>RUN QUICK BENCHMARK MATRIX<small>Nine planners · paired scenarios</small></button><button onClick={() => start('calibration')}>RUN CALIBRATION CHECK<small>Coverage · rank · reliability</small></button><button onClick={() => start('ablation')}>RUN MECHANISM ABLATION<small>Seven controlled removals</small></button><button onClick={() => start('dataset_generation')}>GENERATE TINY RESPONSE BANK<small>Chunked · resumable · sealed truth</small></button><button onClick={() => start('surrogate_training')}>ACTIVE-LEARN SURROGATE<small>Ensemble disagreement · sealed physics oracle</small></button><button onClick={() => start('demo_scenario', { scenario: 'rival_hypotheses', seed: 17 })}>DEMO · RIVAL HYPOTHESES<small>Legitimate deterministic simulator trace</small></button><button onClick={() => start('demo_scenario', { scenario: 'model_mismatch', seed: 17 })}>DEMO · MODEL MISMATCH<small>NEO versus naive paired ablation</small></button><button onClick={() => start('demo_scenario', { scenario: 'measurement_compression', cases: 4, seed: 100 })}>DEMO · COMPRESSION<small>Paired seeds · shared stopping criterion</small></button></div>
    {error && <p className="error-banner">{error}</p>}
    <div className="job-table"><div><b>JOB</b><b>STATE</b><b>PROGRESS</b><b>RESULT</b></div>{jobs.length === 0 && <p className="empty-copy">No local research jobs have been submitted.</p>}{jobs.map((job) => <article key={job.id}><span><b>{job.job_type.replaceAll('_', ' ').toUpperCase()}</b><small>{job.id}</small></span><strong className={`job-${job.status}`}>{job.status.toUpperCase()}</strong><span><i><em style={{ width: `${Math.round(job.progress * 100)}%` }} /></i><small>{Math.round(job.progress * 100)}%</small></span><span>{job.error ? <small className="danger-copy">{job.error}</small> : job.result ? <details><summary>OPEN RESULT</summary><pre>{JSON.stringify(job.result, null, 2).slice(0, 12000)}</pre></details> : <small>Awaiting result</small>}</span></article>)}</div>
    <p className="research-disclaimer">All built-in studies are explicitly labeled simulated. The failure explorer preserves unsuccessful, overconfident and abstained runs; no result is hard-coded or presented as physical validation.</p>
  </section>;
}
