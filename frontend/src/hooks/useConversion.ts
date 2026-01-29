/**
 * React Query hooks for conversion operations
 */

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { api } from '@/lib/api'

// Query keys
export const CONVERSION_QUERY_KEY = ['conversion']

// Types
export type ConversionStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface SnowflakeWarning {
  is_configured: boolean
  warning_message: string | null
  can_proceed: boolean
  placeholder_schema: string
}

export interface ConversionJobCreate {
  conversion_id: string
  status: ConversionStatus
  started_at: string
  snowflake_configured: boolean
  message: string
}

export interface ConversionProgress {
  conversion_id: string
  status: ConversionStatus
  current_step: string | null
  steps_completed: number
  total_steps: number
  progress_percent: number
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
}

export interface ConversionOutputFile {
  filename: string
  file_type: string
  size_bytes: number
  path: string
}

export interface DownloadableFile {
  type: string
  name: string
  size: number
  size_display: string
  download_url: string
  available: boolean
}

export interface ConversionOutputsResponse {
  conversion_id: string
  status: ConversionStatus
  report_name: string
  generated_at: string | null
  files: DownloadableFile[]
  message: string | null
}

export interface ConversionResult {
  conversion_id: string
  status: ConversionStatus
  report_name: string
  report_path: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  snowflake_configured: boolean
  snowflake_schema: string | null
  output_files: ConversionOutputFile[]
}

interface ErrorDetail {
  code: string
  message: string
  details?: Record<string, unknown>
  can_retry?: boolean
}

interface ConversionRequest {
  analysisId: number
  force?: boolean
}

/**
 * Check Snowflake configuration status
 */
export function useSnowflakeStatus(enabled = true) {
  return useQuery<SnowflakeWarning, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, 'snowflake-status'],
    queryFn: async () => {
      const response = await api.get<SnowflakeWarning>(
        '/api/v1/conversions/snowflake-status'
      )
      return response.data
    },
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Get conversion status by ID
 */
export function useConversionStatus(conversionId: string | null, enabled = true) {
  return useQuery<ConversionProgress, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, conversionId],
    queryFn: async () => {
      const response = await api.get<ConversionProgress>(
        `/api/v1/conversions/${conversionId}`
      )
      return response.data
    },
    enabled: enabled && !!conversionId,
    refetchInterval: (query) => {
      // Stop polling when completed or failed
      const data = query.state.data
      if (data && ['completed', 'failed', 'cancelled'].includes(data.status)) {
        return false
      }
      return 1000 // Poll every 1 second while running
    },
    staleTime: 0, // Always fetch fresh status
  })
}

/**
 * Get latest conversion for an analysis
 */
export function useLatestConversion(analysisId: number | null, enabled = true) {
  return useQuery<ConversionProgress | null, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, 'analysis', analysisId, 'latest'],
    queryFn: async () => {
      const response = await api.get<ConversionProgress | null>(
        `/api/v1/conversions/analysis/${analysisId}/latest`
      )
      return response.data
    },
    enabled: enabled && !!analysisId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Get conversion result with output files
 */
export function useConversionResult(conversionId: string | null, enabled = true) {
  return useQuery<ConversionResult, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, conversionId, 'result'],
    queryFn: async () => {
      const response = await api.get<ConversionResult>(
        `/api/v1/conversions/${conversionId}/result`
      )
      return response.data
    },
    enabled: enabled && !!conversionId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to initiate conversion with automatic status polling
 */
