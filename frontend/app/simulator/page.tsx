'use client';

import Link from 'next/link';
import type { CSSProperties, KeyboardEvent, PointerEvent } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  DEFAULT_VIRTUAL_CONFIG,
  MATERIALS,
  clamp,
  simulateVirtualExperiment,
  type DefectType,
  type MaterialKey,
  type NormalizedPoint,
  type SensorMode,
  type SpectrumPoint,
  type VirtualExperimentConfig,
  type VirtualSimulation,
} from '@/utils/virtualAcoustics';

type MarkerKey = 'source' | 'receiver' | 'defect';

const DEFECT_LABELS: Record<DefectType, string> = {
  mass_loading: 'Washer / mass loading',
  delamination: 'Delamination surrogate',
  crack: 'Open crack surrogate',
  damping_patch: 'Damping patch',
};

const MARKER_LABELS: Record<MarkerKey, string> = { source: 'TX', receiver: 'RX', defect: 'D' };

function RangeControl({ label, value, display, min, max, step, onChange }: { label: string; value: number; display: string; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return <label className="virtual-range"><span>{label}<b>{display}</b></span><input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function wavBlob(samples: number[], sampleRateHz: number) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeText = (offset: number, value: string) => [...value].forEach((character, index) => view.setUint8(offset + index, character.charCodeAt(0)));
  writeText(0, 'RIFF'); view.setUint32(4, 36 + samples.length * 2, true); writeText(8, 'WAVE'); writeText(12, 'fmt ');
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, sampleRateHz, true);
  view.setUint32(28, sampleRateHz * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true); writeText(36, 'data'); view.setUint32(40, samples.length * 2, true);
  const peak = Math.max(1, ...samples.map((sample) => Math.abs(sample)));
  samples.forEach((sample, index) => view.setInt16(44 + index * 2, Math.round(clamp(sample / peak, -1, 1) * 32767 * 0.96), true));
  return new Blob([buffer], { type: 'audio/wav' });
}

function canvasColors() {
  const styles = getComputedStyle(document.documentElement);
  const value = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;
  return { acid: value('--acid', '#b7f55a'), orange: value('--orange', '#f19554'), muted: value('--muted', '#7e918b'), line: value('--line', '#263732'), field: value('--field', '#08100e'), ink: value('--ink', '#eaf4ef') };
}

function drawFrame(canvas: HTMLCanvasElement) {
  const width = Math.max(320, canvas.clientWidth);
  const height = Math.max(190, canvas.clientHeight);
  const ratio = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const context = canvas.getContext('2d');
  if (!context) return null;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  const colors = canvasColors();
  context.fillStyle = colors.field;
  context.fillRect(0, 0, width, height);
  context.strokeStyle = colors.line;
  context.lineWidth = 1;
  const left = 48, right = width - 15, top = 17, bottom = height - 31;
  for (let index = 0; index <= 4; index += 1) {
    const y = top + (bottom - top) * index / 4;
    context.beginPath(); context.moveTo(left, y); context.lineTo(right, y); context.stroke();
  }
  for (let index = 0; index <= 5; index += 1) {
    const x = left + (right - left) * index / 5;
    context.beginPath(); context.moveTo(x, top); context.lineTo(x, bottom); context.stroke();
  }
  context.font = '8px IBM Plex Mono, Consolas, monospace';
  context.fillStyle = colors.muted;
  return { context, colors, width, height, left, right, top, bottom };
}

