import styles from './researchEvidence.module.css';

export function EvidenceMetricChart({ title, unit, rows, note, adverse = false }: {
  title: string; unit: 'fraction' | 'mm' | 'count' | 'dimensionless';
  rows: { label: string; value: number | null }[]; note: string; adverse?: boolean;
}) {
  const maximumValue = Math.max(0, ...rows.map((row) => row.value ?? 0));
  const maximum = unit === 'fraction' || unit === 'dimensionless' ? 1
    : unit === 'mm' ? Math.max(10, Math.ceil(maximumValue / 10) * 10) : Math.max(1, Math.ceil(maximumValue));
  const format = (value: number | null) => value === null ? 'Unavailable'
    : unit === 'fraction' ? `${(value * 100).toFixed(1)}%`
      : unit === 'dimensionless' ? value.toFixed(3) : unit === 'mm' ? `${value.toFixed(1)} mm` : value.toLocaleString('en-US');
  return <figure className={styles.chart}>
    <figcaption><strong>{title}</strong><span>{note}</span></figcaption>
    <ul className={styles.chartRows}>{rows.map((row, index) => <li key={row.label}>
      <span className={styles.chartLabel}>{row.label}</span>
      <span className={styles.chartTrack} aria-hidden="true"><span className={adverse && index > 0 ? styles.adverseBar : styles.chartBar} style={{ width: `${row.value === null ? 0 : row.value / maximum * 100}%` }} /></span>
      <strong>{format(row.value)}</strong>
    </li>)}</ul>
    <div className={styles.chartAxis} aria-hidden="true"><span>0</span><span>{format(maximum / 2)}</span><span>{format(maximum)}</span></div>
  </figure>;
}
