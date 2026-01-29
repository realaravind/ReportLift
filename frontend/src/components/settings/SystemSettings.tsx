/**
 * System Settings Tab - System Health Dashboard
 */

import { useCallback } from 'react'
import { RefreshCw, AlertCircle, CheckCircle2, AlertTriangle } from 'lucide-react'
import { SettingsCard } from './SettingsCard'
import { ServiceHealthCard } from './ServiceHealthCard'
import { Button } from '@/components/ui/button'
import {
  useServicesHealth,
  useRefreshHealth,
  ServiceHealth,
} from '@/hooks/useHealthCheck'

interface SystemSettingsProps {
  onNavigateToTab?: (tab: string) => void
}

function OverallStatusBanner({
  status,
  isLoading,
}: {
  status: 'healthy' | 'degraded' | 'unhealthy'
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-50 border border-blue-200">
        <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
        <div>
          <p className="font-medium text-blue-700">Checking Services</p>
          <p className="text-sm text-blue-600">
            Testing connections to all configured services...
          </p>
        </div>
      </div>
    )
  }

  if (status === 'healthy') {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 border border-green-200">
        <CheckCircle2 className="h-5 w-5 text-green-600" />
        <div>
          <p className="font-medium text-green-700">All Systems Operational</p>
          <p className="text-sm text-green-600">
            All configured services are connected and responding.
          </p>
        </div>
      </div>
    )
  }

  if (status === 'degraded') {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
        <AlertTriangle className="h-5 w-5 text-amber-600" />
        <div>
          <p className="font-medium text-amber-700">Some Services Need Attention</p>
          <p className="text-sm text-amber-600">
            One or more services are disconnected or not configured.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 border border-red-200">
      <AlertCircle className="h-5 w-5 text-red-600" />
      <div>
        <p className="font-medium text-red-700">Services Unavailable</p>
        <p className="text-sm text-red-600">
          All configured services are currently disconnected.
        </p>
      </div>
    </div>
  )
}

export function SystemSettings({ onNavigateToTab }: SystemSettingsProps) {
  const { data: health, isLoading, isFetching, error } = useServicesHealth()
  const { refreshHealth } = useRefreshHealth()

  const handleCardClick = useCallback(
    (service: string) => {
      if (onNavigateToTab) {
        // Map service name to tab name
        const tabMap: Record<string, string> = {
          ssrs: 'ssrs',
          snowflake: 'snowflake',
          ollama: 'ollama',
        }
        onNavigateToTab(tabMap[service] || service)
      }
    },
    [onNavigateToTab]
  )

  const handleRefresh = () => {
    refreshHealth()
  }

  // Create placeholder health data for loading state
  const getPlaceholderHealth = (service: 'ssrs' | 'snowflake' | 'ollama'): ServiceHealth => ({
    service,
    status: 'checking',
    message: 'Checking connection...',
    last_checked: null,
  })

  if (error) {
    return (
      <SettingsCard
        title="System Health"
        description="Monitor the health status of all connected services."
      >
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-medium mb-2">Failed to Load Health Status</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      </SettingsCard>
    )
  }

  return (
    <SettingsCard
      title="System Health"
      description="Monitor the health status of all connected services."
      actions={
        <Button
          onClick={handleRefresh}
          disabled={isFetching}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh All
        </Button>
      }
    >
      <div className="space-y-6">
        {/* Overall Status Banner */}
        <OverallStatusBanner
          status={health?.overall_status || 'healthy'}
          isLoading={isLoading}
        />

        {/* Service Health Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(health?.services || [
            getPlaceholderHealth('ssrs'),
            getPlaceholderHealth('snowflake'),
            getPlaceholderHealth('ollama'),
          ]).map((service) => (
            <ServiceHealthCard
              key={service.service}
              health={service}
              onClick={() => handleCardClick(service.service)}
              isLoading={isLoading || isFetching}
            />
          ))}
        </div>

        {/* Last Checked Timestamp */}
        {health?.checked_at && (
          <div className="text-center">
            <p className="text-xs text-muted-foreground">
              Last updated: {new Date(health.checked_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>
    </SettingsCard>
  )
}

export default SystemSettings