function SignalPlot({ simulation }: { simulation: VirtualSimulation }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const frame = drawFrame(canvas);
      if (!frame) return;
      const { context, colors, left, right, top, bottom } = frame;
      const maximum = Math.max(0.05, simulation.metrics.peakAmplitude * 1.08);
      context.fillText('+A', 18, top + 4); context.fillText('0', 29, (top + bottom) / 2 + 3); context.fillText('−A', 18, bottom + 3);
      for (let tick = 0; tick <= 5; tick += 1) context.fillText(`${Math.round(simulation.config.durationMs * tick / 5)}`, left + (right - left) * tick / 5 - (tick === 5 ? 15 : 4), bottom + 18);
      context.fillText('TIME (MS)', Math.max(left, right - 55), bottom + 27);
      const direct = simulation.paths[0], scatter = simulation.paths[1];
      [direct, scatter].forEach((path) => {
        const x = left + (right - left) * path.arrivalMs / simulation.config.durationMs;
        if (x < left || x > right) return;
        context.strokeStyle = path.kind === 'direct' ? colors.acid : colors.orange;
        context.globalAlpha = 0.55; context.beginPath(); context.moveTo(x, top); context.lineTo(x, bottom); context.stroke(); context.globalAlpha = 1;
        context.fillStyle = path.kind === 'direct' ? colors.acid : colors.orange; context.fillText(path.kind === 'direct' ? 'DIRECT' : 'SCATTER', Math.min(x + 4, right - 43), top + (path.kind === 'direct' ? 10 : 22));
      });
      context.strokeStyle = colors.acid; context.lineWidth = 1.4; context.beginPath();
      const points = Math.max(2, Math.floor(right - left));
      for (let pixel = 0; pixel < points; pixel += 1) {
        const sampleIndex = Math.min(simulation.samples.length - 1, Math.floor(pixel / (points - 1) * (simulation.samples.length - 1)));
        const x = left + pixel / (points - 1) * (right - left);
        const y = (top + bottom) / 2 - simulation.samples[sampleIndex] / maximum * (bottom - top) * 0.48;
        if (pixel === 0) context.moveTo(x, y); else context.lineTo(x, y);
      }
      context.stroke();
    };
    draw();
    const observer = new ResizeObserver(draw); observer.observe(canvas); return () => observer.disconnect();
  }, [simulation]);
  return <canvas ref={ref} className="virtual-plot-canvas" role="img" aria-label={`Synthetic time trace lasting ${simulation.config.durationMs} milliseconds with direct arrival at ${simulation.metrics.directArrivalMs.toFixed(3)} milliseconds`} />;
}

function SpectrumPlot({ spectrum, peakFrequencyHz }: { spectrum: SpectrumPoint[]; peakFrequencyHz: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const frame = drawFrame(canvas);
      if (!frame || spectrum.length === 0) return;
      const { context, colors, left, right, top, bottom } = frame;
      const maximumFrequency = spectrum[spectrum.length - 1].frequencyHz;
      for (let tick = 0; tick <= 4; tick += 1) context.fillText(`${Math.round(maximumFrequency * tick / 4000)}`, left + (right - left) * tick / 4 - 5, bottom + 18);
      context.fillText('FREQUENCY (KHZ)', Math.max(left, right - 90), bottom + 27); context.fillText('0', 28, top + 3); context.fillText('−50', 17, top + (bottom - top) * 0.625 + 3); context.fillText('−80', 17, bottom + 3);
      context.strokeStyle = colors.orange; context.lineWidth = 1.4; context.beginPath();
      const points = Math.max(2, Math.floor(right - left));
      for (let pixel = 0; pixel < points; pixel += 1) {
        const index = Math.min(spectrum.length - 1, Math.floor(pixel / (points - 1) * (spectrum.length - 1)));
        const x = left + pixel / (points - 1) * (right - left);
        const y = top + clamp(-spectrum[index].magnitudeDb / 80, 0, 1) * (bottom - top);
        if (pixel === 0) context.moveTo(x, y); else context.lineTo(x, y);
      }
      context.stroke();
      const peakX = left + peakFrequencyHz / maximumFrequency * (right - left);
      context.fillStyle = colors.acid; context.beginPath(); context.arc(peakX, top + 3, 3, 0, 2 * Math.PI); context.fill(); context.fillText(`${(peakFrequencyHz / 1000).toFixed(2)} kHz`, Math.min(peakX + 6, right - 50), top + 10);
    };
    draw();
    const observer = new ResizeObserver(draw); observer.observe(canvas); return () => observer.disconnect();
  }, [peakFrequencyHz, spectrum]);
  return <canvas ref={ref} className="virtual-plot-canvas" role="img" aria-label={`Synthetic frequency spectrum with a peak at ${(peakFrequencyHz / 1000).toFixed(2)} kilohertz`} />;
}

