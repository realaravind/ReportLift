/**
 * ScoreBadge Component - Displays analysis score with color indicator
 */

import { cn } from '@/lib/utils'

export type ScoreStatus = 'green' | 'yellow' | 'red'

export interface ScoreBadgeProps {
  score: number
  status?: ScoreStatus
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

/**
 * Calculate status from score if not provided
 * Green: 70-100, Yellow: 40-69, Red: 0-39
 */
function getStatusFromScore(score: number): ScoreStatus {
  if (score >= 70) return 'green'
  if (score >= 40) return 'yellow'
  return 'red'
}

/**
 * Get status label text
 */
function getStatusLabel(status: ScoreStatus): string {
  switch (status) {
    case 'green':
      return 'Good'
    case 'yellow':
      return 'Moderate'
    case 'red':
      return 'Complex'
  }
}

const statusColors: Record<ScoreStatus, string> = {
  green: 'bg-green-100 text-green-800 border-green-200',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  red: 'bg-red-100 text-red-800 border-red-200',
}

const sizeClasses = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-3 py-1.5',
}

export function ScoreBadge({
  score,
  status,
  size = 'md',
  showLabel = true,
  className,
}: ScoreBadgeProps) {
  const computedStatus = status ?? getStatusFromScore(score)
  const label = getStatusLabel(computedStatus)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        statusColors[computedStatus],
        sizeClasses[size],
        className
      )}
    >
      <span className="font-bold">{score}%</span>
      {showLabel && <span className="font-normal">{label}</span>}
    </span>
  )
}

/**
 * Placeholder badge for reports that haven't been analyzed
 */
export function NotAnalyzedBadge({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        'bg-muted text-muted-foreground border-border',
        sizeClasses[size],
        className
      )}
    >
      Not Analyzed
    </span>
  )
}
