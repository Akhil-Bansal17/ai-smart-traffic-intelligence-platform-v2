/**
 * Analysis Persistence & History API Client module.
 * Communicates with backend /api/v1/analysis endpoints.
 */
import { apiClient } from './client';
import {
  AnalysisInfoResponse,
  AnalysisSessionDetail,
  AnalysisSessionListResponse,
} from '@/types/analysis';

/**
 * Fetches paginated analysis sessions from database.
 */
export async function getAnalysisSessions(
  page: number = 1,
  pageSize: number = 50,
  videoId?: string
): Promise<AnalysisSessionListResponse> {
  const params = new URLSearchParams();
  params.set('page', page.toString());
  params.set('page_size', pageSize.toString());
  if (videoId) {
    params.set('video_id', videoId);
  }
  return apiClient<AnalysisSessionListResponse>(`/api/v1/analysis/sessions?${params.toString()}`);
}

/**
 * Fetches analysis sessions for a specific video.
 */
export async function getVideoAnalysisSessions(
  videoId: string
): Promise<AnalysisSessionListResponse> {
  return apiClient<AnalysisSessionListResponse>(`/api/v1/analysis/videos/${videoId}/sessions`);
}

/**
 * Fetches detailed analysis session by ID with all metrics, lane density, and crossing events.
 */
export async function getAnalysisSessionDetail(
  sessionId: string
): Promise<AnalysisSessionDetail> {
  return apiClient<AnalysisSessionDetail>(`/api/v1/analysis/sessions/${sessionId}`);
}

/**
 * Deletes an analysis session and cascades to all child records.
 */
export async function deleteAnalysisSession(
  sessionId: string
): Promise<{ message: string; session_id: string; deleted: boolean }> {
  return apiClient<{ message: string; session_id: string; deleted: boolean }>(
    `/api/v1/analysis/sessions/${sessionId}`,
    {
      method: 'DELETE',
    }
  );
}

/**
 * Fetches metadata and schema rules for analysis persistence.
 */
export async function getAnalysisInfo(): Promise<AnalysisInfoResponse> {
  return apiClient<AnalysisInfoResponse>('/api/v1/analysis/info');
}
