'use client';

import type { SessionState } from '@/types/argus';
export { SpatialScene as NarrativeTwin } from './SpatialScene';

const STORY = [
  { number: '01', act: 'EXCITE', title: 'Ask the object.', copy: 'Choose a source, a receiver and a waveform. Turn a hidden structure into an observable response.' },
  { number: '02', act: 'LISTEN', title: 'Read the response.', copy: 'Arrival time, frequency and amplitude become evidence about what could be happening inside.' },
  { number: '03', act: 'INFER', title: 'Hold the uncertainty.', copy: 'Update the probability of competing locations. Keep uncertainty visible with every observation.' },
  { number: '04', act: 'CHOOSE', title: 'Ask a better question.', copy: 'Use the remaining hypotheses to choose the next experiment. Repeat until the stopping criteria are met.' },
];
export function LandingStory() {
  return <section className="landing-story" aria-labelledby="story-title"><div className="story-intro"><p className="eyebrow accent">THE ARGUS METHOD / A CLOSED LOOP</p><h2 id="story-title">The next question<br />changes everything.</h2><span>Every measurement should earn its place. ARGUS connects physical signals to an explicit belief, then uses that belief to decide where to listen next.</span></div><div className="story-track">{STORY.map((item) => <article key={item.number}><div><b>{item.number}</b><small>{item.act}</small></div><h3>{item.title}</h3><p>{item.copy}</p></article>)}</div></section>;
}
export function ExperimentStoryline({ session, busy }: { session: SessionState; busy: boolean }) {
  const experiment = session.recommendation.experiment;
  const stages = [
    { label: 'Excite', value: `${experiment.waveform.replaceAll('_', ' ')} · ${(experiment.frequency_start_hz / 1000).toFixed(1)}–${(experiment.frequency_end_hz / 1000).toFixed(1)} kHz` },
    { label: 'Listen', value: `TX ${experiment.source_x.toFixed(2)}, ${experiment.source_y.toFixed(2)} → RX ${experiment.receiver_x.toFixed(2)}, ${experiment.receiver_y.toFixed(2)}` },
    { label: 'Infer', value: `H/H₀ ${session.status.normalized_entropy.toFixed(3)} · R90 ${session.status.posterior_containment.radius90_mm.toFixed(1)} mm` },
    { label: 'Choose', value: `${session.recommendation.action_type} · utility proxy ${session.recommendation.expected_information_gain.toFixed(3)}` },
  ];
  return <section className={`experiment-storyline ${busy ? 'is-running' : ''}`} aria-label="Current experiment loop"><div className="storyline-heading"><span>THE RECURSIVE LOOP</span><b>{busy ? 'PROCESSING EVIDENCE' : session.status.should_stop ? 'REVIEW THE EVIDENCE' : 'READY TO INTERROGATE'}</b></div><div className="storyline-track">{stages.map((stage, index) => <article key={stage.label}><i>{String(index + 1).padStart(2, '0')}</i><div><small>{stage.label}</small><strong>{stage.value}</strong></div></article>)}</div></section>;
}
