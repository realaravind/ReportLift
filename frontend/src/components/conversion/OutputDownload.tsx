/**
 * OutputDownload - Component for downloading conversion outputs
 *
 * Displays a list of available files with download buttons, size info,
 * and handles download progress and errors.
 */

import { Download, FileText, Database, Archive, FileJson, AlertCircle, Loader2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  useConversionOutputs,
  useDownloadFile,
  FILE_TYPE_INFO,
  formatDuration,
} from '@/hooks/useConversion'

interface OutputDownloadProps {
  conversionId: string
  reportName: string
  completedAt?: string | null
  durationMs?: number | null
  className?: string
}

// Icon mapping for file types
const FileIcons: Record<string, React.ElementType> = {
  pbix: FileText,
  sql: Database,
  'sql-zip': Archive,
  analysis: FileJson,
}

export function OutputDownload({
  conversionId,
  reportName,
  completedAt,
  durationMs,
  className,
}: OutputDownloadProps) {
  const { data: outputs, isLoading, error } = useConversionOutputs(conversionId)
  const {
    downloadFile,
    isDownloading,
    downloadError,
    downloadProgress,
    reset: resetDownload,
  } = useDownloadFile()

  // Handle download click
  const handleDownload = (fileType: string, filename: string) => {
    downloadFile(conversionId, fileType, filename)
  }

  // Format the generated date
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null
    const date = new Date(dateStr)
    return date.toLocaleString()
  }

  // Get icon component for file type
  const getFileIcon = (fileType: string) => {
    const IconComponent = FileIcons[fileType] || FileText
    return <IconComponent className="h-5 w-5" />
  }

  // Loading state
  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading download options...
          </div>
        </CardContent>
      </Card>
    )
  }

  // Error state
  if (error) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error loading files</AlertTitle>
            <AlertDescription>
              {error.response?.data?.detail?.message || 'Failed to load download options'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  // Incomplete conversion
  if (outputs && outputs.status !== 'completed') {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Download Outputs</CardTitle>
          <CardDescription>Files generated from the conversion</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Conversion Incomplete</AlertTitle>
            <AlertDescription>
              {outputs.message || 'No files are available for download.'}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  // No outputs or empty files list
  if (!outputs || outputs.files.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Download Outputs</CardTitle>
          <CardDescription>Files generated from the conversion</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>No Files Available</AlertTitle>
            <AlertDescription>
              No output files were generated for this conversion.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          Download Outputs
        </CardTitle>
        <CardDescription>
          {reportName} - Generated {formatDate(outputs.generated_at || completedAt || null)}
          {durationMs && ` (${formatDuration(durationMs)})`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Download error alert */}
        {downloadError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Download failed</AlertTitle>
            <AlertDescription className="flex items-center justify-between">
              {downloadError}
              <Button variant="outline" size="sm" onClick={resetDownload}>
                Dismiss
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Download progress */}
        {isDownloading && downloadProgress !== null && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>Downloading...</span>
              <span>{downloadProgress}%</span>
            </div>
            <Progress value={downloadProgress} />
          </div>
        )}

        {/* Files list */}
        <div className="border rounded-lg divide-y">
          <TooltipProvider>
            {outputs.files.map((file) => {
              const fileInfo = FILE_TYPE_INFO[file.type] || {
                label: file.type.toUpperCase(),
                description: 'Download file',
                icon: 'file',
              }

              return (
                <div
                  key={file.type}
                  className="flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-muted rounded-lg">
                      {getFileIcon(file.type)}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{fileInfo.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {file.name} ({file.size_display})
                      </div>
                    </div>
                  </div>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(file.type, file.name)}
                        disabled={isDownloading || !file.available}
                      >
                        {isDownloading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : downloadProgress === 100 ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                        <span className="ml-2">Download</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{fileInfo.description}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              )
            })}
          </TooltipProvider>
        </div>

        {/* Download all hint */}
        {outputs.files.length > 2 && (
          <p className="text-xs text-muted-foreground text-center">
            Tip: Use &quot;All Scripts (ZIP)&quot; to download all SQL files at once
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export default OutputDownload
