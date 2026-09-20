/**
 * Camera source and live monitoring type definitions.
 * Phase 21: Live Traffic Monitoring & Camera Source Management.
 */

export type CameraSourceType =
  | 'local_camera'
  | 'rtsp'
  | 'http_stream'
  | 'test_fixture'
  | 'file';

export type CameraSourceStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'
  | 'stopped';

export interface CameraSource {
  id: string;
  name: string;
  description?: string | null;
  source_type: CameraSourceType;
  connection_uri: string;
  status: CameraSourceStatus;
  enabled: boolean;
  location_name?: string | null;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  last_connected_at?: string | null;
  last_frame_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CameraSourceListResponse {
  total: number;
  items: CameraSource[];
}

export interface CameraSourceCreatePayload {
  name: string;
  description?: string;
  source_type: CameraSourceType;
  connection_uri: string;
  enabled?: boolean;
  location_name?: string;
}

export interface CameraSourceUpdatePayload {
  name?: string;
  description?: string;
  source_type?: CameraSourceType;
  connection_uri?: string;
  enabled?: boolean;
  location_name?: string;
}

export interface CameraSourceTestResponse {
  success: boolean;
  message: string;
  source_type: string;
  connection_uri: string;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  error?: string | null;
}

export interface LiveMonitoringStatus {
  camera_source_id: string;
  camera_name: string;
  status: string;
  active_job_id?: string | null;
  is_live: boolean;
  source_type: string;
  source_fps: number;
  processing_fps: number;
  frames_acquired: number;
  frames_processed: number;
  dropped_frames: number;
  reconnect_count: number;
  total_volume: number;
  inbound_volume: number;
  outbound_volume: number;
  active_tracks_count: number;
  class_distribution: Record<string, number>;
  direction_distribution: Record<string, number>;
  lane_occupancies: Record<string, number>;
  lane_densities: Record<string, number>;
  provenance_tag: string;
  last_frame_timestamp?: number | null;
  last_updated?: string | null;
  error_message?: string | null;
}
