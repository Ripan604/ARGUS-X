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
import { ExperimentStoryline, LandingStory, NarrativeTwin } from '@/components/NarrativeTwin';
import { useArgusSession } from '@/hooks/useArgusSession';
import type { Preset } from '@/types/argus';

type Tab = 'interrogate' | 'assurance' | 'brain' | 'signal' | 'evolution' | 'benchmark' | 'research' | 'evidence' | 'camera';

const tabLabels: Record<Tab, string> = {
  interrogate: 'Overview',
  assurance: 'Assurance',
  brain: 'Reasoning',
  signal: 'Signals',
  evolution: 'Evolution',
  benchmark: 'Benchmark',
  research: 'Research',
  evidence: 'Evidence',
  camera: 'Registration',
};

function readableAction(value: string) {
  return value.replaceAll('_', ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase()) + '.';
}

function Landing({ create, resume, resumable, apiOnline, busy, error }: { create: (preset: Preset, mode?: 'simulation' | 'physical', panelWidthMm?: number, panelHeightMm?: number, nuisanceAwareDesign?: boolean) => void; resume: () => void; resumable: boolean; apiOnline: boolean | null; busy: boolean; error: string | null }) {
  const [preset, setPreset] = useState<Preset>('medium');
  const [panelWidthMm, setPanelWidthMm] = useState(600);
  const [panelHeightMm, setPanelHeightMm] = useState(400);
  const [nuisanceAwareDesign, setNuisanceAwareDesign] = useState(false);
  const invalidDimensions = !Number.isFinite(panelWidthMm) || !Number.isFinite(panelHeightMm) || panelWidthMm < 100 || panelWidthMm > 5000 || panelHeightMm < 100 || panelHeightMm > 5000;
  return <main className="landing-shell">
    <header className="landing-nav"><div className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS<span className="brand-period">.</span></strong><small>PHYSICAL INTELLIGENCE</small></div></div><div className="landing-utilities"><a className="text-link" href="/simulator">Explore the virtual lab ↗</a><a className="text-link" href="/setup">Hardware guide ↗</a><div className={`system-state ${apiOnline === false ? 'offline' : ''}`}><span className="live-dot" />{apiOnline === null ? 'Connecting to engine' : apiOnline ? 'Local engine online' : 'Local engine offline'}</div></div></header>
    <section className="landing-hero">
      <div className="landing-copy"><p className="eyebrow accent"><span className="eyebrow-rule" />ADAPTIVE SENSING / RESEARCH INSTRUMENT</p><h1>See beyond<br />the surface.<br /><em>Ask what’s next.</em></h1><p className="hero-description">An object. A vibration. A better question.<br />ARGUS turns physical measurements into a changing picture of what lies within—and chooses where to listen next.</p><div className="hero-index"><span>01 — EXCITE</span><i /><span>02 — INFER</span><i /><span>03 — ADAPT</span></div></div>
      <NarrativeTwin />
    </section>
    <section className="launch-console" aria-labelledby="launch-title"><div className="launch-intro"><p className="eyebrow accent">YOUR FIRST QUESTION</p><h2 id="launch-title">Enter the instrument.</h2><p>Start with a hidden simulated defect, or connect a physical object.</p></div><div className="launch-settings"><div className="preset-picker"><span>SIMULATION DIFFICULTY</span>{(['easy', 'medium', 'hard'] as Preset[]).map((item) => <button aria-pressed={preset === item} className={preset === item ? 'selected' : ''} key={item} onClick={() => setPreset(item)}>{item}</button>)}</div><div className="physical-dimensions"><span>PANEL SIZE</span><label>W <input aria-label="Panel width in millimeters" type="number" min="100" max="5000" value={panelWidthMm} onChange={(event) => setPanelWidthMm(Number(event.target.value))} /> mm</label><span>×</span><label>H <input aria-label="Panel height in millimeters" type="number" min="100" max="5000" value={panelHeightMm} onChange={(event) => setPanelHeightMm(Number(event.target.value))} /> mm</label></div><label className="experimental-option"><input type="checkbox" checked={nuisanceAwareDesign} onChange={(event) => setNuisanceAwareDesign(event.target.checked)} /><span>Nuisance-aware design <small>EXPERIMENTAL</small></span></label>{invalidDimensions && <p className="dimension-error" role="alert">Enter dimensions between 100 and 5,000 mm.</p>}</div><div className="landing-actions"><button className="run-button landing-run" onClick={() => create(preset, 'simulation', panelWidthMm, panelHeightMm, nuisanceAwareDesign)} disabled={busy || apiOnline !== true || invalidDimensions}><span>{busy ? 'Initializing instrument…' : 'Start simulation'}</span><b>↗</b></button><button className="physical-button" onClick={() => create(preset, 'physical', panelWidthMm, panelHeightMm, nuisanceAwareDesign)} disabled={busy || apiOnline !== true || invalidDimensions}>Connect a physical object <span>→</span></button>{resumable && <button className="resume-button text-link" onClick={resume} disabled={busy || apiOnline !== true}>Resume last session ↗</button>}</div>{error && <p className="error-banner" role="alert">{error}</p>}</section>
    <LandingStory />
    <footer className="landing-footer"><strong>ARGUS.</strong><span>Designed to question. Built to learn.</span><small>RESEARCH PROTOTYPE / NOT A CERTIFIED SAFETY SYSTEM</small><a href="/research" className="text-link">Read the evidence ↗</a><a href="/probe" className="text-link">Phone probe ↗</a></footer>
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
      <div className={`system-state ${session.safety.emergency_stop.latched ? 'stop-latched' : ''}`}><span className="live-dot" /> {session.safety.emergency_stop.latched ? 'EMERGENCY STOP' : physical ? 'PHYSICAL INPUT' : 'SIMULATOR ONLINE'} <b>{String(status.experiment_count).padStart(2, '0')}/{session.config.max_experiments}</b></div>
      <a className="probe-link" href="/simulator" target="_blank" rel="noreferrer">VIRTUAL LAB</a>
      <a className="probe-link" href="/setup" target="_blank" rel="noreferrer">SETUP GUIDE</a>
      <a className="probe-link" href="/probe" target="_blank" rel="noreferrer">PHONE PROBE</a>
      <button className="ghost-button" onClick={argus.reset}>NEW SESSION</button>
    </header>
    <nav className="workspace-navigation" aria-label="Instrument views"><div className="navigation-label">WORKSPACE</div><div className="mode-tabs">{(Object.keys(tabLabels) as Tab[]).map((item) => <button key={item} aria-current={tab === item ? "page" : undefined} className={tab === item ? 'active' : ''} onClick={() => { setTab(item); if (item === 'benchmark' && !argus.benchmarks) argus.loadBenchmarks(); }}>{tabLabels[item]}</button>)}</div></nav>
    <div className="view-stage" key={tab}>


    {argus.error && <div className="error-banner workspace-error">{argus.error}</div>}
    {tab === 'interrogate' && <>
      <section className="hero-strip compact-hero"><div><p className="eyebrow">SESSION {session.id} · {session.preset.toUpperCase()} · {physical ? 'PHYSICAL' : 'DIGITAL TWIN'}</p><h1>{session.safety.emergency_stop.latched ? 'Emergency stop is latched.' : status.should_stop ? 'A moment to review the evidence.' : 'Design the next observation.'}</h1></div><div className="phase-readout containment-readout"><small>POSTERIOR MASS WITHIN <select aria-label="Containment radius" value={containmentRadiusMm} onChange={(event) => setContainmentRadiusMm(Number(event.target.value))}>{status.posterior_containment.probabilities.map((item) => <option key={item.radius_mm} value={item.radius_mm}>{item.radius_mm}</option>)}</select> MM</small><strong>{(containmentProbability * 100).toFixed(1)}<span>%</span></strong><em>CEP50 {status.posterior_containment.cep50_mm.toFixed(1)} mm · R90 {status.posterior_containment.radius90_mm.toFixed(1)} mm</em></div></section>
      <div className="mission-narrative"><NarrativeTwin session={session} /><ExperimentStoryline session={session} busy={argus.busy} /></div>
      <section className="workspace-grid">
        <article className="panel-card object-card"><div className="card-header"><div><p className="eyebrow">Recursive posterior</p><h2>Hidden-defect probability field</h2></div><div className="legend"><i /> LOW <i /> HIGH</div></div><div className="panel-canvas-stage"><HeatmapCanvas session={session} history={argus.history} onNoGoChange={argus.setNoGoRegions} /><span className="vertical-dimension">{Math.round(session.panel.height_m * 1000)} mm</span><span className="horizontal-dimension">{Math.round(session.panel.width_m * 1000)} mm</span></div><div className="object-footer"><div><small>MAP ESTIMATE</small><b>X {status.map_x.toFixed(3)} · Y {status.map_y.toFixed(3)}</b></div><div><small>CEP50 / R90</small><b>{status.posterior_containment.cep50_mm.toFixed(1)} / {status.posterior_containment.radius90_mm.toFixed(1)} MM</b></div><div><small>TRUST-ADJUSTED SCORE</small><b className="accent">{(status.decision_confidence * 100).toFixed(1)}%</b></div></div><p className="containment-caveat">Containment is posterior mass around the MAP at grid-cell centers; it is not yet field-calibrated coverage.</p></article>
        <aside className="recommendation-card"><div className="scanline" /><p className="eyebrow accent">{status.should_stop ? 'TERMINATION CONDITION' : 'NEXT ARGUS RECOMMENDATION'}</p><h2>{status.should_stop ? readableAction(status.recommended_engineering_action) : `The next question. Experiment ${String(status.experiment_count + 1).padStart(2, '0')}.`}</h2><div className="coordinate-pair"><div><small>EXCITATION</small><strong>{experiment.source_x.toFixed(2)}, {experiment.source_y.toFixed(2)}</strong><span>{Math.round(experiment.source_x * session.panel.width_m * 1000)} × {Math.round(experiment.source_y * session.panel.height_m * 1000)} mm</span></div><div><small>RECEIVER</small><strong>{experiment.receiver_x.toFixed(2)}, {experiment.receiver_y.toFixed(2)}</strong><span>{Math.round(experiment.receiver_x * session.panel.width_m * 1000)} × {Math.round(experiment.receiver_y * session.panel.height_m * 1000)} mm</span></div></div><div className="signal-spec"><span><small>WAVEFORM</small><b>{experiment.waveform.toUpperCase()}</b></span><span><small>SWEEP</small><b>{(experiment.frequency_start_hz / 1000).toFixed(1)} → {(experiment.frequency_end_hz / 1000).toFixed(1)} kHz</b></span><span><small>DRIVE</small><b>{Math.round(experiment.amplitude * 100)}%</b></span><span><small>DURATION</small><b>{Math.round(experiment.duration_s * 1000)} ms</b></span></div><div className="rationale"><span>WHY THIS PROBE</span><p>{recommendation.explanation}</p></div><div className="score-row"><span>INFORMATION UTILITY / PROXY</span><strong>{recommendation.expected_information_gain.toFixed(2)} <small>relative</small></strong></div><button className="run-button" onClick={runNext} disabled={argus.busy || session.safety.emergency_stop.latched}><span>{session.safety.emergency_stop.latched ? 'EMERGENCY STOP LATCHED' : argus.busy ? 'PROCESSING WAVEFIELD…' : physical ? 'CONFIRM PLACEMENT · ACQUIRE' : status.should_stop ? 'RUN ONE MORE EXPERIMENT' : 'RUN EXPERIMENT'}</span><b>{String(status.experiment_count + 1).padStart(2, '0')}</b></button></aside>
      </section>
      <section className="candidate-section"><div className="section-heading"><div><p className="eyebrow">Planner audit</p><h2>Top candidate experiments</h2></div><span>score balances information, risk, calibration, trust, coverage, time, cost, and repetition</span></div><div className="candidate-table"><div className="candidate-head"><span>RANK / SOURCE → RECEIVER</span><span>INFO PROXY</span><span>DISAGREEMENT</span><span>COST</span><span>FINAL SCORE</span></div>{recommendation.top_candidates.map((candidate, index) => <div key={index} className={index === 0 ? 'selected-candidate' : ''}><span><b>{String(index + 1).padStart(2, '0')}</b> ({candidate.experiment.source_x.toFixed(2)},{candidate.experiment.source_y.toFixed(2)}) → ({candidate.experiment.receiver_x.toFixed(2)},{candidate.experiment.receiver_y.toFixed(2)})</span><span>{candidate.expected_information_gain.toFixed(3)}</span><span>{candidate.hypothesis_disagreement.toFixed(3)}</span><span>{candidate.experiment_cost.toFixed(3)}</span><strong>{candidate.final_score.toFixed(3)}</strong></div>)}</div></section>
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
    </div>
    <footer className="footer-rail"><span className={tab === 'interrogate' ? 'active' : ''}><b>01</b> ACQUIRE</span><i /><span><b>02</b> INTERPRET</span><i /><span><b>03</b> UPDATE BELIEF</span><i /><span><b>04</b> CHOOSE NEXT</span><p>RESEARCH PROTOTYPE · NOT A CERTIFIED STRUCTURAL-SAFETY SYSTEM · <button onClick={argus.calibrate} disabled={physical} title={physical ? 'Physical calibration requires acquired healthy-reference signals.' : undefined}>{physical ? 'PHYSICAL CALIBRATION REQUIRES REFERENCE SIGNALS' : session.calibration ? 'CALIBRATION ACTIVE' : 'RUN REFERENCE CALIBRATION'}</button></p></footer>
  </main>;
}
