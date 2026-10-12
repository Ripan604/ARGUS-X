'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import type { SessionState } from '@/types/argus';
import './instrument-workspace.css';

export const instrumentViews = [
  { id: 'interrogate', label: 'Overview', hint: 'Probability field and next experiment', group: 'Investigate', icon: 'grid' },
  { id: 'signal', label: 'Signals', hint: 'Acquisition, waveform and spectrum', group: 'Investigate', icon: 'wave' },
  { id: 'evolution', label: 'Posterior review', hint: 'Compare recorded belief updates', group: 'Investigate', icon: 'layers' },
  { id: 'brain', label: 'Reasoning', hint: 'Inspect planner decisions and costs', group: 'Investigate', icon: 'branch' },
  { id: 'assurance', label: 'Assurance', hint: 'Trust, sensor health and emergency stop', group: 'Validate', icon: 'shield' },
  { id: 'benchmark', label: 'Benchmarks', hint: 'Compare simulation planners', group: 'Validate', icon: 'bars' },
  { id: 'research', label: 'Research jobs', hint: 'Local studies and failure analysis', group: 'Validate', icon: 'flask' },
  { id: 'evidence', label: 'Evidence ledger', hint: 'Verify and export the session record', group: 'Validate', icon: 'file' },
  { id: 'camera', label: 'Registration', hint: 'Align the object with camera coordinates', group: 'Field tools', icon: 'focus' },
] as const;
export type InstrumentView = typeof instrumentViews[number]['id'];

function Glyph({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    wave: <path d="M2 12h4l3-8 5 16 3-8h5" />,
    layers: <><path d="m3 8 9-5 9 5-9 5zM3 12l9 5 9-5M3 16l9 5 9-5" /></>,
    branch: <><circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="12" cy="19" r="2" /><path d="M5 7v3l7 4 7-4V7m-7 7v3" /></>,
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z" /><path d="m8 12 3 3 5-6" /></>,
    bars: <><path d="M4 20h17M6 17v-5m6 5V7m6 10V3" /></>,
    flask: <path d="M9 3h6m-5 0v7L4 19a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2l-6-9V3M7 15h10" />,
    file: <><path d="M5 3h10l4 4v14H5zM15 3v5h4M8 12h8m-8 4h6" /></>,
    focus: <><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" /><circle cx="12" cy="12" r="3" /></>,
  };
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.grid}</svg>;
}

interface Props {
  session: SessionState; view: InstrumentView; onView: (view: InstrumentView) => void;
  online: boolean | null; busy: boolean; onReset: () => void; onRefresh: () => void; onStop: () => void;
  activity?: { label: string; status: string; detail?: string } | null;
  children: ReactNode;
}

