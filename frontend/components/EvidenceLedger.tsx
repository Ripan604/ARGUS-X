'use client';

import { useEffect, useState } from 'react';
import { argusApi } from '@/services/api';
import type { SessionState } from '@/types/argus';

export function EvidenceLedger({ session }: { session: SessionState }) {
  const [entries, setEntries] = useState<Array<Record<string, unknown>>>([]);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { argusApi.ledger(session.id).then((result) => setEntries(result.entries)).catch(() => setEntries([])); }, [session.id, session.status.experiment_count]);
  const verify = async () => { setBusy(true); try { setVerification(await argusApi.verifyLedger(session.id)); } finally { setBusy(false); } };
  const exportBundle = async () => { setBusy(true); try { const blob = await argusApi.exportBundle(session.id); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `argus_session_${session.id}.zip`; anchor.click(); URL.revokeObjectURL(url); } finally { setBusy(false); } };
  return <section className="secondary-page evidence-page"><div className="secondary-header"><div><p className="eyebrow">INNOVATION EVIDENCE</p><h1>Trace mechanism to measurement.</h1></div><div className="acquisition-actions"><button className="ghost-button" onClick={verify} disabled={busy}>VERIFY LEDGER</button><button className="run-button compact" onClick={exportBundle} disabled={busy}>EXPORT RESEARCH BUNDLE</button></div></div>
    <div className="innovation-grid">{[
      ['DIAGNOSTIC ↔ CALIBRATION', session.recommendation.action_type, `Structural ${session.status.structural_uncertainty.toFixed(3)} · metrology ${session.status.metrology_uncertainty.toFixed(3)}`],
      ['JOINT UNCERTAINTY', 'ACTIVE', `${Object.keys((session.joint_inference.nuisance as Record<string, unknown> | undefined)?.parameters as Record<string, unknown> ?? {}).length} nuisance variables tracked`],
      ['WAVEFORM + GEOMETRY', session.recommendation.experiment.waveform, `${(session.recommendation.experiment.frequency_start_hz / 1000).toFixed(1)}–${(session.recommendation.experiment.frequency_end_hz / 1000).toFixed(1)} kHz`],
      ['DISCREPANCY + FIDELITY', `LEVEL ${session.recommendation.chosen_model_fidelity}`, `Model trust ${(session.status.model_trust * 100).toFixed(1)}%`],
      ['HORIZON PLANNING', `H = ${session.recommendation.planning_horizon}`, session.recommendation.objective],
      ['OOD ABSTENTION', session.status.ood_status, `OOD score ${session.status.ood_score.toFixed(3)}`],
    ].map(([title, state, detail]) => <article key={title}><small>{title}</small><strong>{state.replaceAll('_', ' ').toUpperCase()}</strong><p>{detail}</p></article>)}</div>
    {verification && <div className={`verification-result ${verification.valid ? 'pass' : 'fail'}`}><strong>{String(verification.status)}</strong><span>{verification.valid ? `${verification.record_count} linked records verified` : `Integrity failure at record ${verification.failed_at_record}`}</span><code>{String(verification.head_hash ?? '')}</code></div>}
    <div className="ledger-table"><div><b>STEP</b><b>ACTION</b><b>ACQUISITION</b><b>MODEL</b><b>ENTRY HASH</b></div>{entries.length === 0 && <p className="empty-copy">The chain begins when the first measurement is accepted.</p>}{entries.map((record, index) => { const entry = record.entry as Record<string, unknown>; return <article key={index}><b>{String(record.experiment_index).padStart(3, '0')}</b><span>{String(entry.action_type).toUpperCase()}</span><span>{String(entry.acquisition_source)}</span><span>L{String(entry.model_fidelity_level)}</span><code>{String(record.entry_hash).slice(0, 18)}…</code></article>; })}</div>
    <p className="research-disclaimer">This is a tamper-evident cryptographic hash chain, not a blockchain and not a certification record. Patentability cannot be determined by this software.</p>
  </section>;
}

