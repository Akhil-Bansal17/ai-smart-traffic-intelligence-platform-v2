/**
 * Health check schema types matching backend/app/schemas/health.py
 */

export interface HealthResponse {
  status: string;
  environment: string;
  version: string;
}

export interface RootHealthResponse {
  status: string;
  service: string;
}

export type HealthStatusState = 'online' | 'offline' | 'checking';

export interface HealthState {
  status: HealthStatusState;
  data: HealthResponse | null;
  error: ApiError | null;
  latencyMs: number | null;
  lastChecked: Date | null;
}

import { ApiError } from './api';
