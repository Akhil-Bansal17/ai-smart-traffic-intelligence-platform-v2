import { apiClient } from './client';
import {
  NetworkDirectionalResponse,
  NetworkFilterParams,
  NetworkHotspotResponse,
  NetworkLaneResponse,
  NetworkOverviewResponse,
  NetworkSourceComparisonResponse,
  NetworkTemporalAnalysisResponse,
  NetworkVehicleCompositionResponse,
  PeriodComparisonResponse,
} from '@/types/networkIntelligence';

function buildQueryString(params: NetworkFilterParams = {}, extra?: Record<string, string | number | boolean | undefined>): string {
  const query = new URLSearchParams();
  if (params.time_preset) query.set('time_preset', params.time_preset);
  if (params.start_time) query.set('start_time', params.start_time);
  if (params.end_time) query.set('end_time', params.end_time);
  if (params.source_ids && params.source_ids.length > 0) {
    params.source_ids.forEach((id) => query.append('source_ids', id));
  }
  if (params.include_synthetic !== undefined) {
    query.set('include_synthetic', String(params.include_synthetic));
  }
  if (params.bucket_interval) {
    query.set('bucket_interval', params.bucket_interval);
  }
  if (extra) {
    Object.entries(extra).forEach(([k, v]) => {
      if (v !== undefined) query.set(k, String(v));
    });
  }
  const qs = query.toString();
  return qs ? `?${qs}` : '';
}

export async function getNetworkOverview(params: NetworkFilterParams = {}): Promise<NetworkOverviewResponse> {
  return apiClient<NetworkOverviewResponse>(`/api/v1/network-intelligence/overview${buildQueryString(params)}`);
}

export async function compareTrafficSources(params: NetworkFilterParams = {}): Promise<NetworkSourceComparisonResponse> {
  return apiClient<NetworkSourceComparisonResponse>(`/api/v1/network-intelligence/compare${buildQueryString(params)}`);
}

export async function getTrafficHotspots(params: NetworkFilterParams = {}, limit: number = 10): Promise<NetworkHotspotResponse> {
  return apiClient<NetworkHotspotResponse>(`/api/v1/network-intelligence/hotspots${buildQueryString(params, { limit })}`);
}

export async function getNetworkVehicleComposition(params: NetworkFilterParams = {}): Promise<NetworkVehicleCompositionResponse> {
  return apiClient<NetworkVehicleCompositionResponse>(`/api/v1/network-intelligence/vehicle-composition${buildQueryString(params)}`);
}

export async function getNetworkDirectionalAnalysis(params: NetworkFilterParams = {}): Promise<NetworkDirectionalResponse> {
  return apiClient<NetworkDirectionalResponse>(`/api/v1/network-intelligence/directional-analysis${buildQueryString(params)}`);
}

export async function getNetworkLaneAnalysis(params: NetworkFilterParams = {}): Promise<NetworkLaneResponse> {
  return apiClient<NetworkLaneResponse>(`/api/v1/network-intelligence/lane-analysis${buildQueryString(params)}`);
}

export async function getNetworkTemporalAnalysis(params: NetworkFilterParams = {}): Promise<NetworkTemporalAnalysisResponse> {
  return apiClient<NetworkTemporalAnalysisResponse>(`/api/v1/network-intelligence/temporal-analysis${buildQueryString(params)}`);
}

export async function getNetworkHistoricalComparison(params: NetworkFilterParams = {}): Promise<PeriodComparisonResponse> {
  return apiClient<PeriodComparisonResponse>(`/api/v1/network-intelligence/historical-comparison${buildQueryString(params)}`);
}
