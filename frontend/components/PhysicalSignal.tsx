'use client';

import { useRef, useState } from 'react';
import { SignalPlots } from '@/components/SignalPlots';
import type { MeasurementAnalysis, SessionState } from '@/types/argus';
import { MAX_CALIBRATION_JSON_BYTES, parseProbeTimingCalibration, type ProbeTimingCalibration } from '@/utils/probeCalibration';

interface Props {
  session: SessionState;
  analysis: MeasurementAnalysis | null;
  busy: boolean;
  onCapture: () => unknown;
  onUpload: (file: Blob) => unknown;
  onAcquireDevice: (device: 'serial_probe' | 'microphone', calibration?: ProbeTimingCalibration) => unknown;
  onRun: () => unknown;
}

export function PhysicalSignal({ session, analysis, busy, onCapture, onUpload, onAcquireDevice, onRun }: Props) {
  const uploadRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [calibration, setCalibration] = useState<ProbeTimingCalibration | null>(null);
  const [calibrationMessage, setCalibrationMessage] = useState('No operator calibration record loaded.');
  const blocked = busy || session.safety.emergency_stop.latched;
  const physical = session.mode === 'physical';
  const loadRecord = (contents: string) => {
    setCalibration(null);
    try {
      const record = parseProbeTimingCalibration(contents);
      setText(contents); setCalibration(record);
      setCalibrationMessage('Operator record loaded. The connected chip and complete frame will be checked during acquisition.');
    } catch (reason) { setCalibrationMessage(reason instanceof Error ? reason.message : 'Invalid operator record.'); }
  };
  const loadFile = async (file?: File) => {
    if (!file) return;
    setCalibration(null);
    if (file.size > MAX_CALIBRATION_JSON_BYTES) { setCalibrationMessage('Calibration JSON exceeds 32 KiB.'); return; }
    try { loadRecord(await file.text()); }
    catch { setCalibrationMessage('This calibration file could not be read.'); }
  };

  return <section className="secondary-page">
    <div className="secondary-header"><div><p className="eyebrow">Signal interpretation engine</p><h1>Measurement anatomy.</h1></div>
      <div className="acquisition-actions">
        <button className="ghost-button" onClick={onCapture} disabled={blocked}>BROWSER MICROPHONE</button>
        {physical && <button className="ghost-button" onClick={() => onAcquireDevice('serial_probe', calibration ?? undefined)} disabled={blocked || !calibration}>ACQUIRE CALIBRATED V2 PROBE</button>}
        <button className="ghost-button" onClick={() => uploadRef.current?.click()} disabled={blocked}>UPLOAD WAV</button>
        <input ref={uploadRef} hidden type="file" accept=".wav,audio/wav" onChange={(event) => { if (event.target.files?.[0]) onUpload(event.target.files[0]); event.target.value = ''; }} />
        <button className="run-button compact" onClick={onRun} disabled={physical || blocked}>{session.status.should_stop ? 'SIMULATE ONE MORE' : 'SIMULATE SIGNAL'}</button>
      </div>
    </div>
    {physical && <details className="engine-access" open>
      <summary>Serial v2 operator calibration</summary>
      <p>External bench evidence is required. This JSON declares prior checks of this chip&apos;s clock, trigger alignment, and DAC/receiver adapter. Loading it does not certify those checks or the specimen.</p>
      <label>Operator calibration JSON (maximum 32 KiB)
        <textarea aria-label="Operator timing calibration JSON" rows={8} value={text} placeholder="Paste the complete operator record from your external bench report."
          onChange={(event) => {
            setCalibration(null);
            if (new TextEncoder().encode(event.target.value).byteLength > MAX_CALIBRATION_JSON_BYTES) { setCalibrationMessage('Calibration JSON exceeds 32 KiB.'); return; }
            setText(event.target.value); setCalibrationMessage('Edited record must be checked again before acquisition.');
          }} />
      </label>
      <div className="acquisition-actions"><button className="ghost-button" disabled={blocked || !text.trim()} onClick={() => loadRecord(text)}>CHECK OPERATOR RECORD</button>
        <label>Upload recorded JSON <input type="file" accept=".json,application/json" disabled={blocked} onChange={(event) => { void loadFile(event.target.files?.[0]); event.target.value = ''; }} /></label>
        <button className="ghost-button" disabled={blocked} onClick={() => { setText(''); setCalibration(null); setCalibrationMessage('Operator record cleared from this page.'); }}>CLEAR RECORD</button>
      </div>
      <p role="status">{calibrationMessage}</p>
      {calibration && <p>Chip <code>{calibration.device_id}</code> · record <code>{calibration.calibration_id}</code> · {calibration.sample_rate_hz} Hz · reference SHA256 <code>{calibration.reference_sha256}</code></p>}
      <small>Adapter envelope: chirp or equal-endpoint sine/tone burst, 100 Hz to min(6000 Hz, 0.40 × acquisition rate), drive ≤ 0.60, window 20–250 ms. Unsupported recommendations are rejected before excitation. The 90-day record age is an operator policy.</small>
    </details>}
    <p className="research-disclaimer">Arrival localization stays gated until timing and adapter support are declared and checked. Plain browser/WAV recordings do not provide a known excitation trigger. No physical accuracy or structural-safety certification follows from a protocol check.</p>
    <SignalPlots analysis={analysis} />
  </section>;
}
