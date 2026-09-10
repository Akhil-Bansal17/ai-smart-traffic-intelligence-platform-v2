/**
 * Emergency Corridor Simulation & Signal Priority API Client.
 * Communicates with backend `/api/v1/emergency-corridor` endpoints.
 */
import { apiClient } from './client';
import {
  CorridorPresetsResponse,
  EmergencyCorridorDetailResponse,
  EmergencyCorridorInfoResponse,
  EmergencyCorridorListResponse,
  EmergencyCorridorSimulationRequest,
} from '@/types/emergencyCorridor';

/**
 * Fetches emergency corridor simulation pipeline info, supported strategies, and safety disclaimers.
 */
export async function getEmergencyCorridorInfo(): Promise<EmergencyCorridorInfoResponse> {
  return apiClient<EmergencyCorridorInfoResponse>('/api/v1/emergency-corridor/info');
}

/**
 * Fetches pre-configured multi-intersection corridor topologies and emergency vehicle scenarios.
 */
export async function getEmergencyCorridorPresets(): Promise<CorridorPresetsResponse> {
  return apiClient<CorridorPresetsResponse>('/api/v1/emergency-corridor/presets');
}

/**
 * Executes an emergency corridor simulation comparing baseline vs coordinated priority plans.
 */
export async function runEmergencyCorridorSimulation(
  request: EmergencyCorridorSimulationRequest = {}
): Promise<EmergencyCorridorDetailResponse> {
  return apiClient<EmergencyCorridorDetailResponse>('/api/v1/emergency-corridor/simulate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Fetches paginated historical corridor simulation runs.
 */
export async function getEmergencyCorridorRuns(
  page: number = 1,
  pageSize: number = 20,
  dataSource?: string,
  vehicleType?: string,
  strategy?: string
): Promise<EmergencyCorridorListResponse> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('page_size', pageSize.toString());
  if (dataSource) {
    params.set('data_source', dataSource);
  }
  if (vehicleType) {
    params.set('vehicle_type', vehicleType);
  }
  if (strategy) {
    params.set('strategy', strategy);
  }
  return apiClient<EmergencyCorridorListResponse>(
    `/api/v1/emergency-corridor/runs?${params.toString()}`
  );
}

/**
 * Fetches detailed simulation run metrics, node timelines, and comparison results by ID.
 */
export async function getEmergencyCorridorRunDetail(
  runId: string
): Promise<EmergencyCorridorDetailResponse> {
  return apiClient<EmergencyCorridorDetailResponse>(
    `/api/v1/emergency-corridor/runs/${runId}`
  );
}

/**
 * Permanently deletes a historical corridor simulation run.
 */
export async function deleteEmergencyCorridorRun(runId: string): Promise<void> {
  return apiClient<void>(`/api/v1/emergency-corridor/runs/${runId}`, {
    method: 'DELETE',
  });
}
