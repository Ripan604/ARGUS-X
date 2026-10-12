'use client';

import { lazy, Suspense, useState } from 'react';
import { SpatialObservatory } from '@/components/SpatialObservatory';
import { CandidateComparison } from '@/components/CandidateComparison';
import { ExperimentStoryline, LandingStory, NarrativeTwin } from '@/components/NarrativeTwin';
import { useArgusSession } from '@/hooks/useArgusSession';
import { EngineAccess } from '@/components/EngineAccess';
import { InstrumentViewBoundary } from '@/components/InstrumentViewBoundary';
import { InstrumentWorkspace, type InstrumentView } from '@/components/InstrumentWorkspace';
import type { Preset } from '@/types/argus';

const BenchmarkPanel = lazy(() => import('@/components/BenchmarkPanel').then(module => ({ default: module.BenchmarkPanel })));
const CameraOverlay = lazy(() => import('@/components/CameraOverlay').then(module => ({ default: module.CameraOverlay })));
const ArgusBrain = lazy(() => import('@/components/ArgusBrain').then(module => ({ default: module.ArgusBrain })));
const AssurancePanel = lazy(() => import('@/components/AssurancePanel').then(module => ({ default: module.AssurancePanel })));
const EvidenceLedger = lazy(() => import('@/components/EvidenceLedger').then(module => ({ default: module.EvidenceLedger })));
const ResearchLab = lazy(() => import('@/components/ResearchLab').then(module => ({ default: module.ResearchLab })));
const PhysicalSignal = lazy(() => import('@/components/PhysicalSignal').then(module => ({ default: module.PhysicalSignal })));
const PosteriorReview = lazy(() => import('@/components/PosteriorReview').then(module => ({ default: module.PosteriorReview })));

function readableAction(value: string) {
  return value.replaceAll('_', ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase()) + '.';
}

