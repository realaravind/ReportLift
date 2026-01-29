/**
 * TemplateUpload - Component for managing Power BI branding templates
 *
 * Allows users to upload, view, download, and remove branding templates.
 */

import { useCallback, useRef, useState } from 'react'
import { Upload, Download, Trash2, FileIcon, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { SettingsCard } from './SettingsCard'
import {
  useTemplateStatus,
  useUploadTemplate,
  useDeleteTemplate,
  useDownloadTemplate,
  validateTemplateFile,
  TEMPLATE_MAX_SIZE_MB,
} from '@/hooks/useTemplate'

export function TemplateUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [showReplaceDialog, setShowReplaceDialog] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [pendingFile, setPendingFile] = useState<File | null>(null)

  const { data: templateStatus, isLoading } = useTemplateStatus()
  const uploadMutation = useUploadTemplate()
  const deleteMutation = useDeleteTemplate()
  const downloadMutation = useDownloadTemplate()

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file
    const validation = validateTemplateFile(file)
    if (!validation.valid) {
      setValidationError(validation.error || 'Invalid file')
      return
    }

    setValidationError(null)

    // Check if we need to confirm replacement
    if (templateStatus?.is_configured) {
      setPendingFile(file)
      setShowReplaceDialog(true)
    } else {
      // No existing template, upload directly
      uploadMutation.mutate({ file })
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [templateStatus?.is_configured, uploadMutation])

  const handleConfirmReplace = useCallback(() => {
    if (pendingFile) {
      uploadMutation.mutate({ file: pendingFile, replaceExisting: true })
    }
    setPendingFile(null)
    setShowReplaceDialog(false)
  }, [pendingFile, uploadMutation])

  const handleCancelReplace = useCallback(() => {
    setPendingFile(null)
    setShowReplaceDialog(false)
  }, [])

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleDownload = useCallback(() => {
    if (templateStatus?.data) {
      downloadMutation.mutate({
        templateId: templateStatus.data.id,
        filename: templateStatus.data.name,
      })
    }
  }, [templateStatus?.data, downloadMutation])

  const handleDeleteClick = useCallback(() => {
    setShowDeleteDialog(true)
  }, [])

  const handleConfirmDelete = useCallback(() => {
    if (templateStatus?.data) {
      deleteMutation.mutate(templateStatus.data.id)
    }
    setShowDeleteDialog(false)
  }, [templateStatus?.data, deleteMutation])

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <SettingsCard
        title="Branding Template"
        description="Apply corporate branding to converted Power BI reports"
      >
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </SettingsCard>
    )
  }

  const template = templateStatus?.data
  const isConfigured = templateStatus?.is_configured

  return (
    <SettingsCard
      title="Branding Template"
      description="Apply corporate branding to converted Power BI reports"
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pbit"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Validation error */}
      {validationError && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{validationError}</AlertDescription>
        </Alert>
      )}

      {/* Upload error */}
      {uploadMutation.isError && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {(uploadMutation.error as Error)?.message || 'Failed to upload template'}
          </AlertDescription>
        </Alert>
      )}

      {/* Upload success */}
      {uploadMutation.isSuccess && (
        <Alert className="mb-4 border-green-500 text-green-700">
          <CheckCircle2 className="h-4 w-4" />
          <AlertDescription>
            {uploadMutation.data.replaced_existing
              ? 'Branding template replaced successfully'
              : 'Branding template uploaded successfully'}
          </AlertDescription>
        </Alert>
      )}

      {isConfigured && template ? (
        /* Template is configured - show details */
        <div className="space-y-4">
          <div className="flex items-start gap-4 p-4 bg-muted/50 rounded-lg">
            <div className="p-3 bg-primary/10 rounded-lg">
              <FileIcon className="h-8 w-8 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="font-medium truncate">{template.name}</h4>
                <Badge variant="secondary">Active</Badge>
              </div>
              <div className="text-sm text-muted-foreground mt-1 space-y-1">
                <p>Size: {formatFileSize(template.file_size)}</p>
                <p>Uploaded: {formatDate(template.uploaded_at)}</p>
                {template.uploaded_by && <p>By: {template.uploaded_by}</p>}
              </div>

              {/* Theme preview */}
              {template.theme_metadata?.dataColors && (
                <div className="mt-3">
                  <p className="text-xs text-muted-foreground mb-1">Theme Colors:</p>
                  <div className="flex gap-1">
                    {template.theme_metadata.dataColors.map((color, index) => (
                      <div
                        key={index}
                        className="w-6 h-6 rounded border"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={handleUploadClick}
              disabled={uploadMutation.isPending}
            >
              <Upload className="h-4 w-4 mr-2" />
              Replace Template
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={downloadMutation.isPending}
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeleteClick}
              disabled={deleteMutation.isPending}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Remove
            </Button>
          </div>
        </div>
      ) : (
        /* No template configured - show upload prompt */
        <div className="space-y-4">
          <div
            className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
            onClick={handleUploadClick}
          >
            <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm font-medium">Click to upload a branding template</p>
            <p className="text-xs text-muted-foreground mt-1">
              Power BI Template files (.pbit) up to {TEMPLATE_MAX_SIZE_MB}MB
            </p>
          </div>

          <Button
            onClick={handleUploadClick}
            disabled={uploadMutation.isPending}
            className="w-full"
          >
            <Upload className="h-4 w-4 mr-2" />
            {uploadMutation.isPending ? 'Uploading...' : 'Upload Template'}
          </Button>
        </div>
      )}

      {/* Replace confirmation dialog */}
      <AlertDialog open={showReplaceDialog} onOpenChange={setShowReplaceDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace existing template?</AlertDialogTitle>
            <AlertDialogDescription>
              A branding template is already configured. Uploading a new template will replace the
              existing one. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelReplace}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmReplace}>Replace Template</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete confirmation dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove branding template?</AlertDialogTitle>
            <AlertDialogDescription>
              Future report conversions will not have corporate branding applied. You can upload a
              new template at any time.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Remove Template
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SettingsCard>
  )
}

export default TemplateUpload
