/**
 * ConversionPanel - Main conversion UI component that integrates all conversion functionality
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useInitiateConversion,
  useSnowflakeStatus,
  useConversionResult,
} from '@/hooks/useConversion'
import { ConversionProgress } from './ConversionProgress'
import { SnowflakeWarningDialog } from './SnowflakeWarningDialog'
import { CancelConversionDialog } from './CancelConversionDialog'
import { OutputDownload } from './OutputDownload'

interface ConversionPanelProps {
  analysisId: number
  reportName: string
  className?: string
}

export function ConversionPanel({
  analysisId,
  reportName,
  className,
}: ConversionPanelProps) {
  const navigate = useNavigate()
  const [showSnowflakeWarning, setShowSnowflakeWarning] = useState(false)
  const [showCancelDialog, setShowCancelDialog] = useState(false)

  // Hooks for conversion
  const { data: snowflakeStatus, isLoading: isLoadingSnowflake } = useSnowflakeStatus()
  const {
    initiate,
    cancel,
    reset,
    isConverting,
    isCancelling,
    status,
    progress,
    currentStep,
    conversionId,
    snowflakeConfigured,
    error,
    conversionResult,
  } = useInitiateConversion()

  // Get conversion result when completed
  const { data: result } = useConversionResult(
    status === 'completed' ? conversionId : null
  )

  // Navigation guard - warn user before leaving during conversion
  useEffect(() => {
    if (!isConverting) return

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = 'Conversion is in progress. Are you sure you want to leave?'
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isConverting])

  // Handle starting conversion
  const handleStartConversion = () => {
    // Check if Snowflake is configured
    if (snowflakeStatus && !snowflakeStatus.is_configured) {
      setShowSnowflakeWarning(true)
      return
    }

    // Start conversion
    initiate({ analysisId })
  }

  // Handle proceeding without Snowflake
  const handleProceedWithoutSnowflake = () => {
    setShowSnowflakeWarning(false)
    initiate({ analysisId, force: true })
  }

  // Handle cancel button click
  const handleCancelClick = () => {
    setShowCancelDialog(true)
  }

  // Handle confirmed cancellation
  const handleConfirmCancel = () => {
    setShowCancelDialog(false)
    cancel()
  }

  // Handle view results
  const handleViewResults = () => {
    if (conversionId) {
      navigate(`/conversion/${conversionId}/result`)
    }
  }

  return (
    <div className={className}>
      {/* Conversion Progress or Start Button */}
      {status === 'idle' ? (
        <Card>
          <CardHeader>
            <CardTitle>Convert Report</CardTitle>
            <CardDescription>
              Convert &quot;{reportName}&quot; to Power BI format with Snowflake-compatible SQL
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Snowflake status indicator */}
              {isLoadingSnowflake ? (
                <p className="text-sm text-muted-foreground">Checking Snowflake configuration...</p>
              ) : snowflakeStatus?.is_configured ? (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <Database className="h-4 w-4" />
                  <span>Snowflake configured - Schema: {snowflakeStatus.placeholder_schema}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-yellow-600">
                  <Database className="h-4 w-4" />
                  <span>Snowflake not configured - SQL will use placeholder schema</span>
                </div>
              )}

              <Button onClick={handleStartConversion} disabled={isLoadingSnowflake}>
                <Play className="mr-2 h-4 w-4" />
                Start Conversion
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <ConversionProgress
          status={status}
          progress={progress}
          currentStep={currentStep}
          stepsCompleted={conversionResult?.steps_completed ?? 0}
          error={error}
          snowflakeConfigured={snowflakeConfigured}
          onCancel={handleCancelClick}
          isCancelling={isCancelling}
          onViewResult={handleViewResults}
        />
      )}

      {/* Conversion Results */}
      {status === 'completed' && conversionId && (
        <div className="mt-4 space-y-4">
          <OutputDownload
            conversionId={conversionId}
            reportName={reportName}
            completedAt={result?.completed_at}
            durationMs={result?.duration_ms}
          />

          {/* Actions */}
          <div className="flex gap-2">
            <Button onClick={() => reset()}>
              Convert Another Report
            </Button>
          </div>
        </div>
      )}

      {/* Snowflake Warning Dialog */}
      <SnowflakeWarningDialog
        open={showSnowflakeWarning}
        onOpenChange={setShowSnowflakeWarning}
        onProceed={handleProceedWithoutSnowflake}
        placeholderSchema={snowflakeStatus?.placeholder_schema ?? 'PLACEHOLDER_SCHEMA'}
      />

      {/* Cancel Confirmation Dialog */}
      <CancelConversionDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        onConfirm={handleConfirmCancel}
        currentStep={currentStep}
        progress={progress}
      />
    </div>
  )
}
