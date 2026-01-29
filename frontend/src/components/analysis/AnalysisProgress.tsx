/**
 * AnalysisProgress Component - Shows progress during report analysis
 */

import { Loader2, XCircle, CheckCircle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface AnalysisProgressProps {
  status: 'idle' | 'starting' | 'running' | 'completed' | 'failed' | 'cached'
  progress: number
  currentStep: string | null
  error: string | null
  onCancel?: () => void
  onRetry?: () => void
  onViewResults?: () => void
  className?: string
}

export function AnalysisProgress({
  status,
  progress,
  currentStep,
  error,
  onCancel,
  onRetry,
  onViewResults,
  className,
}: AnalysisProgressProps) {
  // Don't show anything when idle
  if (status === 'idle') {
    return null
  }

  return (
    <div className={cn('rounded-lg border bg-card p-4', className)}>
      {/* Header with status icon */}
      <div className="flex items-center gap-3 mb-3">
        {status === 'starting' || status === 'running' ? (
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        ) : status === 'completed' ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : status === 'failed' ? (
          <XCircle className="h-5 w-5 text-destructive" />
        ) : status === 'cached' ? (
          <AlertCircle className="h-5 w-5 text-yellow-500" />
        ) : null}

        <span className="font-medium">
          {status === 'starting'
            ? 'Starting analysis...'
            : status === 'running'
              ? 'Analyzing report...'
              : status === 'completed'
                ? 'Analysis complete'
                : status === 'failed'
                  ? 'Analysis failed'
                  : status === 'cached'
                    ? 'Previous analysis found'
                    : ''}
        </span>
      </div>

      {/* Progress bar for running state */}
      {(status === 'starting' || status === 'running') && (
        <div className="space-y-2">
          <Progress value={progress} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{currentStep || 'Initializing...'}</span>
            <span>{progress}%</span>
          </div>
        </div>
      )}

      {/* Error message for failed state */}
      {status === 'failed' && error && (
        <div className="mt-2 p-3 rounded bg-destructive/10 text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-4">
        {(status === 'starting' || status === 'running') && onCancel && (
          <Button variant="outline" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}

        {status === 'failed' && onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}

        {status === 'completed' && onViewResults && (
          <Button size="sm" onClick={onViewResults}>
            View Results
          </Button>
        )}

        {status === 'cached' && onViewResults && (
          <Button variant="outline" size="sm" onClick={onViewResults}>
            View Previous Results
          </Button>
        )}
      </div>
    </div>
  )
}

/**
 * Inline progress indicator for use in buttons or compact spaces
 */
interface InlineProgressProps {
  isAnalyzing: boolean
  progress: number
}

export function InlineProgress({ isAnalyzing, progress }: InlineProgressProps) {
  if (!isAnalyzing) return null

  return (
    <div className="flex items-center gap-2">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span className="text-sm">{progress}%</span>
    </div>
  )
}
