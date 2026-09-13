/**
 * Analysis Persistence & History API Client module.
 * Communicates with backend /api/v1/analysis endpoints.
 */
import { apiClient } from './client';
import {
  AnalysisInfoResponse,
  AnalysisJob,
  AnalysisJobCancelResponse,
  AnalysisJobCreateRequest,
  AnalysisJobListResponse,
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
  const limit = pageSize;
  const offset = (page - 1) * pageSize;
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());
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

// =========================================================================
// Phase 17: Analysis Job Orchestration API Functions
// =========================================================================

/**
 * Submits an asynchronous video analysis background job.
 */
export async function createAnalysisJob(
  request: AnalysisJobCreateRequest
): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>('/api/v1/analysis/jobs', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Retrieves the status and progress of an analysis job.
 */
export async function getAnalysisJob(
  jobId: string
): Promise<AnalysisJob> {
  return apiClient<AnalysisJob>(`/api/v1/analysis/jobs/${jobId}`);
}

/**
 * Lists historical and active analysis jobs with pagination and filtering.
 */
export async function listAnalysisJobs(
  limit: number = 50,
  offset: number = 0,
  status?: string,
  videoId?: string
): Promise<AnalysisJobListResponse> {
  const params = new URLSearchParams();
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());
  if (status && status !== 'all') {
    params.set('status', status);
  }
  if (videoId) {
    params.set('video_id', videoId);
  }
  return apiClient<AnalysisJobListResponse>(`/api/v1/analysis/jobs?${params.toString()}`);
}

/**
 * Requests cooperative cancellation of an active analysis job.
 */
export async function cancelAnalysisJob(
  jobId: string
): Promise<AnalysisJobCancelResponse> {
  return apiClient<AnalysisJobCancelResponse>(`/api/v1/analysis/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
}
