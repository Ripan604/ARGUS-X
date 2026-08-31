'use client';

import Link from 'next/link';
import { useState } from 'react';

const steps = [
  { id: 'panel', number: '01', label: 'MARK PANEL', title: 'Shape a repeatable test surface.', detail: 'Use a sacrificial 600 × 400 mm board. Mark eight perimeter measurement points, six hidden-anomaly locations underneath, and four fixed foam supports.' },
  { id: 'devices', number: '02', label: 'ASSIGN DEVICES', title: 'Give every device one stable job.', detail: 'Laptop A runs ARGUS. The phone is the movable microphone receiver. Laptop B displays coordinates, monitors the run, and keeps backup WAV files.' },
  { id: 'geometry', number: '03', label: 'PLACE HARDWARE', title: 'Control the geometry before recording.', detail: 'Release a pendulum impact at TX, hold the phone microphone 2–5 mm above RX, and tape a reversible washer or damping patch beneath the panel.' },
  { id: 'capture', number: '04', label: 'RECORD', title: 'Capture one trace the same way every time.', detail: 'Place TX and RX, begin capture, release the impact, preserve 120 ms around the event, save the metadata, and repeat five times before moving anything.' },
  { id: 'dataset', number: '05', label: 'BUILD DATASET', title: 'Create a location-held-out response bank.', detail: 'Begin with 420 WAV files: seven physical conditions, twelve source–receiver pairs, and five repeats. Keep one complete anomaly location blind.' },
] as const;

function PanelScene() {
  const measurements = [
    ['M1', '8%', '8%'], ['M2', '50%', '8%'], ['M3', '92%', '8%'], ['M4', '92%', '50%'],
    ['M5', '92%', '92%'], ['M6', '50%', '92%'], ['M7', '8%', '92%'], ['M8', '8%', '50%'],
  ];
  const anomalies = [
    ['A1', '30%', '32%'], ['A2', '50%', '32%'], ['A3', '70%', '32%'],
    ['A4', '30%', '68%'], ['A5', '50%', '68%'], ['A6', '70%', '68%'],
  ];
  return <div className="setup-panel-scene">
    <div className="setup-width">600 MM</div><div className="setup-height">400 MM</div>
    <div className="setup-board" aria-label="Top view of 600 by 400 millimetre panel">
      {measurements.map(([label, left, top]) => <span className="setup-measurement" style={{ left, top }} key={label}>{label}</span>)}
      {anomalies.map(([label, left, top]) => <span className="setup-anomaly" style={{ left, top }} key={label}>{label}</span>)}
      {['nw', 'ne', 'sw', 'se'].map((corner) => <span className={`setup-foam ${corner}`} key={corner}>FOAM</span>)}
    </div>
    <div className="setup-legend"><span><i className="tx-dot" />M1–M8 SOURCE OR RECEIVER</span><span><i className="anomaly-dot" />A1–A6 UNDERSIDE ANOMALY</span></div>
  </div>;
}

function DeviceScene() {
  return <div className="setup-device-flow">
    <article><small>CONTROL</small><strong>LAPTOP A</strong><span>ARGUS · API · database</span></article>
    <i>LOCAL WI-FI</i>
    <article className="active"><small>RECEIVER</small><strong>PHONE</strong><span>microphone · camera · /probe</span></article>
    <i>LOCAL WI-FI</i>
    <article><small>OPERATOR</small><strong>LAPTOP B</strong><span>coordinates · backup · edge node</span></article>
    <div className="setup-panel-link">PHYSICAL PANEL <b>TX IMPACT → RX PHONE</b></div>
  </div>;
}

function GeometryScene() {
  return <div className="setup-side-scene">
    <div className="pendulum"><span /><i /><b>FIXED RELEASE ANGLE</b></div>
    <div className="phone-shape"><span>PHONE</span><i /><small>MICROPHONE</small></div>
    <div className="mic-gap">2–5 MM GAP</div>
    <div className="panel-edge"><span className="tx-label">TX</span><span className="rx-label">RX</span></div>
    <div className="hidden-washer">WASHER + TAPE</div>
    <div className="foam-block left">FOAM</div><div className="foam-block right">FOAM</div>
    <p>Keep the panel support, impact angle, phone orientation, and microphone gap unchanged within each condition.</p>
  </div>;
}

