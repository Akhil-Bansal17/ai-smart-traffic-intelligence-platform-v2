/**
 * TypeScript types for YOLO vehicle detection responses and requests.
 * Matches backend schemas in backend/app/schemas/detection.py.
 */

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
}

export interface DetectionItem {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: BoundingBox;
  frame_index?: number;
  timestamp_seconds?: number;
}

export interface FrameDetectionResult {
  frame_index: number;
  timestamp_seconds: number;
  detections: DetectionItem[];
  vehicle_count: number;
}

export interface VideoDetectionResponse {
  video_id: string;
  original_filename: string;
  pipeline_stage: string;
  model_name: string;
  confidence_threshold: number;
  target_fps: number;
  total_frames_processed: number;
  total_detections_count: number;
  detections_by_class: Record<string, number>;
  frames: FrameDetectionResult[];
  processing_time_ms: number;
  preview_frame_base64?: string;
}

export interface DetectionRequest {
  confidence_threshold?: number;
  max_frames?: number;
  target_fps?: number;
  target_classes?: string[];
}

export interface ModelInfoResponse {
  model_name: string;
  device: string;
  confidence_threshold: number;
  target_classes: string[];
  supported_classes: Record<string, string>;
}
