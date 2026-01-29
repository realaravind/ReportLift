/**
 * Audit Logs Page
 * Displays audit logs with filtering, pagination, and live mode
 */

import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileText, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AuditLogTable } from '@/components/audit/AuditLogTable'
import { AuditLogFilters } from '@/components/audit/AuditLogFilters'
import { LiveModeToggle } from '@/components/audit/LiveModeToggle'
import { ExportDialog } from '@/components/audit/ExportDialog'
import { useAuditLogs, AUDIT_LOGS_KEY } from '@/hooks/useAuditLogs'
import type { AuditLogFilter, AuditLogPagination } from '@/types/audit'
import { getDefaultDateFrom } from '@/types/audit'

export function AuditLogs() {
  const queryClient = useQueryClient()

  // Filter state - default to last 24 hours
  const [filters, setFilters] = useState<AuditLogFilter>({
    dateFrom: getDefaultDateFrom(),
    dateTo: new Date().toISOString(),
  })

  // Pagination state
  const [pagination, setPagination] = useState<AuditLogPagination>({
    page: 1,
    pageSize: 50,
  })

  // Live mode state
  const [liveMode, setLiveMode] = useState(false)

  // Export dialog state
  const [exportDialogOpen, setExportDialogOpen] = useState(false)

  // Fetch audit logs
  const { data, isLoading, error, refetch } = useAuditLogs(filters, pagination, liveMode)

  // Handle filter changes - reset to page 1
  const handleFilterChange = useCallback((newFilters: AuditLogFilter) => {
    setFilters(newFilters)
    setPagination((prev) => ({ ...prev, page: 1 }))
  }, [])

  // Handle pagination changes
  const handlePaginationChange = useCallback((newPagination: AuditLogPagination) => {
    setPagination(newPagination)
  }, [])

  // Handle refresh
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: AUDIT_LOGS_KEY })
    refetch()
  }, [queryClient, refetch])

  // Handle live mode toggle
  const handleLiveModeToggle = useCallback((enabled: boolean) => {
    setLiveMode(enabled)
    if (enabled) {
      // When enabling live mode, reset to first page and refresh filters
      setPagination((prev) => ({ ...prev, page: 1 }))
      setFilters((prev) => ({
        ...prev,
        dateFrom: getDefaultDateFrom(),
        dateTo: new Date().toISOString(),
      }))
    }
  }, [])

  return (
    <div className="container mx-auto py-6 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-muted-foreground" />
          <div>
            <h1 className="text-2xl font-bold">Audit Logs</h1>
            <p className="text-sm text-muted-foreground">
              View and search system activity logs
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExportDialogOpen(true)}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
          <LiveModeToggle enabled={liveMode} onToggle={handleLiveModeToggle} />
        </div>
      </div>

      {/* Live mode indicator */}
      {liveMode && (
        <div className="mb-4 p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-md flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="text-sm text-green-700 dark:text-green-300">
            Live mode active - refreshing every 5 seconds
          </span>
        </div>
      )}

      {/* Filters */}
      <AuditLogFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        isLoading={isLoading}
        onRefresh={handleRefresh}
      />

      {/* Results count */}
      {data && (
        <div className="text-sm text-muted-foreground mb-4">
          Showing {data.data.logs.length} of {data.data.total} logs
        </div>
      )}

      {/* Table */}
      <AuditLogTable
        logs={data?.data.logs ?? []}
        isLoading={isLoading}
        error={error}
        pagination={pagination}
        totalCount={data?.data.total ?? 0}
        onPaginationChange={handlePaginationChange}
      />

      {/* Export Dialog */}
      <ExportDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        currentFilters={filters}
      />
    </div>
  )
}

export default AuditLogs
