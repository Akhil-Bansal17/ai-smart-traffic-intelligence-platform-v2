/**
 * API response and error types matching the FastAPI backend schema.
 */

export interface BackendErrorPayload {
  code: string;
  message: string;
}

export interface BackendErrorResponse {
  error: BackendErrorPayload;
}

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly rawError?: BackendErrorPayload;

  constructor(message: string, status: number, code: string = 'api_error', rawError?: BackendErrorPayload) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.rawError = rawError;
  }
}
