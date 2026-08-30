'use client';

import { useState } from 'react';
import type { SessionState } from '@/types/argus';

function readable(value: string) {
  return value.replaceAll('_', ' ');
}

function ProbabilityCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <article className={`assurance-probability ${tone}`}>
    <small>{label}</small>
    <strong>{(value * 100).toFixed(1)}<span>%</span></strong>
    <i><em style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></i>
  </article>;
}

export function AssurancePanel({ session, busy, onStop, onRelease }: {
  session: SessionState;
  busy: boolean;
  onStop: (reason: string) => void;
  onRelease: (reason: string) => void;
}) {
  const [reason, setReason] = useState('Operator safety intervention');
  const assessment = session.status.integrity_assessment;
  const probabilities = assessment.state_probabilities;
  const health = session.status.sensor_health;
  const sensors = Object.values(health.sensors);
  const latched = session.safety.emergency_stop.latched;
  return <section className="secondary-page assurance-page">
    <div className="secondary-header"><div><p className="eyebrow">FAIL-CLOSED RUNTIME ASSURANCE</p><h1>Know when not to trust the answer.</h1></div><span className={`assurance-state state-${assessment.integrity_state.toLowerCase()}`}>{readable(assessment.integrity_state)}</span></div>

    <div className="assurance-probabilities">
      <ProbabilityCard label="HEALTHY / NO DETECTABLE DAMAGE" value={probabilities.healthy_or_no_detectable_damage} tone="healthy" />
      <ProbabilityCard label="KNOWN DAMAGE CANDIDATE" value={probabilities.known_damage_candidate} tone="damage" />
      <ProbabilityCard label="UNKNOWN / UNSUPPORTED" value={probabilities.unknown_or_unsupported} tone="unknown" />
    </div>

    <div className="assurance-action">
      <div><small>CURRENT ENGINEERING ACTION</small><strong>{readable(assessment.engineering_action)}</strong><p>{assessment.decision_basis}</p></div>
      <span>HUMAN AUTHORITY {assessment.human_authority_required ? 'REQUIRED' : 'RETAINED'}</span>
    </div>

    <div className="assurance-grid">
      <article className="assurance-card"><div className="card-header"><div><p className="eyebrow">Independent metrology state</p><h2>Sensor reliability</h2></div><b>{health.accepted_measurements} ACCEPTED · {health.rejected_measurements} REJECTED</b></div>
        {sensors.length === 0 && <p className="empty-copy">No channel evidence yet. Reliability begins as an explicit uninformative prior.</p>}
        <div className="sensor-list">{sensors.map((sensor) => <div key={sensor.sensor_id}><span><b>{sensor.sensor_id}</b><small>{sensor.measurement_count} measurements · {sensor.rejected_count} rejected</small></span><i><em style={{ width: `${sensor.reliability_mean * 100}%` }} /></i><strong className={`sensor-${sensor.status.toLowerCase()}`}>{sensor.status}<small>{(sensor.reliability_mean * 100).toFixed(1)}%</small></strong></div>)}</div>
      </article>

      <article className="assurance-card"><p className="eyebrow">Competing spatial modes</p><h2>Candidate regions—not confirmed instances</h2><div className="candidate-region-list">{assessment.candidate_regions.slice(0, 4).map((candidate) => <div key={candidate.rank}><b>0{candidate.rank}</b><span>X {candidate.x.toFixed(3)} · Y {candidate.y.toFixed(3)}<small>{readable(candidate.dominant_type)} screening hypothesis</small></span><strong>{(candidate.probability * 100).toFixed(2)}%</strong></div>)}</div><p className="research-disclaimer">Multiple separated modes are exposed so a single-location estimate cannot hide ambiguity. This is not yet a validated multi-scatterer inverse solution.</p></article>

      <article className="assurance-card"><p className="eyebrow">Operating envelope</p><h2>Environment and drift</h2>{Object.keys(health.environment_latest).length ? <dl className="environment-list">{Object.entries(health.environment_latest).map(([name, value]) => <div key={name}><dt>{readable(name)}</dt><dd>{value.toFixed(2)} <small>baseline {health.environment_baseline[name]?.toFixed(2)}</small></dd></div>)}</dl> : <p className="empty-copy">No environmental metadata supplied. ARGUS will not assume laboratory conditions.</p>}<div className={`drift-strip ${health.drift_flags.length ? 'warning' : ''}`}>{health.drift_flags.length ? health.drift_flags.map(readable).join(' · ') : 'NO RECORDED ENVELOPE VIOLATION'}</div></article>

      <article className={`assurance-card emergency-card ${latched ? 'latched' : ''}`}><p className="eyebrow">Persistent safety interlock</p><h2>{latched ? 'Emergency stop latched' : 'Emergency stop armed'}</h2><p>{latched ? `Reason: ${session.safety.emergency_stop.reason}` : 'Latching blocks every acquisition path. Release requires an explicit human acknowledgement and is written to the audit trail.'}</p><label>OPERATOR REASON<input value={reason} minLength={3} maxLength={500} onChange={(event) => setReason(event.target.value)} /></label>{latched ? <button className="release-stop" disabled={busy || reason.trim().length < 3} onClick={() => onRelease(reason.trim())}>ACKNOWLEDGE CHECKS · RELEASE</button> : <button className="latch-stop" disabled={busy || reason.trim().length < 3} onClick={() => onStop(reason.trim())}>LATCH EMERGENCY STOP</button>}<small>THE RELEASE ACTION DOES NOT CERTIFY THE STRUCTURE OR HARDWARE AS SAFE.</small></article>
    </div>

    <p className="assurance-boundary">Research-screening output only. Minimum detectable damage and POD have not been established without a representative physical campaign. Size, type, severity, and defect-count fields remain unvalidated screening estimates.</p>
  </section>;
}
