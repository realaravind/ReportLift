import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from './lib/api'
import { useAppStore } from './store'
import { useUIStore, type SelectedReport } from './store/uiStore'
import { SplitPanel } from './components/layout'
import { ReportList } from './components/ssrs/ReportList'
import { ReportPreview, type PreviousAnalysis } from './components/ssrs/ReportPreview'
import { AnalysisProgress } from './components/analysis/AnalysisProgress'
import type { ReportItem } from './hooks/useReportList'
import { useAnalyzeReport, useReportAnalysis } from './hooks/useAnalysis'

interface HealthResponse {
  status: string
  timestamp: string
  version: string
}

function App() {
  const navigate = useNavigate()
  const { setInitialized } = useAppStore()
  const {
    selectedFolderPath,
    setSelectedFolderPath,
    selectedReport,
    setSelectedReport,
  } = useUIStore()

  // Analysis hooks
  const {
    analyze,
    reset: resetAnalysis,
    isAnalyzing,
    status: analysisStatus,
    progress: analysisProgress,
    currentStep,
    error: analysisError,
    previousAnalysis: mutationPreviousAnalysis,
  } = useAnalyzeReport()

  // Fetch existing analysis for selected report
  const { data: existingAnalysis } = useReportAnalysis(
    selectedReport?.path ?? null,
    !!selectedReport
  )

  // Reset analysis state when report changes
  useEffect(() => {
    resetAnalysis()
  }, [selectedReport?.path, resetAnalysis])

  const handleFolderSelect = useCallback(
    (path: string) => {
      setSelectedFolderPath(path)
      resetAnalysis()
    },
    [setSelectedFolderPath, resetAnalysis]
  )

  const handleReportSelect = useCallback(
    (report: ReportItem) => {
      const selected: SelectedReport = {
        id: report.id,
        name: report.name,
        path: report.path,
        description: report.description,
        modified_date: report.modified_date,
        size_bytes: report.size_bytes,
        created_by: report.created_by,
      }
      setSelectedReport(selected)
    },
    [setSelectedReport]
  )

  const handleReportDoubleClick = useCallback(
    (report: ReportItem) => {
      handleReportSelect(report)
      // Trigger analysis immediately on double-click
      analyze({
        report_path: report.path,
        report_name: report.name,
        force: false,
      })
    },
    [handleReportSelect, analyze]
  )

  const handleAnalyze = useCallback(() => {
    if (!selectedReport) return
    analyze({
      report_path: selectedReport.path,
      report_name: selectedReport.name,
      force: false,
    })
  }, [selectedReport, analyze])

  const handleForceAnalyze = useCallback(() => {
    if (!selectedReport) return
    analyze({
      report_path: selectedReport.path,
      report_name: selectedReport.name,
      force: true,
    })
  }, [selectedReport, analyze])

  const handleViewAnalysis = useCallback(() => {
    if (existingAnalysis?.id) {
      navigate(`/analysis/${existingAnalysis.id}`, {
        state: {
          reportPath: selectedReport?.path,
          reportName: selectedReport?.name,
        },
      })
    }
  }, [navigate, existingAnalysis?.id, selectedReport?.path, selectedReport?.name])

  // Initialize app on first health check
  useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get<HealthResponse>('/api/health')
      setInitialized(true)
      return response.data
    },
  })

  // Build previous analysis object for ReportPreview
  const previousAnalysis: PreviousAnalysis | null = existingAnalysis
    ? {
        score: existingAnalysis.score ?? 0,
        status: (existingAnalysis.status as 'green' | 'yellow' | 'red') ?? 'yellow',
        classification: existingAnalysis.classification ?? 'Unknown',
        analyzed_at: existingAnalysis.analyzed_at,
      }
    : mutationPreviousAnalysis
      ? {
          score: mutationPreviousAnalysis.score ?? 0,
          status: (mutationPreviousAnalysis.status as 'green' | 'yellow' | 'red') ?? 'yellow',
          classification: mutationPreviousAnalysis.classification ?? 'Unknown',
          analyzed_at: mutationPreviousAnalysis.analyzed_at,
        }
      : null

  return (
    <SplitPanel onFolderSelect={handleFolderSelect}>
      <div className="flex flex-col xl:flex-row h-full gap-4 xl:gap-6">
        {/* Report list panel */}
        <div className="xl:w-[420px] shrink-0 rounded-lg border border-border bg-card overflow-hidden flex flex-col min-h-[300px] xl:min-h-0">
          <div className="px-4 py-3 border-b bg-muted/30">
            <h2 className="font-semibold truncate">
              {selectedFolderPath
                ? `Reports in ${selectedFolderPath}`
                : 'Reports'}
            </h2>
          </div>
          <ReportList
            folderPath={selectedFolderPath}
            onReportSelect={handleReportSelect}
            onReportDoubleClick={handleReportDoubleClick}
            selectedReportId={selectedReport?.id}
            className="flex-1"
          />
        </div>

        {/* Report preview and analysis panel */}
        <div className="flex-1 flex flex-col gap-4 min-h-[400px] xl:min-h-0">
          {/* Analysis progress (shown when analyzing) */}
          {analysisStatus !== 'idle' && (
            <AnalysisProgress
              status={analysisStatus}
              progress={analysisProgress}
              currentStep={currentStep}
              error={analysisError}
              onCancel={resetAnalysis}
              onRetry={handleForceAnalyze}
              onViewResults={handleViewAnalysis}
            />
          )}

          {/* Report preview */}
          <ReportPreview
            report={selectedReport}
            previousAnalysis={previousAnalysis}
            onAnalyze={handleAnalyze}
            onViewAnalysis={previousAnalysis ? handleViewAnalysis : undefined}
            isAnalyzing={isAnalyzing}
            className="flex-1"
          />
        </div>
      </div>
    </SplitPanel>
  )
}

export default App
