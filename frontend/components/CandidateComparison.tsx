'use client';

import { useId, useState } from 'react';
import type { CandidateScore, ExperimentParameters, SessionState } from '@/types/argus';
import { candidatePanelGeometry, candidateScoreGeometry, sameCandidateExperiment } from './candidateGeometry';
import './candidate-comparison.css';

const number = (value: number, digits = 3) => Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
const waveformName = (value: string) => value.replaceAll('_', ' ');

function RoutePreview({ experiment, widthMm, heightMm, detailed = false }: {
  experiment: ExperimentParameters; widthMm: number; heightMm: number; detailed?: boolean;
}) {
  const id = useId().replaceAll(':', '');
  const width = detailed ? 430 : 230;
  const height = detailed ? 236 : 104;
  const panel = candidatePanelGeometry(widthMm, heightMm, width, height, detailed ? 40 : 16);
  if (!panel) return <span className="candidate-route-unavailable">Panel dimensions unavailable</span>;
  const sx = panel.x + experiment.source_x * panel.width;
  const sy = panel.y + experiment.source_y * panel.height;
  const rx = panel.x + experiment.receiver_x * panel.width;
  const ry = panel.y + experiment.receiver_y * panel.height;
  const description = `Transmitter at ${number(experiment.source_x * widthMm, 1)}, ${number(experiment.source_y * heightMm, 1)} millimetres; receiver at ${number(experiment.receiver_x * widthMm, 1)}, ${number(experiment.receiver_y * heightMm, 1)} millimetres.`;
  return <svg className={`candidate-route${detailed ? ' is-detailed' : ''}`} viewBox={`0 0 ${width} ${height}`} role={detailed ? 'img' : undefined} aria-label={detailed ? description : undefined} aria-hidden={detailed ? undefined : true}>
    <defs><linearGradient id={`${id}-route`}><stop stopColor="#9fe1f1"/><stop offset="1" stopColor="#e8b989"/></linearGradient></defs>
    <rect x={panel.x} y={panel.y} width={panel.width} height={panel.height} rx="2" fill="#122639" stroke="#5d819a" strokeWidth=".7"/>
    {[.25, .5, .75].map((ratio) => <g key={ratio} stroke="#86a8be" strokeOpacity=".13" strokeWidth=".5"><path d={`M ${panel.x + panel.width * ratio} ${panel.y} v ${panel.height}`}/><path d={`M ${panel.x} ${panel.y + panel.height * ratio} h ${panel.width}`}/></g>)}
    <path d={`M ${sx} ${sy} L ${rx} ${ry}`} stroke={`url(#${id}-route)`} strokeWidth={detailed ? 2 : 1.4} strokeDasharray="4 3"/>
    <circle cx={sx} cy={sy} r={detailed ? 10 : 6} fill="#9fe1f1" fillOpacity=".11"/>
    <circle cx={sx} cy={sy} r={detailed ? 4 : 2.8} fill="#a9e5f1" stroke="#112131" strokeWidth="1"/>
    <circle cx={rx} cy={ry} r={detailed ? 10 : 6} fill="#e8b989" fillOpacity=".11"/>
    <rect x={rx - (detailed ? 3.5 : 2.3)} y={ry - (detailed ? 3.5 : 2.3)} width={detailed ? 7 : 4.6} height={detailed ? 7 : 4.6} fill="#e8b989" stroke="#112131" strokeWidth="1"/>
    {detailed && <g fontFamily="monospace" fontSize="9" fill="#aac1d1">
      <text x={panel.x} y={panel.y - 13}>ORIGIN (0, 0)</text>
      <text x={panel.x + panel.width / 2} y={panel.y + panel.height + 24} textAnchor="middle">X · {number(widthMm, 0)} mm →</text>
      <text transform={`translate(${panel.x - 19},${panel.y + panel.height / 2}) rotate(-90)`} textAnchor="middle">Y · {number(heightMm, 0)} mm</text>
      <text x={sx + (experiment.source_x > .7 ? -12 : 12)} y={sy - 9} textAnchor={experiment.source_x > .7 ? 'end' : 'start'} fill="#bde9f5">TX</text>
      <text x={rx + (experiment.receiver_x > .7 ? -12 : 12)} y={ry + 18} textAnchor={experiment.receiver_x > .7 ? 'end' : 'start'} fill="#f4cfa7">RX</text>
    </g>}
  </svg>;
}

