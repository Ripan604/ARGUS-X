'use client';

import type { CandidateScore, SessionState } from '@/types/argus';
import { percent, responseDelayMilliseconds, typedValue } from '@/utils/neo';

function Meter({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const width = Math.max(2, Math.min(100, value * 100));
  const tone = inverse ? (value > 0.7 ? 'danger' : value > 0.45 ? 'warn' : 'good') : (value > 0.7 ? 'good' : value > 0.4 ? 'warn' : 'danger');
  return <div className="neo-meter"><div><span>{label}</span><b>{percent(value, 1)}</b></div><i><em className={tone} style={{ width: `${width}%` }} /></i></div>;
}

function Candidate({ item, rank }: { item: CandidateScore; rank: number }) {
  return <div className="brain-candidate"><b>{String(rank).padStart(2, '0')}</b><span>{item.experiment.waveform.replaceAll('_', ' ').toUpperCase()}<small>{(item.experiment.frequency_start_hz / 1000).toFixed(1)}–{(item.experiment.frequency_end_hz / 1000).toFixed(1)} kHz</small></span><span>ΔH {item.expected_information_gain.toFixed(3)}<small>RISK ↓ {(item.expected_risk_reduction ?? 0).toFixed(3)}</small></span><strong>{item.final_score.toFixed(3)}</strong></div>;
}

export function ArgusBrain({ session }: { session: SessionState }) {
  const status = session.status;
  const recommendation = session.recommendation;
  const explanation = recommendation.structured_explanation ?? {};
  const counterfactual = explanation.counterfactual as Record<string, unknown> | undefined;
  const predictions = Array.isArray(counterfactual?.predictions) ? counterfactual.predictions as Array<Record<string, unknown>> : [];
  const metrology = session.uncertainty?.metrology ?? {};
  const dominant = typeof metrology.dominant_component === 'string' ? metrology.dominant_component : 'not yet resolved';
  return <section className="brain-page">
    <div className={`ood-banner ${status.ood_status.toLowerCase()}`}><span>MODEL DOMAIN</span><strong>{status.ood_status.replaceAll('_', ' ')}</strong><p>{status.ood_status === 'NOMINAL' ? 'Current residuals remain inside the empirical model envelope.' : 'A confident defect conclusion is restricted until calibration or verification reduces this mismatch.'}</p></div>
    <div className="brain-title"><div><p className="eyebrow">ARGUS NEO · JOINT INFERENCE</p><h1>See the experiment decision form.</h1></div><div className={`action-token ${recommendation.action_type}`}><small>CURRENT CONTROL MODE</small><strong>{recommendation.action_type.toUpperCase()}</strong><span>{recommendation.objective.replaceAll('_', ' ')}</span></div></div>
    <div className="brain-grid">
      <article className="brain-card"><p className="eyebrow">UNCERTAINTY SPLIT</p><h2>Structure versus instrument</h2><Meter label="STRUCTURAL UNCERTAINTY" value={status.structural_uncertainty} inverse /><Meter label="METROLOGY UNCERTAINTY" value={status.metrology_uncertainty} inverse /><Meter label="MODEL TRUST" value={status.model_trust} /><Meter label="DECISION CONFIDENCE" value={status.decision_confidence} /><p className="brain-note">Dominant metrology term: <b>{dominant.replaceAll('_', ' ')}</b>. These are posterior and proxy quantities, not certified probabilities of structural safety.</p></article>
      <article className="brain-card"><p className="eyebrow">RIVAL HYPOTHESES</p><h2>What the structure might contain</h2><div className="hypothesis-stack">{status.top_hypotheses.slice(0, 5).map((item) => <div key={item.rank}><b>{item.rank}</b><span>X {item.x.toFixed(3)} · Y {item.y.toFixed(3)}<small>{item.dominant_type.replaceAll('_', ' ')} · severity {item.severity_mean.toFixed(2)}</small></span><strong>{(item.probability * 100).toFixed(2)}%</strong></div>)}</div></article>
      <article className="brain-card wide"><p className="eyebrow">WHY THIS EXPERIMENT?</p><h2>{recommendation.explanation}</h2><div className="utility-grid"><span><small>EXPECTED INFORMATION</small><b>{recommendation.expected_information_gain.toFixed(3)}</b></span><span><small>HYPOTHESIS SEPARATION</small><b>{recommendation.hypothesis_disagreement.toFixed(3)}</b></span><span><small>RISK REDUCTION</small><b>{typedValue(explanation, 'expected_risk_reduction').toFixed(3)}</b></span><span><small>PHYSICAL COST</small><b>{recommendation.experiment_cost.toFixed(3)}</b></span><span><small>CALIBRATION VALUE</small><b>{typedValue(explanation, 'calibration_value').toFixed(3)}</b></span><span><small>FIDELITY / HORIZON</small><b>L{recommendation.chosen_model_fidelity} / H{recommendation.planning_horizon}</b></span></div><details open><summary>STRUCTURED RATIONALE</summary><pre>{JSON.stringify({ primary_reason: explanation.primary_reason, reason_for_fidelity: recommendation.reason_for_fidelity, uncertainty_before: explanation.uncertainty_before, predicted_uncertainty_after: explanation.predicted_uncertainty_after }, null, 2)}</pre></details></article>
      <article className="brain-card"><p className="eyebrow">COUNTERFACTUAL RESPONSES</p><h2>Predicted under each explanation</h2>{predictions.length ? <div className="prediction-stack">{predictions.slice(0, 5).map((item, index) => { const prediction = item.prediction as Record<string, unknown>; const delay = responseDelayMilliseconds(prediction); return <div key={index}><b>H{index + 1}</b><span>Predicted delay<small>{delay === null ? '—' : `${delay.toFixed(3)} ms`}</small></span><strong>{typeof item.probability === 'number' ? percent(item.probability, 1) : '—'}</strong></div>; })}</div> : <p className="empty-copy">Calibration actions estimate the inspection system; structural response rivalry is intentionally not used as their primary value.</p>}<p className="brain-note">Combined separation: <b>{typedValue(counterfactual, 'combined_separation').toFixed(3)}</b> near {(session.recommendation.experiment.frequency_start_hz + session.recommendation.experiment.frequency_end_hz) / 2000} kHz.</p></article>
      <article className="brain-card"><p className="eyebrow">NEXT-BEST ACTIONS</p><h2>Auditable alternatives</h2><div className="brain-candidates">{recommendation.top_candidates.map((item, index) => <Candidate key={index} item={item} rank={index + 1} />)}</div></article>
    </div>
  </section>;
}

