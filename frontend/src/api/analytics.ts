/**
 * Traffic Analytics API Client module.
 */
import { apiClient } from './client';
import {
  AnalyticsInfoResponse,
  AnalyticsRequestParams,
  TrafficMetricsResponse,
} from '@/types/analytics';

/**
 * Executes full traffic flow analytics pipeline on an ingested video.
 */
export async function analyzeTrafficVideo(
  videoId: string,
  params?: AnalyticsRequestParams
): Promise<TrafficMetricsResponse> {
  return apiClient<TrafficMetricsResponse>(
    `/api/v1/analytics/videos/${videoId}`,
    {
      method: 'POST',
      body: JSON.stringify(params || {}),
      timeoutMs: 60000,
    }
  );
}

export const analyzeTraffic = analyzeTrafficVideo;

/**
 * Fetches information about active traffic analytics formulas and data honesty policy.
 */
export async function getAnalyticsInfo(): Promise<AnalyticsInfoResponse> {
  return apiClient<AnalyticsInfoResponse>('/api/v1/analytics/info');
}
