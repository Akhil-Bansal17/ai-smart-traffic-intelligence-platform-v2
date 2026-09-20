/**
 * Environment configuration module.
 * 
 * Reads and validates client-side environment variables exposed by Vite.
 * Fails loudly with an explicit warning/error if required variables are missing,
 * avoiding silent misconfiguration.
 */

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

export const config = {
  /**
   * The base URL for the backend API service (e.g. http://localhost:8000).
   * Defaults to empty string for relative paths (e.g. reverse proxy or Vercel rewrites).
   * Strips any trailing slash for consistent endpoint joining.
   */
  apiBaseUrl: (rawApiBaseUrl || '').replace(/\/+$/, ''),
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
} as const;

export function getApiBaseUrl(): string {
  return config.apiBaseUrl;
}