export function InstrumentWorkspace({ session, view, onView, online, busy, onReset, onRefresh, onStop, activity, children }: Props) {
  const [query, setQuery] = useState('');
  const [compact, setCompact] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const content = useRef<HTMLElement>(null);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
    content.current?.focus({ preventScroll: true });
  }, [view]);
  const openSearch = () => { setQuery(''); dialog.current?.showModal(); search.current?.focus(); };
  useEffect(() => {
    const shortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); if (dialog.current?.open) dialog.current.close(); else { setQuery(''); dialog.current?.showModal(); search.current?.focus(); }
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, []);
  const filtered = instrumentViews.filter(item => `${item.label} ${item.hint} ${item.group}`.toLowerCase().includes(query.trim().toLowerCase()));
  const choose = (next: InstrumentView) => { onView(next); dialog.current?.close(); };
  const active = instrumentViews.find(item => item.id === view)!;
  const stopped = session.safety.emergency_stop.latched;
  return <div className={`workbench ${compact ? 'workbench-compact' : ''}`}>
    <a className="workbench-skip" href="#workspace-content">Skip to instrument content</a>
    <aside className="workbench-sidebar" aria-label="Instrument navigation">
      <Link className="workbench-brand" href="/"><span className="brand-mark"><span /></span><span>ARGUS<small>RESEARCH INSTRUMENT</small></span></Link>
      <button className="workbench-search" onClick={openSearch}><span>Find a view</span><kbd>Ctrl K</kbd></button>
      <nav>{['Investigate', 'Validate', 'Field tools'].map(group => <div className="workbench-nav-group" key={group}><p>{group}</p>{instrumentViews.filter(item => item.group === group).map(item => <button key={item.id} aria-current={view === item.id ? 'page' : undefined} className={view === item.id ? 'is-active' : ''} onClick={() => choose(item.id)}><Glyph name={item.icon} /><span>{item.label}</span>{item.id === 'assurance' && stopped && <i className="workbench-alert-dot" />}</button>)}</div>)}</nav>
      <div className="workbench-sidebar-end"><a href="/research"><Glyph name="file" />Measured evidence<span aria-hidden="true">↗</span></a><a href="/simulator"><Glyph name="wave" />Virtual lab<span aria-hidden="true">↗</span></a><a href="/setup"><Glyph name="branch" />Hardware guide<span aria-hidden="true">↗</span></a><button onClick={onReset}>← Session launcher</button><p>Local workspace<br /><span>Operator review remains required</span></p></div>
    </aside>
    <div className="workbench-main">
      <header className="workbench-header"><div><span>Workspace</span><span aria-hidden="true">/</span><strong>{active.label}</strong></div><div className="workbench-tools"><span className={`workbench-connection ${online === false ? 'is-offline' : ''}`}><i />{online === null ? 'Connecting' : online ? 'Engine connected' : 'Engine offline'}</span><button aria-pressed={compact} onClick={() => setCompact(value => !value)} title="Reduce workspace spacing">{compact ? 'Comfort view' : 'Compact view'}</button><button onClick={openSearch} aria-label="Find an instrument view" className="workbench-mobile-search">⌕</button><button onClick={onRefresh} disabled={busy || online !== true} title="Read the latest saved state without running an experiment">Refresh state</button><button className="workbench-emergency" onClick={onStop} disabled={stopped} title="Latch the session stop immediately; releasing requires review in Assurance">{stopped ? 'Stop latched' : 'Stop session'}</button></div></header>
      <div className="workbench-mobile-nav"><label>Instrument view<select value={view} onChange={event => choose(event.target.value as InstrumentView)}>{instrumentViews.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label><button onClick={onReset}>Launcher</button></div>
      <div className="workbench-session-strip"><span className="workbench-mode">{session.mode === 'physical' ? 'PHYSICAL SESSION' : 'SIMULATION'}</span><span>{session.panel.width_m * 1000} × {session.panel.height_m * 1000} mm</span><span>{session.preset} preset</span><span className="workbench-session-id" title={session.id}>Session {session.id.slice(0, 8)}</span><span>{session.status.experiment_count} / {session.config.max_experiments} experiments</span></div>
      {stopped && <div className="workbench-stop" role="alert"><strong>Emergency stop is latched.</strong><span>{session.safety.emergency_stop.reason}</span><button onClick={() => choose('assurance')}>Review stop state →</button></div>}
      {activity && <div className={`workbench-activity activity-${activity.status}`} role="status"><i /><span>{activity.label}</span><small>{activity.status === 'running' ? 'In progress · keep this session open' : activity.detail || activity.status}</small></div>}
      <main id="workspace-content" tabIndex={-1} ref={content} className="workbench-content">{children}</main>
      <footer className="workbench-footer"><span>ARGUS / Adaptive recursive guided uncertainty sensing</span><span>Research prototype · physical accuracy requires validation</span></footer>
    </div>
    <dialog ref={dialog} className="workbench-command" aria-labelledby="command-title" onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}><div><div className="command-heading"><h2 id="command-title">Go to a workspace</h2><button onClick={() => dialog.current?.close()} aria-label="Close view search">Esc</button></div><input ref={search} value={query} onChange={event => setQuery(event.target.value)} type="search" placeholder="Search signals, evidence, calibration…" aria-label="Search instrument views" onKeyDown={event => { if (event.key === 'Enter' && filtered.length === 1) choose(filtered[0].id); }} /><div className="command-results">{filtered.map(item => <button key={item.id} onClick={() => choose(item.id)}><Glyph name={item.icon} /><span><strong>{item.label}</strong><small>{item.hint}</small></span><span aria-hidden="true">↗</span></button>)}{!filtered.length && <p>No matching views. Try “signals” or “evidence”.</p>}</div><p className="command-footnote">Tab to browse · Enter to open · Escape to close</p></div></dialog>
  </div>;
}
