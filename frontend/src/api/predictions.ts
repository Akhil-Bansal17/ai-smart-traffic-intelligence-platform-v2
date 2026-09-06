/**
 * Traffic Prediction & Forecasting API Client module.
 * Communicates with backend /api/v1/predictions endpoints.
 */
import { apiClient } from './client';
import {
  PredictionInfoResponse,
  DatasetReadinessResponse,
  TrainModelRequest,
  PredictionRunDetailResponse,
  PredictionRunListResponse,
  GenerateFixturesRequest,
  GenerateFixturesResponse,
} from '@/types/prediction';

/**
 * Fetches prediction pipeline metadata and supported model architectures.
 */
export async function getPredictionInfo(): Promise<PredictionInfoResponse> {
  return apiClient<PredictionInfoResponse>('/api/v1/predictions/info');
}

/**
 * Checks if enough real historical traffic data exists for ML training.
 */
export async function getDatasetReadiness(): Promise<DatasetReadinessResponse> {
  return apiClient<DatasetReadinessResponse>('/api/v1/predictions/readiness');
}

/**
 * Triggers ML model training and generates multi-step forward predictions.
 */
export async function trainAndForecast(
  request: TrainModelRequest = {}
): Promise<PredictionRunDetailResponse> {
  return apiClient<PredictionRunDetailResponse>('/api/v1/predictions/train', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Fetches historical prediction runs with paginated summary info.
 */
export async function getPredictionRuns(
  page: number = 1,
  pageSize: number = 20,
  modelType?: string
): Promise<PredictionRunListResponse> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('page_size', pageSize.toString());
  if (modelType) {
    params.set('model_type', modelType);
  }
  return apiClient<PredictionRunListResponse>(`/api/v1/predictions/runs?${params.toString()}`);
}

/**
 * Fetches detailed prediction run by ID, including item forecasts and intervals.
 */
export async function getPredictionRunDetail(
  runId: string
): Promise<PredictionRunDetailResponse> {
  return apiClient<PredictionRunDetailResponse>(`/api/v1/predictions/runs/${runId}`);
}

/**
 * Populates synthetic test fixtures for development and testing.
 */
export async function generateSyntheticFixtures(
  request: GenerateFixturesRequest = {}
): Promise<GenerateFixturesResponse> {
  return apiClient<GenerateFixturesResponse>('/api/v1/predictions/fixtures/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
