/**
 * React Query hooks for SSRS settings management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface SSRSSettings {
  report_server_url: string | null
  auth_method: string
  service_account_username: string | null
  has_credentials: boolean
  updated_at: string | null
}

export interface SSRSSettingsUpdateRequest {
  report_server_url: string
  auth_method: string
  service_account_username?: string
  service_account_password?: string
}

export interface SSRSTestResultDetails {
  server_version: string | null
  response_time_ms: number
  root_folder_accessible: boolean
  error_code: string | null
}

export interface SSRSTestResult {
  success: boolean
  message: string
  details: SSRSTestResultDetails
  suggestions: string[] | null
  tested_at: string
}

const SSRS_SETTINGS_KEY = ['settings', 'ssrs']

/**
 * Hook to fetch SSRS settings
 */
export function useSSRSSettings() {
  return useQuery<SSRSSettings>({
    queryKey: SSRS_SETTINGS_KEY,
    queryFn: async () => {
      const response = await api.get<SSRSSettings>('/api/v1/settings/ssrs')
      return response.data
    },
  })
}

/**
 * Hook to update SSRS settings
 */
export function useUpdateSSRSSettings() {
  const queryClient = useQueryClient()

  return useMutation<SSRSSettings, Error, SSRSSettingsUpdateRequest>({
    mutationFn: async (data: SSRSSettingsUpdateRequest) => {
      const response = await api.put<SSRSSettings>('/api/v1/settings/ssrs', data)
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new settings
      queryClient.setQueryData(SSRS_SETTINGS_KEY, data)
    },
  })
}

/**
 * Hook to clear SSRS credentials
 */
export function useClearSSRSCredentials() {
  const queryClient = useQueryClient()

  return useMutation<SSRSSettings, Error, void>({
    mutationFn: async () => {
      const response = await api.delete<SSRSSettings>('/api/v1/settings/ssrs/credentials')
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new settings
      queryClient.setQueryData(SSRS_SETTINGS_KEY, data)
    },
  })
}

/**
 * Hook to test SSRS connection
 */
export function useTestSSRSConnection() {
  return useMutation<SSRSTestResult, Error, void>({
    mutationFn: async () => {
      const response = await api.post<SSRSTestResult>('/api/v1/settings/ssrs/test')
      return response.data
    },
  })
}
