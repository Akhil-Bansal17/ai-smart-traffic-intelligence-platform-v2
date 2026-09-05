import { useState, useEffect, useCallback, useRef } from 'react';
import { getHealth } from '@/api/health';
import { HealthResponse, HealthState, HealthStatusState } from '@/types/health';
import { ApiError } from '@/types/api';

interface UseBackendHealthOptions {
  /**
   * Polling interval in milliseconds. Defaults to 15,000 (15 seconds).
   * Set to 0 to disable automatic polling.
   */
  pollIntervalMs?: number;
  /**
   * If true, runs health check immediately on hook mount. Defaults to true.
   */
  autoCheck?: boolean;
}

export interface UseBackendHealthReturn extends HealthState {
  isChecking: boolean;
  checkHealth: () => Promise<HealthResponse | null>;
}

/**
 * Custom hook to monitor backend connectivity status against GET /api/v1/health.
 * Automatically tracks latency, handles network disconnection gracefully,
 * and allows on-demand status verification.
 */
export function useBackendHealth(options: UseBackendHealthOptions = {}): UseBackendHealthReturn {
  const { pollIntervalMs = 15000, autoCheck = true } = options;

  const [status, setStatus] = useState<HealthStatusState>('checking');
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const checkHealth = useCallback(async (): Promise<HealthResponse | null> => {
    setIsChecking(true);
    const startTime = performance.now();

    try {
      const response = await getHealth();
      const endTime = performance.now();
      const latency = Math.round(endTime - startTime);

      if (isMounted.current) {
        setStatus('online');
        setData(response);
        setError(null);
        setLatencyMs(latency);
        setLastChecked(new Date());
      }
      return response;
    } catch (err: unknown) {
      const endTime = performance.now();
      const latency = Math.round(endTime - startTime);
      const apiError = err instanceof ApiError
        ? err
        : new ApiError('Unexpected error checking backend health', 500);

      if (isMounted.current) {
        setStatus('offline');
        setData(null);
        setError(apiError);
        setLatencyMs(latency);
        setLastChecked(new Date());
      }
      return null;
    } finally {
      if (isMounted.current) {
        setIsChecking(false);
      }
    }
  }, []);

  useEffect(() => {
    if (autoCheck) {
      checkHealth();
    }

    if (pollIntervalMs > 0) {
      const intervalId = setInterval(() => {
        checkHealth();
      }, pollIntervalMs);

      return () => clearInterval(intervalId);
    }
  }, [autoCheck, pollIntervalMs, checkHealth]);

  return {
    status,
    data,
    error,
    latencyMs,
    lastChecked,
    isChecking,
    checkHealth,
  };
}
