'use client';

import { useRef } from 'react';
import type { CSSProperties, PointerEvent } from 'react';
import type { SessionState } from '@/types/argus';

type VariableStyle = CSSProperties & Record<`--${string}`, string | number>;

function pointStyle(x: number, y: number): VariableStyle {
  return { '--x': `${Math.max(0, Math.min(1, x)) * 100}%`, '--y': `${Math.max(0, Math.min(1, y)) * 100}%` };
}

export function NarrativeTwin({ session }: { session?: SessionState }) {
  const stageRef = useRef<HTMLDivElement>(null);
  const experiment = session?.recommendation.experiment;
  const source = { x: experiment?.source_x ?? 0.16, y: experiment?.source_y ?? 0.72 };
  const receiver = { x: experiment?.receiver_x ?? 0.84, y: experiment?.receiver_y ?? 0.22 };
  const estimate = { x: session?.status.map_x ?? 0.57, y: session?.status.map_y ?? 0.48 };
  const experimentNumber = session ? String(session.status.experiment_count + 1).padStart(2, '0') : '01';

  const tilt = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - bounds.left) / bounds.width - 0.5;
    const y = (event.clientY - bounds.top) / bounds.height - 0.5;
    stageRef.current?.style.setProperty('--pointer-x', `${x * 7}deg`);
    stageRef.current?.style.setProperty('--pointer-y', `${y * -5}deg`);
    stageRef.current?.style.setProperty('--glow-x', `${(x + 0.5) * 100}%`);
    stageRef.current?.style.setProperty('--glow-y', `${(y + 0.5) * 100}%`);
  };

  const resetTilt = () => {
    stageRef.current?.style.setProperty('--pointer-x', '0deg');
    stageRef.current?.style.setProperty('--pointer-y', '0deg');
  };

  return <div
    ref={stageRef}
    className={`narrative-twin ${session ? 'session-twin' : 'landing-twin'}`}
    onPointerMove={tilt}
    onPointerLeave={resetTilt}
    role="img"
    aria-label="Animated digital twin showing an acoustic experiment interrogating a hidden structure"
  >
    <div className="twin-noise" />
    <div className="twin-glow" />
    <div className="twin-status"><span><i /> DIGITAL TWIN · LIVE</span><b>EXPERIMENT {experimentNumber}</b></div>
    <div className="twin-coordinate top-left">Y 0.000</div>
    <div className="twin-coordinate bottom-right">X 1.000</div>
    <div className="twin-viewport" aria-hidden="true">
      <div className="twin-world">
        <div className="twin-panel-depth" />
        <div className="twin-panel">
          <div className="twin-surface-grid" />
          <svg className="twin-field" viewBox="0 0 100 68" preserveAspectRatio="none">
            <defs>
              <linearGradient id="argusBeam" x1="0" x2="1">
                <stop offset="0" stopColor="#b7f55a" stopOpacity="0.9" />
                <stop offset="0.52" stopColor="#f19554" stopOpacity="0.85" />
                <stop offset="1" stopColor="#e8f3ee" stopOpacity="0.7" />
              </linearGradient>
              <radialGradient id="argusBelief">
                <stop offset="0" stopColor="#f19554" stopOpacity="0.8" />
                <stop offset="0.45" stopColor="#b7f55a" stopOpacity="0.28" />
                <stop offset="1" stopColor="#b7f55a" stopOpacity="0" />
              </radialGradient>
            </defs>
            <path className="twin-beam-shadow" d={`M ${source.x * 100} ${source.y * 68} Q 50 8 ${receiver.x * 100} ${receiver.y * 68}`} />
            <path className="twin-beam" d={`M ${source.x * 100} ${source.y * 68} Q 50 8 ${receiver.x * 100} ${receiver.y * 68}`} />
            <ellipse cx={estimate.x * 100} cy={estimate.y * 68} rx="17" ry="15" fill="url(#argusBelief)" />
            <ellipse className="twin-credible-ring" cx={estimate.x * 100} cy={estimate.y * 68} rx="10" ry="8" />
          </svg>
          <div className="twin-defect" style={pointStyle(estimate.x, estimate.y)}><span /><i /></div>
          <div className="twin-wave-origin" style={pointStyle(source.x, source.y)}><i /><i /><i /></div>
          <div className="twin-probe source" style={pointStyle(source.x, source.y)}><span>TX</span><i /></div>
          <div className="twin-probe receiver" style={pointStyle(receiver.x, receiver.y)}><span>RX</span><i /></div>
        </div>
        <div className="twin-axis axis-x"><i /><span>PHYSICAL X</span></div>
        <div className="twin-axis axis-y"><i /><span>PHYSICAL Y</span></div>
      </div>
    </div>
    <div className="twin-readout readout-wave"><small>WAVEFIELD</small><strong>{experiment?.waveform.replaceAll('_', ' ').toUpperCase() ?? 'CODED CHIRP'}</strong><span>{experiment ? `${(experiment.frequency_start_hz / 1000).toFixed(1)}–${(experiment.frequency_end_hz / 1000).toFixed(1)} kHz` : '1.2–6.2 kHz'}</span></div>
    <div className="twin-readout readout-belief"><small>HIDDEN STATE</small><strong>{session ? `H/H₀ ${session.status.normalized_entropy.toFixed(3)}` : 'UNOBSERVED'}</strong><span>{session ? `R90 ${session.status.posterior_containment.radius90_mm.toFixed(1)} mm` : 'Waiting for evidence'}</span></div>
    <div className="twin-caption"><span>01</span><p>Sound enters the object. Competing explanations become visible. ARGUS chooses the question that separates them.</p></div>
  </div>;
}

