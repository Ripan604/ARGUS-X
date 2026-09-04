'use client';

import { useMemo, useRef, useState } from 'react';
import { BeliefEvolution } from '@/components/BeliefEvolution';
import { BenchmarkPanel } from '@/components/BenchmarkPanel';
import { CameraOverlay } from '@/components/CameraOverlay';
import { ArgusBrain } from '@/components/ArgusBrain';
import { AssurancePanel } from '@/components/AssurancePanel';
import { EvidenceLedger } from '@/components/EvidenceLedger';
import { HeatmapCanvas } from '@/components/HeatmapCanvas';
import { ResearchLab } from '@/components/ResearchLab';
import { SignalPlots } from '@/components/SignalPlots';
import { useArgusSession } from '@/hooks/useArgusSession';
import type { Preset } from '@/types/argus';

type Tab = 'interrogate' | 'assurance' | 'brain' | 'signal' | 'evolution' | 'benchmark' | 'research' | 'evidence' | 'camera';

const tabLabels: Record<Tab, string> = {
  interrogate: 'MISSION CONTROL',
  assurance: 'ASSURANCE',
  brain: 'ARGUS BRAIN',
  signal: 'SIGNALS',
  evolution: 'EVOLUTION',
  benchmark: 'BASELINE',
  research: 'RESEARCH',
  evidence: 'EVIDENCE',
  camera: 'REGISTRATION',
};

function readableAction(value: string) {
  return value.replaceAll('_', ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase()) + '.';
}

function Landing({ create, resume, resumable, apiOnline, busy, error }: { create: (preset: Preset, mode?: 'simulation' | 'physical', panelWidthMm?: number, panelHeightMm?: number) => void; resume: () => void; resumable: boolean; apiOnline: boolean | null; busy: boolean; error: string | null }) {
  const [preset, setPreset] = useState<Preset>('medium');
  const [panelWidthMm, setPanelWidthMm] = useState(600);
  const [panelHeightMm, setPanelHeightMm] = useState(400);
  return <main className="landing-shell">
    <header className="landing-nav"><div className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS</strong><small>ADAPTIVE PHYSICAL INTELLIGENCE</small></div></div><div className="landing-utilities"><a className="probe-link" href="/simulator">VIRTUAL LAB</a><a className="probe-link" href="/setup">PHYSICAL SETUP GUIDE</a><div className={`system-state ${apiOnline === false ? 'offline' : ''}`}><span className="live-dot" /> {apiOnline === null ? 'CHECKING LOCAL ENGINE' : apiOnline ? 'LOCAL ENGINE ONLINE · PRIVATE' : 'LOCAL ENGINE OFFLINE'}</div></div></header>
    <section className="landing-hero">
      <div className="landing-copy"><p className="eyebrow accent">A CLOSED-LOOP SENSING SYSTEM</p><h1>Don’t just analyze<br />the measurement.<br /><em>Choose the next one.</em></h1><p className="hero-description">ARGUS interrogates opaque objects with vibration, carries uncertainty forward, and selects the next physical experiment that best separates competing hidden-defect hypotheses.</p>
        <div className="preset-picker"><span>SECRET DEFECT DIFFICULTY</span>{(['easy', 'medium', 'hard'] as Preset[]).map((item) => <button className={preset === item ? 'selected' : ''} key={item} onClick={() => setPreset(item)}>{item.toUpperCase()}</button>)}</div>
        <div className="physical-dimensions"><span>PHYSICAL PANEL</span><label>WIDTH <input type="number" min="100" max="5000" value={panelWidthMm} onChange={(event) => setPanelWidthMm(Number(event.target.value))} /> MM</label><label>HEIGHT <input type="number" min="100" max="5000" value={panelHeightMm} onChange={(event) => setPanelHeightMm(Number(event.target.value))} /> MM</label></div>
        <div className="landing-actions"><button className="run-button landing-run" onClick={() => create(preset)} disabled={busy || apiOnline === false}><span>{busy ? 'INITIALIZING DIGITAL TWIN…' : 'START SECRET SIMULATION'}</span><b>→</b></button><button className="physical-button" onClick={() => create(preset, 'physical', panelWidthMm, panelHeightMm)} disabled={busy || apiOnline === false || panelWidthMm < 100 || panelWidthMm > 5000 || panelHeightMm < 100 || panelHeightMm > 5000}>START PHYSICAL SESSION</button>{resumable && <button className="physical-button resume-button" onClick={resume} disabled={busy || apiOnline === false}>RESUME LAST SESSION</button>}</div>
        {error && <p className="error-banner">BACKEND CONNECTION · {error}</p>}
      </div>
      <div className="hero-diagram" aria-label="ARGUS recursive experiment loop"><div className="loop-orbit orbit-one" /><div className="loop-orbit orbit-two" /><div className="loop-core"><span>ARGUS</span><strong>ΔH</strong><small>MAXIMIZE</small></div>{['OBSERVE', 'BELIEVE', 'PREDICT', 'CHOOSE', 'EXCITE', 'UPDATE'].map((label, index) => <div key={label} className={`loop-node node-${index + 1}`}><i>{String(index + 1).padStart(2, '0')}</i>{label}</div>)}</div>
    </section>
    <footer className="landing-footer"><span>PHYSICS-INSPIRED FORWARD MODEL</span><span>BAYESIAN RECURSION</span><span>COUNTERFACTUAL PLANNING</span><span>REAL SIGNALS</span></footer>
  </main>;
}

