'use client';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
const MotionContext = createContext({ paused: false, toggle: () => {} });
export function useSceneMotion() { return useContext(MotionContext); }
export function SpatialWorld({ children }: { children: React.ReactNode }) {
  const [paused, setPaused] = useState(false);
  return <MotionContext.Provider value={{ paused, toggle: () => setPaused((value) => !value) }}><div className={`spatial-world ${paused ? 'motion-paused' : ''}`}><AmbientField />{children}<button className="world-motion" onClick={() => setPaused((value) => !value)} aria-pressed={paused} aria-label={paused ? 'Resume ambient motion' : 'Pause ambient motion'}><span aria-hidden="true">{paused ? '▷' : 'Ⅱ'}</span>{paused ? 'Motion paused' : 'Pause motion'}</button></div></MotionContext.Provider>;
}
function AmbientField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { paused } = useSceneMotion();
  useEffect(() => {
    const canvas = canvasRef.current, ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0, width = 1, height = 1, last = 0, time = 0;
    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const center = width * .72, horizon = height * .19;
      for (let row = 0; row < 31; row++) {
        const depth = row / 30, y = horizon + depth * depth * height * 1.1;
        ctx.beginPath();
        for (let col = 0; col <= 60; col++) {
          const x = center + (col / 60 - .5) * (width * .5 + depth * width * 2);
          const wave = Math.sin(col * .16 + row * .25 + time) * Math.sin(col * .06 + time * .3) * depth * 35;
          if (col === 0) ctx.moveTo(x, y + wave); else ctx.lineTo(x, y + wave);
        }
        ctx.strokeStyle = `rgba(121,177,217,${.015 + depth * .038})`; ctx.lineWidth = .65; ctx.stroke();
      }
      for (let col = -14; col <= 14; col++) { ctx.beginPath(); ctx.moveTo(center + col * width * .011, horizon); ctx.lineTo(center + col * width * .065, height * 1.4); ctx.strokeStyle = 'rgba(121,177,217,.024)'; ctx.stroke(); }
    };
    const tick = (now: number) => { if (now - last > 48) { time += .007; draw(); last = now; } frame = requestAnimationFrame(tick); };
    const sync = () => { cancelAnimationFrame(frame); draw(); if (!paused && !motion.matches && !document.hidden) frame = requestAnimationFrame(tick); };
    const resize = () => { width = innerWidth; height = innerHeight; const ratio = Math.min(devicePixelRatio || 1, 1.5); canvas.width = width * ratio; canvas.height = height * ratio; ctx.setTransform(ratio, 0, 0, ratio, 0, 0); draw(); };
    resize(); sync(); window.addEventListener('resize', resize); document.addEventListener('visibilitychange', sync); motion.addEventListener('change', sync);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('resize', resize); document.removeEventListener('visibilitychange', sync); motion.removeEventListener('change', sync); };
  }, [paused]);
  return <canvas className="ambient-field" ref={canvasRef} aria-hidden="true" />;
}
