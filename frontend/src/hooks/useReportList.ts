/**
 * React Query hooks for SSRS report listing
 */

import { useQuery } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { api } from '@/lib/api'

// Query key for caching
export const REPORTS_QUERY_KEY = ['ssrs', 'reports']

// Report item from API
export interface ReportItem {
  id: string
  name: string
  path: string
  description: string | null
  modified_date: string | null
  size_bytes: number
  created_by: string | null
}

// Response metadata
interface ReportsMeta {
  timestamp: string
  total_count: number
  folder_path: string
}

// Full response
export interface ReportsResponse {
  data: ReportItem[]
  meta: ReportsMeta
}

// Error detail structure
interface ReportsError {
  code: string
  message: string
  suggestions?: string[]
}

/**
 * Hook to fetch reports in a specific folder
 * @param folderPath - The SSRS folder path to list reports from
 * @param enabled - Whether to enable the query (default: true)
 */
export function useReportList(folderPath: string, enabled: boolean = true) {
  return useQuery<ReportsResponse, AxiosError<{ detail: ReportsError }>>({
    queryKey: [...REPORTS_QUERY_KEY, folderPath],
    queryFn: async () => {
      const response = await api.get<ReportsResponse>('/api/v1/ssrs/reports', {
        params: { path: folderPath },
      })
      return response.data
    },
    enabled: enabled && !!folderPath,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  })
}

/**
 * Check if error indicates folder not found
 */
export function isFolderNotFound(error: unknown): boolean {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    return detail?.code === 'NOT_FOUND'
  }
  return false
}

/**
 * Check if error indicates permission denied
 */
export function isPermissionDenied(error: unknown): boolean {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    return detail?.code === 'PERMISSION_DENIED'
  }
  return false
}

/**
 * Get error message from API error
 */
export function getReportsErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (detail?.message) {
      return detail.message
    }
    if (error.response?.status === 401) {
      return 'Authentication failed. Please try logging in again.'
    }
    if (error.response?.status === 403) {
      return 'You do not have permission to view this folder.'
    }
    if (error.response?.status === 404) {
      return 'The requested folder was not found.'
    }
  }
  return 'Unable to load reports. Please try again.'
}
