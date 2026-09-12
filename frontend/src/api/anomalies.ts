/**
 * REST API client module for Phase 15 Traffic Anomaly & Congestion Incident Detection.
 * Connects to /api/v1/anomalies endpoints.
 */
import { apiClient } from './client';
import {
  AnomalyEventDetailResponse,
  AnomalyEventListResponse,
  AnomalyEvent,
  AnomalyInfoResponse,
  AnomalyQueryParams,
  DetectAnomaliesResponse,
  UpdateAnomalyStatusRequest,
} from '@/types/anomaly';

/**
 * Retrieves rule threshold configurations, engine metadata, and anti-fabrication guidelines.
 */
export async function getAnomalyInfo(): Promise<AnomalyInfoResponse> {
  return apiClient<AnomalyInfoResponse>('/api/v1/anomalies/info');
}

/**
 * Queries persisted anomaly events with multi-parameter filtering.
 */
export async function listAnomalyEvents(
  params?: AnomalyQueryParams
): Promise<AnomalyEventListResponse> {
  const queryParams = new URLSearchParams();
  if (params) {
    if (params.session_id) queryParams.set('session_id', params.session_id);
    if (params.anomaly_type) queryParams.set('anomaly_type', params.anomaly_type);
    if (params.severity) queryParams.set('severity', params.severity);
    if (params.status) queryParams.set('status', params.status);
    if (params.provenance_category) queryParams.set('provenance_category', params.provenance_category);
    if (params.is_synthetic !== undefined) queryParams.set('is_synthetic', String(params.is_synthetic));
    if (params.limit !== undefined) queryParams.set('limit', String(params.limit));
    if (params.offset !== undefined) queryParams.set('offset', String(params.offset));
  }
  const qs = queryParams.toString();
  return apiClient<AnomalyEventListResponse>(`/api/v1/anomalies/events${qs ? `?${qs}` : ''}`);
}

/**
 * Fetches single anomaly event with parent session and video provenance lineage.
 */
export async function getAnomalyEventDetail(
  eventId: string
): Promise<AnomalyEventDetailResponse> {
  return apiClient<AnomalyEventDetailResponse>(`/api/v1/anomalies/events/${eventId}`);
}

/**
 * Triggers on-demand idempotent statistical anomaly detection over an existing AnalysisSession.
 */
export async function triggerAnomalyDetection(
  sessionId: string
): Promise<DetectAnomaliesResponse> {
  return apiClient<DetectAnomaliesResponse>(`/api/v1/anomalies/detect/${sessionId}`, {
    method: 'POST',
  });
}

/**
 * Updates an anomaly event status ('acknowledged' or 'resolved') with optional operator note.
 */
export async function updateAnomalyStatus(
  eventId: string,
  data: UpdateAnomalyStatusRequest
): Promise<AnomalyEvent> {
  return apiClient<AnomalyEvent>(`/api/v1/anomalies/events/${eventId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Deletes an anomaly event by ID.
 */
export async function deleteAnomalyEvent(
  eventId: string
): Promise<{ status: string; id: string }> {
  return apiClient<{ status: string; id: string }>(`/api/v1/anomalies/events/${eventId}`, {
    method: 'DELETE',
  });
}
