/**
 * Conversion Method Summary Component
 *
 * Shows breakdown of conversion methods used:
 * - AI-assisted conversions
 * - Rule-based conversions
 * - AI fallback conversions
 * - Manual conversions required
 */

import { Brain, Code, AlertTriangle, User } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

export interface MethodBreakdown {
  ruleBasedCount: number
  aiAssistedCount: number
  aiFallbackCount: number
  manualCount: number
  totalCount: number
}

interface ConversionMethodSummaryProps {
  breakdown: MethodBreakdown
  showCard?: boolean
  className?: string
}

interface MethodRowProps {
  label: string
  count: number
  total: number
  icon: React.ReactNode
  variant: 'success' | 'info' | 'warning' | 'destructive'
}

const variantColors = {
  success: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    progress: 'bg-green-500',
  },
  info: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    progress: 'bg-blue-500',
  },
  warning: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    progress: 'bg-yellow-500',
  },
  destructive: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    progress: 'bg-red-500',
  },
}

function MethodRow({ label, count, total, icon, variant }: MethodRowProps) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0
  const colors = variantColors[variant]

  if (count === 0) {
    return null
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className={cn('flex items-center gap-2', colors.text)}>
          {icon}
          {label}
        </span>
        <span className={cn('font-medium', colors.text)}>
          {count} ({percentage}%)
        </span>
      </div>
      <Progress
        value={percentage}
        className="h-2"
        // Note: Progress component styling may vary
      />
    </div>
  )
}

function MethodContent({ breakdown }: { breakdown: MethodBreakdown }) {
  return (
    <div className="space-y-3">
      <MethodRow
        label="AI-Assisted"
        count={breakdown.aiAssistedCount}
        total={breakdown.totalCount}
        icon={<Brain className="h-4 w-4" />}
        variant="success"
      />
      <MethodRow
        label="Rule-Based"
        count={breakdown.ruleBasedCount}
        total={breakdown.totalCount}
        icon={<Code className="h-4 w-4" />}
        variant="info"
      />
      <MethodRow
        label="AI Fallback"
        count={breakdown.aiFallbackCount}
        total={breakdown.totalCount}
        icon={<AlertTriangle className="h-4 w-4" />}
        variant="warning"
      />
      <MethodRow
        label="Manual Required"
        count={breakdown.manualCount}
        total={breakdown.totalCount}
        icon={<User className="h-4 w-4" />}
        variant="destructive"
      />

      {breakdown.totalCount === 0 && (
        <p className="text-sm text-muted-foreground text-center py-2">
          No conversions recorded yet
        </p>
      )}
    </div>
  )
}

export function ConversionMethodSummary({
  breakdown,
  showCard = true,
  className,
}: ConversionMethodSummaryProps) {
  if (!showCard) {
    return <MethodContent breakdown={breakdown} />
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Code className="h-5 w-5" />
          Conversion Methods
        </CardTitle>
      </CardHeader>
      <CardContent>
        <MethodContent breakdown={breakdown} />
      </CardContent>
    </Card>
  )
}

/**
 * Inline summary for compact display
 */
export function ConversionMethodInline({ breakdown }: { breakdown: MethodBreakdown }) {
  if (breakdown.totalCount === 0) {
    return null
  }

  return (
    <div className="flex items-center gap-4 text-sm text-muted-foreground">
      {breakdown.aiAssistedCount > 0 && (
        <span className="flex items-center gap-1 text-green-600">
          <Brain className="h-3.5 w-3.5" />
          {breakdown.aiAssistedCount} AI
        </span>
      )}
      {breakdown.ruleBasedCount > 0 && (
        <span className="flex items-center gap-1 text-blue-600">
          <Code className="h-3.5 w-3.5" />
          {breakdown.ruleBasedCount} Rule
        </span>
      )}
      {breakdown.aiFallbackCount > 0 && (
        <span className="flex items-center gap-1 text-yellow-600">
          <AlertTriangle className="h-3.5 w-3.5" />
          {breakdown.aiFallbackCount} Fallback
        </span>
      )}
      {breakdown.manualCount > 0 && (
        <span className="flex items-center gap-1 text-red-600">
          <User className="h-3.5 w-3.5" />
          {breakdown.manualCount} Manual
        </span>
      )}
    </div>
  )
}

export default ConversionMethodSummary
