/**
 * Vehicle Counting API Client module.
 */
import { apiClient } from './client';
import {
  CountingInfoResponse,
  CountingRequestParams,
  VideoCountingResponse,
} from '@/types/counting';

/**
 * Runs full detection, tracking, and line-crossing vehicle counting inference on an ingested video.
 */
export async function countVideo(
  videoId: string,
  params?: CountingRequestParams
): Promise<VideoCountingResponse> {
  return apiClient<VideoCountingResponse>(
    `/api/v1/counting/videos/${videoId}`,
    {
      method: 'POST',
      body: JSON.stringify(params || {}),
      timeoutMs: 60000,
    }
  );
}

/**
 * Fetches information about the active counting engine and default virtual tripwire.
 */
export async function getCountingInfo(): Promise<CountingInfoResponse> {
  return apiClient<CountingInfoResponse>('/api/v1/counting/info');
}
