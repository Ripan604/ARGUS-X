'use client';

import { useMemo, useState } from 'react';
import type { HistoryItem, SessionState } from '@/types/argus';
import { comparePosteriors, summarizePosterior, type PosteriorSummary } from '@/utils/posteriorReview';
import { panelCanvasSize, posteriorColor } from '@/utils/posteriorDisplay';

function Field({ summary, difference, showRegion, widthMm, heightMm, title }: {
  summary: PosteriorSummary; difference?: number[]; showRegion: boolean; widthMm: number; heightMm: number; title: string;
}) {
  const size = panelCanvasSize(widthMm, heightMm), width = size.width - 48, height = size.height - 48;
  const maximum = Math.max(...summary.values), deltaMax = difference ? Math.max(...difference.map(Math.abs), 1e-12) : 1;
  return <figure className="review-field"><figcaption><strong>{title}</strong><span>{difference ? 'Change in probability mass per cell' : 'Probability mass per cell'}</span></figcaption><svg viewBox={`0 0 ${size.width} ${size.height}`} role="img" aria-label={`${title}. Physical panel ${widthMm} by ${heightMm} millimetres. ${difference ? 'Cyan cells gained probability; amber cells lost probability.' : `Entropy ${summary.entropyBits.toFixed(3)} bits.`}`}>
    {summary.values.map((p, i) => {
      const delta = difference?.[i] ?? 0, strength = Math.sqrt(Math.abs(delta) / deltaMax);
      return <rect key={i} x={24 + (i % summary.columns) * width / summary.columns} y={24 + Math.floor(i / summary.columns) * height / summary.rows} width={width / summary.columns} height={height / summary.rows} fill={difference ? (delta >= 0 ? `rgba(120,216,230,${strength})` : `rgba(240,164,115,${strength})`) : posteriorColor(p, maximum)} stroke={showRegion && p >= summary.threshold90 ? '#e7eef34d' : '#0d182755'} strokeWidth=".65"><title>{`x ${(((i % summary.columns) + .5) / summary.columns * widthMm).toFixed(1)} mm, y ${((Math.floor(i / summary.columns) + .5) / summary.rows * heightMm).toFixed(1)} mm · ${difference ? `change ${(delta * 100).toFixed(4)} percentage points` : `${(p * 100).toFixed(4)}% mass`}`}</title></rect>;
    })}
    <rect x="24" y="24" width={width} height={height} fill="none" stroke="#6b829a" />
    <circle cx={24 + summary.mean.x * width} cy={24 + summary.mean.y * height} r="5" fill="#f5eee2" stroke="#0c1522" strokeWidth="2" />
    <text x={size.width / 2} y={size.height - 5} textAnchor="middle" fill="#9badbf" fontSize="11">{widthMm} mm</text>
  </svg><div className="review-field-key"><span><i />Posterior mean</span><span>{difference ? 'Amber − / Cyan +' : 'Brightness relative to this field’s maximum'}</span></div></figure>;
}