function Landing({ create, resume, resumable, apiOnline, authenticationRequired, busy, error, warning }: { create: (preset: Preset, mode?: 'simulation' | 'physical', panelWidthMm?: number, panelHeightMm?: number, nuisanceAwareDesign?: boolean, riskCalibrationDesign?: boolean) => void; resume: () => void; resumable: boolean; apiOnline: boolean | null; authenticationRequired: boolean; busy: boolean; error: string | null; warning: string | null }) {
  const [preset, setPreset] = useState<Preset>('medium');
  const [panelWidthMm, setPanelWidthMm] = useState(600);
  const [panelHeightMm, setPanelHeightMm] = useState(400);
  const [nuisanceAwareDesign, setNuisanceAwareDesign] = useState(false);
  const [riskCalibrationDesign, setRiskCalibrationDesign] = useState(false);
  const invalidDimensions = !Number.isFinite(panelWidthMm) || !Number.isFinite(panelHeightMm) || panelWidthMm < 100 || panelWidthMm > 5000 || panelHeightMm < 100 || panelHeightMm > 5000;
  return <main className="landing-shell">
    <header className="landing-nav"><div className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS<span className="brand-period">.</span></strong><small>PHYSICAL INTELLIGENCE</small></div></div><div className="landing-utilities"><a className="text-link" href="/research">Measured evidence ↗</a><a className="text-link" href="/simulator">Explore the virtual lab ↗</a><a className="text-link" href="/setup">Hardware guide ↗</a><div className={`system-state ${apiOnline === false ? 'offline' : ''}`}><span className="live-dot" />{apiOnline === null ? 'Connecting to engine' : apiOnline ? 'Local engine online' : 'Local engine offline'}</div></div></header>
    <section className="landing-hero">
      <div className="landing-copy"><p className="eyebrow accent"><span className="eyebrow-rule" />ADAPTIVE SENSING / RESEARCH INSTRUMENT</p><h1>See beyond<br />the surface.<br /><em>Ask what’s next.</em></h1><p className="hero-description">An object. A vibration. A better question.<br />ARGUS turns physical measurements into a changing picture of what lies within—and chooses where to listen next.</p><div className="landing-entry-actions"><a href="#launch-console">Open the instrument <span>↗</span></a><a href="/research">Explore the evidence <span>→</span></a></div><div className="hero-index"><span>01 — EXCITE</span><i /><span>02 — INFER</span><i /><span>03 — ADAPT</span></div></div>
      <NarrativeTwin />
    </section>
    <section className="launch-console" id="launch-console" aria-labelledby="launch-title"><div className="launch-intro"><p className="eyebrow accent">YOUR FIRST QUESTION</p><h2 id="launch-title">Enter the instrument.</h2><p>Start with a hidden simulated defect, or connect a physical object.</p></div><div className="launch-settings"><div className="preset-picker"><span>SIMULATION DIFFICULTY</span>{(['easy', 'medium', 'hard'] as Preset[]).map((item) => <button aria-pressed={preset === item} className={preset === item ? 'selected' : ''} key={item} onClick={() => setPreset(item)}>{item}</button>)}</div><div className="physical-dimensions"><span>PANEL SIZE</span><label>W <input aria-label="Panel width in millimeters" type="number" min="100" max="5000" value={panelWidthMm} onChange={(event) => setPanelWidthMm(Number(event.target.value))} /> mm</label><span>×</span><label>H <input aria-label="Panel height in millimeters" type="number" min="100" max="5000" value={panelHeightMm} onChange={(event) => setPanelHeightMm(Number(event.target.value))} /> mm</label></div><label className="experimental-option"><input type="checkbox" checked={nuisanceAwareDesign} onChange={(event) => setNuisanceAwareDesign(event.target.checked)} /><span>Nuisance-aware design <small>EXPERIMENTAL</small></span></label><label className="experimental-option"><input type="checkbox" checked={riskCalibrationDesign} onChange={(event) => setRiskCalibrationDesign(event.target.checked)} /><span>Calibration-aware risk planning <small>EXPERIMENTAL · SLOWER</small></span></label>{riskCalibrationDesign && <p className="brain-note">Uses two possible measurements to compare calibration and diagnosis in squared millimetres. Overrides the information planner; physical accuracy is unvalidated.</p>}{invalidDimensions && <p className="dimension-error" role="alert">Enter dimensions between 100 and 5,000 mm.</p>}</div><div className="landing-actions"><button className="run-button landing-run" onClick={() => create(preset, 'simulation', panelWidthMm, panelHeightMm, nuisanceAwareDesign, riskCalibrationDesign)} disabled={busy || apiOnline !== true || invalidDimensions}><span>{busy ? 'Initializing instrument…' : 'Start simulation'}</span><b>↗</b></button><button className="physical-button" onClick={() => create(preset, 'physical', panelWidthMm, panelHeightMm, nuisanceAwareDesign, riskCalibrationDesign)} disabled={busy || apiOnline !== true || invalidDimensions}>Connect a physical object <span>→</span></button>{resumable && <button className="resume-button text-link" onClick={resume} disabled={busy || apiOnline !== true}>Resume last session ↗</button>}</div>{error && <p className="error-banner" role="alert">{error}</p>}</section>
    {warning && <p className="workspace-warning" role="status">{warning}</p>}
    <EngineAccess required={authenticationRequired} />
    <LandingStory />
    <footer className="landing-footer"><strong>ARGUS.</strong><span>Designed to question. Built to learn.</span><small>RESEARCH PROTOTYPE / NOT A CERTIFIED SAFETY SYSTEM</small><a href="/research" className="text-link">Read the evidence ↗</a><a href="/probe" className="text-link">Phone probe ↗</a></footer>
  </main>;
}