export function useInitiateConversion() {
  const queryClient = useQueryClient()
  const [conversionId, setConversionId] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  // Poll status when we have a conversion ID
  const {
    data: conversionStatus,
    error: statusError,
  } = useConversionStatus(conversionId, isPolling)

  // Stop polling when conversion completes
  useEffect(() => {
    if (
      conversionStatus &&
      ['completed', 'failed', 'cancelled'].includes(conversionStatus.status)
    ) {
      setIsPolling(false)
      // Invalidate related caches
      queryClient.invalidateQueries({ queryKey: CONVERSION_QUERY_KEY })
    }
  }, [conversionStatus, queryClient])

  // Mutation to start conversion
  const mutation = useMutation<
    ConversionJobCreate,
    AxiosError<{ detail: ErrorDetail }>,
    ConversionRequest
  >({
    mutationFn: async ({ analysisId, force = false }) => {
      const response = await api.post<ConversionJobCreate>(
        `/api/v1/conversions/analysis/${analysisId}`,
        { force }
      )
      return response.data
    },
    onSuccess: (data) => {
      setConversionId(data.conversion_id)
      setIsPolling(true)
    },
  })

  // Cancel mutation
  const cancelMutation = useMutation<
    { conversion_id: string; status: string; message: string },
    AxiosError<{ detail: ErrorDetail }>,
    void
  >({
    mutationFn: async () => {
      if (!conversionId) throw new Error('No conversion to cancel')
      const response = await api.delete(`/api/v1/conversions/${conversionId}`)
      return response.data
    },
    onSuccess: () => {
      setIsPolling(false)
      queryClient.invalidateQueries({ queryKey: CONVERSION_QUERY_KEY })
    },
  })

  // Reset function
  const reset = useCallback(() => {
    setConversionId(null)
    setIsPolling(false)
    mutation.reset()
    cancelMutation.reset()
  }, [mutation, cancelMutation])

  // Combined state
  const isConverting = mutation.isPending || isPolling
  const progress = conversionStatus?.progress_percent ?? 0
  const currentStep = conversionStatus?.current_step ?? null

  // Determine final status
  let status: 'idle' | 'starting' | ConversionStatus = 'idle'
  if (mutation.isPending) {
    status = 'starting'
  } else if (isPolling && conversionStatus) {
    status = conversionStatus.status
  } else if (mutation.isError || statusError) {
    status = 'failed'
  } else if (conversionStatus?.status === 'completed') {
    status = 'completed'
  }

  // Error handling
  const error = mutation.error || statusError
  const errorMessage = error
    ? (error.response?.data?.detail as ErrorDetail)?.message || error.message
    : null

  return {
    initiate: mutation.mutate,
    initiateAsync: mutation.mutateAsync,
    cancel: cancelMutation.mutate,
    reset,
    isConverting,
    isCancelling: cancelMutation.isPending,
    status,
    progress,
    currentStep,
    conversionId,
    snowflakeConfigured: mutation.data?.snowflake_configured ?? null,
    error: errorMessage,
    conversionResult: conversionStatus,
  }
}

/**
 * Helper to format duration
 */
export function formatDuration(ms: number | null): string {
  if (ms === null) return '-'
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

/**
 * Helper to format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Get list of downloadable files for a conversion
 */
export function useConversionOutputs(conversionId: string | null, enabled = true) {
  return useQuery<ConversionOutputsResponse, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, conversionId, 'outputs'],
    queryFn: async () => {
      const response = await api.get<ConversionOutputsResponse>(
        `/api/v1/conversions/${conversionId}/outputs`
      )
      return response.data
    },
    enabled: enabled && !!conversionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Download a file from conversion outputs
 */
export function useDownloadFile() {
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null)

  const downloadFile = useCallback(
    async (conversionId: string, fileType: string, filename: string) => {
      setIsDownloading(true)
      setDownloadError(null)
      setDownloadProgress(0)

      try {
        const response = await api.get(
          `/api/v1/conversions/${conversionId}/download/${fileType}`,
          {
            responseType: 'blob',
            onDownloadProgress: (progressEvent) => {
              if (progressEvent.total) {
                const percent = Math.round(
                  (progressEvent.loaded * 100) / progressEvent.total
                )
                setDownloadProgress(percent)
              }
            },
          }
        )

        // Create blob URL and trigger download
        const blob = new Blob([response.data], {
          type: response.headers['content-type'] || 'application/octet-stream',
        })
        const downloadUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(downloadUrl)

        setDownloadProgress(100)
      } catch (error) {
        if (error instanceof AxiosError) {
          const errorDetail = error.response?.data?.detail as ErrorDetail | undefined
          setDownloadError(errorDetail?.message || error.message)
        } else {
          setDownloadError('Failed to download file')
        }
      } finally {
        setIsDownloading(false)
        // Clear progress after a short delay
        setTimeout(() => setDownloadProgress(null), 1000)
      }
    },
    []
  )

  const reset = useCallback(() => {
    setIsDownloading(false)
    setDownloadError(null)
    setDownloadProgress(null)
  }, [])

  return {
    downloadFile,
    isDownloading,
    downloadError,
    downloadProgress,
    reset,
  }
}

