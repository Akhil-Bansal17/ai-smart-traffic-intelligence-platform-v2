import { getApiBaseUrl } from '@/config/env';
import { ApiError, BackendErrorResponse } from '@/types/api';

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

/**
 * Centralized API client wrapper.
 * All HTTP requests must go through this helper to guarantee consistent base URL usage,
 * timeout handling, and backend error schema extraction.
 */
export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${normalizedEndpoint}`;

  const { timeoutMs = 10000, headers, ...restOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const defaultHeaders: Record<string, string> = {
    'Accept': 'application/json',
  };

  // Only add Content-Type: application/json if body is not FormData
  if (!(restOptions.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: {
        ...defaultHeaders,
        ...headers,
      },
      signal: controller.signal,
    });

    // Parse JSON response body if present
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      // Check if response matches standard backend error schema: {"error": {"code": "...", "message": "..."}}
      const errorPayload = (data as BackendErrorResponse)?.error;
      const code = errorPayload?.code || (response.status === 404 ? 'not_found' : 'http_error');
      const message = errorPayload?.message || `HTTP error ${response.status}: ${response.statusText}`;

      throw new ApiError(message, response.status, code, errorPayload);
    }

    return data as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }

    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(
        `Request to ${normalizedEndpoint} timed out after ${timeoutMs}ms`,
        408,
        'timeout_error'
      );
    }

    // Network error (e.g. backend server is down, CORS failure, DNS failure)
    const originalMessage = err instanceof Error ? err.message : 'Network error';
    throw new ApiError(
      `Failed to connect to backend at ${baseUrl}. (${originalMessage})`,
      0,
      'network_error'
    );
  } finally {
    clearTimeout(timeoutId);
  }
}
