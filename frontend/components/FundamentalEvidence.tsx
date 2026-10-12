'use client';

import { useEffect, useState } from 'react';
import { parseFundamentalReport, type FundamentalReport } from '@/utils/fundamentalEvidence';
import { EvidenceMetricChart } from './EvidenceMetricChart';
import styles from './researchEvidence.module.css';

export function FundamentalEvidence() {
  const [report, setReport] = useState<FundamentalReport | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [stageName, setStageName] = useState<'confirmation' | 'development'>('confirmation');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/research/fundamental-summary.json', { signal: controller.signal, cache: 'no-cache' })
      .then(async (response) => {
        if (!response.ok) throw new Error('The saved reference-conditioned study could not be loaded.');
        const body = await response.text();
        if (body.length > 100_000) throw new Error('The study summary exceeds its supported size.');
        const parsed = parseFundamentalReport(JSON.parse(body) as unknown);
        if (!parsed) throw new Error('The study summary has missing, invalid or unverified evidence.');
        if (!controller.signal.aborted) setReport(parsed);
      })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Study unavailable.'); });
    return () => controller.abort();
  }, [attempt]);
  const stage = report?.[stageName];
  const raw = report?.confirmation.adaptive.find((row) => row.variant === 'raw_global');
  const global = report?.confirmation.adaptive.find((row) => row.variant === 'transport_global');
  const pathSpecific = report?.confirmation.adaptive.find((row) => row.variant === 'transport_heteroscedastic');
  const exported = report ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(report.exported_at_utc)) : '';
  return <section id="fundamental-evidence" className={styles.explorer} aria-labelledby="fundamental-evidence-title">
    <div className={styles.heading}><div><p className={styles.kicker}>Latest completed study / reference-conditioned control</p><h2 id="fundamental-evidence-title">Better references. A harder result.</h2></div><a className={styles.link} href="/research/fundamental-summary.json" download>Download study JSON ↗</a></div>
    <p className={styles.scope}>Healthy waveform transport, qualified path selection and trajectory-level reference gates were tested on separate recorded confirmation banks. The engineering chain is implemented; its localization and adaptive damage sensitivity still need a better physical model.</p>
    {error && <div className={styles.error} role="alert">{error}<button type="button" onClick={() => { setError(''); setAttempt((value) => value + 1); }}>Retry saved study</button></div>}
    {!report && !error && <p className={styles.loading} role="status">Loading completed confirmation and artifact identities…</p>}
    {report && stage && <>
      <div className={styles.strip}><div><strong>{report.confirmation_acquired_banks}/{report.confirmation_required_banks}</strong><span>original confirmation banks acquired and scored</span></div><div><strong>{report.specimens}</strong><span>physical specimen; external recorded reanalysis</span></div><div><strong>{report.qualified_paths}/{report.recorded_paths}</strong><span>paths qualified by healthy-only development</span></div></div>
      <div className={styles.notice}><h3>Separate confirmation retained the negative localization finding.</h3><p>Raw adaptive error was <b>{raw?.mean_error_mm.toFixed(1)} mm</b>; global transport reached <b>{global?.mean_error_mm.toFixed(1)} mm</b> and path-specific transport <b>{pathSpecific?.mean_error_mm.toFixed(1)} mm</b>.</p><p>{report.confirmation.adaptive.map((row) => `${row.label}: ${row.damage_alerts}/${row.damage_conditions} damage conditions and ${row.healthy_alerts}/${row.unique_healthy_banks} unique healthy banks alerted`).join('; ')}. These are supported any-prefix alerts; the current zero damage detections show poor sensitivity.</p></div>
      <div className={styles.split}><div><h3>Healthy-reference discrepancy</h3><EvidenceMetricChart title="Leave-middle-temperature-out mean DI" unit="dimensionless" rows={[{ label: 'Uncompensated reference', value: report.healthy_reference.before_di }, { label: 'Healthy-only transport', value: report.healthy_reference.after_di }]} note="Dimensionless damage index; lower is better for these healthy references." /><p>{report.healthy_reference.scope}</p></div><div><h3>Qualification controls the feasible bank.</h3><p className={styles.fraction}>{report.qualified_paths}<span> / {report.recorded_paths} paths</span></p><p>Qualified across {report.healthy_reference.healthy_anchors} measured temperature anchors. The fixed horizon is {report.confirmation.horizon} reveals. The diagnostic mean above includes every recorded path; qualification is a separate outcome.</p><p>Reference residual scales remain development proxies. The receiver test response does not fit its own baseline correction.</p></div></div>
      <div className={styles.controls}><label htmlFor="fundamental-stage">Study stage<select id="fundamental-stage" value={stageName} onChange={(event) => setStageName(event.target.value as 'confirmation' | 'development')}><option value="confirmation">Separate confirmation · completed</option><option value="development">Previously seen development</option></select></label><p aria-live="polite"><b>{stage.model_order_trajectories.toLocaleString('en-US')}</b> model/order trajectories · <b>{stage.unique_calibration_blocks}</b> unique healthy calibration blocks</p></div>
      <EvidenceMetricChart title={`${stageName === 'confirmation' ? 'Separate confirmation' : 'Exploratory development'} · adaptive conditional location error`} unit="mm" rows={stage.adaptive.map((row) => ({ label: row.label, value: row.mean_error_mm }))} note={`Fixed ${stage.horizon}-path horizon. Conditional location error; lower is better. Amber bars retain worse compensated results.`} adverse />
      <div className={styles.tableWrap}><table><caption>{stageName === 'confirmation' ? 'New warming confirmation banks; settings fixed before test responses were opened.' : 'Previously seen recordings; exploratory development only.'} Supported alerts count any declared prefix. Healthy denominators count unique banks.</caption><thead><tr><th scope="col">Adaptive variant</th><th scope="col">Mean error</th><th scope="col">Damage conditions alerted</th><th scope="col">Unique healthy banks alerted</th><th scope="col">Unsupported trajectories</th></tr></thead><tbody>{stage.adaptive.map((row) => <tr key={row.variant}><th scope="row">{row.label}</th><td>{row.mean_error_mm.toFixed(2)} mm</td><td>{row.damage_alerts} / {row.damage_conditions}</td><td>{row.healthy_alerts} / {row.unique_healthy_banks}</td><td>{row.unsupported_trajectories} / {row.model_order_trajectories}</td></tr>)}</tbody></table></div>
      <p className={styles.fineprint}>{stage.model_order_trajectories.toLocaleString('en-US')} trajectory evaluations and {stage.controller_model_calibrations.toLocaleString('en-US')} controller/model calibrations reuse measured banks. They are not independent physical trials. Minimum reference rank {stage.minimum_reference_rank.toFixed(2)} at nominal α = {stage.alpha.toFixed(2)}; exchangeability and field coverage remain unverified.{stageName === 'development' && ' Three healthy calibration blocks make the rank too coarse to support a 5% claim.'}</p>
      <div className={styles.notice}><h3>Qualification is an experimental scope, not a release decision.</h3><ul className={styles.riskList}>{report.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul></div>
      <div className={styles.sourceLinks}><a className={styles.link} href={report.source_url} target="_blank" rel="noopener noreferrer">Original OGW collection ↗</a><a className={styles.link} href={report.license_url} target="_blank" rel="noopener noreferrer">{report.license} ↗</a></div>
      <details className={styles.provenance}><summary>Source hashes, completed stage and export freshness</summary><p>{report.verification_scope}</p><p>Exported {exported} IST. {report.source_files_checked} distinct recorded source/data hashes matched local files at export. Review date: {report.review_date}. Native recordings: {report.native_sample_rate_hz.toLocaleString('en-US')} Hz; excitation: {report.excitation_hz.toLocaleString('en-US')} Hz.</p>{report.artifacts.map((artifact) => <article key={artifact.role}><p>{artifact.role} artifact · {artifact.source_verification.files_checked} source/input files checked</p><code>{artifact.path}</code><code>{artifact.sha256}</code><p>Recorded source-manifest SHA-256:</p><code>{artifact.source_verification.manifest_sha256}</code></article>)}<p>Canonical recorded overview:</p><code>{report.canonical_summary.path}</code><code>{report.canonical_summary.sha256}</code><p>Technical review document:</p><code>{report.review_document.path}</code><code>{report.review_document.sha256}</code><p>Hash checks establish content consistency. This page does not rerun an experiment, validate the local apparatus or establish patent novelty.</p></details>
    </>}
  </section>;
}