function pathStyle(start: NormalizedPoint, end: NormalizedPoint, panelWidthMm: number, panelHeightMm: number): CSSProperties {
  const dx = end.x - start.x;
  const dy = (end.y - start.y) * panelHeightMm / panelWidthMm;
  return { left: `${start.x * 100}%`, top: `${start.y * 100}%`, width: `${Math.hypot(dx, dy) * 100}%`, transform: `rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)` };
}

function PanelBench({ config, activeMarker, runNumber, onActiveMarker, onPointChange }: { config: VirtualExperimentConfig; activeMarker: MarkerKey; runNumber: number; onActiveMarker: (marker: MarkerKey) => void; onPointChange: (marker: MarkerKey, point: NormalizedPoint) => void }) {
  const [dragging, setDragging] = useState<MarkerKey | null>(null);
  const pointFromEvent = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    return { x: clamp((event.clientX - bounds.left) / bounds.width, 0.01, 0.99), y: clamp((event.clientY - bounds.top) / bounds.height, 0.01, 0.99) };
  };
  const pointerDown = (event: PointerEvent<HTMLDivElement>) => {
    const selected = (event.target as HTMLElement).closest<HTMLElement>('[data-marker]')?.dataset.marker as MarkerKey | undefined;
    const marker = selected ?? activeMarker;
    onActiveMarker(marker); setDragging(marker); event.currentTarget.setPointerCapture(event.pointerId); onPointChange(marker, pointFromEvent(event));
  };
  const keyboardMove = (marker: MarkerKey, event: KeyboardEvent<HTMLButtonElement>) => {
    const movement = { ArrowLeft: [-1 / config.panelWidthMm, 0], ArrowRight: [1 / config.panelWidthMm, 0], ArrowUp: [0, -1 / config.panelHeightMm], ArrowDown: [0, 1 / config.panelHeightMm] }[event.key];
    if (!movement) return;
    event.preventDefault(); const point = config[marker]; onPointChange(marker, { x: clamp(point.x + movement[0], 0.01, 0.99), y: clamp(point.y + movement[1], 0.01, 0.99) });
  };
  const defectWidth = config.defectRadiusMm * 2 / config.panelWidthMm * 100;
  const defectHeight = config.defectRadiusMm * 2 / config.panelHeightMm * 100;
  return <div className="virtual-panel-wrap">
    <div className="virtual-panel-toolbar"><span>ACTIVE HANDLE</span>{(['source', 'receiver', 'defect'] as MarkerKey[]).map((marker) => <button type="button" key={marker} className={activeMarker === marker ? 'active' : ''} onClick={() => onActiveMarker(marker)}>{MARKER_LABELS[marker]}</button>)}</div>
    <div className={`virtual-panel dragging-${dragging ?? 'none'}`} style={{ aspectRatio: `${config.panelWidthMm} / ${config.panelHeightMm}` }} onPointerDown={pointerDown} onPointerMove={(event) => dragging && onPointChange(dragging, pointFromEvent(event))} onPointerUp={(event) => { setDragging(null); event.currentTarget.releasePointerCapture(event.pointerId); }} onPointerCancel={() => setDragging(null)} aria-label={`Virtual ${config.panelWidthMm} by ${config.panelHeightMm} millimetre panel`}>
      <i className="virtual-path direct" style={pathStyle(config.source, config.receiver, config.panelWidthMm, config.panelHeightMm)} />
      <i className="virtual-path scatter first" style={pathStyle(config.source, config.defect, config.panelWidthMm, config.panelHeightMm)} /><i className="virtual-path scatter second" style={pathStyle(config.defect, config.receiver, config.panelWidthMm, config.panelHeightMm)} />
      <span className="virtual-defect-zone" style={{ left: `${config.defect.x * 100}%`, top: `${config.defect.y * 100}%`, width: `${defectWidth}%`, height: `${defectHeight}%`, opacity: 0.3 + config.defectSeverity * 0.55 }} />
      <span key={`a-${runNumber}`} className="virtual-wavefront wave-one" style={{ left: `${config.source.x * 100}%`, top: `${config.source.y * 100}%` }} /><span key={`b-${runNumber}`} className="virtual-wavefront wave-two" style={{ left: `${config.source.x * 100}%`, top: `${config.source.y * 100}%` }} />
      {(['source', 'receiver', 'defect'] as MarkerKey[]).map((marker) => <button type="button" data-marker={marker} key={marker} className={`virtual-marker ${marker === 'source' ? 'tx' : marker === 'receiver' ? 'rx' : 'defect'} ${activeMarker === marker ? 'active' : ''}`} style={{ left: `${config[marker].x * 100}%`, top: `${config[marker].y * 100}%` }} onKeyDown={(event) => keyboardMove(marker, event)} aria-label={`${marker} at ${Math.round(config[marker].x * config.panelWidthMm)} by ${Math.round(config[marker].y * config.panelHeightMm)} millimetres. Drag or use arrow keys.`}>{MARKER_LABELS[marker]}</button>)}
    </div>
    <div className="virtual-panel-caption"><span>{config.panelWidthMm} MM</span><b>DRAG OR USE 1 MM ARROW-KEY STEPS</b><span>{config.panelHeightMm} MM</span></div>
  </div>;
}

