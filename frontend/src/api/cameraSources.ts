/**
 * API client module for Camera Sources and Live Monitoring.
 * Phase 21: Live Traffic Monitoring & Camera Source Management.
 */
import { apiClient } from './client';
import { getApiBaseUrl } from '@/config/env';
import {
  CameraSource,
  CameraSourceCreatePayload,
  CameraSourceListResponse,
  CameraSourceTestResponse,
  CameraSourceUpdatePayload,
  LiveMonitoringStatus,
} from '@/types/camera';
import { AnalysisJob } from '@/types/analysis';

export async function listCameraSources(
  sourceType?: string,
  enabled?: boolean
): Promise<CameraSourceListResponse> {
  const params = new URLSearchParams();
  if (sourceType) params.append('source_type', sourceType);
  if (enabled !== undefined) params.append('enabled', String(enabled));
  const queryString = params.toString();
  const endpoint = queryString ? `/camera-sources?${queryString}` : '/camera-sources';
  return apiClient<CameraSourceListResponse>(endpoint);
}

export async function getCameraSource(id: string): Promise<CameraSource> {
  return apiClient<CameraSource>(`/camera-sources/${id}`);
}

export async function createCameraSource(
  payload: CameraSourceCreatePayload
): Promise<CameraSource> {
  return apiClient<CameraSource>('/camera-sources', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCameraSource(
  id: string,
  payload: CameraSourceUpdatePayload
): Promise<CameraSource> {
  return apiClient<CameraSource>(`/camera-sources/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteCameraSource(id: string): Promise<void> {
  return apiClient<void>(`/camera-sources/${id}`, {
    method: 'DELETE',
  });
}

export async function testCameraConnection(
  id: string
): Promise<CameraSourceTestResponse> {
  return apiClient<CameraSourceTestResponse>(`/camera-sources/${id}/test`, {
    method: 'POST',
  });
}

export async function startLiveMonitoring(
  id: string,
  config?: Record<string, any>
): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>(`/camera-sources/${id}/start`, {
    method: 'POST',
    body: config ? JSON.stringify(config) : undefined,
  });
}

export async function stopLiveMonitoring(id: string): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>(`/camera-sources/${id}/stop`, {
    method: 'POST',
  });
}

export async function getLiveMonitoringStatus(
  id: string
): Promise<LiveMonitoringStatus> {
  return apiClient<LiveMonitoringStatus>(`/camera-sources/${id}/live-status`);
}

export function getCameraPreviewUrl(id: string, cacheBust = true): string {
  const baseUrl = getApiBaseUrl();
  const base = `${baseUrl}/camera-sources/${id}/preview.jpg`;
  return cacheBust ? `${base}?t=${Date.now()}` : base;
}
