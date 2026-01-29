/**
 * React Query hooks for service health check management
 */

import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useHealthStore } from '@/store/healthStore'

export type ServiceStatus = 'connected' | 'disconnected' | 'not_configured' | 'checking'

export interface ServiceHealthDetails {
  version?: string
  response_time_ms: number
  error_code?: string
}

export interface ServiceHealth {
  service: 'ssrs' | 'snowflake' | 'ollama'
  status: ServiceStatus
  message?: string
  details?: ServiceHealthDetails
  last_checked: string | null
}

export interface HealthResponse {
  services: ServiceHealth[]
  overall_status: 'healthy' | 'degraded' | 'unhealthy'
  checked_at: string
}

const HEALTH_QUERY_KEY = ['health', 'services']

/**
 * Hook to fetch all services health status
 * Also syncs the result to the Zustand store for global access
 */
export function useServicesHealth() {
  const { setHealthStatus, setIsChecking } = useHealthStore()

  const query = useQuery<HealthResponse>({
    queryKey: HEALTH_QUERY_KEY,
    queryFn: async () => {
      const response = await api.get<HealthResponse>('/health/services')
      return response.data
    },
    // Cache for 5 minutes but show stale data while refetching
    staleTime: 5 * 60 * 1000,
    // Refetch on mount to ensure fresh data when tab is selected
    refetchOnMount: true,
    // Don't refetch in background automatically
    refetchInterval: false,
  })

  // Sync query state to Zustand store
  useEffect(() => {
    if (query.isFetching) {
      setIsChecking(true)
    }
  }, [query.isFetching, setIsChecking])

  useEffect(() => {
    if (query.data) {
      setHealthStatus(
        query.data.services,
        query.data.overall_status,
        query.data.checked_at
      )
    }
  }, [query.data, setHealthStatus])

  return query
}

/**
 * Hook to manually refresh health status
 */
export function useRefreshHealth() {
  const queryClient = useQueryClient()

  return {
    refreshHealth: () => {
      queryClient.invalidateQueries({ queryKey: HEALTH_QUERY_KEY })
    },
    invalidateOnSettingsSave: () => {
      // Invalidate health cache when any settings are saved
      queryClient.invalidateQueries({ queryKey: HEALTH_QUERY_KEY })
    },
  }
}

/**
 * Get display color for service status
 */
export function getStatusColor(status: ServiceStatus): string {
  switch (status) {
    case 'connected':
      return 'text-green-600'
    case 'disconnected':
      return 'text-red-600'
    case 'not_configured':
      return 'text-gray-400'
    case 'checking':
      return 'text-blue-500'
    default:
      return 'text-gray-400'
  }
}

/**
 * Get display badge variant for service status
 */
export function getStatusBadgeVariant(
  status: ServiceStatus
): 'default' | 'destructive' | 'secondary' | 'outline' {
  switch (status) {
    case 'connected':
      return 'default'
    case 'disconnected':
      return 'destructive'
    case 'not_configured':
      return 'secondary'
    case 'checking':
      return 'outline'
    default:
      return 'secondary'
  }
}

/**
 * Format timestamp as relative time (e.g., "2 minutes ago")
 */
export function formatLastChecked(timestamp: string | null): string {
  if (!timestamp) return 'Never'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)

  if (diffSeconds < 60) {
    return 'Just now'
  }

  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`
  }

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  }

  return date.toLocaleDateString()
}

/**
 * Get service display name
 */
export function getServiceDisplayName(service: string): string {
  switch (service) {
    case 'ssrs':
      return 'SSRS Report Server'
    case 'snowflake':
      return 'Snowflake'
    case 'ollama':
      return 'Ollama AI'
    default:
      return service
  }
}

/**
 * Get status display label
 */
export function getStatusLabel(status: ServiceStatus): string {
  switch (status) {
    case 'connected':
      return 'Connected'
    case 'disconnected':
      return 'Disconnected'
    case 'not_configured':
      return 'Not Configured'
    case 'checking':
      return 'Checking...'
    default:
      return status
  }
}
