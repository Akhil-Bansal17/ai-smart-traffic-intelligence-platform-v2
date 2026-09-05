/**
 * TypeScript types for Object Tracking API responses and requests.
 * Matches backend schemas in backend/app/schemas/tracking.py.
 */
import { BoundingBox } from './detection';

export interface TrackedItem {
  track_id: number;
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
  frame_index?: number;
  timestamp_seconds?: number;
  state: 'new' | 'active' | 'lost' | 'terminated' | string;
  age_frames: number;
  hits: number;
}

export interface FrameTrackingResult {
  frame_index: number;
  timestamp_seconds: number;
  tracked_objects: TrackedItem[];
  active_tracks_count: number;
}

export interface VideoTrackingResponse {
  video_id: string;
  original_filename: string;
  pipeline_stage: string;
  detector_model: string;
  tracker_name: string;
  confidence_threshold: number;
  target_fps: number;
  total_frames_processed: number;
  total_detections_count: number;
  total_unique_tracks: number;
  tracks_by_class: Record<string, number>;
  frames: FrameTrackingResult[];
  processing_time_ms: number;
  preview_frame_base64?: string;
}

export interface TrackingRequest {
  confidence_threshold?: number;
  max_frames?: number;
  target_fps?: number;
  iou_threshold?: number;
  max_lost_frames?: number;
}

export interface TrackerInfoResponse {
  tracker_name: string;
  iou_threshold: number;
  max_lost_frames: number;
  track_lifecycle: Record<string, string>;
}