export function PosteriorReview({ session, history }: { session: SessionState; history: HistoryItem[] }) {
  const [selection, setSelection] = useState<number | 'latest'>('latest');
  const [reference, setReference] = useState<'previous' | 'initial'>('previous');
  const [difference, setDifference] = useState(false);
  const [showRegion, setShowRegion] = useState(false);
  const initial = history[0]?.posterior_before ?? session.posterior;
  const frames = useMemo(() => [{ index: history[0] ? history[0].experiment_index - 1 : 0, grid: initial }, ...history.map(item => ({ index: item.experiment_index, grid: item.posterior_after }))], [initial, history]);
  const frame = selection === 'latest' ? frames.length - 1 : Math.min(selection, frames.length - 1);
  const record = frame ? history[frame - 1] : null;
  const before = reference === 'initial' ? initial : record?.posterior_before ?? initial;
  const widthMm = session.panel.width_m * 1000, heightMm = session.panel.height_m * 1000;
  const comparison = comparePosteriors(before, frames[frame].grid, widthMm, heightMm);
  const summaries = frames.map(item => summarizePosterior(item.grid));
  const saveCsv = () => {
    const rows = frames.map((item, index) => {
      const c = comparePosteriors(index ? history[index - 1].posterior_before : initial, item.grid, widthMm, heightMm);
      return c ? [item.index, c.current.entropyBits, c.current.effectiveCells, c.current.area90Fraction, c.current.mass90, c.entropyChangeBits, c.jsBits, c.meanShiftMm, index ? history[index - 1].diagnostics.evidence_weight ?? '' : ''].join(',') : `${item.index},,,,,,,,`;
    });
    const blob = new Blob([`experiment,entropy_bits,effective_cells,area90_fraction,mass_in_area90,entropy_change_bits,js_divergence_bits,mean_shift_mm,evidence_weight\n${rows.join('\n')}\n`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob), anchor = document.createElement('a'); anchor.href = url;
    anchor.download = `argus-posterior-review-${session.id.replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 60)}.csv`; anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  if (!history.length && session.status.experiment_count > 0) return <section className="review-invalid" role="status"><h2>The saved measurement history is not loaded yet.</h2><p>This session has {session.status.experiment_count} measurements. Use Refresh state to load their before/after fields for review.</p></section>;
  if (!comparison) return <section className="review-invalid" role="alert"><h2>Recorded posterior cannot be reviewed.</h2><p>The field is invalid, unnormalised or has incompatible dimensions. Refresh the saved session to retrieve its latest history.</p></section>;
  const largestEntropy = Math.max(1, ...summaries.map(s => s?.entropyBits ?? 0));
  const changeLabel = comparison.entropyChangeBits > 1e-9 ? 'Uncertainty increased' : comparison.entropyChangeBits < -1e-9 ? 'Uncertainty decreased' : 'Entropy unchanged';
  return <section className="posterior-review">
    {history.length !== session.status.experiment_count && <p className="workspace-warning" role="status">Showing {history.length} loaded records from a session with {session.status.experiment_count} measurements. Refresh state to reconcile the history; “latest” refers to the loaded records.</p>}
    <div className="workbench-page-heading"><div><p className="eyebrow">MEASUREMENT BY MEASUREMENT</p><h1>How the evidence changed belief.</h1><p>Compare saved probability fields. Concentration describes the model’s belief; it does not establish that a location is correct.</p></div><button className="workbench-button" onClick={saveCsv}>Export review CSV ↗</button></div>
    <div className="review-controls"><label>Selected state<select value={selection} onChange={event => setSelection(event.target.value === 'latest' ? 'latest' : Number(event.target.value))}><option value="latest">Latest recorded state</option>{frames.map((item, index) => <option key={index} value={index}>{index ? `After experiment ${item.index}` : 'Initial saved state'}</option>)}</select></label><label>Compare against<select value={reference} onChange={event => setReference(event.target.value as 'previous' | 'initial')}><option value="previous">Before this experiment</option><option value="initial">Initial saved state</option></select></label><label className="review-check"><input type="checkbox" checked={difference} onChange={event => setDifference(event.target.checked)} />Show probability change</label><label className="review-check"><input type="checkbox" checked={showRegion} onChange={event => setShowRegion(event.target.checked)} />Outline 90% mass cells</label></div>
    <div className="review-snapshot-label"><span>{record ? `Experiment ${record.experiment_index} · ${record.planner.action_type} · ${record.parameters.waveform.replaceAll('_', ' ')}` : 'Initial state · no measurement selected'}</span><span>{record ? `Evidence weight ${Number(record.diagnostics.evidence_weight ?? 0).toFixed(3)}` : `${session.mode} session`}</span></div>
    <div className="review-fields"><Field summary={comparison.previous} showRegion={showRegion} widthMm={widthMm} heightMm={heightMm} title={reference === 'initial' ? 'Initial state' : 'Before measurement'} /><Field summary={comparison.current} difference={difference ? comparison.delta : undefined} showRegion={showRegion} widthMm={widthMm} heightMm={heightMm} title={difference ? 'Where probability moved' : 'Selected posterior'} /></div>
    <div className="review-metrics"><article><small>ENTROPY CHANGE</small><strong>{comparison.entropyChangeBits > 0 ? '+' : ''}{comparison.entropyChangeBits.toFixed(3)} <em>bits</em></strong><p>{changeLabel}</p></article><article><small>DISTRIBUTION CHANGE</small><strong>{comparison.jsBits.toFixed(4)} <em>bits</em></strong><p>Jensen–Shannon divergence · 0 to 1</p></article><article><small>POSTERIOR MEAN SHIFT</small><strong>{comparison.meanShiftMm.toFixed(1)} <em>mm</em></strong><p>Physical distance on this panel</p></article><article><small>90% MASS REGION</small><strong>{(comparison.current.area90Fraction * 100).toFixed(1)}<em>% area</em></strong><p>{(comparison.current.mass90 * 100).toFixed(1)}% mass · tied cells included</p></article></div>
    <div className="review-timeline"><div><p className="eyebrow">RECORDED ENTROPY TRAJECTORY</p><h2>Inspect an observation.</h2><p>A rise in entropy can be a valid response to conflicting evidence.</p></div><div className="review-entropy-bars" role="group" aria-label="Select a saved posterior">{frames.map((item, index) => <button key={index} aria-pressed={frame === index} aria-label={`${index ? `Experiment ${item.index}` : 'Initial state'}: ${summaries[index]?.entropyBits.toFixed(3) ?? 'invalid'} bits`} onClick={() => setSelection(index)}><span className="review-bar-track"><i style={{ height: `${Math.max(1, (summaries[index]?.entropyBits ?? 0) / largestEntropy * 100)}%` }} /></span><b>{index ? item.index : 'Start'}</b></button>)}</div></div>
    <details className="review-method"><summary>Read the calculations and interpretation</summary><p>Entropy is −Σ p log₂ p. The equivalent number of equally likely cells is 2ᴴ: {comparison.current.effectiveCells.toFixed(1)} of {comparison.current.values.length} cells here. The 90% mass region selects cells by decreasing probability and includes all ties at the cutoff; its cells can be disconnected. Mean shift uses cell centers and the panel’s physical dimensions.</p><p>Jensen–Shannon divergence compares both distributions, so belief can move even when entropy stays constant. Heatmap brightness is scaled independently for each probability field; hover a cell for its numerical mass. The difference map uses a common symmetric scale. These are descriptive calculations on stored posteriors. CSV rows compare each observation with its own recorded before-state; use Evidence ledger for the complete acquisition record.</p></details>
  </section>;
}
