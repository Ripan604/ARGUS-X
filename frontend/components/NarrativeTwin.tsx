'use client';

import { useEffect, useRef, useState } from 'react';
import type { SessionState } from '@/types/argus';
import { normalizedRelief, physicalCircle } from './spatialGeometry';
import { useSceneMotion } from './SpatialWorld';

export function NarrativeTwin({ session }: { session?: SessionState }) {
  const canvasRef = useRef<HTMLCanvasElement>(null), stageRef = useRef<HTMLDivElement>(null);
  const pointer = useRef({ x: 0, y: 0 });
  const [angle, setAngle] = useState(-24);
  const { paused } = useSceneMotion();
  const experiment = session?.recommendation.experiment;
  useEffect(() => {
    const canvas = canvasRef.current, stage = stageRef.current, ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !stage) return;
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    const widthMm = (session?.panel.width_m ?? .6) * 1000, heightMm = (session?.panel.height_m ?? .4) * 1000;
    const longest = Math.max(widthMm, heightMm), aspectX = widthMm / longest, aspectY = heightMm / longest;
    const relief = normalizedRelief(session?.posterior), rows = relief?.length ?? 25, columns = relief?.[0]?.length ?? 31;
    const source = { x: experiment?.source_x ?? .16, y: experiment?.source_y ?? .72 }, receiver = { x: experiment?.receiver_x ?? .84, y: experiment?.receiver_y ?? .22 };
    let width = 1, height = 1, frame = 0, last = 0, time = 0, visible = true, smoothX = 0, smoothY = 0;
    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const animate = !paused && !preference.matches;
      smoothX += ((animate ? pointer.current.x : 0) - smoothX) * .055; smoothY += ((animate ? pointer.current.y : 0) - smoothY) * .055;
      const rotation = (angle + smoothX * 9) * Math.PI / 180, scale = Math.min(width * .76, height * 1.13);
      const project = (x: number, y: number, z = 0) => {
        const px = (x - .5) * aspectX, py = (y - .5) * aspectY;
        return { x: width * .5 + (px * Math.cos(rotation) - py * Math.sin(rotation)) * scale, y: height * .53 + (px * Math.sin(rotation) + py * Math.cos(rotation)) * scale * (.53 + smoothY * .05) - z * scale };
      };
      const polygon = (points: {x: number; y: number}[], fill: string, stroke?: string) => {
        ctx.beginPath(); points.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); }); ctx.closePath(); ctx.fillStyle = fill; ctx.fill();
        if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = .7; ctx.stroke(); }
      };
      const line = (points: {x: number; y: number}[], color: string, thickness = 1) => { ctx.beginPath(); points.forEach((p, i) => { if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y); }); ctx.strokeStyle = color; ctx.lineWidth = thickness; ctx.stroke(); };
      const corners = [[0, 0], [1, 0], [1, 1], [0, 1]];
      for (let edge = 0; edge < 4; edge++) { const a = corners[edge], b = corners[(edge + 1) % 4]; polygon([project(a[0], a[1]), project(b[0], b[1]), project(b[0], b[1], -.035), project(a[0], a[1], -.035)], '#0c1727', '#48617966'); }
      polygon(corners.map(([x, y]) => project(x, y)), '#101e31', '#90b8d570');
      const cellHeight = (r: number, c: number) => relief ? relief[Math.min(rows - 1, r)][Math.min(columns - 1, c)] * .19 : 0;
      const cells: {r: number; c: number; depth: number}[] = [];
      for (let r = 0; r < rows - 1; r++) for (let c = 0; c < columns - 1; c++) cells.push({ r, c, depth: project((c + .5) / columns, (r + .5) / rows).y });
      cells.sort((a, b) => a.depth - b.depth);
      for (const { r, c } of cells) {
        const value = relief ? (relief[r][c] + relief[r + 1][c + 1]) / 2 : 0, warm = Math.pow(value, 2.4);
        const cell = [[c, r], [c + 1, r], [c + 1, r + 1], [c, r + 1]].map(([col, row]) => project((col + .5) / columns, (row + .5) / rows, cellHeight(row, col)));
        polygon(cell, `rgba(${Math.round(26 + warm * 195)},${Math.round(66 + value * 105)},${Math.round(96 + value * 28)},.88)`, `rgba(133,205,238,${.13 + value * .32})`);
      }
      const clippedCircle = (cx: number, cy: number, radius: number, color: string, z: number) => {
        let segment: {x: number; y: number}[] = [];
        for (const p of physicalCircle(cx, cy, radius, widthMm, heightMm)) {
          if (p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1) segment.push(project(p.x, p.y, z));
          else { if (segment.length > 1) line(segment, color); segment = []; }
        }
        if (segment.length > 1) line(segment, color);
      };
      if (session) {
        const containment = session.status.posterior_containment;
        ctx.setLineDash([4, 5]); clippedCircle(containment.reference_x, containment.reference_y, containment.radius90_mm, '#f2c18eaa', .008); ctx.setLineDash([]);
        const map = project(session.status.map_x, session.status.map_y, .23), base = project(session.status.map_x, session.status.map_y, .008);
        line([base, map], '#f2c18e77'); ctx.fillStyle = '#f2c18e'; ctx.beginPath(); ctx.arc(map.x, map.y, 3, 0, Math.PI * 2); ctx.fill(); ctx.font = '10px ui-monospace, monospace'; ctx.fillText('MAP', map.x + 9, map.y + 3);
      }
      // These rings illustrate excitation geometry, not measured wave propagation.
      for (let ring = 0; ring < 3; ring++) { const progress = ((time * .15 + ring / 3) % 1); clippedCircle(source.x, source.y, progress * longest * .85, `rgba(148,216,251,${(1 - progress) * .35})`, .012); }
      ctx.setLineDash([3, 6]); line([project(source.x, source.y, .04), project(receiver.x, receiver.y, .04)], '#d9eaf66b'); ctx.setLineDash([]);
      for (const [point, label, color] of [[source, 'TX / EXCITE', '#9adcf8'], [receiver, 'RX / LISTEN', '#f3c594']] as const) {
        const base = project(point.x, point.y, .012), top = project(point.x, point.y, .095); line([base, top], color, 2);
        ctx.beginPath(); ctx.ellipse(base.x, base.y, 10, 5, rotation, 0, Math.PI * 2); ctx.strokeStyle = `${color}77`; ctx.stroke();
        ctx.shadowColor = color; ctx.shadowBlur = 18; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(top.x, top.y, 5, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0; ctx.font = '10px ui-monospace, monospace'; ctx.fillText(label, top.x + 12, top.y - 8);
      }
      const x1 = project(0, 1.14, -.035), x2 = project(1, 1.14, -.035); line([x1, x2], '#728ca566'); ctx.fillStyle = '#98adc2'; ctx.font = '10px ui-monospace, monospace'; ctx.textAlign = 'center'; ctx.fillText(`${Math.round(widthMm)} mm`, (x1.x + x2.x) / 2, (x1.y + x2.y) / 2 + 16);
      const y1 = project(1.12, 0, -.035), y2 = project(1.12, 1, -.035); line([y1, y2], '#728ca566'); ctx.fillText(`${Math.round(heightMm)} mm`, (y1.x + y2.x) / 2 + 30, (y1.y + y2.y) / 2); ctx.textAlign = 'left';
    };
    const tick = (now: number) => { if (now - last >= 32) { time += .032; draw(); last = now; } frame = requestAnimationFrame(tick); };
    const sync = () => { cancelAnimationFrame(frame); draw(); if (visible && !paused && !preference.matches && !document.hidden) frame = requestAnimationFrame(tick); };
    const resize = new ResizeObserver(([entry]) => { width = entry.contentRect.width; height = entry.contentRect.height; const ratio = Math.min(devicePixelRatio || 1, 2); canvas.width = width * ratio; canvas.height = height * ratio; ctx.setTransform(ratio, 0, 0, ratio, 0, 0); draw(); });
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }); resize.observe(canvas); observer.observe(stage); sync(); preference.addEventListener('change', sync); document.addEventListener('visibilitychange', sync);
    return () => { cancelAnimationFrame(frame); resize.disconnect(); observer.disconnect(); preference.removeEventListener('change', sync); document.removeEventListener('visibilitychange', sync); };
  }, [session, experiment, angle, paused]);

  return <section className={`narrative-twin ${session ? 'session-twin' : 'landing-twin'}`} ref={stageRef} aria-label={session ? 'Live posterior in three dimensions' : 'Illustrative acoustic experiment'}>
    <div className="twin-topline"><span><i />{session ? 'LIVE POSTERIOR' : 'THE EXPERIMENT, IN SPACE'}</span><span>{session ? `${String(session.status.experiment_count).padStart(2, '0')} OBSERVATIONS` : 'ILLUSTRATIVE GEOMETRY'}</span></div>
    <div className="spatial-canvas-wrap" onPointerMove={(event) => { const box = event.currentTarget.getBoundingClientRect(); pointer.current = { x: (event.clientX - box.left) / box.width - .5, y: (event.clientY - box.top) / box.height - .5 }; }} onPointerLeave={() => { pointer.current = { x: 0, y: 0 }; }}>
      <canvas ref={canvasRef} className="spatial-canvas" role="img" aria-label={session ? `Posterior probability relief. MAP at normalized X ${session.status.map_x.toFixed(3)}, Y ${session.status.map_y.toFixed(3)}. 90 percent posterior mass radius ${session.status.posterior_containment.radius90_mm.toFixed(1)} millimeters. Height is probability relative to its current peak, not physical depth.` : 'An illustrative 600 by 400 millimeter panel with an excitation source and receiver. No hidden-defect estimate is shown before evidence is collected.'} />
      <div className="twin-margin-label">{session ? 'BELIEF / NOT PHYSICAL DEPTH' : 'AN OPAQUE OBJECT. AN OPEN QUESTION.'}</div>
    </div>
    <div className="twin-bottomline"><div><span className="twin-key cyan" />Excitation <span className="twin-key amber" />{session ? 'Posterior peak' : 'Receiver'}<small>{session ? 'Height ∝ relative probability · dashed ring: R90' : 'Signal paths illustrate the sensing concept'}</small></div><label className="orbit-control">ORBIT<input aria-label="Rotate three dimensional panel" type="range" min="-48" max="20" value={angle} onChange={(event) => setAngle(Number(event.target.value))} /></label></div>
    {session && <p className="twin-science-note">Ring uses physical dimensions and discrete posterior mass at cell centers. Coverage is not field calibrated. Signal rings are illustrative.</p>}
  </section>;
}

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