function MetricBar({ label, value, values }: { label: string; value: number; values: number[] }) {
  const geometry = candidateScoreGeometry(value, values);
  return <div className="candidate-metric"><div><span>{label}</span><b>{number(value)}</b></div><span className="candidate-metric-track" aria-hidden="true"><i className={geometry.negative ? 'is-negative' : undefined} style={{ left: `${geometry.left}%`, width: `${geometry.width}%` }}/><em style={{ left: `${geometry.zero}%` }}/></span></div>;
}

function AuditDetails({ candidate }: { candidate: CandidateScore }) {
  const values: Array<[string, number | undefined | null]> = [
    ['Uncertainty coverage', candidate.uncertainty_coverage], ['Repetition penalty', candidate.repetition_penalty],
    ['Expected risk reduction', candidate.expected_risk_reduction], ['Calibration value', candidate.calibration_value],
    ['Model trust', candidate.model_trust], ['Time cost', candidate.time_cost], ['Energy cost', candidate.energy_cost],
    ['Predicted uncertainty after', candidate.predicted_uncertainty_after], ['Waveform utility', candidate.waveform_utility],
    ['Baseline guard utility', candidate.baseline_guard_utility], ['Nuisance information (bits)', candidate.nuisance_information_bits],
    ['Nuisance penalty (bits)', candidate.nuisance_penalty_bits],
  ];
  return <details className="candidate-audit-details"><summary>Inspect planner terms</summary><dl>{values.filter(([, value]) => value != null).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{number(value!)}</dd></div>)}</dl>{candidate.chosen_model_fidelity != null && <p>Model fidelity: {number(candidate.chosen_model_fidelity, 0)}{candidate.reason_for_fidelity ? ` · ${candidate.reason_for_fidelity}` : ''}</p>}</details>;
}

