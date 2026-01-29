/**
 * Summary card displaying analysis overview
 */

import { formatDistanceToNow } from 'date-fns'
import { FileText, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type {
  AnalysisResult,
  ConversionStatus,
  ReportClassification,
} from '@/types/analysis'

interface AnalysisSummaryCardProps {
  analysis: AnalysisResult
}

const statusColors: Record<ConversionStatus, string> = {
  green: 'border-green-300 bg-green-50',
  yellow: 'border-yellow-300 bg-yellow-50',
  red: 'border-red-300 bg-red-50',
}

const scoreColors: Record<ConversionStatus, string> = {
  green: 'text-green-600',
  yellow: 'text-yellow-600',
  red: 'text-red-600',
}

const classificationBadgeVariants: Record<ReportClassification, 'default' | 'secondary' | 'warning' | 'danger'> = {
  Tabular: 'default',
  Analytical: 'secondary',
  Mixed: 'warning',
  Complex: 'danger',
}

function StatusIndicator({ status }: { status: ConversionStatus }) {
  const colors: Record<ConversionStatus, string> = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  }

  const labels: Record<ConversionStatus, string> = {
    green: 'Ready to Convert',
    yellow: 'Review Recommended',
    red: 'Needs Attention',
  }

  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${colors[status]} animate-pulse`} />
      <span className="text-sm font-medium">{labels[status]}</span>
    </div>
  )
}

export function AnalysisSummaryCard({ analysis }: AnalysisSummaryCardProps) {
  const status = analysis.status || 'yellow'
  const classification = analysis.classification || 'Mixed'
  const score = analysis.score ?? 0

  return (
    <Card className={`border-2 ${statusColors[status]}`}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">{analysis.report_name}</h2>
              <p className="text-sm text-muted-foreground">{analysis.report_path}</p>
            </div>
          </div>
          <Badge variant={classificationBadgeVariants[classification]}>
            {classification}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className={`text-4xl font-bold ${scoreColors[status]}`}>
                {score}%
              </div>
              <div className="text-sm text-muted-foreground">Conversion Score</div>
            </div>
            <div className="h-12 w-px bg-border" />
            <StatusIndicator status={status} />
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              Analyzed {formatDistanceToNow(new Date(analysis.analyzed_at))} ago
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
