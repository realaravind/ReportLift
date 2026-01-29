/**
 * React Query hooks for SSRS folder navigation
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { AxiosError } from 'axios'

export interface FolderItem {
  name: string
  path: string
  has_children: boolean
  description?: string
}

export interface FoldersMeta {
  timestamp: string
  total_count: number
  path: string
}

export interface FoldersResponse {
  data: FolderItem[]
  meta: FoldersMeta
}

export interface FoldersError {
  code: string
  message: string
  suggestions?: string[]
}

const FOLDERS_QUERY_KEY = ['ssrs', 'folders']

/**
 * Hook to fetch SSRS folders at a specific path
 */
export function useSSRSFolders(path: string = '/', enabled: boolean = true) {
  return useQuery<FoldersResponse, AxiosError<{ detail: FoldersError }>>({
    queryKey: [...FOLDERS_QUERY_KEY, path],
    queryFn: async () => {
      const response = await api.get<FoldersResponse>('/api/v1/ssrs/folders', {
        params: { path },
      })
      return response.data
    },
    enabled,
    // Cache folder data for 5 minutes
    staleTime: 5 * 60 * 1000,
    // Retry once on failure
    retry: 1,
  })
}

/**
 * Extract error details from an SSRS folders error response
 */
export function getSSRSFoldersError(
  error: AxiosError<{ detail: FoldersError }> | null
): FoldersError | null {
  if (!error) return null

  if (error.response?.data?.detail) {
    return error.response.data.detail
  }

  // Fallback for network errors
  return {
    code: 'NETWORK_ERROR',
    message: error.message || 'Unable to connect to server',
    suggestions: ['Check your network connection', 'Try again later'],
  }
}

/**
 * Check if error indicates SSRS is not configured
 */
export function isSSRSNotConfigured(
  error: AxiosError<{ detail: FoldersError }> | null
): boolean {
  if (!error) return false
  const errorDetail = getSSRSFoldersError(error)
  return errorDetail?.code === 'SSRS_NOT_CONFIGURED'
}
