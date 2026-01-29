/**
 * ConversionSummary - Page displaying comprehensive conversion results
 */

import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw, FileSearch, FolderOpen, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { SummaryCard } from '@/components/conversion/SummaryCard'
import { ConvertedElements } from '@/components/conversion/ConvertedElements'
import { AttentionItems } from '@/components/conversion/AttentionItems'
import { OutputDownload } from '@/components/conversion/OutputDownload'
import { useConversionSummary } from '@/hooks/useConversion'

export function ConversionSummary() {
  const { conversionId } = useParams<{ conversionId: string }>()
  const navigate = useNavigate()

  const {
    data: summary,
    isLoading,
    error,
    refetch,
  } = useConversionSummary(conversionId || null)

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto max-w-6xl py-8 px-4">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <span className="ml-3 text-muted-foreground">Loading conversion summary...</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto max-w-6xl py-8 px-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error loading summary</AlertTitle>
          <AlertDescription>
            {error.response?.data?.detail?.message || 'Failed to load conversion summary'}
          </AlertDescription>
        </Alert>
        <div className="flex gap-2 mt-4">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  // No data
  if (!summary) {
    return (
      <div className="container mx-auto max-w-6xl py-8 px-4">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Conversion not found</AlertTitle>
          <AlertDescription>
            The requested conversion summary could not be found.
          </AlertDescription>
        </Alert>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Go Back
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-6xl py-8 px-4">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-2xl font-bold">Conversion Summary</h1>
        </div>
        <p className="text-muted-foreground">
          Review what was converted and what needs your attention
        </p>
      </div>

      {/* Summary Card */}
      <SummaryCard
        report={summary.report}
        conversionTimestamp={summary.conversion_timestamp}
        durationMs={summary.duration_ms}
        status={summary.status}
        snowflakeConfigured={summary.snowflake_configured}
        totalFiles={summary.files.length}
        className="mb-6"
      />

      {/* Two Column Layout for Converted and Attention */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ConvertedElements converted={summary.converted} />
        <AttentionItems
          attentionItems={summary.attention_required}
          converted={summary.converted}
          todoCount={summary.todo_count}
          analysisId={summary.analysis_id}
        />
      </div>

      {/* Download Section */}
      {conversionId && (
        <OutputDownload
          conversionId={conversionId}
          reportName={summary.report.name}
          completedAt={summary.conversion_timestamp}
          durationMs={summary.duration_ms}
          className="mb-6"
        />
      )}

      {/* Navigation Actions */}
      <div className="flex flex-wrap gap-3 pt-4 border-t">
        <Button variant="outline" asChild>
          <Link to={`/analysis/${summary.analysis_id}`}>
            <FileSearch className="mr-2 h-4 w-4" />
            View Analysis
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to={`/analysis/${summary.analysis_id}`} state={{ reconvert: true }}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Convert Again
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/browser">
            <FolderOpen className="mr-2 h-4 w-4" />
            Back to Browser
          </Link>
        </Button>
      </div>
    </div>
  )
}

export default ConversionSummary
