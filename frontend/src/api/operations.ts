import { apiClient } from './client';
import {
  OperationsCameraOverviewItem,
  OperationsHistoricalContextResponse,
  OperationsIncidentItem,
  OperationsIncidentListResponse,
  OperationsOverviewResponse,
  OperationsTimelineResponse,
  UpdateIncidentStatusRequest,
} from '@/types/operations';

export interface ListIncidentsParams {
  status?: string;
  severity?: string;
  camera_source_id?: string;
  anomaly_type?: string;
  limit?: number;
  offset?: number;
}

export interface TimelineParams {
  limit?: number;
  event_type?: string;
}

export async function getOperationsOverview(): Promise<OperationsOverviewResponse> {
  return apiClient<OperationsOverviewResponse>('/api/v1/operations/overview');
}

export async function getOperationsCameras(): Promise<OperationsCameraOverviewItem[]> {
  return apiClient<OperationsCameraOverviewItem[]>('/api/v1/operations/cameras');
}

export async function listOperationsIncidents(
  params: ListIncidentsParams = {}
): Promise<OperationsIncidentListResponse> {
  const query = new URLSearchParams();
  if (params.status && params.status !== 'all') query.set('status', params.status);
  if (params.severity && params.severity !== 'all') query.set('severity', params.severity);
  if (params.camera_source_id) query.set('camera_source_id', params.camera_source_id);
  if (params.anomaly_type && params.anomaly_type !== 'all') query.set('anomaly_type', params.anomaly_type);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.offset !== undefined) query.set('offset', String(params.offset));

  const qs = query.toString();
  return apiClient<OperationsIncidentListResponse>(
    `/api/v1/operations/incidents${qs ? `?${qs}` : ''}`
  );
}

export async function getOperationsIncidentDetail(
  incidentId: string
): Promise<OperationsIncidentItem> {
  return apiClient<OperationsIncidentItem>(`/api/v1/operations/incidents/${incidentId}`);
}

export async function updateOperationsIncidentStatus(
  incidentId: string,
  payload: UpdateIncidentStatusRequest
): Promise<OperationsIncidentItem> {
  return apiClient<OperationsIncidentItem>(`/api/v1/operations/incidents/${incidentId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getOperationsTimeline(
  params: TimelineParams = {}
): Promise<OperationsTimelineResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.event_type && params.event_type !== 'all') query.set('event_type', params.event_type);

  const qs = query.toString();
  return apiClient<OperationsTimelineResponse>(
    `/api/v1/operations/timeline${qs ? `?${qs}` : ''}`
  );
}

export async function getOperationsHistoricalContext(
  sourceId: string,
  timeWindow: string = '7d'
): Promise<OperationsHistoricalContextResponse> {
  return apiClient<OperationsHistoricalContextResponse>(
    `/api/v1/operations/context/${sourceId}?time_window=${encodeURIComponent(timeWindow)}`
  );
}
