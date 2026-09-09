/**
 * Traffic Signal Optimization Simulation API Client.
 * Communicates with backend `/api/v1/signal-optimization` endpoints.
 */
import { apiClient } from './client';
import {
  PresetsResponse,
  SignalOptimizationInfoResponse,
  SignalSimulationDetailResponse,
  SignalSimulationListResponse,
  SignalSimulationRequest,
} from '@/types/signalOptimization';

/**
 * Fetches signal optimization pipeline info, algorithms, and disclaimers.
 */
export async function getSignalOptimizationInfo(): Promise<SignalOptimizationInfoResponse> {
  return apiClient<SignalOptimizationInfoResponse>('/api/v1/signal-optimization/info');
}

/**
 * Fetches pre-configured intersection topologies and demand scenarios.
 */
export async function getSignalOptimizationPresets(): Promise<PresetsResponse> {
  return apiClient<PresetsResponse>('/api/v1/signal-optimization/presets');
}

/**
 * Executes a signal optimization and simulation run comparing baseline vs optimized plans.
 */
export async function runSignalSimulation(
  request: SignalSimulationRequest = {}
): Promise<SignalSimulationDetailResponse> {
  return apiClient<SignalSimulationDetailResponse>('/api/v1/signal-optimization/simulate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Fetches paginated historical signal optimization simulation runs.
 */
export async function getSignalSimulationRuns(
  page: number = 1,
  pageSize: number = 20,
  dataSource?: string,
  algorithm?: string
): Promise<SignalSimulationListResponse> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('page_size', pageSize.toString());
  if (dataSource) {
    params.set('data_source', dataSource);
  }
  if (algorithm) {
    params.set('algorithm', algorithm);
  }
  return apiClient<SignalSimulationListResponse>(
    `/api/v1/signal-optimization/runs?${params.toString()}`
  );
}

/**
 * Fetches detailed simulation run metrics and comparison results by ID.
 */
export async function getSignalSimulationRunDetail(
  runId: string
): Promise<SignalSimulationDetailResponse> {
  return apiClient<SignalSimulationDetailResponse>(
    `/api/v1/signal-optimization/runs/${runId}`
  );
}

/**
 * Deletes a historical simulation run.
 */
export async function deleteSignalSimulationRun(runId: string): Promise<void> {
  return apiClient<void>(`/api/v1/signal-optimization/runs/${runId}`, {
    method: 'DELETE',
  });
}
