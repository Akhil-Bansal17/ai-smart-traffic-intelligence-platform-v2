export interface VideoMetadata {
  id: string;
  original_filename: string;
  duration_seconds: number;
  fps: number;
  resolution: string;
  frame_count: number;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  source_type?: 'real_world' | 'synthetic_test';
  uploaded_at: string;
}

export interface VideoUploadResponse extends VideoMetadata {}

export interface VideoListResponse {
  total: number;
  videos: VideoMetadata[];
}
