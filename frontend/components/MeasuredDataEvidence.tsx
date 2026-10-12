'use client';

import { useEffect, useState } from 'react';
import { formatMeasuredMetric, parseMeasuredReport, type MeasuredReport, type MeasuredTask } from '@/utils/measuredEvidence';
import { EvidenceMetricChart } from './EvidenceMetricChart';
import styles from './researchEvidence.module.css';

const TASKS: Record<MeasuredTask, string> = {
  tap_screening: 'Labelled tap screening', transient_source_localization: 'Transient source position',
  acquisition_quality: 'Acquisition quality', recorded_path_replay: 'Recorded ultrasonic paths',
};
const FAILURE_INDEX = { gfrp: 1, impact: 2, morpho: 0, ogw: 0 };

export function MeasuredDataEvidence() {
  const [report, setReport] = useState<MeasuredReport | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [task, setTask] = useState<MeasuredTask | 'all'>('all');
  const [selectedId, setSelectedId] = useState('gfrp');
  const [tableIndex, setTableIndex] = useState(0);
  const [metricKey, setMetricKey] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/research/measured-data-summary.json', { signal: controller.signal, cache: 'no-cache' })
      .then(async (response) => {
        if (!response.ok) throw new Error('The saved measured-data summary could not be loaded.');
        const body = await response.text();
        if (body.length > 100_000) throw new Error('The measured-data summary exceeds its supported size.');
        const validated = parseMeasuredReport(JSON.parse(body) as unknown);
        if (!validated) throw new Error('The saved summary contains missing, invalid or unverified study data.');
        if (!controller.signal.aborted) setReport(validated);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Measured evidence unavailable.');
      });
    return () => controller.abort();
  }, [attempt]);
  const visible = report?.studies.filter((study) => task === 'all' || study.task === task) ?? [];
  const study = visible.find((item) => item.id === selectedId) ?? visible[0];
  const table = study?.tables[tableIndex] ?? study?.tables[0];
  const column = table?.columns.find((item) => item.key === metricKey) ?? table?.columns[0];
  const reviewDate = report ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'long', timeZone: 'Asia/Kolkata' }).format(new Date(`${report.review_date}T00:00:00Z`)) : '';
  return <section id="measured-evidence" className={styles.explorer} aria-labelledby="measured-evidence-title">
    <div className={styles.heading}><div><p className={styles.kicker}>Evidence explorer / external recordings</p><h2 id="measured-evidence-title">Four tasks. Four different limits.</h2></div><a className={styles.link} href="/research/measured-data-summary.json" download>Download measured JSON ↗</a></div>
    <p className={styles.scope}>Select a task, inspect the comparison, and keep its physical unit in view. These saved recording studies evaluate screening, excitation-source position, acquisition quality and offline path replay. They do not validate the ARGUS apparatus or a prospective blind inspection.</p>
    {error && <div className={styles.error} role="alert">{error}<button type="button" onClick={() => { setError(''); setAttempt((value) => value + 1); }}>Retry saved summary</button></div>}
    {!report && !error && <p className={styles.loading} role="status">Loading recorded evidence and source verification…</p>}
    {report && <>
      <div className={styles.notice}>
        <h3>Failures remain visible across every task filter.</h3>
        <ul className={styles.failureIndex}>{report.studies.map((item) => <li key={item.id}><b>{item.title}</b>{item.risks[FAILURE_INDEX[item.id]] ?? item.risks[0]}</li>)}</ul>
      </div>
      <div className={styles.controls}><label htmlFor="measured-task-filter">Task family<select id="measured-task-filter" value={task} onChange={(event) => { setTask(event.target.value as MeasuredTask | 'all'); setTableIndex(0); setMetricKey(''); }}>
        <option value="all">All four measured tasks</option>{Object.entries(TASKS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></label><p aria-live="polite"><b>{visible.length}</b> of {report.studies.length} tasks shown · recorded review {reviewDate}</p></div>
      <div className={styles.studyGrid}>
        <fieldset className={styles.studyPicker}><legend>Choose a recorded study</legend>{visible.map((item) => <button key={item.id} type="button" aria-pressed={study?.id === item.id} aria-controls="measured-study-detail" onClick={() => { setSelectedId(item.id); setTableIndex(0); setMetricKey(''); }}><strong>{item.title}</strong><span>{formatMeasuredMetric(item.headline.value, item.headline.unit)}</span></button>)}</fieldset>
        {study && <article id="measured-study-detail" className={styles.detail} aria-labelledby={`measured-study-${study.id}`}>
          <p className={styles.taskTag}>{TASKS[study.task]}</p><h3 id={`measured-study-${study.id}`}>{study.title}</h3><p>{study.evidence_scope}</p>
          <dl className={styles.counts}>{study.counts.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value.toLocaleString('en-US')}</dd></div>)}<div><dt>native recording rate</dt><dd>{study.native_sample_rate_hz.toLocaleString('en-US')} Hz</dd></div></dl>
          <p><b>Validation unit:</b> {study.validation}</p>
          <div className={styles.headline}><span>{study.headline.label}</span><strong>{formatMeasuredMetric(study.headline.value, study.headline.unit)}</strong>{study.interval && <p>{study.interval.label}: {formatMeasuredMetric(study.interval.bounds[0], study.interval.unit)} to {formatMeasuredMetric(study.interval.bounds[1], study.interval.unit)}.</p>}</div>
          {table && column && <>
            <div className={styles.metricControls}>{study.tables.length > 1 && <label htmlFor="measured-table-context">Recorded baseline context<select id="measured-table-context" value={tableIndex} onChange={(event) => { setTableIndex(Number(event.target.value)); setMetricKey(''); }}>{study.tables.map((item, index) => <option key={item.caption} value={index}>{item.caption}</option>)}</select></label>}
              <label htmlFor="measured-metric">Chart metric<select id="measured-metric" value={column.key} onChange={(event) => setMetricKey(event.target.value)}>{table.columns.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
            </div>
            <EvidenceMetricChart title={column.label} unit={column.unit} rows={table.rows.map((row) => ({ label: row.method, value: row.values[column.key] }))} note={column.unit === 'mm' ? 'Position error in millimetres; lower is better.' : column.unit === 'fraction' ? 'A fixed 0–100% scale. Read the positive class and study scope below.' : 'Recorded counts; inspect the caption and error totals.'} />
            <div className={styles.tableWrap}><table><caption>{table.caption}</caption><thead><tr><th scope="col">Method</th>{table.columns.map((item) => <th scope="col" key={item.key}>{item.label}</th>)}</tr></thead><tbody>{table.rows.map((row) => <tr key={row.method}><th scope="row">{row.method}</th>{table.columns.map((item) => <td key={item.key}>{formatMeasuredMetric(row.values[item.key], item.unit)}</td>)}</tr>)}</tbody></table></div>
          </>}
          <div className={styles.notice}><h3>Interpretation and retained failures</h3><ul className={styles.riskList}>{study.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul></div>
          <div className={styles.sourceLinks}><a className={styles.link} href={study.source_url} target="_blank" rel="noopener noreferrer">Original dataset ↗</a><a className={styles.link} href={study.license_url} target="_blank" rel="noopener noreferrer">{study.license} ↗</a></div>
          {study.doi && <p className={styles.fineprint}>DOI: {study.doi}</p>}
          <details className={styles.provenance}><summary>Artifact identity and source checks</summary><p>Saved study artifact; SHA-256:</p><code>{study.artifact.path}</code><code>{study.artifact.sha256}</code><p>{study.source_verification.files_checked.toLocaleString('en-US')} source/input files matched their saved hashes at export. Source-manifest SHA-256:</p><code>{study.source_verification.manifest_sha256}</code><p>This browser reads a dated export. It does not rehash local recordings or rerun the study. Verification establishes content consistency, not field performance.</p></details>
        </article>}
      </div>
      <details className={styles.provenance}><summary>All four dataset sources and licenses</summary><div className={styles.sourceLinks}>{report.studies.map((item) => <div key={item.id}><a className={styles.link} href={item.source_url} target="_blank" rel="noopener noreferrer">{item.title} ↗</a><p className={styles.fineprint}><a className={styles.link} href={item.license_url} target="_blank" rel="noopener noreferrer">{item.license}</a></p></div>)}</div></details>
    </>}
  </section>;
}
