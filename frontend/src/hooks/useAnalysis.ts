/**
 * React Query hooks for report analysis operations
 */

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { api } from '@/lib/api'

// Query keys
export const ANALYSIS_QUERY_KEY = ['analysis']
export const TASK_QUERY_KEY = ['analysis', 'task']

// Types
export interface PreviousAnalysis {
  id: number
  analyzed_at: string
  score: number | null
  status: string | null
  classification: string | null
}

export interface AnalyzeResponse {
  task_id: string
  status: string
  message: string
  previous_analysis: PreviousAnalysis | null
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  current_step: string | null
  error_message: string | null
  analysis_id: number | null
}

export interface AnalysisDetail {
  id: number
  report_path: string
  report_name: string
  analyzed_at: string
  classification: string | null
  score: number | null
  status: string | null
  features: Record<string, unknown> | null
  penalties: Record<string, unknown> | null
  todo_items: Array<{
    category: string
    priority: string
    title: string
    description: string
    estimated_effort: string
  }> | null
  analysis_duration_ms: number | null
}

interface AnalyzeRequest {
  report_path: string
  report_name: string
  force?: boolean
}

interface ErrorDetail {
  code: string
  message: string
  suggestions?: string[]
}

/**
 * Hook to get the latest analysis for a report
 */
export function useReportAnalysis(reportPath: string | null, enabled = true) {
  return useQuery<AnalysisDetail, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...ANALYSIS_QUERY_KEY, 'report', reportPath],
    queryFn: async () => {
      const response = await api.get<AnalysisDetail>('/api/v1/analysis/report', {
        params: { path: reportPath },
      })
      return response.data
    },
    enabled: enabled && !!reportPath,
    retry: false, // Don't retry 404s
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to get analysis by ID
 */
export function useAnalysisById(analysisId: number | null, enabled = true) {
  return useQuery<AnalysisDetail, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...ANALYSIS_QUERY_KEY, analysisId],
    queryFn: async () => {
      const response = await api.get<AnalysisDetail>(`/api/v1/analysis/${analysisId}`)
      return response.data
    },
    enabled: enabled && !!analysisId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Hook to poll task status
 */
export function useTaskStatus(taskId: string | null, enabled = true) {
  return useQuery<TaskStatus, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...TASK_QUERY_KEY, taskId],
    queryFn: async () => {
      const response = await api.get<TaskStatus>(`/api/v1/analysis/tasks/${taskId}`)
      return response.data
    },
    enabled: enabled && !!taskId,
    refetchInterval: (query) => {
      // Stop polling when completed or failed
      const data = query.state.data
      if (data && ['completed', 'failed', 'cancelled'].includes(data.status)) {
        return false
      }
      return 500 // Poll every 500ms while running
    },
    staleTime: 0, // Always fetch fresh status
  })
}

/**
 * Hook to initiate report analysis with automatic status polling
 */
export function useAnalyzeReport() {
  const queryClient = useQueryClient()
  const [taskId, setTaskId] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  // Task status query - enabled when we have a task ID
  const {
    data: taskStatus,
    error: taskError,
  } = useTaskStatus(taskId, isPolling)

  // Stop polling when task completes
  useEffect(() => {
    if (taskStatus && ['completed', 'failed', 'cancelled'].includes(taskStatus.status)) {
      setIsPolling(false)

      // Invalidate the analysis cache when completed
      if (taskStatus.status === 'completed') {
        queryClient.invalidateQueries({ queryKey: ANALYSIS_QUERY_KEY })
      }
    }
  }, [taskStatus, queryClient])

  // Mutation to start analysis
  const mutation = useMutation<AnalyzeResponse, AxiosError<{ detail: ErrorDetail }>, AnalyzeRequest>({
    mutationFn: async (request) => {
      const response = await api.post<AnalyzeResponse>('/api/v1/analysis/analyze', request)
      return response.data
    },
    onSuccess: (data) => {
      if (data.task_id && data.status !== 'cached') {
        setTaskId(data.task_id)
        setIsPolling(true)
      }
    },
  })

  // Reset function
  const reset = useCallback(() => {
    setTaskId(null)
    setIsPolling(false)
    mutation.reset()
  }, [mutation])

  // Combined state
  const isAnalyzing = mutation.isPending || isPolling
  const progress = taskStatus?.progress ?? 0
  const currentStep = taskStatus?.current_step ?? null
  const analysisId = taskStatus?.analysis_id ?? null

  // Determine final status
  let status: 'idle' | 'starting' | 'running' | 'completed' | 'failed' | 'cached' = 'idle'
  if (mutation.isPending) {
    status = 'starting'
  } else if (isPolling && taskStatus) {
    status = taskStatus.status as typeof status
  } else if (mutation.data?.status === 'cached') {
    status = 'cached'
  } else if (mutation.isError || taskError) {
    status = 'failed'
  } else if (taskStatus?.status === 'completed') {
    status = 'completed'
  }

  // Error handling
  const error = mutation.error || taskError
  const errorMessage = error
    ? (error.response?.data?.detail as ErrorDetail)?.message || error.message
    : taskStatus?.error_message || null

  return {
    analyze: mutation.mutate,
    analyzeAsync: mutation.mutateAsync,
    reset,
    isAnalyzing,
    status,
    progress,
    currentStep,
    analysisId,
    previousAnalysis: mutation.data?.previous_analysis ?? null,
    error: errorMessage,
    taskId,
  }
}

/**
 * Check if a report has been analyzed
 */
export function hasAnalysis(error: unknown): boolean {
  if (error instanceof AxiosError) {
    return error.response?.status !== 404
  }
  return false
}

/**
 * Get error message from analysis error
 */
export function getAnalysisErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail as ErrorDetail | undefined
    if (detail?.message) {
      return detail.message
    }
    if (error.response?.status === 404) {
      return 'This report has not been analyzed yet.'
    }
  }
  return 'Unable to load analysis. Please try again.'
}