export default function VirtualAcousticBench() {
  const [config, setConfig] = useState<VirtualExperimentConfig>(DEFAULT_VIRTUAL_CONFIG);
  const [activeMarker, setActiveMarker] = useState<MarkerKey>('source');
  const [runNumber, setRunNumber] = useState(1);
  const [savedRuns, setSavedRuns] = useState<Array<{ id: string; config: VirtualExperimentConfig; metrics: VirtualSimulation['metrics'] }>>([]);
  const effectiveConfig = useMemo(() => ({ ...config, seed: config.seed + runNumber * 7919 }), [config, runNumber]);
  const simulation = useMemo(() => simulateVirtualExperiment(effectiveConfig), [effectiveConfig]);
  const update = <Key extends keyof VirtualExperimentConfig>(key: Key, value: VirtualExperimentConfig[Key]) => setConfig((current) => ({ ...current, [key]: value }));
  const updatePoint = (marker: MarkerKey, point: NormalizedPoint) => setConfig((current) => ({ ...current, [marker]: point }));
  const updateCoordinateMm = (marker: MarkerKey, axis: 'x' | 'y', millimetres: number) => {
    const dimension = axis === 'x' ? config.panelWidthMm : config.panelHeightMm;
    updatePoint(marker, { ...config[marker], [axis]: clamp(millimetres / dimension, 0.01, 0.99) });
  };
  const baseFilename = `argus-${config.material}-tx${Math.round(config.source.x * config.panelWidthMm)}-${Math.round(config.source.y * config.panelHeightMm)}-rx${Math.round(config.receiver.x * config.panelWidthMm)}-${Math.round(config.receiver.y * config.panelHeightMm)}`;
  const downloadJson = () => downloadBlob(new Blob([JSON.stringify({ format: 'argus-virtual-trace-v1', generatedAt: new Date().toISOString(), ...simulation }, null, 2)], { type: 'application/json' }), `${baseFilename}.json`);
  const downloadCsv = () => {
    const rows = ['time_s,amplitude_normalized', ...simulation.samples.map((sample, index) => `${(index / simulation.config.sampleRateHz).toFixed(9)},${sample.toFixed(9)}`)];
    downloadBlob(new Blob([rows.join('\n')], { type: 'text/csv' }), `${baseFilename}.csv`);
  };
  const saveRun = () => setSavedRuns((runs) => [...runs, { id: `VIRTUAL-${String(runs.length + 1).padStart(3, '0')}`, config: simulation.config, metrics: simulation.metrics }]);
  const downloadManifest = () => downloadBlob(new Blob([JSON.stringify({ format: 'argus-virtual-manifest-v1', runs: savedRuns }, null, 2)], { type: 'application/json' }), 'argus-virtual-manifest.json');

  return <main className="virtual-lab-shell">
    <header className="virtual-lab-nav">
      <Link href="/" className="brand-lockup"><div className="brand-mark"><span /></div><div><strong>ARGUS</strong><small>VIRTUAL ACOUSTIC BENCH</small></div></Link>
      <div><span className="virtual-model-state"><i /> MODEL LIVE · {config.sampleRateHz / 1000} KHZ</span><Link href="/setup" className="probe-link">PHYSICAL GUIDE</Link><Link href="/" className="ghost-button virtual-home-link">BACK TO ARGUS</Link></div>
    </header>
    <section className="virtual-lab-hero">
      <div><p className="eyebrow accent">INTERACTIVE DIGITAL EXPERIMENT</p><h1>Move the experiment.<br /><em>Measure the consequence.</em></h1></div>
      <p>Drag the impact, receiver, and hidden defect. The browser computes a dispersive thin-plate response, defect scattering, four edge reflections, sensor transfer, and repeatable noise.</p>
    </section>
    <section className="virtual-lab-grid">
      <aside className="virtual-controls">
        <div><p className="eyebrow">MODEL INPUTS</p><h2>Experiment parameters</h2></div>
        <section className="virtual-control-section"><h3>01 · PANEL</h3><label>MATERIAL<select value={config.material} onChange={(event) => update('material', event.target.value as MaterialKey)}>{(Object.keys(MATERIALS) as MaterialKey[]).map((key) => <option value={key} key={key}>{MATERIALS[key].label}</option>)}</select></label><div className="virtual-number-grid"><label>WIDTH MM<input type="number" min="100" max="5000" value={config.panelWidthMm} onChange={(event) => update('panelWidthMm', clamp(event.target.valueAsNumber, 100, 5000))} /></label><label>HEIGHT MM<input type="number" min="100" max="5000" value={config.panelHeightMm} onChange={(event) => update('panelHeightMm', clamp(event.target.valueAsNumber, 100, 5000))} /></label></div><RangeControl label="THICKNESS" value={config.thicknessMm} display={`${config.thicknessMm.toFixed(1)} mm`} min={0.5} max={12} step={0.1} onChange={(value) => update('thicknessMm', value)} /></section>
        <section className="virtual-control-section"><h3>02 · EXCITATION + SENSOR</h3><RangeControl label="IMPACT ENERGY" value={config.impactEnergyJ} display={`${config.impactEnergyJ.toFixed(2)} J`} min={0.05} max={2} step={0.05} onChange={(value) => update('impactEnergyJ', value)} /><RangeControl label="CENTRE FREQUENCY" value={config.centerFrequencyHz} display={`${(config.centerFrequencyHz / 1000).toFixed(1)} kHz`} min={1000} max={16000} step={250} onChange={(value) => update('centerFrequencyHz', value)} /><RangeControl label="NOISE FLOOR" value={config.noiseFloorDb} display={`${config.noiseFloorDb} dBFS`} min={-80} max={-12} step={1} onChange={(value) => update('noiseFloorDb', value)} /><label>SENSOR MODEL<select value={config.sensorMode} onChange={(event) => update('sensorMode', event.target.value as SensorMode)}><option value="phone_microphone">Phone microphone · near field</option><option value="contact_accelerometer">Ideal contact accelerometer</option></select></label></section>
        <section className="virtual-control-section"><h3>03 · HIDDEN CONDITION</h3><label>DEFECT SURROGATE<select value={config.defectType} onChange={(event) => update('defectType', event.target.value as DefectType)}>{(Object.keys(DEFECT_LABELS) as DefectType[]).map((key) => <option value={key} key={key}>{DEFECT_LABELS[key]}</option>)}</select></label><RangeControl label="SEVERITY" value={config.defectSeverity} display={`${Math.round(config.defectSeverity * 100)}%`} min={0} max={1} step={0.01} onChange={(value) => update('defectSeverity', value)} /><RangeControl label="EFFECTIVE RADIUS" value={config.defectRadiusMm} display={`${config.defectRadiusMm.toFixed(0)} mm`} min={3} max={80} step={1} onChange={(value) => update('defectRadiusMm', value)} /></section>
        <details className="virtual-advanced"><summary>ADVANCED MODEL SETTINGS</summary><RangeControl label="EDGE REFLECTION" value={config.boundaryReflectivity} display={`${Math.round(config.boundaryReflectivity * 100)}%`} min={0} max={0.9} step={0.01} onChange={(value) => update('boundaryReflectivity', value)} /><RangeControl label="VELOCITY CALIBRATION" value={config.velocityScale} display={`${config.velocityScale.toFixed(2)}×`} min={0.6} max={1.4} step={0.01} onChange={(value) => update('velocityScale', value)} /><RangeControl label="SENSOR GAIN" value={config.sensorGain} display={`${config.sensorGain.toFixed(2)}×`} min={0.2} max={3} step={0.05} onChange={(value) => update('sensorGain', value)} /><RangeControl label="TRACE DURATION" value={config.durationMs} display={`${config.durationMs.toFixed(0)} ms`} min={40} max={200} step={5} onChange={(value) => update('durationMs', value)} /><label>SAMPLE RATE<select value={config.sampleRateHz} onChange={(event) => update('sampleRateHz', Number(event.target.value))}><option value={44100}>44.1 kHz</option><option value={48000}>48 kHz</option><option value={96000}>96 kHz</option></select></label></details>
      </aside>
      <div className="virtual-bench-column">
        <PanelBench config={config} activeMarker={activeMarker} runNumber={runNumber} onActiveMarker={setActiveMarker} onPointChange={updatePoint} />
        <div className="virtual-position-editor"><div><span>HANDLE</span><b>X POSITION</b><b>Y POSITION</b></div>{(['source', 'receiver', 'defect'] as MarkerKey[]).map((marker) => <label key={marker} className={activeMarker === marker ? 'active' : ''} onClick={() => setActiveMarker(marker)}><strong>{MARKER_LABELS[marker]}</strong><span><input aria-label={`${marker} x position in millimetres`} type="number" min="0" max={config.panelWidthMm} step="1" value={Math.round(config[marker].x * config.panelWidthMm)} onChange={(event) => updateCoordinateMm(marker, 'x', Number(event.target.value))} /> MM</span><span><input aria-label={`${marker} y position in millimetres`} type="number" min="0" max={config.panelHeightMm} step="1" value={Math.round(config[marker].y * config.panelHeightMm)} onChange={(event) => updateCoordinateMm(marker, 'y', Number(event.target.value))} /> MM</span></label>)}</div>
      </div>
      <aside className="virtual-readout" aria-live="polite">
        <div className="virtual-readout-title"><p className="eyebrow">SYNTHETIC MEASUREMENT</p><h2>Propagation result</h2><span>RUN {String(runNumber).padStart(3, '0')}</span></div>
        <div><small>FLEXURAL GROUP VELOCITY</small><strong>{simulation.metrics.groupVelocityMps.toFixed(1)} <span>m/s</span></strong></div>
        <div><small>DIRECT PATH / ARRIVAL</small><strong>{(simulation.metrics.directPathM * 1000).toFixed(1)} <span>mm</span></strong><em>{simulation.metrics.directArrivalMs.toFixed(3)} ms</em></div>
        <div><small>DEFECT-SCATTER DELAY</small><strong>{simulation.metrics.scatterDelayUs.toFixed(1)} <span>µs</span></strong><em>{(simulation.metrics.defectIntercept * 100).toFixed(0)}% ray overlap</em></div>
        <div><small>DOMINANT FREQUENCY</small><strong>{(simulation.metrics.peakFrequencyHz / 1000).toFixed(2)} <span>kHz</span></strong></div>
        <div><small>TRACE RMS / PEAK</small><strong>{simulation.metrics.rms.toFixed(4)}</strong><em>{simulation.metrics.peakAmplitude.toFixed(3)} peak {simulation.metrics.clipped ? '· CLIPS' : ''}</em></div>
        <div><small>TIME RESOLUTION</small><strong>{simulation.metrics.timeResolutionUs.toFixed(2)} <span>µs/sample</span></strong></div>
        <button type="button" className="run-button" onClick={() => setRunNumber((run) => run + 1)}><span>RUN NEW VIRTUAL IMPACT</span><b>→</b></button>
      </aside>
    </section>
    <section className="virtual-signal-section">
      <header><div><p className="eyebrow">MEASUREMENT OUTPUT</p><h2>Trace, spectrum, and propagation audit</h2></div><div className="virtual-export-actions"><button type="button" onClick={() => downloadBlob(wavBlob(simulation.samples, simulation.config.sampleRateHz), `${baseFilename}.wav`)}>DOWNLOAD WAV</button><button type="button" onClick={downloadCsv}>CSV</button><button type="button" onClick={downloadJson}>JSON + SETTINGS</button></div></header>
      <div className="virtual-plot-grid"><article><span>TIME RESPONSE · NORMALIZED SENSOR AMPLITUDE</span><SignalPlot simulation={simulation} /></article><article><span>HANN-WINDOWED FFT · RELATIVE DB</span><SpectrumPlot spectrum={simulation.spectrum} peakFrequencyHz={simulation.metrics.peakFrequencyHz} /></article></div>
      <div className="virtual-audit-grid"><div className="virtual-path-table"><div><span>PATH</span><span>LENGTH</span><span>ARRIVAL</span><span>REL. GAIN</span></div>{simulation.paths.map((path) => <article key={path.id} className={path.kind}><span><i />{path.label}</span><b>{(path.lengthM * 1000).toFixed(1)} mm</b><b>{path.arrivalMs.toFixed(3)} ms</b><b>{path.relativeGain.toFixed(3)}</b></article>)}</div><aside className="virtual-dataset-box"><p className="eyebrow">VIRTUAL DATASET QUEUE</p><strong>{savedRuns.length}</strong><span>parameter-complete run records</span><button type="button" onClick={saveRun}>ADD CURRENT RUN</button><button type="button" onClick={downloadManifest} disabled={savedRuns.length === 0}>DOWNLOAD MANIFEST</button><small>Download each trace as WAV; the manifest preserves material, geometry, defect truth, timing, and model settings.</small></aside></div>
    </section>
    <section className="virtual-model-note"><strong>WHAT THIS MODEL SOLVES</strong><p>Kirchhoff–Love dispersive flexural propagation, geometric defect scattering, first-order image-source edge reflections, material loss, sensor transfer, and seeded noise.</p><strong>WHAT REQUIRES REAL CALIBRATION</strong><p>Absolute microphone pressure, impact coupling, support impedance, anisotropy, temperature, manufacturing variability, and the mapping from a surrogate defect to real damage.</p></section>
    <p className="virtual-boundary">SYNTHETIC DATA · RESEARCH AND EXPERIMENT PLANNING ONLY · DO NOT PRESENT SIMULATOR-ONLY ACCURACY AS PHYSICAL VALIDATION</p>
  </main>;
}
