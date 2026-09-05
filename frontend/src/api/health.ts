import { apiClient } from './client';
import { HealthResponse, RootHealthResponse } from '@/types/health';

/**
 * Fetches the versioned application health check: GET /api/v1/health
 * Returns { status: "ok", environment: "development", version: "0.1.0" }
 */
export async function getHealth(): Promise<HealthResponse> {
  return apiClient<HealthResponse>('/api/v1/health', { timeoutMs: 5000 });
}

/**
 * Fetches the root infrastructure liveness check: GET /health
 * Returns { status: "ok", service: "traffic-platform-api" }
 */
export async function getRootHealth(): Promise<RootHealthResponse> {
  return apiClient<RootHealthResponse>('/health', { timeoutMs: 5000 });
}
