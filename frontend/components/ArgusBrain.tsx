'use client';

import type { CandidateScore, SessionState } from '@/types/argus';
import { percent, responseDelayMilliseconds, typedValue } from '@/utils/neo';
import { readNuisanceDesign } from '@/utils/researchDesign';

function Meter({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const width = Math.max(2, Math.min(100, value * 100));
  const tone = inverse ? (value > 0.7 ? 'danger' : value > 0.45 ? 'warn' : 'good') : (value > 0.7 ? 'good' : value > 0.4 ? 'warn' : 'danger');
  return <div className="neo-meter"><div><span>{label}</span><b>{percent(value, 1)}</b></div><i><em className={tone} style={{ width: `${width}%` }} /></i></div>;
}

function Candidate({ item, rank, researchEnabled, riskDesign }: { item: CandidateScore; rank: number; researchEnabled: boolean; riskDesign: boolean }) {
  return <div className="brain-candidate"><b>{String(rank).padStart(2, '0')}</b><span>{item.experiment.waveform.replaceAll('_', ' ').toUpperCase()}<small>{(item.experiment.frequency_start_hz / 1000).toFixed(1)}–{(item.experiment.frequency_end_hz / 1000).toFixed(1)} kHz</small></span><span>{riskDesign ? `NET VALUE ${(item.final_score * 1e6).toFixed(1)} mm²` : `UTILITY ${item.expected_information_gain.toFixed(3)}`}<small>{riskDesign ? `RISK REDUCTION ${((item.expected_risk_reduction ?? 0) * 1e6).toFixed(1)} mm²` : researchEnabled && typeof item.nuisance_information_bits === 'number' ? `MI ${item.nuisance_information_bits.toFixed(3)} bits` : `RISK ↓ ${(item.expected_risk_reduction ?? 0).toFixed(3)}`}</small></span><strong>{item.final_score.toFixed(3)}</strong></div>;
}

export function ArgusBrain({ session }: { session: SessionState }) {
  const status = session.status;
  const recommendation = session.recommendation;
  const explanation = recommendation.structured_explanation ?? {};
  const riskDesign = explanation.method === 'correlated_arrival_two_step_bayes_risk_v1';
  const nuisanceDesign = readNuisanceDesign(explanation.nuisance_design);
  const researchEnabled = typeof explanation.nuisance_design === 'object' && explanation.nuisance_design !== null
    && (explanation.nuisance_design as Record<string, unknown>).enabled === true;
  const counterfactual = explanation.counterfactual as Record<string, unknown> | undefined;
  const predictions = Array.isArray(counterfactual?.predictions) ? counterfactual.predictions as Array<Record<string, unknown>> : [];
  const metrology = session.uncertainty?.metrology ?? {};
  const dominant = typeof metrology.dominant_component === 'string' ? metrology.dominant_component : 'not yet resolved';
  return <section className="brain-page">
    <div className={`ood-banner ${status.ood_status.toLowerCase()}`}><span>MODEL DOMAIN</span><strong>{status.ood_status.replaceAll('_', ' ')}</strong><p>{status.ood_status === 'NOMINAL' ? 'Current residuals remain inside the empirical model envelope.' : 'A confident defect conclusion is restricted until calibration or verification reduces this mismatch.'}</p></div>
    <div className="brain-title"><div><p className="eyebrow">ARGUS NEO · JOINT INFERENCE</p><h1>See the experiment decision form.</h1></div><div className={`action-token ${recommendation.action_type}`}><small>CURRENT CONTROL MODE</small><strong>{recommendation.action_type.toUpperCase()}</strong><span>{recommendation.objective.replaceAll('_', ' ')}</span></div></div>
    <div className="brain-grid">
      {riskDesign && <article className="brain-card wide"><p className="eyebrow accent">CALIBRATION-AWARE RISK DESIGN · EXPERIMENTAL</p><h2>Which measurement reduces location error?</h2><p className="brain-note">The planner compares calibration and diagnosis using the same squared-distance loss. It branches over possible observations and shares propagation uncertainty between measurements. These are model predictions; physical accuracy is unvalidated.</p><div className="utility-grid">{[['CURRENT POSITION RISK', 'prior_risk_m2'], ['EXPECTED FINAL RISK', 'expected_terminal_risk_m2'], ['RISK + MEASUREMENT COST', 'expected_total_loss_m2'], ['NUMERICAL DIFFERENCE', 'maximum_quadrature_error_m2']].map(([label, key]) => <span key={key}><small>{label}</small><b>{(typedValue(explanation, key) * 1e6).toFixed(1)} <em>mm²</em></b></span>)}</div><p className="brain-note">{explanation.ranking_numerically_ambiguous ? 'Candidate ranking is within numerical uncertainty; no decisive winner is established.' : 'Candidate loss difference exceeds the observed quadrature difference.'}</p><details><summary>MODEL ASSUMPTIONS AND ALTERNATIVES</summary><pre>{JSON.stringify(explanation, null, 2)}</pre></details></article>}
      <article className="brain-card wide research-design-card">
        <p className="eyebrow accent">RESEARCH LENS · NUISANCE-AWARE EXPERIMENT DESIGN</p>
        <h2>What if the instrument is the uncertainty?</h2>
        <p className="brain-note">A useful probe must distinguish possible defect locations even when timing, wave speed, and placement are uncertain. The experimental planner predicts an arrival-time distribution for each spatial region and estimates how much observing it could teach us.</p>
        {nuisanceDesign ? <>
          <div className="utility-grid">
            <span><small>ARRIVAL-TIME INFORMATION</small><b>{nuisanceDesign.informationBits.toFixed(3)} <em>bits</em></b></span>
            <span><small>NUISANCE INFORMATION PENALTY</small><b>{nuisanceDesign.nuisancePenaltyBits.toFixed(3)} <em>bits</em></b></span>
            <span><small>QUADRATURE DIFFERENCE</small><b>{nuisanceDesign.quadratureErrorBits.toExponential(1)} <em>bits</em></b></span>
            <span><small>SPATIAL REGIONS</small><b>{nuisanceDesign.regionCount}</b></span>
            <span><small>POSTERIOR MASS REPRESENTED</small><b>{(nuisanceDesign.posteriorMass * 100).toFixed(1)}%</b></span>
            <span><small>REGION ENTROPY FRACTION</small><b>{(nuisanceDesign.normalizedInformation * 100).toFixed(1)}%</b></span>
          </div>
          <p className="brain-note">Bits apply to the approximate regional arrival-time model, not the entire waveform or observed entropy reduction. The quadrature difference is a numerical check, not an error guarantee. These values do not certify field accuracy.</p>
        </> : <p className="brain-note">{researchEnabled ? 'Research diagnostics are not available in a supported format for this recommendation.' : 'This recommendation uses the established planner or a calibration action. To compare, start a new session with “Nuisance-aware design” enabled. The established planner’s information utility is a proxy, not bits.'}</p>}
      </article>
      <article className="brain-card"><p className="eyebrow">UNCERTAINTY SPLIT</p><h2>Structure versus instrument</h2><Meter label="STRUCTURAL UNCERTAINTY" value={status.structural_uncertainty} inverse /><Meter label="METROLOGY UNCERTAINTY" value={status.metrology_uncertainty} inverse /><Meter label="MODEL TRUST" value={status.model_trust} /><Meter label="DECISION CONFIDENCE" value={status.decision_confidence} /><p className="brain-note">Dominant metrology term: <b>{dominant.replaceAll('_', ' ')}</b>. These are posterior and proxy quantities, not certified probabilities of structural safety.</p></article>
      <article className="brain-card"><p className="eyebrow">RIVAL HYPOTHESES</p><h2>What the structure might contain</h2><div className="hypothesis-stack">{status.top_hypotheses.slice(0, 5).map((item) => <div key={item.rank}><b>{item.rank}</b><span>X {item.x.toFixed(3)} · Y {item.y.toFixed(3)}<small>{item.dominant_type.replaceAll('_', ' ')} · severity {item.severity_mean.toFixed(2)}</small></span><strong>{(item.probability * 100).toFixed(2)}%</strong></div>)}</div></article>
      {!riskDesign && <article className="brain-card wide"><p className="eyebrow">WHY THIS EXPERIMENT?</p><h2>{recommendation.explanation}</h2><div className="utility-grid"><span><small>EXPECTED INFORMATION</small><b>{recommendation.expected_information_gain.toFixed(3)}</b></span><span><small>HYPOTHESIS SEPARATION</small><b>{recommendation.hypothesis_disagreement.toFixed(3)}</b></span><span><small>RISK PROXY REDUCTION</small><b>{typedValue(explanation, 'expected_risk_reduction').toFixed(3)}</b></span><span><small>PHYSICAL COST</small><b>{recommendation.experiment_cost.toFixed(3)}</b></span><span><small>CALIBRATION PROXY</small><b>{typedValue(explanation, 'calibration_value').toFixed(3)}</b></span><span><small>FIDELITY / HORIZON</small><b>L{recommendation.chosen_model_fidelity} / H{recommendation.planning_horizon}</b></span></div><details open><summary>STRUCTURED RATIONALE</summary><pre>{JSON.stringify({ primary_reason: explanation.primary_reason, reason_for_fidelity: recommendation.reason_for_fidelity, uncertainty_before: explanation.uncertainty_before, predicted_uncertainty_after: explanation.predicted_uncertainty_after }, null, 2)}</pre></details></article>}
      <article className="brain-card"><p className="eyebrow">COUNTERFACTUAL RESPONSES</p><h2>Predicted under each explanation</h2>{predictions.length ? <div className="prediction-stack">{predictions.slice(0, 5).map((item, index) => { const prediction = item.prediction as Record<string, unknown>; const delay = responseDelayMilliseconds(prediction); return <div key={index}><b>H{index + 1}</b><span>Predicted delay<small>{delay === null ? '—' : `${delay.toFixed(3)} ms`}</small></span><strong>{typeof item.probability === 'number' ? percent(item.probability, 1) : '—'}</strong></div>; })}</div> : <p className="empty-copy">Calibration actions estimate the inspection system; structural response rivalry is intentionally not used as their primary value.</p>}<p className="brain-note">Combined separation: <b>{typedValue(counterfactual, 'combined_separation').toFixed(3)}</b> near {(session.recommendation.experiment.frequency_start_hz + session.recommendation.experiment.frequency_end_hz) / 2000} kHz.</p></article>
      <article className="brain-card"><p className="eyebrow">NEXT-BEST ACTIONS</p><h2>Auditable alternatives</h2><div className="brain-candidates">{recommendation.top_candidates.map((item, index) => <Candidate key={index} item={item} rank={index + 1} researchEnabled={researchEnabled} riskDesign={riskDesign} />)}</div></article>
    </div>
  </section>;
}
