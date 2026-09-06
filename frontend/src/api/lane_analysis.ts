/**
 * Lane Analysis & Density Estimation API Client module.
 */
import { apiClient } from './client';
import {
  LaneAnalysisInfoResponse,
  LaneAnalysisRequestParams,
  LaneAnalyticsResponse,
} from '@/types/lane_analysis';

/**
 * Executes lane assignment and density estimation pipeline on an ingested video.
 */
export async function analyzeVideoLanes(
  videoId: string,
  params: LaneAnalysisRequestParams
): Promise<LaneAnalyticsResponse> {
  return apiClient<LaneAnalyticsResponse>(
    `/api/v1/lane-analysis/videos/${videoId}`,
    {
      method: 'POST',
      body: JSON.stringify(params),
      timeoutMs: 60000,
    }
  );
}

export const analyzeLanes = analyzeVideoLanes;

/**
 * Fetches information about lane analysis algorithms, boundary rules, and calibration policies.
 */
export async function getLaneAnalysisInfo(): Promise<LaneAnalysisInfoResponse> {
  return apiClient<LaneAnalysisInfoResponse>('/api/v1/lane-analysis/info');
}
