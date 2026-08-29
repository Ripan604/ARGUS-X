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
  waveform: 'impulse' | 'sine' | 'chirp';
}

export interface CandidateScore {
  experiment: ExperimentParameters;
  expected_information_gain: number;
  hypothesis_disagreement: number;
  uncertainty_coverage: number;
  experiment_cost: number;
  repetition_penalty: number;
  final_score: number;
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
