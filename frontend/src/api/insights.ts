/**
 * REST API client module for Phase 18 Traffic Decision Intelligence & Explainable Insights.
 * Connects to /api/v1/insights endpoints.
 */
import { apiClient } from './client';
import {
  InsightGenerateResponse,
  InsightInfoResponse,
  TrafficInsightDetailResponse,
  TrafficInsightListResponse,
} from '@/types/insight';

export interface InsightQueryParams {
  session_id?: string;
  job_id?: string;
  category?: string;
  severity?: string;
  status?: string;
  affected_lane_id?: string;
  provenance_category?: string;
  is_synthetic?: boolean;
  limit?: number;
  offset?: number;
}

/**
 * Retrieves catalog of categories, severities, architectural boundaries, and anti-fabrication policies.
 */
export async function getInsightInfo(): Promise<InsightInfoResponse> {
  return apiClient<InsightInfoResponse>('/api/v1/insights/info');
}

/**
 * Generates deterministic insights for an AnalysisSession.
 * Consumes persisted database records only — zero heavy CV execution.
 */
export async function generateInsights(
  sessionId: string,
  jobId?: string,
  forceRecompute = false
): Promise<InsightGenerateResponse> {
  return apiClient<InsightGenerateResponse>('/api/v1/insights/generate', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      job_id: jobId || null,
      force_recompute: forceRecompute,
    }),
  });
}

/**
 * Queries persisted decision intelligence insights with multi-parameter filtering.
 */
export async function listInsights(
  params?: InsightQueryParams
): Promise<TrafficInsightListResponse> {
  const queryParams = new URLSearchParams();
  if (params) {
    if (params.session_id) queryParams.set('session_id', params.session_id);
    if (params.job_id) queryParams.set('job_id', params.job_id);
    if (params.category && params.category !== 'all') queryParams.set('category', params.category);
    if (params.severity && params.severity !== 'all') queryParams.set('severity', params.severity);
    if (params.status && params.status !== 'all') queryParams.set('status', params.status);
    if (params.affected_lane_id) queryParams.set('affected_lane_id', params.affected_lane_id);
    if (params.provenance_category) queryParams.set('provenance_category', params.provenance_category);
    if (params.is_synthetic !== undefined) queryParams.set('is_synthetic', String(params.is_synthetic));
    if (params.limit !== undefined) queryParams.set('limit', String(params.limit));
    if (params.offset !== undefined) queryParams.set('offset', String(params.offset));
  }
  const qs = queryParams.toString();
  return apiClient<TrafficInsightListResponse>(`/api/v1/insights${qs ? `?${qs}` : ''}`);
}

/**
 * Retrieves a single detailed insight by ID.
 */
export async function getInsightDetail(
  insightId: string
): Promise<TrafficInsightDetailResponse> {
  return apiClient<TrafficInsightDetailResponse>(`/api/v1/insights/${insightId}`);
}

/**
 * Updates the operational status of an insight (e.g. DISMISSED, ACTIVE).
 */
export async function updateInsightStatus(
  insightId: string,
  status: string,
  note?: string
): Promise<TrafficInsightDetailResponse> {
  return apiClient<TrafficInsightDetailResponse>(`/api/v1/insights/${insightId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, note }),
  });
}
