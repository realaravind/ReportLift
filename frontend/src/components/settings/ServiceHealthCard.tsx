/**
 * Service Health Card - Displays health status for a single service
 */

import { Server, Snowflake, Bot, Clock, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  ServiceHealth,
  ServiceStatus,
  getServiceDisplayName,
  getStatusLabel,
  formatLastChecked,
} from '@/hooks/useHealthCheck'

interface ServiceHealthCardProps {
  health: ServiceHealth
  onClick?: () => void
  isLoading?: boolean
}

function getServiceIcon(service: string) {
  switch (service) {
    case 'ssrs':
      return Server
    case 'snowflake':
      return Snowflake
    case 'ollama':
      return Bot
    default:
      return Server
  }
}

function getStatusStyles(status: ServiceStatus): {
  border: string
  bg: string
  icon: string
  badge: string
  badgeText: string
} {
  switch (status) {
    case 'connected':
      return {
        border: 'border-green-200 hover:border-green-300',
        bg: 'bg-green-50',
        icon: 'text-green-600',
        badge: 'bg-green-100',
        badgeText: 'text-green-700',
      }
    case 'disconnected':
      return {
        border: 'border-red-200 hover:border-red-300',
        bg: 'bg-red-50',
        icon: 'text-red-600',
        badge: 'bg-red-100',
        badgeText: 'text-red-700',
      }
    case 'not_configured':
      return {
        border: 'border-gray-200 hover:border-gray-300',
        bg: 'bg-gray-50',
        icon: 'text-gray-400',
        badge: 'bg-gray-100',
        badgeText: 'text-gray-600',
      }
    case 'checking':
      return {
        border: 'border-blue-200',
        bg: 'bg-blue-50',
        icon: 'text-blue-500',
        badge: 'bg-blue-100',
        badgeText: 'text-blue-700',
      }
    default:
      return {
        border: 'border-gray-200',
        bg: 'bg-gray-50',
        icon: 'text-gray-400',
        badge: 'bg-gray-100',
        badgeText: 'text-gray-600',
      }
  }
}

export function ServiceHealthCard({ health, onClick, isLoading }: ServiceHealthCardProps) {
  const Icon = getServiceIcon(health.service)
  const displayStatus = isLoading ? 'checking' : health.status
  const styles = getStatusStyles(displayStatus)

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isLoading}
      className={cn(
        'w-full p-4 rounded-lg border-2 transition-all text-left',
        styles.border,
        'hover:shadow-md',
        onClick && 'cursor-pointer',
        isLoading && 'opacity-75'
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn('p-2 rounded-lg', styles.bg)}>
          <Icon
            className={cn('h-6 w-6', styles.icon, isLoading && 'animate-pulse')}
          />
        </div>
        <span
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            styles.badge,
            styles.badgeText
          )}
        >
          {isLoading ? 'Checking...' : getStatusLabel(health.status)}
        </span>
      </div>

      <h3 className="font-semibold text-gray-900 mb-1">
        {getServiceDisplayName(health.service)}
      </h3>

      {health.message && (
        <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
          {health.message}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{formatLastChecked(health.last_checked)}</span>
        </div>
        {health.details?.response_time_ms ? (
          <span>{health.details.response_time_ms}ms</span>
        ) : null}
      </div>

      {onClick && health.status !== 'checking' && (
        <div className="mt-3 flex items-center gap-1 text-xs text-primary">
          <span>Configure</span>
          <ExternalLink className="h-3 w-3" />
        </div>
      )}
    </button>
  )
}

export default ServiceHealthCard
