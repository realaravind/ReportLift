/**
 * React Query hooks for Snowflake settings management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface SnowflakeSettings {
  account_identifier: string | null
  warehouse: string | null
  database: string | null
  schema_name: string | null
  auth_method: string
  has_oauth_config: boolean
  oauth_status: 'authorized' | 'not_authorized' | 'expired'
  username: string | null
  has_password: boolean
  updated_at: string | null
}

export interface SnowflakeSettingsUpdateRequest {
  account_identifier: string
  warehouse: string
  database: string
  schema_name: string
  auth_method: 'oauth' | 'basic'
  username?: string
  password?: string
}

export interface SnowflakeTestResultDetails {
  account: string | null
  warehouse: string | null
  database: string | null
  schema: string | null
  role: string | null
  user: string | null
  response_time_ms: number
  error_code: string | null
  snowflake_error_code: number | null
}

export interface SnowflakeTestResult {
  success: boolean
  message: string
  details: SnowflakeTestResultDetails
  suggestions: string[] | null
  requires_reauth: boolean
  tested_at: string
}

const SNOWFLAKE_SETTINGS_KEY = ['settings', 'snowflake']

/**
 * Hook to fetch Snowflake settings
 */
export function useSnowflakeSettings() {
  return useQuery<SnowflakeSettings>({
    queryKey: SNOWFLAKE_SETTINGS_KEY,
    queryFn: async () => {
      const response = await api.get<SnowflakeSettings>('/api/v1/settings/snowflake')
      return response.data
    },
  })
}

/**
 * Hook to update Snowflake settings
 */
export function useUpdateSnowflakeSettings() {
  const queryClient = useQueryClient()

  return useMutation<SnowflakeSettings, Error, SnowflakeSettingsUpdateRequest>({
    mutationFn: async (data: SnowflakeSettingsUpdateRequest) => {
      const response = await api.put<SnowflakeSettings>('/api/v1/settings/snowflake', data)
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new settings
      queryClient.setQueryData(SNOWFLAKE_SETTINGS_KEY, data)
    },
  })
}

/**
 * Hook to clear Snowflake basic auth credentials
 */
export function useClearSnowflakeCredentials() {
  const queryClient = useQueryClient()

  return useMutation<SnowflakeSettings, Error, void>({
    mutationFn: async () => {
      const response = await api.delete<SnowflakeSettings>('/api/v1/settings/snowflake/credentials')
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new settings
      queryClient.setQueryData(SNOWFLAKE_SETTINGS_KEY, data)
    },
  })
}

/**
 * Hook to test Snowflake connection
 */
export function useTestSnowflakeConnection() {
  return useMutation<SnowflakeTestResult, Error, void>({
    mutationFn: async () => {
      const response = await api.post<SnowflakeTestResult>('/api/v1/settings/snowflake/test')
      return response.data
    },
  })
}