const STORY = [
  { number: '01', act: 'EXCITE', title: 'Ask the object.', copy: 'A safe, coded vibration turns an opaque structure into a measurable response.', metric: 'CONTROLLED ENERGY' },
  { number: '02', act: 'LISTEN', title: 'Capture what returns.', copy: 'Arrival time, phase, spectrum and amplitude carry evidence about hidden paths.', metric: 'RAW WAVEFORM' },
  { number: '03', act: 'BELIEVE', title: 'Keep every possibility alive.', copy: 'Bayesian inference concentrates evidence without pretending uncertainty disappeared.', metric: 'POSTERIOR FIELD' },
  { number: '04', act: 'CHOOSE', title: 'Make the next measurement matter.', copy: 'ARGUS selects the geometry and waveform most likely to split the remaining hypotheses.', metric: 'EXPECTED ΔH' },
];

export function LandingStory() {
  return <section className="landing-story" aria-labelledby="story-title">
    <div className="story-intro"><p className="eyebrow accent">ONE OBJECT · FOUR ACTS · A CLOSED LOOP</p><h2 id="story-title">From silence to a defensible next move.</h2><span>Most systems wait for data. ARGUS designs the next piece of evidence.</span></div>
    <div className="story-track">
      <div className="story-signal"><i /></div>
      {STORY.map((item, index) => <article key={item.number} style={{ '--story-delay': `${index * 140}ms` } as VariableStyle}>
        <div><b>{item.number}</b><small>{item.act}</small></div>
        <h3>{item.title}</h3><p>{item.copy}</p><span>{item.metric}</span>
      </article>)}
    </div>
  </section>;
}

export function ExperimentStoryline({ session, busy }: { session: SessionState; busy: boolean }) {
  const experiment = session.recommendation.experiment;
  const stages = [
    { label: 'EXCITE', value: `${experiment.waveform.replaceAll('_', ' ').toUpperCase()} · ${(experiment.frequency_start_hz / 1000).toFixed(1)}–${(experiment.frequency_end_hz / 1000).toFixed(1)} kHz` },
    { label: 'LISTEN', value: `TX ${experiment.source_x.toFixed(2)},${experiment.source_y.toFixed(2)} → RX ${experiment.receiver_x.toFixed(2)},${experiment.receiver_y.toFixed(2)}` },
    { label: 'INFER', value: `ENTROPY ${session.status.normalized_entropy.toFixed(3)} · CEP50 ${session.status.posterior_containment.cep50_mm.toFixed(1)} mm` },
    { label: 'CHOOSE', value: `${session.recommendation.action_type.toUpperCase()} · ΔH ${session.recommendation.expected_information_gain.toFixed(3)}` },
  ];
  return <section className={`experiment-storyline ${busy ? 'is-running' : ''}`} aria-label="Live ARGUS experiment narrative">
    <div className="storyline-heading"><span>THE EXPERIMENT, AS A STORY</span><b>{busy ? 'WAVEFIELD IN FLIGHT' : session.status.should_stop ? 'EVIDENCE REVIEW' : 'READY FOR NEXT QUESTION'}</b></div>
    <div className="storyline-track"><div className="storyline-pulse" />{stages.map((stage, index) => <article key={stage.label}>
      <i>{String(index + 1).padStart(2, '0')}</i><div><small>{stage.label}</small><strong>{stage.value}</strong></div>
    </article>)}</div>
  </section>;
}
