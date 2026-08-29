import type { BenchmarkResult } from '@/types/argus';

const labels = { random: 'RANDOM', uniform_grid: 'UNIFORM GRID', argus: 'ARGUS ACTIVE' };
const colors = { random: '#8aa097', uniform_grid: '#e59f52', argus: '#a8e86b' };

function trajectoryPoints(values: number[], width = 620, height = 170): string {
  const maximum = Math.max(1, ...values);
  return values.map((value, index) => {
    const x = 24 + index * ((width - 48) / Math.max(1, values.length - 1));
    const y = 12 + (height - 30) * (value / maximum);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}

export function BenchmarkPanel({ data, onLoad, busy }: { data: BenchmarkResult | null; onLoad: () => void; busy: boolean }) {
  if (!data) return <div className="empty-analysis"><b>ACTUAL BENCHMARK DATA</b><p>Load the locally generated evaluation comparing identical seeded defects under random, grid, and adaptive probing.</p><button className="run-button compact" onClick={onLoad} disabled={busy}>LOAD BENCHMARK</button></div>;
  const maximumEntropy = Math.max(...Object.values(data.summary).map((item) => item.mean_final_entropy));
  return <div className="benchmark-wrap">
    <div className="benchmark-note">N = {data.metadata.cases} SEEDED {String(data.metadata.preset).toUpperCase()} DEFECTS · RESULTS ARE GENERATED, NOT FABRICATED</div>
    <div className="benchmark-cards">
      {(Object.keys(labels) as (keyof typeof labels)[]).map((strategy) => { const item = data.summary[strategy]; return <article className={strategy === 'argus' ? 'winner' : ''} key={strategy}>
        <p className="eyebrow">{labels[strategy]}</p><strong>{item.mean_localization_error_mm.toFixed(1)}<small> mm</small></strong><span>MEAN LOCALIZATION ERROR</span>
        <dl><div><dt>FINAL ENTROPY</dt><dd>{item.mean_final_entropy.toFixed(3)}</dd></div><div><dt>EXPERIMENTS</dt><dd>{item.mean_experiments.toFixed(1)}</dd></div><div><dt>SUCCESS ≤15 MM</dt><dd>{Math.round(item.success_rate_15mm * 100)}%</dd></div><div><dt>COST</dt><dd>{item.mean_measurement_cost.toFixed(2)}</dd></div></dl>
        <div className="entropy-meter"><i style={{ width: `${item.mean_final_entropy / maximumEntropy * 100}%` }} /></div>
      </article>; })}
    </div>
    <section className="benchmark-evidence">
      <div>
        <p className="eyebrow">UNCERTAINTY TRAJECTORY</p>
        <svg className="benchmark-plot" viewBox="0 0 620 170" role="img" aria-label="Mean normalized posterior entropy by experiment">
          <title>Mean normalized posterior entropy by experiment; lower is better</title>
          {[0.25, 0.5, 0.75, 1].map((tick) => <line key={tick} x1="24" x2="596" y1={12 + 140 * tick} y2={12 + 140 * tick} />)}
          {(Object.keys(labels) as (keyof typeof labels)[]).map((strategy) => <polyline key={strategy} points={trajectoryPoints(data.trajectories[strategy].mean_entropy)} style={{ stroke: colors[strategy] }} />)}
        </svg>
        <div className="plot-legend">{(Object.keys(labels) as (keyof typeof labels)[]).map((strategy) => <span key={strategy}><i style={{ background: colors[strategy] }} />{labels[strategy]}</span>)}</div>
      </div>
      <div className="paired-proof">
        <p className="eyebrow">PAIRED ARGUS ADVANTAGE</p>
        {(['argus_vs_random', 'argus_vs_uniform_grid'] as const).map((key) => { const item = data.paired_comparisons[key]; return <article key={key}>
          <span>{key === 'argus_vs_random' ? 'VERSUS RANDOM' : 'VERSUS GRID'}</span>
          <strong>+{item.mean_entropy_advantage.toFixed(3)}</strong>
          <small>LOWER ENTROPY · 95% CI {item.entropy_advantage_95ci[0].toFixed(3)} TO {item.entropy_advantage_95ci[1].toFixed(3)}</small>
        </article>; })}
      </div>
    </section>
    <p className="benchmark-caveat">Success cards use a ≤15 mm threshold. Confidence intervals are paired bootstrap intervals across identical hidden defects. This simulator benchmark demonstrates closed-loop behavior under the declared model; it is not evidence of field performance.</p>
  </div>;
}
