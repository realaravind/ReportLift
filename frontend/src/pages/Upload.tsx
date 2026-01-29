/**
 * Upload Page - Upload RDL files for conversion
 *
 * Allows users to upload RDL files directly without needing
 * an SSRS server connection.
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, AlertCircle, CheckCircle, Loader2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useUploadRDL } from '@/hooks/useAnalysis'
import { cn } from '@/lib/utils'

export function UploadPage() {
  const navigate = useNavigate()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [customName, setCustomName] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)

  const {
    upload,
    reset,
    isUploading,
    status,
    progress,
    currentStep,
    analysisId,
    error,
  } = useUploadRDL()

  const handleFileSelect = useCallback((file: File) => {
    if (file.name.toLowerCase().endsWith('.rdl')) {
      setSelectedFile(file)
      setCustomName(file.name.replace(/\.rdl$/i, ''))
      reset()
    }
  }, [reset])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  const handleUpload = useCallback(() => {
    if (selectedFile) {
      upload({ file: selectedFile, reportName: customName || undefined })
    }
  }, [selectedFile, customName, upload])

  const handleClear = useCallback(() => {
    setSelectedFile(null)
    setCustomName('')
    reset()
  }, [reset])

  const handleViewAnalysis = useCallback(() => {
    if (analysisId) {
      navigate(`/analysis/${analysisId}`)
    }
  }, [navigate, analysisId])

  const isComplete = status === 'completed'
  const isFailed = status === 'failed'

  return (
    <div className="container max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload RDL File
          </CardTitle>
          <CardDescription>
            Upload an SSRS report definition file (.rdl) to analyze and convert to Power BI
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Drop zone */}
          <div
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center transition-colors',
              isDragOver && 'border-primary bg-primary/5',
              selectedFile && !isDragOver && 'border-green-500 bg-green-50',
              !selectedFile && !isDragOver && 'border-muted-foreground/25 hover:border-muted-foreground/50'
            )}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            {selectedFile ? (
              <div className="flex flex-col items-center gap-3">
                <FileText className="h-12 w-12 text-green-600" />
                <div>
                  <p className="font-medium">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={handleClear} disabled={isUploading}>
                  <X className="h-4 w-4 mr-1" />
                  Remove
                </Button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload className="h-12 w-12 text-muted-foreground" />
                <div>
                  <p className="font-medium">Drop your RDL file here</p>
                  <p className="text-sm text-muted-foreground">or click to browse</p>
                </div>
                <label>
                  <Input
                    type="file"
                    accept=".rdl"
                    className="hidden"
                    onChange={handleInputChange}
                  />
                  <Button variant="outline" asChild>
                    <span>Browse Files</span>
                  </Button>
                </label>
              </div>
            )}
          </div>

          {/* Custom report name */}
          {selectedFile && !isComplete && (
            <div className="space-y-2">
              <Label htmlFor="report-name">Report Name (optional)</Label>
              <Input
                id="report-name"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Enter a custom name for the report"
                disabled={isUploading}
              />
            </div>
          )}

          {/* Progress */}
          {isUploading && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {currentStep || 'Processing...'}
                </span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} />
            </div>
          )}

          {/* Error */}
          {isFailed && error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Upload Failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Success */}
          {isComplete && (
            <Alert className="border-green-500 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-800">Analysis Complete</AlertTitle>
              <AlertDescription className="text-green-700">
                Your report has been analyzed and is ready for conversion.
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            {isComplete ? (
              <>
                <Button variant="outline" onClick={handleClear}>
                  Upload Another
                </Button>
                <Button onClick={handleViewAnalysis}>
                  View Analysis Results
                </Button>
              </>
            ) : (
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    Upload & Analyze
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Help text */}
      <div className="mt-6 text-sm text-muted-foreground space-y-2">
        <p>
          <strong>What is an RDL file?</strong> RDL (Report Definition Language) is the file
          format used by SQL Server Reporting Services (SSRS) to define report layouts and queries.
        </p>
        <p>
          <strong>How to get your RDL file:</strong> In SSRS, right-click on a report and select
          &quot;Download&quot; or export the report definition from Report Builder.
        </p>
      </div>
    </div>
  )
}

export default UploadPage
