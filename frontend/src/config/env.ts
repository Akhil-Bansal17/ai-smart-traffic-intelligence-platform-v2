/**
 * Environment configuration module.
 * 
 * Reads and validates client-side environment variables exposed by Vite.
 * Fails loudly with an explicit warning/error if required variables are missing,
 * avoiding silent misconfiguration.
 */

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!rawApiBaseUrl) {
  const errorMsg = 
    '[CONFIG ERROR] VITE_API_BASE_URL is not set in the environment!\n' +
    'Please configure VITE_API_BASE_URL in your .env file (e.g., VITE_API_BASE_URL=http://localhost:8000).';
  console.error(`%c${errorMsg}`, 'background: #7f1d1d; color: #fecaca; font-weight: bold; padding: 4px;');
}

export const config = {
  /**
   * The base URL for the backend API service (e.g. http://localhost:8000).
   * Strips any trailing slash for consistent endpoint joining.
   */
  apiBaseUrl: (rawApiBaseUrl || '').replace(/\/+$/, ''),
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
} as const;

export function getApiBaseUrl(): string {
  if (!config.apiBaseUrl) {
    throw new Error(
      'Missing required environment variable: VITE_API_BASE_URL. Ensure .env is present and configured.'
    );
  }
  return config.apiBaseUrl;
}