export function CandidateComparison({ session }: { session: SessionState }) {
  const candidates = session.recommendation.top_candidates;
  const recommendationIndex = candidates.findIndex((candidate) => sameCandidateExperiment(candidate.experiment, session.recommendation.experiment));
  const candidateSet = `${session.id}:${session.status.experiment_count}:${JSON.stringify(candidates.map((candidate) => candidate.experiment))}`;
  const [preview, setPreview] = useState<{ set: string; index: number } | null>(null);
  const selectedIndex = preview?.set === candidateSet && preview.index < candidates.length ? preview.index : Math.max(0, recommendationIndex);
  const selected = candidates[selectedIndex];
  const widthMm = session.panel.width_m * 1000;
  const heightMm = session.panel.height_m * 1000;
  const detailId = useId();
  const experiment = selected?.experiment;
  const scores = candidates.map((candidate) => candidate.final_score);
  return <section className="candidate-comparison" aria-label="Candidate experiment comparison">
    <div className="candidate-comparison-heading"><div><p className="eyebrow">Planner audit</p><h2>Compare the next experiment</h2><p>Inspect the geometry and tradeoffs behind each proposed measurement.</p></div><span>{candidates.length} CANDIDATES<br/><b>Engine recommendation marked explicitly</b></span></div>
    {candidates.length === 0 ? <p className="candidate-empty">No candidate audit is available for this recommendation.</p> : <>
      <div className="candidate-card-grid">{candidates.map((candidate, index) => {
        const recommended = sameCandidateExperiment(candidate.experiment, session.recommendation.experiment);
        const geometry = candidateScoreGeometry(candidate.final_score, scores);
        return <button type="button" key={index} className={`candidate-choice${recommended ? ' is-recommended' : ''}`} aria-pressed={index === selectedIndex} aria-controls={detailId} aria-label={`Preview candidate ${index + 1}, ${waveformName(candidate.experiment.waveform)}, score ${number(candidate.final_score)}${recommended ? ', engine recommendation' : ''}`} onClick={() => setPreview({ set: candidateSet, index })}>
          <span className="candidate-choice-top"><b>{String(index + 1).padStart(2, '0')}</b><span>{recommended ? 'RECOMMENDED' : 'ALTERNATIVE'}</span><i aria-hidden="true">↗</i></span>
          <RoutePreview experiment={candidate.experiment} widthMm={widthMm} heightMm={heightMm}/>
          <span className="candidate-waveform">{waveformName(candidate.experiment.waveform)}</span>
          <span className="candidate-frequency">{number(candidate.experiment.frequency_start_hz / 1000, 1)}–{number(candidate.experiment.frequency_end_hz / 1000, 1)} kHz</span>
          <span className="candidate-choice-score"><small>Planner score</small><strong>{number(candidate.final_score)}</strong></span>
          <span className="candidate-metric-track" aria-hidden="true"><i className={geometry.negative ? 'is-negative' : undefined} style={{ left: `${geometry.left}%`, width: `${geometry.width}%` }}/><em style={{ left: `${geometry.zero}%` }}/></span>
          <span className="candidate-choice-bottom">{index === selectedIndex ? 'Viewing details' : 'Inspect candidate'} <span aria-hidden="true">{index === selectedIndex ? '●' : '+'}</span></span>
        </button>;
      })}</div>
      {recommendationIndex < 0 && <p className="candidate-unlisted">The current engine recommendation is outside this candidate shortlist.</p>}
      {selected && experiment && <div id={detailId} className="candidate-inspector">
        <div className="candidate-inspector-heading"><p aria-live="polite">Previewing candidate <strong>{String(selectedIndex + 1).padStart(2, '0')}</strong>{selectedIndex === recommendationIndex && <span>Engine recommendation</span>}</p><span>Preview only; execution uses the engine recommendation.</span></div>
        <div className="candidate-inspector-body"><figure><RoutePreview experiment={experiment} widthMm={widthMm} heightMm={heightMm} detailed/><figcaption><span><i/> Transmitter</span><span><i/> Receiver</span><span>{number(Math.hypot((experiment.receiver_x - experiment.source_x) * widthMm, (experiment.receiver_y - experiment.source_y) * heightMm), 1)} mm path</span></figcaption></figure>
          <div className="candidate-inspector-specs"><dl className="candidate-parameter-grid">
            <div><dt>Source X / Y</dt><dd>{number(experiment.source_x * widthMm, 1)} / {number(experiment.source_y * heightMm, 1)} <em>mm</em></dd></div>
            <div><dt>Receiver X / Y</dt><dd>{number(experiment.receiver_x * widthMm, 1)} / {number(experiment.receiver_y * heightMm, 1)} <em>mm</em></dd></div>
            <div><dt>Waveform</dt><dd>{waveformName(experiment.waveform)}</dd></div>
            <div><dt>Frequency range</dt><dd>{number(experiment.frequency_start_hz / 1000, 2)}–{number(experiment.frequency_end_hz / 1000, 2)} <em>kHz</em></dd></div>
            <div><dt>Amplitude</dt><dd>{number(experiment.amplitude)} <em>engine units</em></dd></div>
            <div><dt>Duration</dt><dd>{number(experiment.duration_s * 1000, 2)} <em>ms</em></dd></div>
            {experiment.sample_rate_hz != null && <div><dt>Sample rate</dt><dd>{number(experiment.sample_rate_hz / 1000, 1)} <em>kHz</em></dd></div>}
            {experiment.code_length != null && <div><dt>Code length</dt><dd>{experiment.code_length}</dd></div>}
            {experiment.phase_code && <div><dt>Phase code</dt><dd>{experiment.phase_code}</dd></div>}
            {!!experiment.spectral_notches_hz?.length && <div><dt>Spectral notches</dt><dd>{experiment.spectral_notches_hz.map(([start, end]) => `${number(start / 1000, 1)}–${number(end / 1000, 1)}`).join(', ')} <em>kHz</em></dd></div>}
          </dl><div className="candidate-comparative-metrics"><MetricBar label="Information proxy" value={selected.expected_information_gain} values={candidates.map((candidate) => candidate.expected_information_gain)}/><MetricBar label="Hypothesis disagreement" value={selected.hypothesis_disagreement} values={candidates.map((candidate) => candidate.hypothesis_disagreement)}/><MetricBar label="Experiment cost" value={selected.experiment_cost} values={candidates.map((candidate) => candidate.experiment_cost)}/></div></div>
        </div><AuditDetails candidate={selected}/>
      </div>}
      <p className="candidate-comparison-note">Bars compare the displayed candidates on a shared zero-inclusive axis for each metric. Planner scores and information proxies are internal utilities, not calibrated success probabilities. Straight lines show source–receiver geometry, not a simulated wave path.</p>
    </>}
  </section>;
}
