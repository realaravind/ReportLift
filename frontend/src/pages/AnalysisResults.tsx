/**
 * Analysis Results Page
 *
 * Displays detailed analysis breakdown for a report
 */

import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAnalysisById, useAnalyzeReport } from '@/hooks/useAnalysis'
import { useTodosForAnalysis, hasTodos } from '@/hooks/useTodos'
import { AnalysisSummaryCard } from '@/components/analysis/AnalysisSummaryCard'
import { ScoreBreakdown } from '@/components/analysis/ScoreBreakdown'
import { FeaturesTabs } from '@/components/analysis/FeaturesTabs'
import { TodoSection } from '@/components/analysis/TodoSection'
import { ConvertButton, ReAnalyzeButton } from '@/components/analysis/ConvertButton'
import type { AnalysisResult, TodoItem } from '@/types/analysis'

function AnalysisSkeleton() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="h-8 w-48 bg-muted rounded" />
      <div className="h-32 bg-muted rounded-lg" />
      <div className="h-64 bg-muted rounded-lg" />
      <div className="h-48 bg-muted rounded-lg" />
    </div>
  )
}

function AnalysisError({ error, onBack }: { error: string; onBack: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-6">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold mb-2">Unable to Load Analysis</h2>
        <p className="text-muted-foreground mb-4">{error}</p>
        <Button onClick={onBack} variant="outline">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Go Back
        </Button>
      </div>
    </div>
  )
}

function NoAnalysis({
  onBack,
  onAnalyze,
}: {
  onBack: () => void
  onAnalyze: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-6">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold mb-2">No Analysis Found</h2>
        <p className="text-muted-foreground mb-4">
          This report hasn't been analyzed yet. Would you like to analyze it now?
        </p>
        <div className="flex gap-4 justify-center">
          <Button onClick={onBack} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
          <Button onClick={onAnalyze}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Analyze Report
          </Button>
        </div>
      </div>
    </div>
  )
}

export function AnalysisResults() {
  const navigate = useNavigate()
  const location = useLocation()
  const { analysisId } = useParams<{ analysisId: string }>()

  // Get report path from location state (passed when navigating)
  const reportPath = location.state?.reportPath as string | undefined
  const reportName = location.state?.reportName as string | undefined

  // Fetch analysis data
  const {
    data: analysis,
    isLoading,
    error: analysisError,
  } = useAnalysisById(analysisId ? parseInt(analysisId) : null)

  // Fetch todos for this analysis
  const { data: todosResponse } = useTodosForAnalysis(
    analysis?.id ?? null,
    true,
    !!analysis?.id
  )

  // Re-analyze mutation
  const {
    analyze,
    isAnalyzing,
    progress: reanalyzeProgress,
    currentStep: reanalyzeStep,
  } = useAnalyzeReport()

  const handleBack = () => {
    navigate(-1)
  }

  const handleReanalyze = () => {
    if (analysis) {
      analyze({
        report_path: analysis.report_path,
        report_name: analysis.report_name,
        force: true,
      })
    } else if (reportPath && reportName) {
      analyze({
        report_path: reportPath,
        report_name: reportName,
        force: true,
      })
    }
  }

  // Loading state
  if (isLoading) {
    return <AnalysisSkeleton />
  }

  // Error state
  if (analysisError) {
    return (
      <AnalysisError
        error="Failed to load analysis details. Please try again."
        onBack={handleBack}
      />
    )
  }

  // No analysis found
  if (!analysis) {
    return (
      <NoAnalysis
        onBack={handleBack}
        onAnalyze={handleReanalyze}
      />
    )
  }

  // Build todos list from response
  const todos: TodoItem[] = hasTodos(todosResponse) ? todosResponse.items : []
  const unresolvedCount = todos.filter((t) => !t.is_resolved).length

  // Convert analysis to AnalysisResult type
  const analysisResult: AnalysisResult = {
    id: analysis.id,
    report_path: analysis.report_path,
    report_name: analysis.report_name,
    analyzed_at: analysis.analyzed_at,
    classification: analysis.classification as AnalysisResult['classification'],
    score: analysis.score,
    status: analysis.status as AnalysisResult['status'],
    features: analysis.features as AnalysisResult['features'],
    penalties: analysis.penalties as AnalysisResult['penalties'],
    todo_items: todos,
    analysis_duration_ms: analysis.analysis_duration_ms,
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header with back button and actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-4">
            <Button onClick={handleBack} variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Analysis Results</h1>
              <p className="text-sm text-muted-foreground">
                {analysis.report_name}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <ReAnalyzeButton
              onReanalyze={handleReanalyze}
              isLoading={isAnalyzing}
            />
            <ConvertButton
              status={analysisResult.status}
              reportPath={analysis.report_path}
              todoCount={unresolvedCount}
              disabled={isAnalyzing}
            />
          </div>
        </div>

        {/* Re-analysis progress */}
        {isAnalyzing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-4">
              <RefreshCw className="h-5 w-5 animate-spin text-blue-600" />
              <div className="flex-1">
                <p className="font-medium">Re-analyzing report...</p>
                <p className="text-sm text-muted-foreground">
                  {reanalyzeStep || 'Starting analysis'}
                </p>
              </div>
              <div className="text-right">
                <span className="text-lg font-bold text-blue-600">
                  {reanalyzeProgress}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Summary Card */}
        <AnalysisSummaryCard analysis={analysisResult} />

        {/* Score Breakdown */}
        <ScoreBreakdown
          breakdown={analysisResult.penalties}
          status={analysisResult.status}
          score={analysisResult.score}
        />

        {/* Features Tabs */}
        <FeaturesTabs features={analysisResult.features} />

        {/* TODO Section */}
        <TodoSection todos={todos} analysisId={analysis.id} />
      </div>
    </div>
  )
}
