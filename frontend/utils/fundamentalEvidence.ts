export type FundamentalVariant = 'raw_global' | 'transport_global' | 'transport_heteroscedastic';
export interface FundamentalAdaptiveRow {
  variant: FundamentalVariant; label: string; mean_error_mm: number;
  damage_alerts: number; damage_conditions: number; healthy_alerts: number; unique_healthy_banks: number;
  model_order_trajectories: number; unsupported_trajectories: number; descriptive_healthy_model_positive_rate: number;
}
export interface FundamentalStage {
  stage: 'development' | 'confirmation'; previously_seen_data: boolean; horizon: number;
  model_order_trajectories: number; controller_model_calibrations: number;
  unique_calibration_blocks: number; unique_test_banks: number; minimum_reference_rank: number; alpha: number;
  adaptive: FundamentalAdaptiveRow[];
}
export interface FundamentalReport {
  schema_version: 1; evidence_source: 'measured_reference_conditioned_external_reanalysis';
  review_date: string; exported_at_utc: string; status: 'completed'; sources_verified_at_export: true;
  hardware_validated: false; field_accuracy_established: false; patent_novelty_established: false;
  source_files_checked: number; scope: string; source_url: string; license: string; license_url: string;
  native_sample_rate_hz: number; excitation_hz: number; specimens: number; recorded_paths: number; qualified_paths: number;
  healthy_reference: { before_di: number; after_di: number; unit: 'dimensionless_damage_index'; paths_in_diagnostic_mean: number; healthy_anchors: number; scope: string };
  confirmation_acquired_banks: number; confirmation_required_banks: number;
  development: FundamentalStage; confirmation: FundamentalStage; risks: string[];
  artifacts: { role: 'healthy' | 'development' | 'confirmation'; path: string; sha256: string;
    source_verification: { files_checked: number; matches_at_export: true; source_changed_during_run: false; manifest_sha256: string } }[];
  canonical_summary: { path: string; sha256: string }; review_document: { path: string; sha256: string };
  verification_scope: string;
}

const object = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.length > 0 && value.length <= 1600;
const hash = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const finite = (value: unknown, maximum = 1_000_000): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= maximum;
const count = (value: unknown): value is number => finite(value, 1_000_000_000) && Number.isInteger(value);
const positive = (value: unknown): value is number => count(value) && value > 0;
function url(value: unknown): boolean {
  if (!text(value)) return false;
  try { const parsed = new URL(value); return parsed.protocol === 'https:' && !parsed.username && !parsed.password && ['doi.org', 'creativecommons.org'].includes(parsed.hostname); }
  catch { return false; }
}
function stage(value: unknown, expected: 'development' | 'confirmation'): value is FundamentalStage {
  if (!object(value) || value.stage !== expected || value.previously_seen_data !== (expected === 'development')
    || !positive(value.horizon) || !positive(value.model_order_trajectories) || !positive(value.controller_model_calibrations)
    || !positive(value.unique_calibration_blocks) || !positive(value.unique_test_banks)
    || !finite(value.minimum_reference_rank, 1) || value.minimum_reference_rank === 0 || !finite(value.alpha, 1) || value.alpha === 0
    || !Array.isArray(value.adaptive) || value.adaptive.length !== 3) return false;
  const variants = ['raw_global', 'transport_global', 'transport_heteroscedastic'];
  if (new Set(value.adaptive.map((row) => object(row) ? row.variant : null)).size !== 3) return false;
  return value.adaptive.every((row) => object(row) && variants.includes(String(row.variant)) && text(row.label)
    && finite(row.mean_error_mm) && positive(row.damage_conditions) && count(row.damage_alerts) && row.damage_alerts <= row.damage_conditions
    && positive(row.unique_healthy_banks) && count(row.healthy_alerts) && row.healthy_alerts <= row.unique_healthy_banks
    && positive(row.model_order_trajectories) && count(row.unsupported_trajectories) && row.unsupported_trajectories <= row.model_order_trajectories
    && finite(row.descriptive_healthy_model_positive_rate, 1));
}

export function parseFundamentalReport(value: unknown): FundamentalReport | null {
  if (!object(value) || value.schema_version !== 1 || value.evidence_source !== 'measured_reference_conditioned_external_reanalysis'
    || value.status !== 'completed' || value.sources_verified_at_export !== true
    || value.hardware_validated !== false || value.field_accuracy_established !== false || value.patent_novelty_established !== false
    || !text(value.scope) || !text(value.verification_scope) || !positive(value.source_files_checked)
    || typeof value.review_date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value.review_date)
    || typeof value.exported_at_utc !== 'string' || !Number.isFinite(Date.parse(value.exported_at_utc)) || !/(Z|\+00:00)$/.test(value.exported_at_utc)
    || !url(value.source_url) || !url(value.license_url) || !text(value.license)
    || !positive(value.native_sample_rate_hz) || !positive(value.excitation_hz) || value.excitation_hz >= value.native_sample_rate_hz / 2
    || !positive(value.specimens) || !positive(value.recorded_paths) || !positive(value.qualified_paths) || value.qualified_paths > value.recorded_paths
    || !positive(value.confirmation_acquired_banks) || value.confirmation_acquired_banks !== value.confirmation_required_banks
    || !stage(value.development, 'development') || !stage(value.confirmation, 'confirmation')) return null;
  if (value.confirmation.unique_calibration_blocks + value.confirmation.unique_test_banks !== value.confirmation_acquired_banks
    || value.confirmation.horizon > value.qualified_paths || value.development.horizon > value.qualified_paths) return null;
  const healthy = value.healthy_reference;
  if (!object(healthy) || !finite(healthy.before_di, 1) || !finite(healthy.after_di, 1) || healthy.unit !== 'dimensionless_damage_index'
    || healthy.paths_in_diagnostic_mean !== value.recorded_paths || !positive(healthy.healthy_anchors) || !text(healthy.scope)) return null;
  if (!Array.isArray(value.risks) || value.risks.length < 1 || value.risks.length > 8 || !value.risks.every(text)
    || !Array.isArray(value.artifacts) || value.artifacts.length !== 3) return null;
  const names = { healthy: 'healthy_reference_development', development: 'reference_conditioned_development', confirmation: 'reference_conditioned_confirmation' };
  const roles = new Set<string>();
  for (const artifact of value.artifacts) {
    if (!object(artifact) || !['healthy', 'development', 'confirmation'].includes(String(artifact.role))
      || !text(artifact.path) || !hash(artifact.sha256) || !object(artifact.source_verification)) return null;
    const role = artifact.role as keyof typeof names;
    if (!new RegExp(`^research_results/${names[role]}_\\d{4}_\\d{2}_\\d{2}\\.json$`).test(artifact.path)) return null;
    roles.add(role);
    const check = artifact.source_verification;
    if (!positive(check.files_checked) || check.matches_at_export !== true || check.source_changed_during_run !== false || !hash(check.manifest_sha256)) return null;
  }
  if (roles.size !== 3 || !object(value.canonical_summary) || value.canonical_summary.path !== 'output/fundamental_upgrade_summary.json'
    || !hash(value.canonical_summary.sha256) || !object(value.review_document)
    || !/^docs\/FUNDAMENTAL_UPGRADE_RESULTS_\d{4}_\d{2}_\d{2}\.md$/.test(String(value.review_document.path)) || !hash(value.review_document.sha256)) return null;
  return value as unknown as FundamentalReport;
}
