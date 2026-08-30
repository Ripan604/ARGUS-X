export type Preset = 'easy' | 'medium' | 'hard';

export interface ExperimentParameters {
  source_x: number;
  source_y: number;
  receiver_x: number;
  receiver_y: number;
  frequency_start_hz: number;
  frequency_end_hz: number;
  amplitude: number;
  duration_s: number;
  waveform: 'impulse' | 'sine' | 'chirp' | 'tone_burst' | 'ricker' | 'multisine' | 'phase_coded' | 'complementary_coded' | 'spectrally_notched';
  phase_code?: string | null;
  code_length?: number;
  sample_rate_hz?: number | null;
  spectral_notches_hz?: [number, number][];
}

export interface CandidateScore {
  experiment: ExperimentParameters;
  expected_information_gain: number;
  hypothesis_disagreement: number;
  uncertainty_coverage: number;
  experiment_cost: number;
  repetition_penalty: number;
  final_score: number;
  expected_risk_reduction?: number;
  calibration_value?: number;
  model_trust?: number;
  time_cost?: number;
  energy_cost?: number;
  chosen_model_fidelity?: number;
  reason_for_fidelity?: string;
  predicted_uncertainty_after?: number | null;
}

export interface Recommendation {
  experiment: ExperimentParameters;
  expected_information_gain: number;
  hypothesis_disagreement: number;
  uncertainty_coverage: number;
  experiment_cost: number;
  repetition_penalty: number;
  planner_score: number;
  explanation: string;
  strategy: string;
  action_type: 'diagnostic' | 'calibration' | 'verification' | 'exploration';
  objective: string;
  structured_explanation: Record<string, unknown>;
  chosen_model_fidelity: number;
  reason_for_fidelity: string;
  planning_horizon: number;
  top_candidates: CandidateScore[];
}

export interface Defect {
  center_x: number;
  center_y: number;
  radius_x: number;
  radius_y: number;
  severity: number;
  defect_type: string;
}

export interface SessionStatus {
  map_x: number;
  map_y: number;
  mean_x: number;
  mean_y: number;
  peak_probability: number;
  local_probability_mass: number;
  confidence: number;
  entropy_bits: number;
  normalized_entropy: number;
  covariance: number[][];
  experiment_count: number;
  should_stop: boolean;
  stop_reason: string | null;
  stop_explanation?: string;
  structural_uncertainty: number;
  metrology_uncertainty: number;
  model_trust: number;
  ood_score: number;
  ood_status: 'NOMINAL' | 'CAUTION' | 'OUT_OF_DISTRIBUTION' | 'ABSTAIN';
  decision_confidence: number;
  bayes_risk: number;
  expected_value_of_information: number;
  credible_region_90: { mass: number; cell_count: number; area_fraction: number; x_min: number; x_max: number; y_min: number; y_max: number };
  top_hypotheses: Array<{ rank: number; x: number; y: number; probability: number; radius_mean: number; severity_mean: number; dominant_type: string }>;
  integrity_assessment: IntegrityAssessment;
  sensor_health: SensorHealth;
  recommended_engineering_action: string;
}

export interface IntegrityAssessment {
  scope: 'research_screening_only';
  integrity_state: 'HEALTHY_OR_NO_DETECTABLE_DAMAGE' | 'KNOWN_DAMAGE_CANDIDATE' | 'UNKNOWN_OR_UNSUPPORTED';
  state_probabilities: {
    healthy_or_no_detectable_damage: number;
    known_damage_candidate: number;
    unknown_or_unsupported: number;
  };
  defect_count_screening: Record<string, number>;
  candidate_regions: SessionStatus['top_hypotheses'];
  engineering_action: string;
  decision_basis: string;
  human_authority_required: boolean;
  minimum_detectable_damage_size: string;
  characterization_status: string;
}

export interface SensorHealth {
  version: number;
  accepted_measurements: number;
  rejected_measurements: number;
  damage_screening_probability: number;
  sensors: Record<string, {
    sensor_id: string;
    reliability_mean: number;
    status: 'NOMINAL' | 'DEGRADED' | 'UNRELIABLE';
    measurement_count: number;
    rejected_count: number;
    consecutive_rejections: number;
    last_failure_reasons: string[];
  }>;
  environment_baseline: Record<string, number>;
  environment_latest: Record<string, number>;
  drift_flags: string[];
  failure_conditions: Array<Record<string, unknown>>;
}

export interface SessionState {
  id: string;
  mode: string;
  preset: Preset;
  revealed: boolean;
  panel: { width_m: number; height_m: number; material: string };
  material: Record<string, number>;
  config: Record<string, number>;
  status: SessionStatus;
  posterior: number[][];
  recommendation: Recommendation;
  calibration: Record<string, unknown> | null;
  ground_truth: Defect | null;
  localization_error_mm: number | null;
  joint_inference: Record<string, unknown>;
  uncertainty: {
    structural: Record<string, number | string | Record<string, number>>;
    metrology: Record<string, number | string | Record<string, number>>;
    model_discrepancy: Record<string, unknown>;
    ood: Record<string, unknown>;
  };
  no_go_regions: Array<{ x_min: number; y_min: number; x_max: number; y_max: number; label: string }>;
  human_decisions: Array<Record<string, unknown>>;
  assurance: SensorHealth;
  safety: {
    emergency_stop: { latched: boolean; reason: string | null; latched_at: string | null; released_at: string | null };
    automation_scope: string;
    human_release_authority: boolean;
  };
}

export interface ResearchJob {
  id: string;
  job_type: 'benchmark' | 'calibration' | 'ablation' | 'dataset_generation' | 'surrogate_training' | 'demo_scenario';
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  request: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  cancellation_requested: boolean;
}

export interface MeasurementAnalysis {
  sample_rate: number;
  time_s: number[];
  waveform: number[];
  fft_frequency_hz: number[];
  fft_power: number[];
  psd_frequency_hz: number[];
  psd: number[];
  spectrogram_time_s: number[];
  spectrogram_frequency_hz: number[];
  spectrogram_db: number[][];
  features: Record<string, number>;
}

export interface HistoryItem {
  experiment_index: number;
  created_at: string;
  parameters: ExperimentParameters;
  features: MeasurementAnalysis;
  posterior_before: number[][];
  posterior_after: number[][];
  likelihood: number[][];
  planner: Recommendation;
  diagnostics: Record<string, number>;
}

export interface BenchmarkSummary {
  mean_localization_error_mm: number;
  median_localization_error_mm: number;
  mean_experiments: number;
  mean_final_entropy: number;
  mean_entropy_reduction: number;
  mean_entropy_auc: number;
  mean_measurement_cost: number;
  success_rate_10mm: number;
  success_rate_15mm: number;
  success_rate_20mm: number;
  success_rate_30mm: number;
}

export interface PairedBenchmarkComparison {
  mean_error_advantage_mm: number;
  error_advantage_95ci_mm: [number, number];
  error_win_rate: number;
  mean_entropy_advantage: number;
  entropy_advantage_95ci: [number, number];
  entropy_win_rate: number;
}

export interface BenchmarkResult {
  metadata: Record<string, number | string>;
  summary: Record<'random' | 'uniform_grid' | 'argus', BenchmarkSummary>;
  trajectories: Record<'random' | 'uniform_grid' | 'argus', {
    mean_entropy: number[];
    mean_localization_error_mm: number[];
  }>;
  paired_comparisons: Record<'argus_vs_random' | 'argus_vs_uniform_grid', PairedBenchmarkComparison>;
  runs: Record<string, unknown>[];
}
