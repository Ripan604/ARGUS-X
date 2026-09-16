'use client';

import { useEffect, useState } from 'react';

type Variant = 'legacy_proxy' | 'nuisance_aware';
type Context = 'nominal' | 'mismatch_noise';
interface Result {
  completed: number;
  execution_failures: number;
  localization_error_mm: { mean: number; median: number; p90: number };
  success_20mm_rate: number;
  failure_30mm_rate: number;
}
interface Report {
  schema_version: number;
  evidence_source: string;
  artifact: string;
  artifact_sha256: string;
  command: string;
  seeds: number[];
  steps: number;
  candidate_count: number;
  summary: Record<Context, Record<Variant, Result>>;
  paired_comparisons: Record<Context, {
    complete_pairs: number;
    mean_error_advantage_mm: number;
    bootstrap_95ci_mm: [number, number];
    win_rate: number;
    loss_rate: number;
    tie_rate: number;
  }>;
}

export function ResearchEvidence() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/research/nuisance-design-summary.json', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('The published research report could not be loaded.');
        const data = await response.json() as Report;
        if (data.schema_version !== 1 || data.evidence_source !== 'synthetic_only'
          || !data.summary?.nominal?.nuisance_aware || !data.paired_comparisons?.mismatch_noise) {
          throw new Error('The published research report has an unsupported format.');
        }
        if (!controller.signal.aborted) setReport(data);
      })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Report unavailable.'); });
    return () => controller.abort();
  }, []);
  return <section className="research-evidence" aria-labelledby="evidence-study-title">
    <div className="research-evidence-heading"><div><p className="eyebrow accent">MEASURED, NOT ASSUMED / SYNTHETIC ABLATION</p><h2 id="evidence-study-title">Let the evidence disagree.</h2></div><a className="text-link" href="/research/nuisance-design-summary.json" download>Download recorded results ↗</a></div>
    <p>Can uncertainty about the instrument change which measurement is worth taking? We compared the established planner with the experimental arrival-time information method using the same candidate opportunities and acquisition noise streams.</p>
    {error && <p className="error-banner" role="alert">{error}</p>}
    {!report && !error && <p role="status">Loading recorded study…</p>}
    {report && <>
      <div className="study-protocol"><span><b>{report.seeds.length}</b> held-out seeds per context</span><span><b>{report.steps}</b> acquisitions per run</span><span><b>{report.candidate_count}</b> shared candidate probes</span><span><b>{Object.values(report.summary).reduce((total, context) => total + Object.values(context).reduce((sum, result) => sum + result.completed, 0), 0)}</b> completed runs</span></div>
      <div className="study-contexts">{(['nominal', 'mismatch_noise'] as Context[]).map((context) => {
        const pair = report.paired_comparisons[context];
        const interval = pair.bootstrap_95ci_mm;
        return <article key={context} className="study-context"><p className="eyebrow">{context === 'nominal' ? '01 / NOMINAL MATERIAL' : '02 / MATERIAL + NOISE STRESS'}</p><h3>{context === 'nominal' ? 'Same model. Different questions.' : 'When assumptions drift.'}</h3><p>{context === 'nominal' ? 'Acquisition and inference start with the same material.' : 'Acquisition-only: velocity +2%, attenuation +4%, noise ×2.'}</p><table><caption>Localization error in millimetres. Lower is better.</caption><thead><tr><th scope="col">Method</th><th scope="col">Mean</th><th scope="col">Median</th><th scope="col">P90</th></tr></thead><tbody>{(['legacy_proxy', 'nuisance_aware'] as Variant[]).map((variant) => { const result = report.summary[context][variant]; return <tr key={variant}><th scope="row">{variant === 'legacy_proxy' ? 'Established' : 'Nuisance-aware'}</th><td>{result.localization_error_mm.mean.toFixed(2)}</td><td>{result.localization_error_mm.median.toFixed(2)}</td><td>{result.localization_error_mm.p90.toFixed(2)}</td></tr>; })}</tbody></table><div className="study-effect"><small>PAIRED MEAN ERROR REDUCTION</small><strong>{pair.mean_error_advantage_mm.toFixed(2)} <span>mm</span></strong><p>95% bootstrap interval: {interval[0].toFixed(2)} to {interval[1].toFixed(2)} mm.<br />{interval[0] <= 0 && interval[1] >= 0 ? 'Includes zero: no clear improvement established.' : 'Interval excludes zero in this synthetic study only.'}</p></div><p className="study-outcomes">{Math.round(pair.win_rate * pair.complete_pairs)} wins · {Math.round(pair.loss_rate * pair.complete_pairs)} losses · {Math.round(pair.tie_rate * pair.complete_pairs)} ties.<br />Errors above 30 mm: established {Math.round(report.summary[context].legacy_proxy.failure_30mm_rate * report.summary[context].legacy_proxy.completed)}/{report.summary[context].legacy_proxy.completed}; experimental {Math.round(report.summary[context].nuisance_aware.failure_30mm_rate * report.summary[context].nuisance_aware.completed)}/{report.summary[context].nuisance_aware.completed}. Execution failures: {report.summary[context].legacy_proxy.execution_failures + report.summary[context].nuisance_aware.execution_failures}.</p></article>;
      })}</div>
      <p className="study-conclusion">The new method supplies an auditable, nuisance-marginal information calculation. This study does not establish general accuracy superiority or close the simulation-to-reality gap. Both methods have substantial stress-test failures. The established planner remains the default.</p>
      <details className="study-reproduce"><summary>Reproduce this comparison</summary><code>{report.command}</code><p>Full traces: {report.artifact}. Publication hash:</p><code>{report.artifact_sha256}</code><p>Held-out seeds {report.seeds[0]}–{report.seeds.at(-1)}. Fixed measurement budget; not evidence of measurement compression. Bootstrap resampling is paired by seed, 10,000 samples.</p></details>
    </>}
  </section>;
}