/**
 * Download file types for UI labels and icons
 */
export const FILE_TYPE_INFO: Record<
  string,
  { label: string; description: string; icon: string }
> = {
  pbix: {
    label: 'Power BI Report',
    description: 'Download the converted Power BI file',
    icon: 'file-text',
  },
  sql: {
    label: 'SQL Scripts',
    description: 'Combined Snowflake SQL scripts',
    icon: 'database',
  },
  'sql-zip': {
    label: 'All Scripts (ZIP)',
    description: 'All SQL scripts bundled in a ZIP file',
    icon: 'archive',
  },
  analysis: {
    label: 'Analysis Report',
    description: 'Conversion analysis and metadata',
    icon: 'file-json',
  },
}

// Summary types
export type SummaryStatus = 'success' | 'partial' | 'failed'

export interface ReportInfo {
  name: string
  path: string
}

export interface DatasetSummary {
  total: number
  converted_to_sql: number
}

export interface VisualSummary {
  total: number
  tables: number
  charts: number
  matrices: number
  textboxes: number
  placeholders: number
}

export interface ExpressionSummary {
  total: number
  auto_converted: number
  manual_required: number
}

export interface StoredProcedureSummary {
  total: number
  auto_rewritten: number
  partial_rewrite: number
  manual_required: number
}

export interface ConvertedSummary {
  datasets: DatasetSummary
  visuals: VisualSummary
  expressions: ExpressionSummary
  stored_procedures: StoredProcedureSummary
}

export interface AttentionItem {
  type: string
  name: string
  reason: string
  visual_type?: string
}

export interface SummaryFile {
  type: string
  name: string
  size: number
  size_display: string
}

export interface ConversionSummaryResponse {
  conversion_id: string
  analysis_id: number
  report: ReportInfo
  conversion_timestamp: string
  duration_ms: number | null
  status: SummaryStatus
  snowflake_configured: boolean
  converted: ConvertedSummary
  attention_required: AttentionItem[]
  files: SummaryFile[]
  todo_count: number
}

/**
 * Get conversion summary data
 */
export function useConversionSummary(conversionId: string | null, enabled = true) {
  return useQuery<ConversionSummaryResponse, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...CONVERSION_QUERY_KEY, conversionId, 'summary'],
    queryFn: async () => {
      const response = await api.get<ConversionSummaryResponse>(
        `/api/v1/conversions/${conversionId}/summary`
      )
      return response.data
    },
    enabled: enabled && !!conversionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Helper to format date for display
 */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

/**
 * Status display configuration
 */
export const SUMMARY_STATUS_CONFIG: Record<
  SummaryStatus,
  { label: string; variant: 'success' | 'warning' | 'destructive'; description: string }
> = {
  success: {
    label: 'Success',
    variant: 'success',
    description: 'All elements converted successfully',
  },
  partial: {
    label: 'Partial Success',
    variant: 'warning',
    description: 'Some items need attention',
  },
  failed: {
    label: 'Failed',
    variant: 'destructive',
    description: 'Conversion failed',
  },
}
