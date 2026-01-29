/**
 * ReportPreview Component - Shows detailed preview of selected report
 */

import { useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  FileText,
  FolderOpen,
  Calendar,
  User,
  HardDrive,
  Clock,
  Play,
  ExternalLink,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { ScoreBadge, NotAnalyzedBadge } from '@/components/analysis/ScoreBadge'
import type { SelectedReport } from '@/store/uiStore'

// Previous analysis data structure (will be populated in Epic 4)
export interface PreviousAnalysis {
  score: number
  status: 'green' | 'yellow' | 'red'
  classification: string
  analyzed_at: string
}

interface ReportPreviewProps {
  report: SelectedReport | null
  previousAnalysis?: PreviousAnalysis | null
  onAnalyze?: (reportPath: string) => void
  onViewAnalysis?: (reportPath: string) => void
  isAnalyzing?: boolean
  className?: string
}

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

/**
 * Format date for display
 */
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

/**
 * Format relative time (e.g., "2 days ago")
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
  return `${Math.floor(diffDays / 365)} years ago`
}

export function ReportPreview({
  report,
  previousAnalysis,
  onAnalyze,
  onViewAnalysis,
  isAnalyzing = false,
  className,
}: ReportPreviewProps) {
  const handleAnalyze = useCallback(() => {
    if (report && onAnalyze) {
      onAnalyze(report.path)
    }
  }, [report, onAnalyze])

  const handleViewAnalysis = useCallback(() => {
    if (report && onViewAnalysis) {
      onViewAnalysis(report.path)
    }
  }, [report, onViewAnalysis])

  // Empty state - no report selected
  if (!report) {
    return (
      <Card className={cn('flex flex-col', className)}>
        <CardContent className="flex-1 flex flex-col items-center justify-center py-16 text-center">
          <FileText className="h-12 w-12 text-muted-foreground/40 mb-4" />
          <h3 className="text-lg font-medium mb-2">No Report Selected</h3>
          <p className="text-sm text-muted-foreground max-w-[280px]">
            Select a report from the list to view its details and analysis
            options.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-start gap-3">
          <FileText className="h-5 w-5 shrink-0 mt-0.5 text-primary" />
          <span className="break-words">{report.name}</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4">
        {/* Metadata section */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FolderOpen className="h-4 w-4 shrink-0" />
            <span className="font-mono text-xs break-all">{report.path}</span>
          </div>

          {report.created_by && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <User className="h-4 w-4 shrink-0" />
              <span>Created by {report.created_by}</span>
            </div>
          )}

          {report.modified_date && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4 shrink-0" />
              <span>
                Modified {formatRelativeTime(report.modified_date)} (
                {formatDate(report.modified_date)})
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 text-muted-foreground">
            <HardDrive className="h-4 w-4 shrink-0" />
            <span>Size: {formatFileSize(report.size_bytes)}</span>
          </div>
        </div>

        <Separator />

        {/* Description section */}
        <div className="flex-1 min-h-0">
          <h4 className="text-sm font-medium mb-2">Description</h4>
          {report.description ? (
            <div className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground">
              <ReactMarkdown>{report.description}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No description available.
            </p>
          )}
        </div>

        <Separator />

        {/* Previous Analysis section */}
        <div>
          <h4 className="text-sm font-medium mb-2">Previous Analysis</h4>
          {previousAnalysis ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <ScoreBadge
                  score={previousAnalysis.score}
                  status={previousAnalysis.status}
                />
                <span className="text-sm text-muted-foreground">
                  {previousAnalysis.classification}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span>Analyzed {formatRelativeTime(previousAnalysis.analyzed_at)}</span>
                {onViewAnalysis && (
                  <Button
                    variant="link"
                    size="sm"
                    className="h-auto p-0 text-primary"
                    onClick={handleViewAnalysis}
                  >
                    View Details
                    <ExternalLink className="h-3 w-3 ml-1" />
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <NotAnalyzedBadge size="sm" />
              <span className="text-sm text-muted-foreground">
                This report has not been analyzed yet.
              </span>
            </div>
          )}
        </div>

        <Separator />

        {/* Action buttons */}
        <div className="pt-2">
          <Button
            size="lg"
            className="w-full gap-2"
            onClick={handleAnalyze}
            disabled={isAnalyzing || !onAnalyze}
          >
            {isAnalyzing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Analyze Report
              </>
            )}
          </Button>
          {!onAnalyze && (
            <p className="text-xs text-muted-foreground text-center mt-2">
              Analysis functionality will be available in a future update.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