export default function Home() {
  const argus = useArgusSession();
  const [tab, setTab] = useState<Tab>('interrogate');
  const [containmentRadiusMm, setContainmentRadiusMm] = useState(25);
  const uploadRef = useRef<HTMLInputElement>(null);
  const uniformPrior = useMemo(() => {
    const size = argus.session?.posterior.length ?? 20; return Array.from({ length: size }, () => Array(size).fill(1 / size ** 2));
  }, [argus.session?.posterior.length]);
  if (!argus.session) return <Landing create={argus.create} resume={argus.resume} resumable={Boolean(argus.lastSessionId)} apiOnline={argus.apiOnline} busy={argus.busy} error={argus.error} />;
  const session = argus.session, recommendation = session.recommendation, experiment = recommendation.experiment, status = session.status;
  const physical = session.mode === 'physical';
  const containmentProbability = status.posterior_containment.probabilities.find(
    (item) => item.radius_mm === containmentRadiusMm,
  )?.probability ?? 0;
  const runNext = () => { if (physical) setTab('signal'); else argus.run(status.should_stop); };
  return <main className="instrument-shell">
    <header className="topbar">
      <div className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS</strong><small>ADAPTIVE PHYSICAL INTELLIGENCE</small></div></div>
      <nav className="mode-tabs">{(Object.keys(tabLabels) as Tab[]).map((item) => <button key={item} className={tab === item ? 'active' : ''} onClick={() => { setTab(item); if (item === 'benchmark' && !argus.benchmarks) argus.loadBenchmarks(); }}>{tabLabels[item]}</button>)}</nav>
      <div className={`system-state ${session.safety.emergency_stop.latched ? 'stop-latched' : ''}`}><span className="live-dot" /> {session.safety.emergency_stop.latched ? 'EMERGENCY STOP' : physical ? 'PHYSICAL INPUT' : 'SIMULATOR ONLINE'} <b>{String(status.experiment_count).padStart(2, '0')}/{session.config.max_experiments}</b></div>
      <a className="probe-link" href="/simulator" target="_blank" rel="noreferrer">VIRTUAL LAB</a>
      <a className="probe-link" href="/setup" target="_blank" rel="noreferrer">SETUP GUIDE</a>
      <a className="probe-link" href="/probe" target="_blank" rel="noreferrer">PHONE PROBE</a>
      <button className="ghost-button" onClick={argus.reset}>NEW SESSION</button>
    </header>

    {argus.error && <div className="error-banner workspace-error">{argus.error}</div>}
    {tab === 'interrogate' && <>
      <section className="hero-strip compact-hero"><div><p className="eyebrow">SESSION {session.id} · {session.preset.toUpperCase()} · {physical ? 'PHYSICAL' : 'DIGITAL TWIN'}</p><h1>{session.safety.emergency_stop.latched ? 'Emergency stop is latched.' : status.should_stop ? 'Research stopping criterion reached.' : 'Adaptive interrogation in progress.'}</h1></div><div className="phase-readout containment-readout"><small>POSTERIOR MASS WITHIN <select aria-label="Containment radius" value={containmentRadiusMm} onChange={(event) => setContainmentRadiusMm(Number(event.target.value))}>{status.posterior_containment.probabilities.map((item) => <option key={item.radius_mm} value={item.radius_mm}>{item.radius_mm}</option>)}</select> MM</small><strong>{(containmentProbability * 100).toFixed(1)}<span>%</span></strong><em>CEP50 {status.posterior_containment.cep50_mm.toFixed(1)} mm · R90 {status.posterior_containment.radius90_mm.toFixed(1)} mm</em></div></section>
      <section className="workspace-grid">
        <article className="panel-card object-card"><div className="card-header"><div><p className="eyebrow">Recursive posterior</p><h2>Hidden-defect probability field</h2></div><div className="legend"><i /> LOW <i /> HIGH</div></div><div className="panel-canvas-stage"><HeatmapCanvas session={session} history={argus.history} onNoGoChange={argus.setNoGoRegions} /><span className="vertical-dimension">{Math.round(session.panel.height_m * 1000)} mm</span><span className="horizontal-dimension">{Math.round(session.panel.width_m * 1000)} mm</span></div><div className="object-footer"><div><small>MAP ESTIMATE</small><b>X {status.map_x.toFixed(3)} · Y {status.map_y.toFixed(3)}</b></div><div><small>CEP50 / R90</small><b>{status.posterior_containment.cep50_mm.toFixed(1)} / {status.posterior_containment.radius90_mm.toFixed(1)} MM</b></div><div><small>TRUST-ADJUSTED SCORE</small><b className="accent">{(status.decision_confidence * 100).toFixed(1)}%</b></div></div><p className="containment-caveat">Containment is posterior mass around the MAP at grid-cell centers; it is not yet field-calibrated coverage.</p></article>
        <aside className="recommendation-card"><div className="scanline" /><p className="eyebrow accent">{status.should_stop ? 'TERMINATION CONDITION' : 'NEXT ARGUS RECOMMENDATION'}</p><h2>{status.should_stop ? readableAction(status.recommended_engineering_action) : `Experiment ${String(status.experiment_count + 1).padStart(2, '0')} separates the leading hypotheses.`}</h2><div className="coordinate-pair"><div><small>EXCITATION</small><strong>{experiment.source_x.toFixed(2)}, {experiment.source_y.toFixed(2)}</strong><span>{Math.round(experiment.source_x * session.panel.width_m * 1000)} × {Math.round(experiment.source_y * session.panel.height_m * 1000)} mm</span></div><div><small>RECEIVER</small><strong>{experiment.receiver_x.toFixed(2)}, {experiment.receiver_y.toFixed(2)}</strong><span>{Math.round(experiment.receiver_x * session.panel.width_m * 1000)} × {Math.round(experiment.receiver_y * session.panel.height_m * 1000)} mm</span></div></div><div className="signal-spec"><span><small>WAVEFORM</small><b>{experiment.waveform.toUpperCase()}</b></span><span><small>SWEEP</small><b>{(experiment.frequency_start_hz / 1000).toFixed(1)} → {(experiment.frequency_end_hz / 1000).toFixed(1)} kHz</b></span><span><small>DRIVE</small><b>{Math.round(experiment.amplitude * 100)}%</b></span><span><small>DURATION</small><b>{Math.round(experiment.duration_s * 1000)} ms</b></span></div><div className="rationale"><span>WHY THIS PROBE</span><p>{recommendation.explanation}</p></div><div className="score-row"><span>EXPECTED INFORMATION GAIN</span><strong>{recommendation.expected_information_gain.toFixed(2)} <small>bits</small></strong></div><button className="run-button" onClick={runNext} disabled={argus.busy || session.safety.emergency_stop.latched}><span>{session.safety.emergency_stop.latched ? 'EMERGENCY STOP LATCHED' : argus.busy ? 'PROCESSING WAVEFIELD…' : physical ? 'CONFIRM PLACEMENT · ACQUIRE' : status.should_stop ? 'RUN ONE MORE EXPERIMENT' : 'RUN EXPERIMENT'}</span><b>{String(status.experiment_count + 1).padStart(2, '0')}</b></button></aside>
      </section>
      <section className="candidate-section"><div className="section-heading"><div><p className="eyebrow">Planner audit</p><h2>Top candidate experiments</h2></div><span>score balances information, risk, calibration, trust, coverage, time, cost, and repetition</span></div><div className="candidate-table"><div className="candidate-head"><span>RANK / SOURCE → RECEIVER</span><span>INFO GAIN</span><span>DISAGREEMENT</span><span>COST</span><span>FINAL SCORE</span></div>{recommendation.top_candidates.map((candidate, index) => <div key={index} className={index === 0 ? 'selected-candidate' : ''}><span><b>{String(index + 1).padStart(2, '0')}</b> ({candidate.experiment.source_x.toFixed(2)},{candidate.experiment.source_y.toFixed(2)}) → ({candidate.experiment.receiver_x.toFixed(2)},{candidate.experiment.receiver_y.toFixed(2)})</span><span>{candidate.expected_information_gain.toFixed(3)}</span><span>{candidate.hypothesis_disagreement.toFixed(3)}</span><span>{candidate.experiment_cost.toFixed(3)}</span><strong>{candidate.final_score.toFixed(3)}</strong></div>)}</div></section>
      <section className="results-rail"><div><small>EXPERIMENTS</small><strong>{status.experiment_count}</strong></div><div><small>ENTROPY REDUCTION</small><strong>{((1 - status.normalized_entropy) * 100).toFixed(1)}%</strong></div><div><small>STOP RULE</small><strong>{status.stop_reason?.replaceAll('_', ' ').toUpperCase() || 'SEARCHING'}</strong></div><div><small>GROUND TRUTH</small><strong className={session.revealed ? 'truth-open' : ''}>{physical ? 'NOT AVAILABLE · PHYSICAL OBJECT' : session.revealed ? `${session.ground_truth?.defect_type.replaceAll('_', ' ').toUpperCase()} · ${session.localization_error_mm?.toFixed(1)} mm ERROR` : 'LOCKED'}</strong></div><button className="reveal-button" onClick={argus.reveal} disabled={physical || session.revealed || argus.busy}>{physical ? 'SIMULATION ONLY' : session.revealed ? 'GROUND TRUTH REVEALED' : 'REVEAL GROUND TRUTH'}</button></section>
    </>}

    {tab === 'assurance' && <AssurancePanel session={session} busy={argus.busy} onStop={argus.emergencyStop} onRelease={argus.releaseEmergencyStop} />}
    {tab === 'brain' && <ArgusBrain session={session} />}
    {tab === 'signal' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Signal interpretation engine</p><h1>Measurement anatomy.</h1></div><div className="acquisition-actions"><button className="ghost-button" onClick={argus.capture} disabled={argus.busy || session.safety.emergency_stop.latched}>BROWSER MICROPHONE</button>{physical && <button className="ghost-button" onClick={() => argus.acquireDevice('serial_probe')} disabled={argus.busy || session.safety.emergency_stop.latched}>ACQUIRE SERIAL PROBE</button>}<button className="ghost-button" onClick={() => uploadRef.current?.click()} disabled={argus.busy || session.safety.emergency_stop.latched}>UPLOAD WAV</button><input ref={uploadRef} hidden type="file" accept=".wav,audio/wav" onChange={(event) => event.target.files?.[0] && argus.upload(event.target.files[0])} /><button className="run-button compact" onClick={() => argus.run(status.should_stop)} disabled={physical || argus.busy || session.safety.emergency_stop.latched}>{status.should_stop ? 'SIMULATE ONE MORE' : 'SIMULATE SIGNAL'}</button></div></div><SignalPlots analysis={argus.measurement} /></section>}
    {tab === 'evolution' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Multi-measurement fusion</p><h1>Watch uncertainty collapse.</h1></div><span className="secondary-kpi">{argus.history.length} MEASUREMENTS · {((1 - status.normalized_entropy) * 100).toFixed(1)}% ENTROPY REDUCTION</span></div><BeliefEvolution history={argus.history} initial={uniformPrior} /></section>}
    {tab === 'benchmark' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Technical credibility</p><h1>Adaptive vs. brute force.</h1></div></div><BenchmarkPanel data={argus.benchmarks} onLoad={argus.loadBenchmarks} busy={argus.busy} /></section>}
    {tab === 'research' && <ResearchLab />}
    {tab === 'evidence' && <EvidenceLedger session={session} />}
    {tab === 'camera' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Physical positioning</p><h1>Project inference onto reality.</h1></div></div><CameraOverlay session={session} /></section>}
    <footer className="footer-rail"><span className={tab === 'interrogate' ? 'active' : ''}><b>01</b> ACQUIRE</span><i /><span><b>02</b> INTERPRET</span><i /><span><b>03</b> UPDATE BELIEF</span><i /><span><b>04</b> CHOOSE NEXT</span><p>RESEARCH PROTOTYPE · NOT A CERTIFIED STRUCTURAL-SAFETY SYSTEM · <button onClick={argus.calibrate} disabled={physical} title={physical ? 'Physical calibration requires acquired healthy-reference signals.' : undefined}>{physical ? 'PHYSICAL CALIBRATION REQUIRES REFERENCE SIGNALS' : session.calibration ? 'CALIBRATION ACTIVE' : 'RUN REFERENCE CALIBRATION'}</button></p></footer>
  </main>;
}
