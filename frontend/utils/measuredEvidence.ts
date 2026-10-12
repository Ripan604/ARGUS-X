export type MeasuredTask = 'tap_screening' | 'transient_source_localization' | 'recorded_path_replay' | 'acquisition_quality';
export type MetricUnit = 'fraction' | 'mm' | 'count';
export interface MeasuredTable {
  caption: string;
  columns: { key: string; label: string; unit: MetricUnit }[];
  rows: { method: string; values: Record<string, number | null> }[];
}
export interface MeasuredStudy {
  id: 'gfrp' | 'impact' | 'morpho' | 'ogw';
  title: string;
  task: MeasuredTask;
  native_sample_rate_hz: number;
  counts: { label: string; value: number }[];
  source_url: string;
  doi: string | null;
  license: string;
  license_url: string;
  evidence_scope: string;
  validation: string;
  headline: { label: string; value: number; unit: MetricUnit };
  interval: { label: string; bounds: [number, number]; unit: MetricUnit } | null;
  tables: MeasuredTable[];
  risks: string[];
  artifact: { path: string; sha256: string };
  source_verification: { files_checked: number; current_matches: true; source_changed_during_run: false; manifest_sha256: string };
}
export interface MeasuredReport {
  schema_version: 1;
  evidence_source: 'measured_external_reanalysis';
  review_date: string;
  hardware_validated: false;
  sources_verified_at_export: true;
  scope: string;
  studies: MeasuredStudy[];
}

const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.length > 0 && value.length <= 1200;
const hash = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const integer = (value: unknown) => typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 1_000_000_000;
const unit = (value: unknown): value is MetricUnit => value === 'fraction' || value === 'mm' || value === 'count';
const validNumber = (value: unknown, metricUnit: MetricUnit) => typeof value === 'number' && Number.isFinite(value)
  && value >= 0 && (metricUnit === 'fraction' ? value <= 1 : metricUnit === 'count' ? integer(value) : value <= 1_000_000);
function sourceUrl(value: unknown): boolean {
  if (!text(value)) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password
      && ['doi.org', 'zenodo.org', 'tudatalib.ulb.tu-darmstadt.de', 'creativecommons.org'].includes(url.hostname);
  } catch { return false; }
}
function metric(value: unknown): boolean {
  return object(value) && text(value.label) && unit(value.unit) && validNumber(value.value, value.unit);
}
function validStudy(value: unknown): value is MeasuredStudy {
  if (!object(value) || !['gfrp', 'impact', 'morpho', 'ogw'].includes(String(value.id))
    || !['tap_screening', 'transient_source_localization', 'recorded_path_replay', 'acquisition_quality'].includes(String(value.task))
    || !text(value.title) || !text(value.evidence_scope) || !text(value.validation)
    || !integer(value.native_sample_rate_hz) || Number(value.native_sample_rate_hz) === 0
    || !sourceUrl(value.source_url) || !sourceUrl(value.license_url) || !text(value.license)
    || !(value.doi === null || text(value.doi)) || !metric(value.headline)) return false;
  const tasks = { gfrp: 'tap_screening', impact: 'transient_source_localization', morpho: 'acquisition_quality', ogw: 'recorded_path_replay' };
  const units = { gfrp: 'fraction', impact: 'mm', morpho: 'count', ogw: 'mm' };
  const id = value.id as MeasuredStudy['id'];
  if (value.task !== tasks[id] || !object(value.headline) || value.headline.unit !== units[id]) return false;
  if (!Array.isArray(value.counts) || value.counts.length < 1 || value.counts.length > 8
    || !value.counts.every((count) => object(count) && text(count.label) && integer(count.value))) return false;
  if (!Array.isArray(value.risks) || value.risks.length < 1 || value.risks.length > 8 || !value.risks.every(text)) return false;
  if (!object(value.artifact) || !text(value.artifact.path)
    || !/^research_results\/measured_[a-z_]+_\d{4}_\d{2}_\d{2}\.json$/.test(value.artifact.path)
    || !hash(value.artifact.sha256)) return false;
  if (!object(value.source_verification) || !integer(value.source_verification.files_checked)
    || Number(value.source_verification.files_checked) === 0 || value.source_verification.current_matches !== true
    || value.source_verification.source_changed_during_run !== false || !hash(value.source_verification.manifest_sha256)) return false;
  if (value.interval !== null) {
    const interval = value.interval;
    if (!object(interval) || !text(interval.label) || !unit(interval.unit) || !Array.isArray(interval.bounds)
      || interval.bounds.length !== 2 || !interval.bounds.every((bound) => validNumber(bound, interval.unit as MetricUnit))
      || Number(interval.bounds[0]) > Number(interval.bounds[1])) return false;
  }
  if (!Array.isArray(value.tables) || value.tables.length < 1 || value.tables.length > 4) return false;
  for (const table of value.tables) {
    if (!object(table) || !text(table.caption) || !Array.isArray(table.columns) || table.columns.length < 1 || table.columns.length > 6
      || !table.columns.every((column) => object(column) && text(column.key) && text(column.label) && unit(column.unit))
      || !Array.isArray(table.rows) || table.rows.length < 1 || table.rows.length > 12) return false;
    const columns = table.columns as MeasuredTable['columns'];
    if (new Set(columns.map((column) => column.key)).size !== columns.length) return false;
    for (const row of table.rows) {
      if (!object(row) || !text(row.method) || !object(row.values)) return false;
      if (!columns.every((column) => row.values && object(row.values)
        && (row.values[column.key] === null || validNumber(row.values[column.key], column.unit)))) return false;
    }
  }
  return true;
}

export function parseMeasuredReport(value: unknown): MeasuredReport | null {
  if (!object(value) || value.schema_version !== 1 || value.evidence_source !== 'measured_external_reanalysis'
    || value.hardware_validated !== false || value.sources_verified_at_export !== true
    || !text(value.scope) || typeof value.review_date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value.review_date)
    || !Array.isArray(value.studies) || value.studies.length !== 4 || !value.studies.every(validStudy)
    || new Set(value.studies.map((study) => study.id)).size !== 4) return null;
  return value as unknown as MeasuredReport;
}

export function formatMeasuredMetric(value: number | null, metricUnit: MetricUnit): string {
  if (value === null) return 'Unavailable';
  return metricUnit === 'fraction' ? `${(value * 100).toFixed(1)}%`
    : metricUnit === 'mm' ? `${value.toFixed(2)} mm` : value.toLocaleString('en-US');
}
