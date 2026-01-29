/**
 * Audit Log Table Component
 * Displays audit logs in a table with expandable rows for details
 */

import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertCircle, Loader2 } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { AuditLogDetail } from './AuditLogDetail'
import type { AuditLog, AuditLogPagination, EventType, AuditStatus } from '@/types/audit'
import { formatTimestamp, EVENT_TYPE_CONFIG } from '@/types/audit'

interface AuditLogTableProps {
  logs: AuditLog[]
  isLoading: boolean
  error: Error | null
  pagination: AuditLogPagination
  totalCount: number
  onPaginationChange: (pagination: AuditLogPagination) => void
}

// Badge variant mapping for event types
function getEventTypeBadgeVariant(
  eventType: EventType
): 'default' | 'secondary' | 'outline' | 'destructive' {
  const config = EVENT_TYPE_CONFIG[eventType]
  return config?.variant || 'default'
}

// Badge variant for status
function getStatusBadgeVariant(status: AuditStatus): 'success' | 'destructive' {
  return status === 'SUCCESS' ? 'success' : 'destructive'
}

export function AuditLogTable({
  logs,
  isLoading,
  error,
  pagination,
  totalCount,
  onPaginationChange,
}: AuditLogTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  const totalPages = Math.ceil(totalCount / pagination.pageSize)

  // Loading state
  if (isLoading && logs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading audit logs...</span>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load audit logs: {error.message}
        </AlertDescription>
      </Alert>
    )
  }

  // Empty state
  if (logs.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No audit logs found matching your filters.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]"></TableHead>
              <TableHead className="w-[180px]">Timestamp</TableHead>
              <TableHead className="w-[120px]">User</TableHead>
              <TableHead className="w-[130px]">Event Type</TableHead>
              <TableHead>Action</TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.map((log) => {
              const isExpanded = expandedRows.has(log.id)
              return (
                <Collapsible key={log.id} open={isExpanded} onOpenChange={() => toggleRow(log.id)}>
                  <TableRow className={isExpanded ? 'bg-muted/50' : ''}>
                    <TableCell>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </Button>
                      </CollapsibleTrigger>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {formatTimestamp(log.timestamp)}
                    </TableCell>
                    <TableCell>{log.username || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={getEventTypeBadgeVariant(log.event_type)}>
                        {EVENT_TYPE_CONFIG[log.event_type]?.label || log.event_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate" title={log.action}>
                      {log.action}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(log.status)}>
                        {log.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                  <CollapsibleContent asChild>
                    <TableRow>
                      <TableCell colSpan={6} className="bg-muted/30 p-0">
                        <AuditLogDetail log={log} />
                      </TableCell>
                    </TableRow>
                  </CollapsibleContent>
                </Collapsible>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      <div className="flex items-center justify-between px-2">
        <div className="text-sm text-muted-foreground">
          Showing {(pagination.page - 1) * pagination.pageSize + 1} to{' '}
          {Math.min(pagination.page * pagination.pageSize, totalCount)} of {totalCount} logs
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPaginationChange({ ...pagination, page: pagination.page - 1 })}
            disabled={pagination.page <= 1 || isLoading}
          >
            Previous
          </Button>
          <div className="text-sm">
            Page {pagination.page} of {totalPages}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPaginationChange({ ...pagination, page: pagination.page + 1 })}
            disabled={pagination.page >= totalPages || isLoading}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
