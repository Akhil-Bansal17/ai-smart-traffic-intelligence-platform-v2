/**
 * API client functions for Business-Grade Traffic Reporting & Export.
 * Phase 19: Business-Grade Traffic Reporting & Export.
 */
import { apiClient } from '@/api/client';
import { getApiBaseUrl } from '@/config/env';
import {
  CreateReportRequest,
  ReportDetail,
  ReportInfoResponse,
  ReportListResponse,
} from '@/types/report';

/**
 * Returns reporting subsystem capabilities, supported types, and truth labeling guide.
 */
export async function getReportInfo(): Promise<ReportInfoResponse> {
  return apiClient<ReportInfoResponse>('/api/v1/reports/info');
}

/**
 * Requests deterministic generation of a new report (PDF/CSV).
 */
export async function createReport(payload: CreateReportRequest): Promise<ReportDetail> {
  return apiClient<ReportDetail>('/api/v1/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs: 30000,
  });
}

/**
 * Lists generated reports with pagination and optional filtering.
 */
export async function listReports(
  skip = 0,
  limit = 20,
  reportType?: string,
  status?: string
): Promise<ReportListResponse> {
  const params = new URLSearchParams();
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  if (reportType) params.set('report_type', reportType);
  if (status) params.set('status', status);

  return apiClient<ReportListResponse>(`/api/v1/reports?${params.toString()}`);
}

/**
 * Retrieves detailed metadata and normalized assembled data for a single report.
 */
export async function getReportDetail(reportId: string): Promise<ReportDetail> {
  return apiClient<ReportDetail>(`/api/v1/reports/${reportId}`);
}

/**
 * Downloads a generated report artifact (PDF/CSV) as a binary Blob and triggers browser save.
 */
export async function downloadReportFile(reportId: string, customFilename?: string): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/reports/${reportId}/download`;

  const response = await fetch(url);
  if (!response.ok) {
    let errMsg = `Failed to download report (HTTP ${response.status})`;
    try {
      const errData = await response.json();
      if (errData?.error?.message) errMsg = errData.error.message;
    } catch {
      // ignore
    }
    throw new Error(errMsg);
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = customFilename || `traffic_report_${reportId.slice(0, 8)}`;
  if (contentDisposition && contentDisposition.includes('filename=')) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(downloadUrl);
}

/**
 * Deletes a report record and associated file artifact.
 */
export async function deleteReport(reportId: string): Promise<{ message: string }> {
  return apiClient<{ message: string }>(`/api/v1/reports/${reportId}`, {
    method: 'DELETE',
  });
}
