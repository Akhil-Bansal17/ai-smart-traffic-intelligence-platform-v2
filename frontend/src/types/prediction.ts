/**
 * Types for Phase 11 — Traffic Prediction / Forecasting
 */

export type ModelType = 'random_forest' | 'hist_gradient_boosting' | 'ridge' | 'naive_persistence';

export type DataSource = 'real_observations' | 'real_observations_insufficient' | 'synthetic_pipeline' | 'synthetic_fixture';

export interface PredictionInfoResponse {
  model_types: string[];
  default_model: string;
  min_training_samples: number;
  horizon_steps: number[];
  time_step_seconds: number;
  features_used: string[];
  baseline_model: string;
}

export interface DatasetReadinessResponse {
  is_ready: boolean;
  sample_count: number;
  threshold: number;
  message: string;
  session_count: number;
  status_code: string;
  data_source: DataSource;
  real_sample_count?: number;
  synthetic_sample_count?: number;
  earliest_timestamp?: string | null;
  latest_timestamp?: string | null;
}

export interface PredictionItemDetail {
  id: string;
  step: number;
  predicted_volume: number;
  predicted_inbound: number;
  predicted_outbound: number;
  predicted_density_state: string;
  lower_bound: number;
  upper_bound: number;
  forecast_horizon_seconds: number;
  target_timestamp: string;
}

export interface PredictionRunDetailResponse {
  id: string;
  session_id: string | null;
  model_type: string;
  data_source: DataSource;
  sample_count: number;
  train_samples: number;
  test_samples: number;
  horizon_steps: number;
  time_step_seconds: number;
  mae: number;
  rmse: number;
  r2_score: number;
  baseline_mae: number;
  baseline_rmse: number;
  baseline_improvement_pct: number;
  feature_importance: Record<string, number>;
  predictions: PredictionItemDetail[];
  created_at: string;
}

export interface PredictionRunSummary {
  id: string;
  session_id: string | null;
  model_type: string;
  data_source: DataSource;
  sample_count: number;
  train_samples: number;
  test_samples: number;
  horizon_steps: number;
  time_step_seconds: number;
  mae: number;
  rmse: number;
  r2_score: number;
  baseline_mae: number;
  baseline_rmse: number;
  baseline_improvement_pct: number;
  predictions_count: number;
  created_at: string;
}

export interface PredictionRunListResponse {
  items: PredictionRunSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TrainModelRequest {
  model_type?: string;
  horizon_steps?: number;
  time_step_seconds?: number;
  session_id?: string;
  use_synthetic_if_empty?: boolean;
}

export interface GenerateFixturesRequest {
  sample_count?: number;
  pattern?: 'rush_hour_surge' | 'sine_wave_normal' | 'weekend_calm';
  noise_level?: number;
}

export interface GenerateFixturesResponse {
  message: string;
  sample_count: number;
  pattern: string;
  noise_level: number;
  data_source: string;
}