export default function Home() {
  const argus = useArgusSession();
  const [tab, setTab] = useState<InstrumentView>('interrogate');
  const [containmentRadiusMm, setContainmentRadiusMm] = useState(25);
  if (!argus.session) return <Landing create={argus.create} resume={argus.resume} resumable={Boolean(argus.lastSessionId)} apiOnline={argus.apiOnline} authenticationRequired={argus.authenticationRequired} busy={argus.busy} error={argus.error} warning={argus.warning} />;
  const session = argus.session, recommendation = session.recommendation, experiment = recommendation.experiment, status = session.status;
  const physical = session.mode === 'physical';
  const containmentProbability = status.posterior_containment.probabilities.find(
    (item) => item.radius_mm === containmentRadiusMm,
  )?.probability ?? 0;
  const runNext = () => { if (physical) setTab('signal'); else argus.run(status.should_stop); };
  return <InstrumentWorkspace session={session} view={tab} onView={next => { setTab(next); if (next === 'benchmark' && !argus.benchmarks) void argus.loadBenchmarks(); }} online={argus.apiOnline} busy={argus.busy} onReset={() => { argus.reset(); setTab('interrogate'); }} onRefresh={() => { void argus.refreshSession(); }} activity={argus.operation} onStop={() => { void argus.emergencyStop('Operator stop from workspace toolbar.'); }}>
    <InstrumentViewBoundary key={tab} onOverview={() => setTab('interrogate')}><Suspense fallback={<div className="workspace-loading" role="status"><span />Loading instrument view…</div>}><div className="view-stage" key={tab}>


    {argus.error && <div className="error-banner workspace-error" role="alert">{argus.error}</div>}
    {argus.warning && <div className="workspace-warning" role="status">{argus.warning}</div>}
    {tab === 'interrogate' && <>
      <section className="workbench-overview-title"><div><p className="eyebrow">ADAPTIVE INSPECTION / LIVE SESSION</p><h1>{session.safety.emergency_stop.latched ? 'Review the stopped session.' : status.should_stop ? 'Review the accumulated evidence.' : 'Design the next observation.'}</h1><p>{physical ? 'Position, acquire, verify, then update the model.' : 'Explore a hidden simulated defect with one deliberate experiment at a time.'}</p></div><span>{recommendation.action_type.toUpperCase()} / NEXT ACTION</span></section>
      <section className="workbench-kpis" aria-label="Current inference summary">
        <article><small>90% POSTERIOR RADIUS</small><strong>{status.posterior_containment.radius90_mm.toFixed(1)}<em>mm</em></strong><p>Model mass around the MAP</p></article>
        <article><small>MASS WITHIN <select aria-label="Containment radius" value={containmentRadiusMm} onChange={event => setContainmentRadiusMm(Number(event.target.value))}>{status.posterior_containment.probabilities.map(item => <option key={item.radius_mm} value={item.radius_mm}>{item.radius_mm} mm</option>)}</select></small><strong>{(containmentProbability * 100).toFixed(1)}<em>%</em></strong><p>Not field-calibrated coverage</p></article>
        <article><small>MODEL TRUST</small><strong>{(status.model_trust * 100).toFixed(1)}<em>%</em></strong><p>Internal model agreement score</p></article>
        <article className={status.ood_status !== 'NOMINAL' ? 'is-caution' : ''}><small>OPERATING CONDITION</small><strong>{status.ood_status.replaceAll('_', ' ')}</strong><p>{status.should_stop ? 'Stopping criterion reached' : `${session.assurance.accepted_measurements} accepted · ${session.assurance.rejected_measurements} rejected`}</p></article>
      </section>
      <SpatialObservatory key={session.id} session={session} history={argus.history} disabled={argus.busy || session.safety.emergency_stop.latched || argus.apiOnline !== true} onNoGoChange={argus.setNoGoRegions} />
      <section className="workspace-grid observation-actions">
        <ExperimentStoryline session={session} busy={argus.busy} />
        <aside className="recommendation-card"><div className="scanline" /><p className="eyebrow accent">{status.should_stop ? 'TERMINATION CONDITION' : 'NEXT ARGUS RECOMMENDATION'}</p><h2>{status.should_stop ? readableAction(status.recommended_engineering_action) : `The next question. Experiment ${String(status.experiment_count + 1).padStart(2, '0')}.`}</h2><div className="coordinate-pair"><div><small>EXCITATION</small><strong>{experiment.source_x.toFixed(2)}, {experiment.source_y.toFixed(2)}</strong><span>{Math.round(experiment.source_x * session.panel.width_m * 1000)} × {Math.round(experiment.source_y * session.panel.height_m * 1000)} mm</span></div><div><small>RECEIVER</small><strong>{experiment.receiver_x.toFixed(2)}, {experiment.receiver_y.toFixed(2)}</strong><span>{Math.round(experiment.receiver_x * session.panel.width_m * 1000)} × {Math.round(experiment.receiver_y * session.panel.height_m * 1000)} mm</span></div></div><div className="signal-spec"><span><small>WAVEFORM</small><b>{experiment.waveform.toUpperCase()}</b></span><span><small>SWEEP</small><b>{(experiment.frequency_start_hz / 1000).toFixed(1)} → {(experiment.frequency_end_hz / 1000).toFixed(1)} kHz</b></span><span><small>DRIVE</small><b>{Math.round(experiment.amplitude * 100)}%</b></span><span><small>DURATION</small><b>{Math.round(experiment.duration_s * 1000)} ms</b></span></div><div className="rationale"><span>WHY THIS PROBE</span><p>{recommendation.explanation}</p></div><div className="score-row"><span>INFORMATION UTILITY / PROXY</span><strong>{recommendation.expected_information_gain.toFixed(2)} <small>relative</small></strong></div><button className="run-button" onClick={runNext} disabled={argus.busy || session.safety.emergency_stop.latched || argus.apiOnline !== true}><span>{session.safety.emergency_stop.latched ? 'EMERGENCY STOP LATCHED' : argus.busy ? 'PROCESSING WAVEFIELD…' : physical ? 'CONFIRM PLACEMENT · ACQUIRE' : status.should_stop ? 'RUN ONE MORE EXPERIMENT' : 'RUN EXPERIMENT'}</span><b>{String(status.experiment_count + 1).padStart(2, '0')}</b></button></aside>
      </section>
      <CandidateComparison session={session} />
      <section className="results-rail"><div><small>EXPERIMENTS</small><strong>{status.experiment_count}</strong></div><div><small>ENTROPY REDUCTION</small><strong>{((1 - status.normalized_entropy) * 100).toFixed(1)}%</strong></div><div><small>STOP RULE</small><strong>{status.stop_reason?.replaceAll('_', ' ').toUpperCase() || 'SEARCHING'}</strong></div><div><small>GROUND TRUTH</small><strong className={session.revealed ? 'truth-open' : ''}>{physical ? 'NOT AVAILABLE · PHYSICAL OBJECT' : session.revealed ? `${session.ground_truth?.defect_type.replaceAll('_', ' ').toUpperCase()} · ${session.localization_error_mm?.toFixed(1)} mm ERROR` : 'LOCKED'}</strong></div><button className="reveal-button" onClick={argus.reveal} disabled={physical || session.revealed || argus.busy}>{physical ? 'SIMULATION ONLY' : session.revealed ? 'GROUND TRUTH REVEALED' : 'REVEAL GROUND TRUTH'}</button></section>
    </>}

    {tab === 'assurance' && <AssurancePanel session={session} busy={argus.busy} onStop={argus.emergencyStop} onRelease={argus.releaseEmergencyStop} />}
    {tab === 'brain' && <ArgusBrain session={session} />}
    {tab === 'signal' && <PhysicalSignal session={session} analysis={argus.measurement} busy={argus.busy} onCapture={argus.capture} onUpload={argus.upload} onAcquireDevice={argus.acquireDevice} onRun={() => argus.run(status.should_stop)} />}
    {tab === 'evolution' && <PosteriorReview session={session} history={argus.history} />}
    {tab === 'benchmark' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Technical credibility</p><h1>Adaptive vs. brute force.</h1></div></div><BenchmarkPanel data={argus.benchmarks} onLoad={argus.loadBenchmarks} busy={argus.busy} /></section>}
    {tab === 'research' && <ResearchLab />}
    {tab === 'evidence' && <EvidenceLedger session={session} />}
    {tab === 'camera' && <section className="secondary-page"><div className="secondary-header"><div><p className="eyebrow">Physical positioning</p><h1>Project inference onto reality.</h1></div></div><CameraOverlay session={session} /></section>}
    </div></Suspense></InstrumentViewBoundary>
    <footer className="footer-rail"><span className={tab === 'interrogate' ? 'active' : ''}><b>01</b> ACQUIRE</span><i /><span><b>02</b> INTERPRET</span><i /><span><b>03</b> UPDATE BELIEF</span><i /><span><b>04</b> CHOOSE NEXT</span><p>RESEARCH PROTOTYPE · NOT A CERTIFIED STRUCTURAL-SAFETY SYSTEM · <button onClick={argus.calibrate} disabled={physical || argus.busy || session.safety.emergency_stop.latched} title={physical ? 'Physical calibration requires acquired healthy-reference signals.' : undefined}>{physical ? 'PHYSICAL CALIBRATION REQUIRES REFERENCE SIGNALS' : session.calibration ? 'CALIBRATION ACTIVE' : 'RUN REFERENCE CALIBRATION'}</button></p></footer>
  </InstrumentWorkspace>;
}
