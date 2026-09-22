/**
 * API client functions for Historical Traffic Intelligence & Trend Analysis.
 * Phase 22: Historical Traffic Intelligence & Trend Analysis.
 */
import { apiClient } from '@/api/client';
import {
  AnomalyHistoryResponse,
  DirectionalTrendResponse,
  HistoricalFilterParams,
  HistoricalSummaryResponse,
  HistoricalTimeSeriesResponse,
  LaneIntelligenceResponse,
  PeakPeriodsResponse,
  PeriodComparisonResponse,
  SourceComparisonResponse,
  VehicleCompositionTrendResponse,
} from '@/types/historicalAnalytics';

function buildQueryString(params?: HistoricalFilterParams): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();

  if (params.time_preset) searchParams.set('time_preset', params.time_preset);
  if (params.start_time) searchParams.set('start_time', params.start_time);
  if (params.end_time) searchParams.set('end_time', params.end_time);
  if (params.camera_source_id) searchParams.set('camera_source_id', params.camera_source_id);
  if (params.session_mode) searchParams.set('session_mode', params.session_mode);
  if (params.include_synthetic !== undefined) {
    searchParams.set('include_synthetic', String(params.include_synthetic));
  }
  if (params.bucket_interval) searchParams.set('bucket_interval', params.bucket_interval);

  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

/**
 * Fetches high-level historical traffic summary.
 */
export async function getHistoricalSummary(
  params?: HistoricalFilterParams
): Promise<HistoricalSummaryResponse> {
  const qs = buildQueryString(params);
  return apiClient<HistoricalSummaryResponse>(`/api/v1/historical-analytics/summary${qs}`);
}

/**
 * Fetches discrete non-interpolated time-series buckets.
 */
export async function getHistoricalTimeSeries(
  params?: HistoricalFilterParams
): Promise<HistoricalTimeSeriesResponse> {
  const qs = buildQueryString(params);
  return apiClient<HistoricalTimeSeriesResponse>(`/api/v1/historical-analytics/timeseries${qs}`);
}

/**
 * Fetches vehicle classification breakdown and trends over time.
 */
export async function getVehicleCompositionTrends(
  params?: HistoricalFilterParams
): Promise<VehicleCompositionTrendResponse> {
  const qs = buildQueryString(params);
  return apiClient<VehicleCompositionTrendResponse>(
    `/api/v1/historical-analytics/vehicle-composition${qs}`
  );
}

/**
 * Fetches directional traffic split and flow trends.
 */
export async function getDirectionalTrends(
  params?: HistoricalFilterParams
): Promise<DirectionalTrendResponse> {
  const qs = buildQueryString(params);
  return apiClient<DirectionalTrendResponse>(`/api/v1/historical-analytics/directions${qs}`);
}

/**
 * Fetches lane-level utilization, occupancy, and image-space density history.
 */
export async function getLaneIntelligence(
  params?: HistoricalFilterParams
): Promise<LaneIntelligenceResponse> {
  const qs = buildQueryString(params);
  return apiClient<LaneIntelligenceResponse>(`/api/v1/historical-analytics/lanes${qs}`);
}

/**
 * Fetches deterministic observed peak traffic periods.
 */
export async function getObservedPeakPeriods(
  params?: HistoricalFilterParams
): Promise<PeakPeriodsResponse> {
  const qs = buildQueryString(params);
  return apiClient<PeakPeriodsResponse>(`/api/v1/historical-analytics/peaks${qs}`);
}

/**
 * Fetches operational traffic anomaly and incident statistics.
 */
export async function getAnomalyHistory(
  params?: HistoricalFilterParams
): Promise<AnomalyHistoryResponse> {
  const qs = buildQueryString(params);
  return apiClient<AnomalyHistoryResponse>(`/api/v1/historical-analytics/anomalies${qs}`);
}

/**
 * Fetches comparative metrics grouped by camera or video source.
 */
export async function getSourceComparison(
  params?: HistoricalFilterParams
): Promise<SourceComparisonResponse> {
  const qs = buildQueryString(params);
  return apiClient<SourceComparisonResponse>(`/api/v1/historical-analytics/sources${qs}`);
}

/**
 * Fetches period-over-period delta comparisons.
 */
export async function getPeriodComparison(
  params?: HistoricalFilterParams
): Promise<PeriodComparisonResponse> {
  const qs = buildQueryString(params);
  return apiClient<PeriodComparisonResponse>(`/api/v1/historical-analytics/compare${qs}`);
}
