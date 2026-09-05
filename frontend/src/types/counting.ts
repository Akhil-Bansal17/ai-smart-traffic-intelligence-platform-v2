/**
 * Vehicle counting TypeScript definitions.
 */

export interface Point2D {
  x: number;
  y: number;
}

export interface CountingLineConfig {
  p1: Point2D;
  p2: Point2D;
  label: string;
  direction_a_to_b: string;
  direction_b_to_a: string;
  min_movement_px: number;
}

export interface CrossingEvent {
  track_id: number;
  class_name: string;
  frame_index: number;
  timestamp_seconds: number;
  direction: string;
  crossing_point: [number, number];
  line_label: string;
}

export interface FrameCountingResult {
  frame_index: number;
  timestamp_seconds: number;
  active_tracks_count: number;
  new_crossings: CrossingEvent[];
}

export interface VideoCountingResponse {
  video_id: string;
  original_filename: string;
  pipeline_stage: string;
  detector_model: string;
  tracker_name: string;
  counting_line: CountingLineConfig;
  total_frames_processed: number;
  total_detections_count: number;
  total_unique_tracks: number;
  total_counted_vehicles: number;
  counts_by_class: Record<string, number>;
  counts_by_direction: Record<string, number>;
  counted_track_ids: number[];
  crossing_events: CrossingEvent[];
  frames: FrameCountingResult[];
  processing_time_ms: number;
  preview_frame_base64?: string;
}

export interface CountingRequestParams {
  confidence_threshold?: number;
  iou_threshold?: number;
  max_frames?: number;
  target_fps?: number;
  counting_line?: CountingLineConfig;
}

export interface CountingInfoResponse {
  counter_name: string;
  default_line: CountingLineConfig;
  crossing_semantics: string;
  direction_rules: Record<string, string>;
}
