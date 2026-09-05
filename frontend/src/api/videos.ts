import { apiClient } from './client';
import { VideoListResponse, VideoMetadata, VideoUploadResponse } from '@/types/video';

/**
 * Upload a traffic camera video file to the backend pipeline.
 * Server validates extension, container magic bytes, size limits, and content readability.
 */
export async function uploadVideo(file: File): Promise<VideoUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient<VideoUploadResponse>('/api/v1/videos/upload', {
    method: 'POST',
    body: formData,
    timeoutMs: 60000, // 60 second timeout for video upload
  });
}

/**
 * Retrieve metadata and status for a previously uploaded video.
 */
export async function getVideo(id: string): Promise<VideoMetadata> {
  return apiClient<VideoMetadata>(`/api/v1/videos/${id}`);
}

/**
 * List all ingested videos.
 */
export async function listVideos(): Promise<VideoListResponse> {
  return apiClient<VideoListResponse>('/api/v1/videos');
}
