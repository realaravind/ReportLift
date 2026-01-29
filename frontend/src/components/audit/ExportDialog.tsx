/**
 * Export Dialog Component
 * Allows users to export audit logs in various formats
 */

import { useState } from 'react'
import { Download, FileText, FileJson, FileSpreadsheet, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useAuditExport, useAuditExportEstimate } from '@/hooks/useAuditLogs'
import type { AuditLogFilter, DateRangePreset } from '@/types/audit'
import { EventType, getDateFromPreset } from '@/types/audit'

export type ExportFormat = 'csv' | 'json' | 'pdf'

interface ExportDialogProps {
  open: boolean
  onClose: () => void
  currentFilters?: AuditLogFilter
}

export function ExportDialog({ open, onClose }: ExportDialogProps) {
  // Export options state
  const [datePreset, setDatePreset] = useState<DateRangePreset>('last7d')
  const [format, setFormat] = useState<ExportFormat>('csv')
  const [eventType, setEventType] = useState<EventType | ''>('')

  // Calculate date range from preset
  const dateFrom = getDateFromPreset(datePreset)
  const dateTo = new Date().toISOString()

  // Get export estimate
  const { data: estimate, isLoading: isEstimating } = useAuditExportEstimate(
    dateFrom,
    dateTo,
    eventType || undefined
  )

  // Export mutation
  const { mutate: exportLogs, isPending: isExporting } = useAuditExport()

  const handleExport = () => {
    exportLogs(
      {
        dateFrom,
        dateTo,
        eventTypes: eventType ? [eventType] : undefined,
        format,
      },
      {
        onSuccess: () => {
          onClose()
        },
      }
    )
  }

  const estimatedRows = estimate?.data?.estimated_rows ?? 0
  const requiresAsync = estimate?.data?.requires_async ?? false

  // Format icons
  const formatIcons: Record<ExportFormat, React.ReactNode> = {
    csv: <FileSpreadsheet className="h-4 w-4" />,
    json: <FileJson className="h-4 w-4" />,
    pdf: <FileText className="h-4 w-4" />,
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            Export Audit Logs
          </SheetTitle>
          <SheetDescription>
            Download audit logs for compliance reporting or analysis.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {/* Date Range */}
          <div className="space-y-2">
            <Label htmlFor="dateRange">Date Range</Label>
            <Select
              id="dateRange"
              value={datePreset}
              onChange={(e) => setDatePreset(e.target.value as DateRangePreset)}
            >
              <option value="last24h">Last 24 Hours</option>
              <option value="last7d">Last 7 Days</option>
              <option value="last30d">Last 30 Days</option>
            </Select>
          </div>

          {/* Event Type Filter */}
          <div className="space-y-2">
            <Label htmlFor="eventType">Event Type (optional)</Label>
            <Select
              id="eventType"
              value={eventType}
              onChange={(e) => setEventType(e.target.value as EventType | '')}
            >
              <option value="">All Events</option>
              {Object.values(EventType).map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </Select>
          </div>

          {/* Export Format */}
          <div className="space-y-2">
            <Label>Export Format</Label>
            <div className="grid grid-cols-3 gap-2">
              {(['csv', 'json', 'pdf'] as ExportFormat[]).map((fmt) => (
                <Button
                  key={fmt}
                  type="button"
                  variant={format === fmt ? 'default' : 'outline'}
                  className="flex items-center gap-2"
                  onClick={() => setFormat(fmt)}
                >
                  {formatIcons[fmt]}
                  {fmt.toUpperCase()}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {format === 'csv' && 'CSV format for spreadsheet applications'}
              {format === 'json' && 'JSON format for data analysis tools'}
              {format === 'pdf' && 'PDF report for documentation'}
            </p>
          </div>

          {/* Export Estimate */}
          <div className="rounded-md bg-muted p-4 space-y-2">
            <div className="text-sm font-medium">Export Preview</div>
            {isEstimating ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Calculating...
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">
                <div>Estimated rows: {estimatedRows.toLocaleString()}</div>
                {format === 'csv' && (
                  <div>
                    Estimated size:{' '}
                    {Math.round((estimate?.data?.estimated_csv_size_bytes ?? 0) / 1024)} KB
                  </div>
                )}
                {format === 'json' && (
                  <div>
                    Estimated size:{' '}
                    {Math.round((estimate?.data?.estimated_json_size_bytes ?? 0) / 1024)} KB
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Large Export Warning */}
          {requiresAsync && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This is a large export ({estimatedRows.toLocaleString()} rows). The export may take
                some time to generate.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={onClose} disabled={isExporting}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={isExporting || isEstimating}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Download {format.toUpperCase()}
              </>
            )}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
