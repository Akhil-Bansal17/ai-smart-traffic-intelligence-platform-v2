/**
 * API client methods for Object Tracking endpoints.
 */
import { apiClient } from './client';
import {
  TrackerInfoResponse,
  TrackingRequest,
  VideoTrackingResponse,
} from '@/types/tracking';

/**
 * Executes YOLO detection and multi-object tracking on an ingested video.
 */
export async function trackVideo(
  videoId: string,
  params?: TrackingRequest
): Promise<VideoTrackingResponse> {
  return apiClient<VideoTrackingResponse>(
    `/api/v1/tracking/videos/${videoId}`,
    {
      method: 'POST',
      body: JSON.stringify(params || {}),
      timeoutMs: 60000, // 60s timeout for tracking inference
    }
  );
}

/**
 * Retrieves metadata about the active tracking algorithm and state machine parameters.
 */
export async function getTrackerInfo(): Promise<TrackerInfoResponse> {
  return apiClient<TrackerInfoResponse>('/api/v1/tracking/info');
}
