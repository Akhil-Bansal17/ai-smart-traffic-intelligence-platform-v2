/**
 * API client methods for YOLO vehicle detection endpoints.
 */
import { apiClient } from './client';
import {
  DetectionRequest,
  ModelInfoResponse,
  VideoDetectionResponse,
} from '@/types/detection';

/**
 * Executes YOLO vehicle detection inference on an ingested video.
 */
export async function detectVideo(
  videoId: string,
  params?: DetectionRequest
): Promise<VideoDetectionResponse> {
  return apiClient<VideoDetectionResponse>(
    `/api/v1/detection/videos/${videoId}`,
    {
      method: 'POST',
      body: JSON.stringify(params || {}),
      timeoutMs: 60000, // 60s timeout for model inference
    }
  );
}

/**
 * Retrieves metadata about the active YOLO model and supported vehicle classes.
 */
export async function getModelInfo(): Promise<ModelInfoResponse> {
  return apiClient<ModelInfoResponse>('/api/v1/detection/info');
}
