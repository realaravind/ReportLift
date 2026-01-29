/**
 * Health Store - Zustand store for global health status management
 *
 * This store provides:
 * - Global access to service health status
 * - Warning indicator state for the header
 * - Methods to update health status from health check results
 */

import { create } from 'zustand'
import { ServiceHealth } from '@/hooks/useHealthCheck'

interface HealthState {
  /** Service health status array */
  services: ServiceHealth[]
  /** Overall system status */
  overallStatus: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  /** Number of disconnected services (not including not_configured) */
  disconnectedCount: number
  /** When the status was last checked */
  lastChecked: string | null
  /** Whether there's an active health check in progress */
  isChecking: boolean
  /** Update health status from API response */
  setHealthStatus: (
    services: ServiceHealth[],
    overallStatus: 'healthy' | 'degraded' | 'unhealthy',
    checkedAt: string
  ) => void
  /** Set checking state */
  setIsChecking: (isChecking: boolean) => void
  /** Clear health status */
  clearHealthStatus: () => void
}

export const useHealthStore = create<HealthState>((set) => ({
  services: [],
  overallStatus: 'unknown',
  disconnectedCount: 0,
  lastChecked: null,
  isChecking: false,

  setHealthStatus: (services, overallStatus, checkedAt) => {
    // Count disconnected services (not including not_configured - that's expected)
    const disconnectedCount = services.filter(
      (s) => s.status === 'disconnected'
    ).length

    set({
      services,
      overallStatus,
      disconnectedCount,
      lastChecked: checkedAt,
      isChecking: false,
    })
  },

  setIsChecking: (isChecking) => {
    set({ isChecking })
  },

  clearHealthStatus: () => {
    set({
      services: [],
      overallStatus: 'unknown',
      disconnectedCount: 0,
      lastChecked: null,
      isChecking: false,
    })
  },
}))
