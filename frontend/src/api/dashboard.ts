/**
 * API client functions for Phase 14: System-Wide Traffic Intelligence Dashboard.
 * Strictly read-only operations: never triggers inference, training, or simulations.
 */
import { apiClient } from './client';
import { DashboardInfoResponse, DashboardSummaryResponse } from '@/types/dashboard';

export async function getDashboardInfo(): Promise<DashboardInfoResponse> {
  return apiClient<DashboardInfoResponse>('/api/v1/dashboard/info');
}

export async function getDashboardSummary(sessionId?: string): Promise<DashboardSummaryResponse> {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  return apiClient<DashboardSummaryResponse>(`/api/v1/dashboard/summary${query}`);
}
