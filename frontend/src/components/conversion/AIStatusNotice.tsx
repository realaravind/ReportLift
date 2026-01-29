/**
 * AI Status Notice Component
 *
 * Displays notifications about AI service availability:
 * - Info notice when AI is disabled
 * - Warning notice when AI is unavailable
 * - Success badge when AI is available
 */

import { Info, AlertTriangle, CheckCircle, Brain, XCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type AIStatusType = 'available' | 'degraded' | 'unavailable' | 'disabled'

interface AIStatusNoticeProps {
  status: AIStatusType
  message?: string
  lastAvailable?: string
  consecutiveFailures?: number
  showDetails?: boolean
  className?: string
}

const statusConfig: Record<
  AIStatusType,
  {
    icon: typeof CheckCircle
    variant: 'default' | 'destructive'
    bgColor: string
    borderColor: string
    textColor: string
    title: string
    defaultMessage: string
  }
> = {
  available: {
    icon: CheckCircle,
    variant: 'default',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    textColor: 'text-green-800',
    title: 'AI Assistance Active',
    defaultMessage: 'AI service is available and will be used for complex conversions.',
  },
  degraded: {
    icon: AlertTriangle,
    variant: 'default',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-800',
    title: 'AI Service Degraded',
    defaultMessage: 'AI service is experiencing issues. Some requests may fall back to rule-based conversion.',
  },
  unavailable: {
    icon: XCircle,
    variant: 'destructive',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-800',
    title: 'AI Service Unavailable',
    defaultMessage: 'AI service is unavailable. Using rule-based conversion as fallback.',
  },
  disabled: {
    icon: Info,
    variant: 'default',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-800',
    title: 'AI Assistance Disabled',
    defaultMessage: 'Using rule-based conversion only. Enable AI assistance in settings for better results.',
  },
}

export function AIStatusNotice({
  status,
  message,
  lastAvailable,
  consecutiveFailures,
  showDetails = false,
  className,
}: AIStatusNoticeProps) {
  const config = statusConfig[status]
  const StatusIcon = config.icon

  // Don't show notice for available status unless explicitly requested
  if (status === 'available' && !showDetails) {
    return null
  }

  return (
    <Alert
      className={cn(
        config.bgColor,
        config.borderColor,
        'border',
        className
      )}
    >
      <StatusIcon className={cn('h-4 w-4', config.textColor)} />
      <AlertTitle className={config.textColor}>
        <span className="flex items-center gap-2">
          <Brain className="h-4 w-4" />
          {config.title}
        </span>
      </AlertTitle>
      <AlertDescription className={cn(config.textColor, 'text-opacity-90')}>
        <p>{message || config.defaultMessage}</p>
        {showDetails && (
          <div className="mt-2 text-sm text-opacity-70">
            {lastAvailable && (
              <p>Last available: {new Date(lastAvailable).toLocaleString()}</p>
            )}
            {consecutiveFailures !== undefined && consecutiveFailures > 0 && (
              <p>Consecutive failures: {consecutiveFailures}</p>
            )}
          </div>
        )}
      </AlertDescription>
    </Alert>
  )
}

/**
 * Compact badge for showing AI status in headers
 */
interface AIStatusBadgeProps {
  status: AIStatusType
  className?: string
}

export function AIStatusBadge({ status, className }: AIStatusBadgeProps) {
  const badgeConfig: Record<
    AIStatusType,
    { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }
  > = {
    available: { variant: 'default', label: 'AI Active' },
    degraded: { variant: 'secondary', label: 'AI Degraded' },
    unavailable: { variant: 'destructive', label: 'AI Unavailable' },
    disabled: { variant: 'outline', label: 'AI Disabled' },
  }

  const config = badgeConfig[status]

  return (
    <Badge variant={config.variant} className={cn('flex items-center gap-1', className)}>
      <Brain className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

export default AIStatusNotice
