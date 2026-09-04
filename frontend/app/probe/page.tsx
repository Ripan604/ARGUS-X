'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { getApiUrl, argusApi } from '@/services/api';
import type { SessionState } from '@/types/argus';

type Point = { x: number; y: number };

function recommendationKey(state: SessionState): string {
  return JSON.stringify(state.recommendation.experiment);
}

function bilinear(corners: Point[], x: number, y: number): Point | null {
  if (corners.length !== 4) return null;
  const [a, b, c, d] = corners;
  return {
    x: (1 - x) * (1 - y) * a.x + x * (1 - y) * b.x + x * y * c.x + (1 - x) * y * d.x,
    y: (1 - x) * (1 - y) * a.y + x * (1 - y) * b.y + x * y * c.y + (1 - x) * y * d.y,
  };
}

export default function ProbePage() {
  const [nodeId] = useState(() => `phone-${Math.random().toString(36).slice(2, 10)}`);
  const [sessionId, setSessionId] = useState('');
  const [session, setSession] = useState<SessionState | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({});
  const [permissions, setPermissions] = useState<Record<string, string>>({});
  const [streaming, setStreaming] = useState('idle');
  const [message, setMessage] = useState('Enter the ARGUS session ID shown on Laptop A.');
  const [orientation, setOrientation] = useState({ alpha: 0, beta: 0, gamma: 0 });
  const [motion, setMotion] = useState(0);
  const [corners, setCorners] = useState<Point[]>([]);
  const [manual, setManual] = useState({ x: 0.5, y: 0.5 });
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const lastRecommendation = useRef('');

  useEffect(() => {
    const detected = {
      microphone: Boolean(navigator.mediaDevices?.getUserMedia),
      camera: Boolean(navigator.mediaDevices?.getUserMedia),
      motion: 'DeviceMotionEvent' in window,
      orientation: 'DeviceOrientationEvent' in window,
      touch: navigator.maxTouchPoints > 0,
      websocket: 'WebSocket' in window,
    };
    const capabilityTimer = window.setTimeout(() => setCapabilities(detected), 0);
    const onOrientation = (event: DeviceOrientationEvent) => setOrientation({ alpha: event.alpha ?? 0, beta: event.beta ?? 0, gamma: event.gamma ?? 0 });
    const onMotion = (event: DeviceMotionEvent) => { const value = event.accelerationIncludingGravity; setMotion(Math.hypot(value?.x ?? 0, value?.y ?? 0, value?.z ?? 0)); };
    window.addEventListener('deviceorientation', onOrientation);
    window.addEventListener('devicemotion', onMotion);
    return () => { window.clearTimeout(capabilityTimer); window.removeEventListener('deviceorientation', onOrientation); window.removeEventListener('devicemotion', onMotion); cameraStream.current?.getTracks().forEach((track) => track.stop()); socket.current?.close(); };
  }, []);

  const connect = async () => {
    try {
      const state = await argusApi.getSession(sessionId.trim());
      setSessionId(state.id); setSession(state);
      lastRecommendation.current = recommendationKey(state);
      setManual({ x: state.recommendation.experiment.receiver_x, y: state.recommendation.experiment.receiver_y });
      setMessage('Probe linked. Follow the source and receiver coordinates below.');
      await argusApi.registerProbe(nodeId, capabilities);
      const base = getApiUrl().replace(/^http/, 'ws');
      socket.current?.close();
      const connection = new WebSocket(`${base}/ws/probe/${encodeURIComponent(nodeId)}`);
      socket.current = connection;
      connection.onopen = () => { connection.send(JSON.stringify({ type: 'hello', node_type: 'phone', capabilities, session_id: state.id })); setStreaming('connected'); };
      connection.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'session_state') {
            const next = payload.state as SessionState;
            setSession(next);
            const key = recommendationKey(next);
            if (key !== lastRecommendation.current) {
              lastRecommendation.current = key;
              setManual({ x: next.recommendation.experiment.receiver_x, y: next.recommendation.experiment.receiver_y });
            }
          }
        } catch { setMessage('ARGUS sent an unreadable probe update. Reconnect this phone.'); }
      };
      connection.onerror = () => { if (socket.current === connection) { setStreaming('error'); setMessage('The live probe connection failed. Check Wi-Fi and the Laptop A server.'); } };
      connection.onclose = () => { if (socket.current === connection) setStreaming('disconnected'); };
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : String(reason)); }
  };

  useEffect(() => {
    if (!socket.current || streaming !== 'connected') return;
    const timer = window.setInterval(() => {
      if (socket.current?.readyState === WebSocket.OPEN) {
        socket.current.send(JSON.stringify({ type: 'heartbeat', node_type: 'phone', capabilities, session_id: session?.id }));
        socket.current.send(JSON.stringify({ type: 'state', session_id: session?.id }));
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [streaming, capabilities, session?.id]);

  const enableCamera = async () => {
    try {
      cameraStream.current?.getTracks().forEach((track) => track.stop());
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
      cameraStream.current = stream; if (videoRef.current) videoRef.current.srcObject = stream;
      setPermissions((old) => ({ ...old, camera: 'granted' })); setCorners([]);
    } catch { setPermissions((old) => ({ ...old, camera: 'denied or unavailable' })); }
  };

  const requestMotionPermission = async () => {
    try {
      const constructor = DeviceMotionEvent as typeof DeviceMotionEvent & { requestPermission?: () => Promise<PermissionState> };
      const result = constructor.requestPermission ? await constructor.requestPermission() : 'granted';
      setPermissions((old) => ({ ...old, motion: result }));
    } catch { setPermissions((old) => ({ ...old, motion: 'denied or unavailable' })); }
  };

  const captureAudio = async () => {
    if (!session) return;
    setStreaming('recording');
    let stream: MediaStream | null = null;
    let context: AudioContext | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let processor: ScriptProcessorNode | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }, video: false });
      setPermissions((old) => ({ ...old, microphone: 'granted' }));
      context = new AudioContext(); source = context.createMediaStreamSource(stream); processor = context.createScriptProcessor(2048, 1, 1); const chunks: Float32Array[] = [];
      processor.onaudioprocess = (event) => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      source.connect(processor); processor.connect(context.destination);
      await new Promise((resolve) => window.setTimeout(resolve, Math.max(350, session.recommendation.experiment.duration_s * 1000 + 250)));
      const samples = Array.from(chunks.flatMap((chunk) => Array.from(chunk))).slice(0, Math.round(context.sampleRate * Math.max(0.12, session.recommendation.experiment.duration_s)));
      if (samples.length < 8) throw new Error('The phone microphone returned no usable samples.');
      const experiment = { ...session.recommendation.experiment, receiver_x: manual.x, receiver_y: manual.y };
      const measurementId = `${nodeId}-${typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : Date.now()}`;
      const result = await argusApi.sendProbeMeasurement({ session_id: session.id, node_id: nodeId, measurement_id: measurementId, sample_rate: context.sampleRate, samples, experiment, timestamp: new Date().toISOString(), sensor_metadata: { orientation, acceleration_rms: motion, acceleration_deviation_g: Math.abs(motion - 9.80665) / 9.80665, visual_position_error: corners.length === 4 ? 0.015 : 0.08, actual_receiver_location: manual, corner_count: corners.length } });
      setSession(result.state);
      lastRecommendation.current = recommendationKey(result.state);
      setManual({ x: result.state.recommendation.experiment.receiver_x, y: result.state.recommendation.experiment.receiver_y });
      setMessage(`Measurement accepted · coupling proxy ${Number(result.quality.coupling_quality ?? 0).toFixed(2)} · signal proxy ${Number(result.quality.signal_quality ?? 0).toFixed(2)}`); setStreaming('connected');
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : String(reason)); setStreaming('error');
    } finally {
      try { processor?.disconnect(); } catch { /* already disconnected */ }
      try { source?.disconnect(); } catch { /* already disconnected */ }
      stream?.getTracks().forEach((track) => track.stop());
      if (context && context.state !== 'closed') await context.close();
    }
  };

  const overlay = useMemo(() => {
    if (!session) return { source: null, receiver: null, estimate: null };
    return {
      source: bilinear(corners, session.recommendation.experiment.source_x, session.recommendation.experiment.source_y),
      receiver: bilinear(corners, session.recommendation.experiment.receiver_x, session.recommendation.experiment.receiver_y),
      estimate: bilinear(corners, session.status.map_x, session.status.map_y),
    };
  }, [corners, session]);

  return <main className="probe-shell"><header><div><b>ARGUS</b><span>SMART PROBE · ZERO-INSTALL WEB CLIENT</span></div><strong className={`probe-state ${streaming}`}>{streaming.toUpperCase()}</strong></header>
    <section className="probe-intro"><p>Research commodity-sensor interface</p><h1>Turn this phone into an ARGUS observation node.</h1><span>{message}</span><small>Not a certified NDE instrument. Phone audio and motion values are quality proxies and must not be presented as ultrasonic validation.</small></section>
    <section className="probe-connect"><label>SESSION ID<input value={sessionId} onChange={(event) => setSessionId(event.target.value)} placeholder="Paste from Laptop A" /></label><button onClick={connect} disabled={!sessionId.trim()}>CONNECT TO ARGUS</button><code>{nodeId}</code></section>
    <section className="capability-strip">{Object.entries(capabilities).map(([name, available]) => <div key={name}><i className={available ? 'available' : ''} /><b>{name.toUpperCase()}</b><span>{available ? permissions[name] ?? 'available' : 'unavailable'}</span></div>)}</section>
    {session && <><section className="probe-command"><p>NEXT PHYSICAL ACTION · {session.recommendation.action_type.toUpperCase()}</p><div><article><small>SOURCE</small><strong>{session.recommendation.experiment.source_x.toFixed(3)}, {session.recommendation.experiment.source_y.toFixed(3)}</strong><span>{Math.round(session.recommendation.experiment.source_x * session.panel.width_m * 1000)} × {Math.round(session.recommendation.experiment.source_y * session.panel.height_m * 1000)} mm</span></article><b>→</b><article><small>RECEIVER / PHONE</small><strong>{session.recommendation.experiment.receiver_x.toFixed(3)}, {session.recommendation.experiment.receiver_y.toFixed(3)}</strong><span>{Math.round(session.recommendation.experiment.receiver_x * session.panel.width_m * 1000)} × {Math.round(session.recommendation.experiment.receiver_y * session.panel.height_m * 1000)} mm</span></article></div><p>{session.recommendation.explanation}</p><button onClick={captureAudio} disabled={streaming === 'recording'}>{streaming === 'recording' ? 'RECORDING MEASUREMENT…' : 'CAPTURE MICROPHONE RESPONSE'}</button></section>
      <section className="probe-camera"><div className="probe-section-title"><div><p>CAMERA REGISTRATION</p><h2>Tap panel corners clockwise.</h2></div><div><button onClick={enableCamera}>ENABLE CAMERA</button><button onClick={requestMotionPermission}>ENABLE MOTION</button><button onClick={() => setCorners([])}>RESET CORNERS</button></div></div><div className="probe-video-stage" onClick={(event) => { if (corners.length >= 4) return; const rect = event.currentTarget.getBoundingClientRect(); setCorners((old) => [...old, { x: (event.clientX - rect.left) / rect.width, y: (event.clientY - rect.top) / rect.height }]); }}><video ref={videoRef} autoPlay playsInline muted />{corners.map((point, index) => <i key={index} className="corner-point" style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}>{index + 1}</i>)}{overlay.source && <i className="overlay-point source" style={{ left: `${overlay.source.x * 100}%`, top: `${overlay.source.y * 100}%` }}>S</i>}{overlay.receiver && <i className="overlay-point receiver" style={{ left: `${overlay.receiver.x * 100}%`, top: `${overlay.receiver.y * 100}%` }}>R</i>}{overlay.estimate && <i className="overlay-point estimate" style={{ left: `${overlay.estimate.x * 100}%`, top: `${overlay.estimate.y * 100}%` }}>?</i>}</div><div className="probe-telemetry"><span>CORNERS <b>{corners.length}/4</b></span><span>ORIENTATION <b>{orientation.beta.toFixed(1)}° / {orientation.gamma.toFixed(1)}°</b></span><span>MOTION <b>{motion.toFixed(2)} m/s² proxy</b></span><span>TIMESTAMP <b>{new Date().toLocaleTimeString()}</b></span></div></section>
      <section className="manual-position"><p>ACTUAL PHONE / RECEIVER POSITION · SENT WITH THE WAVEFORM</p><label>MANUAL X <input type="range" min="0" max="1" step="0.01" value={manual.x} onChange={(event) => setManual((old) => ({ ...old, x: Number(event.target.value) }))} /><b>{manual.x.toFixed(2)}</b></label><label>MANUAL Y <input type="range" min="0" max="1" step="0.01" value={manual.y} onChange={(event) => setManual((old) => ({ ...old, y: Number(event.target.value) }))} /><b>{manual.y.toFixed(2)}</b></label></section></>}
  </main>;
}
