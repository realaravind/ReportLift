/**
 * SummaryCard - Displays conversion summary header information
 */

import { FileText, FolderOpen, Clock, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  type SummaryStatus,
  type ReportInfo,
  formatDate,
  formatDuration,
  SUMMARY_STATUS_CONFIG,
} from '@/hooks/useConversion'

interface SummaryCardProps {
  report: ReportInfo
  conversionTimestamp: string
  durationMs: number | null
  status: SummaryStatus
  snowflakeConfigured: boolean
  totalFiles: number
  className?: string
}

// Status icon mapping
const StatusIcons: Record<SummaryStatus, React.ElementType> = {
  success: CheckCircle,
  partial: AlertTriangle,
  failed: XCircle,
}

// Badge variant mapping
const BadgeVariants: Record<SummaryStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  success: 'default',
  partial: 'secondary',
  failed: 'destructive',
}

export function SummaryCard({
  report,
  conversionTimestamp,
  durationMs,
  status,
  snowflakeConfigured,
  totalFiles,
  className,
}: SummaryCardProps) {
  const statusConfig = SUMMARY_STATUS_CONFIG[status]
  const StatusIcon = StatusIcons[status]

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {report.name}
            </CardTitle>
            <CardDescription className="flex items-center gap-1 mt-1">
              <FolderOpen className="h-4 w-4" />
              {report.path}
            </CardDescription>
          </div>
          <Badge variant={BadgeVariants[status]} className="flex items-center gap-1">
            <StatusIcon className="h-3 w-3" />
            {statusConfig.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Conversion Time */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Converted</p>
            <p className="text-sm font-medium">{formatDate(conversionTimestamp)}</p>
          </div>

          {/* Duration */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Duration
            </p>
            <p className="text-sm font-medium">{formatDuration(durationMs)}</p>
          </div>

          {/* Files Generated */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Files Generated</p>
            <p className="text-sm font-medium">{totalFiles} files</p>
          </div>

          {/* Snowflake Status */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Snowflake</p>
            <p className="text-sm font-medium">
              {snowflakeConfigured ? (
                <span className="text-green-600">Configured</span>
              ) : (
                <span className="text-yellow-600">Placeholder Schema</span>
              )}
            </p>
          </div>
        </div>

        {/* Status Description */}
        <div className="mt-4 p-3 bg-muted rounded-lg">
          <p className="text-sm text-muted-foreground">{statusConfig.description}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export default SummaryCard
