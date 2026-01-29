/**
 * React Query hooks for audit log operations
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { api } from '@/lib/api'
import type {
  AuditLogFilter,
  AuditLogPagination,
  AuditLogListResponse,
  AuditLogUsersResponse,
  EventType,
} from '@/types/audit'

// Query keys
export const AUDIT_QUERY_KEY = ['audit']
export const AUDIT_LOGS_KEY = [...AUDIT_QUERY_KEY, 'logs']
export const AUDIT_USERS_KEY = [...AUDIT_QUERY_KEY, 'users']

interface ErrorDetail {
  code: string
  message: string
}

/**
 * Hook to fetch audit logs with filtering and pagination
 */
export function useAuditLogs(
  filters: AuditLogFilter,
  pagination: AuditLogPagination,
  liveMode: boolean = false
) {
  return useQuery<AuditLogListResponse, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...AUDIT_LOGS_KEY, filters, pagination],
    queryFn: async () => {
      const params = new URLSearchParams()

      // Add filter params
      if (filters.dateFrom) params.append('from', filters.dateFrom)
      if (filters.dateTo) params.append('to', filters.dateTo)
      if (filters.eventTypes?.length) {
        filters.eventTypes.forEach((type) => params.append('event_type', type))
      }
      if (filters.userId) params.append('user_id', filters.userId)
      if (filters.username) params.append('username', filters.username)
      if (filters.status) params.append('status', filters.status)
      if (filters.searchText) params.append('search', filters.searchText)

      // Add pagination params
      params.append('page', String(pagination.page))
      params.append('page_size', String(pagination.pageSize))

      const response = await api.get<AuditLogListResponse>(
        `/api/v1/audit/logs?${params.toString()}`
      )
      return response.data
    },
    refetchInterval: liveMode ? 5000 : false,
    staleTime: liveMode ? 0 : 30000, // 30 seconds when not in live mode
  })
}

/**
 * Hook to fetch distinct users from audit logs for filtering
 */
export function useAuditLogUsers() {
  return useQuery<AuditLogUsersResponse, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: AUDIT_USERS_KEY,
    queryFn: async () => {
      const response = await api.get<AuditLogUsersResponse>('/api/v1/audit/users')
      return response.data
    },
    staleTime: 60000, // Cache for 1 minute
  })
}

/**
 * Get error message from audit log error
 */
export function getAuditErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail as ErrorDetail | undefined
    if (detail?.message) {
      return detail.message
    }
    if (error.response?.status === 401) {
      return 'You are not authorized to view audit logs.'
    }
    if (error.response?.status === 403) {
      return 'You do not have permission to view audit logs.'
    }
  }
  return 'Unable to load audit logs. Please try again.'
}

// Export types
export type ExportFormat = 'csv' | 'json' | 'pdf'

export interface ExportRequest {
  dateFrom: string
  dateTo: string
  eventTypes?: EventType[]
  format: ExportFormat
}

interface ExportEstimateResponse {
  data: {
    estimated_rows: number
    estimated_csv_size_bytes: number
    estimated_json_size_bytes: number
    requires_async: boolean
  }
}

/**
 * Hook to get export size estimate
 */
export function useAuditExportEstimate(
  dateFrom: string,
  dateTo: string,
  eventType?: EventType
) {
  return useQuery<ExportEstimateResponse, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: ['audit', 'export', 'estimate', dateFrom, dateTo, eventType],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('date_from', dateFrom)
      params.append('date_to', dateTo)
      if (eventType) {
        params.append('event_type', eventType)
      }
      const response = await api.get<ExportEstimateResponse>(
        `/api/v1/audit/export/estimate?${params.toString()}`
      )
      return response.data
    },
    staleTime: 30000, // 30 seconds
  })
}

/**
 * Hook to export audit logs
 */
export function useAuditExport() {
  return useMutation<Blob, AxiosError<{ detail: ErrorDetail }>, ExportRequest>({
    mutationFn: async (request) => {
      const response = await api.post(
        '/api/v1/audit/export',
        {
          date_from: request.dateFrom,
          date_to: request.dateTo,
          event_types: request.eventTypes,
          format: request.format,
        },
        {
          responseType: 'blob',
        }
      )

      // Extract filename from Content-Disposition header
      const contentDisposition = response.headers['content-disposition']
      let filename = `audit_logs.${request.format}`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }

      // Trigger download
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      return response.data
    },
  })
}
