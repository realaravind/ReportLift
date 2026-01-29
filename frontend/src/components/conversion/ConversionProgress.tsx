/**
 * ConversionProgress Component - Shows progress during report conversion
 */

import { Loader2, XCircle, CheckCircle, Circle, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { ConversionStatus } from '@/hooks/useConversion'

// Conversion steps matching backend
const CONVERSION_STEPS = [
  { key: 'validating', label: 'Validating analysis data...' },
  { key: 'generating_sql', label: 'Generating SQL scripts...' },
  { key: 'rewriting_sp', label: 'Rewriting stored procedures...' },
  { key: 'building_pbix', label: 'Building Power BI report...' },
  { key: 'applying_branding', label: 'Applying branding template...' },
  { key: 'finalizing', label: 'Finalizing outputs...' },
] as const

interface ConversionProgressProps {
  status: 'idle' | 'starting' | ConversionStatus
  progress: number
  currentStep: string | null
  stepsCompleted: number
  error: string | null
  snowflakeConfigured: boolean | null
  onCancel?: () => void
  isCancelling?: boolean
  onViewResult?: () => void
  className?: string
}

export function ConversionProgress({
  status,
  progress,
  currentStep,
  stepsCompleted,
  error,
  snowflakeConfigured,
  onCancel,
  isCancelling = false,
  onViewResult,
  className,
}: ConversionProgressProps) {
  // Don't show anything when idle
  if (status === 'idle') {
    return null
  }

  const isRunning = status === 'starting' || status === 'pending' || status === 'in_progress'
  const isComplete = status === 'completed'
  const isFailed = status === 'failed'
  const isCancelled = status === 'cancelled'

  return (
    <div className={cn('rounded-lg border bg-card p-6', className)}>
      {/* Header with status icon */}
      <div className="flex items-center gap-3 mb-4">
        {isRunning ? (
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        ) : isComplete ? (
          <CheckCircle className="h-6 w-6 text-green-500" />
        ) : isFailed ? (
          <XCircle className="h-6 w-6 text-destructive" />
        ) : isCancelled ? (
          <AlertTriangle className="h-6 w-6 text-yellow-500" />
        ) : null}

        <div>
          <h3 className="font-semibold text-lg">
            {status === 'starting'
              ? 'Starting conversion...'
              : status === 'pending'
                ? 'Preparing conversion...'
                : status === 'in_progress'
                  ? 'Converting report...'
                  : isComplete
                    ? 'Conversion complete!'
                    : isFailed
                      ? 'Conversion failed'
                      : isCancelled
                        ? 'Conversion cancelled'
                        : ''}
          </h3>
          {snowflakeConfigured === false && isRunning && (
            <p className="text-sm text-yellow-600">
              Snowflake not configured - using placeholder schema
            </p>
          )}
        </div>
      </div>

      {/* Progress bar for running state */}
      {isRunning && (
        <div className="space-y-3 mb-4">
          <Progress value={progress} className="h-3" />
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>{currentStep || 'Initializing...'}</span>
            <span>{progress}%</span>
          </div>
        </div>
      )}

      {/* Step indicators */}
      {(isRunning || isComplete) && (
        <div className="space-y-2 mb-4">
          {CONVERSION_STEPS.map((step, index) => {
            const stepNumber = index + 1
            const isCompleted = stepsCompleted >= stepNumber
            const isCurrent = currentStep?.toLowerCase().includes(step.key.replace('_', ' '))

            return (
              <div
                key={step.key}
                className={cn(
                  'flex items-center gap-3 text-sm py-1',
                  isCompleted
                    ? 'text-green-600'
                    : isCurrent
                      ? 'text-primary font-medium'
                      : 'text-muted-foreground'
                )}
              >
                {isCompleted ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : (
                  <Circle className="h-4 w-4" />
                )}
                <span>{step.label}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Error message for failed state */}
      {isFailed && error && (
        <div className="mt-2 p-3 rounded bg-destructive/10 text-destructive text-sm mb-4">
          {error}
        </div>
      )}

      {/* Success message with Snowflake warning */}
      {isComplete && snowflakeConfigured === false && (
        <div className="mt-2 p-3 rounded bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm mb-4">
          <strong>Note:</strong> SQL scripts use placeholder schema names. Update them with your
          actual Snowflake schema before running.
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-4">
        {isRunning && onCancel && (
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isCancelling}
          >
            {isCancelling ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Cancelling...
              </>
            ) : (
              'Cancel'
            )}
          </Button>
        )}

        {isComplete && onViewResult && (
          <Button size="sm" onClick={onViewResult}>
            View Results
          </Button>
        )}
      </div>
    </div>
  )
}

/**
 * Compact conversion status for displaying in headers or cards
 */
interface ConversionStatusBadgeProps {
  status: ConversionStatus | null
  className?: string
}

interface StatusConfig {
  icon: typeof Circle
  color: string
  label: string
  animate?: boolean
}

export function ConversionStatusBadge({ status, className }: ConversionStatusBadgeProps) {
  if (!status) return null

  const statusConfig: Record<ConversionStatus, StatusConfig> = {
    pending: { icon: Circle, color: 'text-gray-500', label: 'Pending' },
    in_progress: { icon: Loader2, color: 'text-primary', label: 'Converting...', animate: true },
    completed: { icon: CheckCircle, color: 'text-green-500', label: 'Converted' },
    failed: { icon: XCircle, color: 'text-destructive', label: 'Failed' },
    cancelled: { icon: AlertTriangle, color: 'text-yellow-500', label: 'Cancelled' },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <div className={cn('flex items-center gap-1.5 text-sm', config.color, className)}>
      <Icon className={cn('h-4 w-4', config.animate && 'animate-spin')} />
      <span>{config.label}</span>
    </div>
  )
}