function CaptureScene() {
  const items = [
    ['1', 'PLACE', 'Match requested TX and RX'], ['2', 'RECORD', 'Start in a quiet room'],
    ['3', 'RELEASE', 'Use the marked pendulum angle'], ['4', 'TRIM', 'Impact begins 10–20 ms in'],
    ['5', 'SAVE', 'WAV + complete metadata'],
  ];
  return <div className="setup-capture-flow">
    {items.map(([number, title, detail], index) => <div className="capture-step" key={number}><article><b>{number}</b><strong>{title}</strong><span>{detail}</span></article>{index < items.length - 1 && <i>→</i>}</div>)}
    <p>REPEAT ×5 BEFORE CHANGING THE SOURCE, RECEIVER, SUPPORTS, OR ANOMALY</p>
  </div>;
}

function DatasetScene() {
  return <div className="setup-dataset-scene">
    <div className="dataset-math"><article><strong>7</strong><span>CONDITIONS</span><small>healthy + A1–A6</small></article><b>×</b><article><strong>12</strong><span>TX→RX PAIRS</span><small>same set for every state</small></article><b>×</b><article><strong>5</strong><span>REPEATS</span><small>new physical acquisition</small></article><b>=</b><article className="total"><strong>420</strong><span>WAV FILES</span><small>starter response bank</small></article></div>
    <div className="dataset-split"><article><small>DEVELOPMENT</small><b>HEALTHY + A1–A4</b></article><article><small>VALIDATION</small><b>A5 · COMPLETE LOCATION</b></article><article className="blind"><small>BLIND TEST</small><b>A6 · TRUTH SEALED</b></article></div>
    <p>Never randomly mix repeated WAV files from one physical location across training and testing.</p>
  </div>;
}

export default function PhysicalSetupPage() {
  const [active, setActive] = useState(0);
  const step = steps[active];
  return <main className="setup-shell">
    <header className="setup-nav">
      <Link href="/" className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS</strong><small>ADAPTIVE PHYSICAL INTELLIGENCE</small></div></Link>
      <div><Link href="/simulator" className="probe-link">VIRTUAL LAB</Link><Link href="/probe" className="probe-link">OPEN PHONE PROBE</Link><Link href="/" className="ghost-button setup-home-link">BACK TO ARGUS</Link></div>
    </header>
    <section className="setup-hero">
      <div><p className="eyebrow accent">STUDENT PHYSICAL DATA PLAYBOOK</p><h1>Build a response bank<br /><em>with what you have.</em></h1></div>
      <p>Two laptops, one phone, one sacrificial panel, and a repeatable impact are enough for an honest audio-band physical proof of concept.</p>
    </section>
    <nav className="setup-step-nav" aria-label="Physical setup steps">
      {steps.map((item, index) => <button key={item.id} className={active === index ? 'active' : ''} onClick={() => setActive(index)}><b>{item.number}</b><span>{item.label}</span></button>)}
    </nav>
    <section className="setup-workspace">
      <div className="setup-step-copy"><p className="eyebrow">STEP {step.number} · {step.label}</p><h2>{step.title}</h2><p>{step.detail}</p><div className="setup-caution">DEMO BOUNDARY <b>Audio-band anomaly surrogate—not certified ultrasonic NDT.</b></div></div>
      <div className="setup-visual">
        {step.id === 'panel' && <PanelScene />}{step.id === 'devices' && <DeviceScene />}{step.id === 'geometry' && <GeometryScene />}{step.id === 'capture' && <CaptureScene />}{step.id === 'dataset' && <DatasetScene />}
      </div>
    </section>
    <footer className="setup-footer"><button onClick={() => setActive((value) => Math.max(0, value - 1))} disabled={active === 0}>← PREVIOUS</button><span>STEP {active + 1} OF {steps.length}</span><button onClick={() => setActive((value) => Math.min(steps.length - 1, value + 1))} disabled={active === steps.length - 1}>NEXT →</button></footer>
  </main>;
}
