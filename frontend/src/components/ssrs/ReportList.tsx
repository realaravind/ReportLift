/**
 * ReportList Component - Displays reports in a selected SSRS folder
 * Features: sorting, filtering, virtual scrolling, empty/error states
 */

import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import {
  FileText,
  Loader2,
  AlertCircle,
  RefreshCw,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  FolderOpen,
  Calendar,
  HardDrive,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import {
  useReportList,
  getReportsErrorMessage,
  ReportItem,
} from '@/hooks/useReportList'

interface ReportListProps {
  folderPath: string | null
  onReportSelect?: (report: ReportItem) => void
  onReportDoubleClick?: (report: ReportItem) => void
  selectedReportId?: string | null
  className?: string
}

type SortField = 'name' | 'modified_date' | 'size_bytes'
type SortDirection = 'asc' | 'desc'

// Virtual scrolling constants
const ROW_HEIGHT = 64 // Height of each row in pixels
const OVERSCAN = 5 // Number of extra rows to render above/below viewport

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

/**
 * Format date for display
 */
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function ReportList({
  folderPath,
  onReportSelect,
  onReportDoubleClick,
  selectedReportId: externalSelectedId,
  className,
}: ReportListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [internalSelectedId, setInternalSelectedId] = useState<string | null>(null)

  // Use external selected ID if provided, otherwise use internal state
  const selectedReportId = externalSelectedId ?? internalSelectedId

  // Virtual scrolling state
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(0)

  // Fetch reports for the selected folder
  const { data, isLoading, error, refetch, isFetching } = useReportList(
    folderPath || '',
    !!folderPath
  )

  // Reset selection when folder changes
  useEffect(() => {
    setInternalSelectedId(null)
    setSearchQuery('')
  }, [folderPath])

  // Track container height for virtual scrolling
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height)
      }
    })

    resizeObserver.observe(container)
    return () => resizeObserver.disconnect()
  }, [])

  // Handle scroll for virtual scrolling
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop)
  }, [])

  // Filter and sort reports
  const processedReports = useMemo(() => {
    if (!data?.data) return []

    let reports = [...data.data]

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      reports = reports.filter(
        (r) =>
          r.name.toLowerCase().includes(query) ||
          r.description?.toLowerCase().includes(query)
      )
    }

    // Sort
    reports.sort((a, b) => {
      let comparison = 0
      switch (sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'modified_date': {
          const dateA = a.modified_date ? new Date(a.modified_date).getTime() : 0
          const dateB = b.modified_date ? new Date(b.modified_date).getTime() : 0
          comparison = dateA - dateB
          break
        }
        case 'size_bytes':
          comparison = a.size_bytes - b.size_bytes
          break
      }
      return sortDirection === 'asc' ? comparison : -comparison
    })

    return reports
  }, [data?.data, searchQuery, sortField, sortDirection])

  // Virtual scrolling calculations
  const { visibleReports, startIndex, totalHeight, offsetY } = useMemo(() => {
    const totalHeight = processedReports.length * ROW_HEIGHT
    const startIndex = Math.max(
      0,
      Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN
    )
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT) + 2 * OVERSCAN
    const endIndex = Math.min(
      processedReports.length,
      startIndex + visibleCount
    )
    const visibleReports = processedReports.slice(startIndex, endIndex)
    const offsetY = startIndex * ROW_HEIGHT

    return { visibleReports, startIndex, totalHeight, offsetY }
  }, [processedReports, scrollTop, containerHeight])

  // Handle sort toggle
  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))
        return prev
      }
      setSortDirection('asc')
      return field
    })
  }, [])

  // Handle report selection
  const handleReportClick = useCallback(
    (report: ReportItem) => {
      setInternalSelectedId(report.id)
      onReportSelect?.(report)
    },
    [onReportSelect]
  )

  // Handle double-click (select + analyze)
  const handleReportDoubleClick = useCallback(
    (report: ReportItem) => {
      setInternalSelectedId(report.id)
      onReportSelect?.(report)
      onReportDoubleClick?.(report)
    },
    [onReportSelect, onReportDoubleClick]
  )

  // Sort indicator component
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/50" />
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-3.5 w-3.5" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5" />
    )
  }

  // No folder selected state
  if (!folderPath) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center h-full py-16 px-4 text-center',
          className
        )}
      >
        <FolderOpen className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-2">No Folder Selected</h3>
        <p className="text-sm text-muted-foreground max-w-[280px]">
          Select a folder from the sidebar to view its reports.
        </p>
      </div>
    )
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center h-full py-16',
          className
        )}
      >
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground">Loading reports...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center h-full py-16 px-4 text-center',
          className
        )}
      >
        <AlertCircle className="h-10 w-10 text-destructive mb-4" />
        <h3 className="text-lg font-medium mb-2">Unable to Load Reports</h3>
        <p className="text-sm text-muted-foreground mb-4 max-w-[320px]">
          {getReportsErrorMessage(error)}
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="gap-2"
        >
          <RefreshCw
            className={cn('h-4 w-4', isFetching && 'animate-spin')}
          />
          Retry
        </Button>
      </div>
    )
  }

  // Empty state
  if (!processedReports.length) {
    if (searchQuery && data?.data?.length) {
      // No search results
      return (
        <div className={cn('flex flex-col h-full', className)}>
          <SearchHeader
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            totalCount={data.data.length}
            filteredCount={0}
            isFetching={isFetching}
            onRefresh={() => refetch()}
          />
          <div className="flex-1 flex flex-col items-center justify-center py-16 px-4 text-center">
            <Search className="h-10 w-10 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-medium mb-2">No Matching Reports</h3>
            <p className="text-sm text-muted-foreground mb-4">
              No reports match "{searchQuery}"
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSearchQuery('')}
            >
              Clear Search
            </Button>
          </div>
        </div>
      )
    }

    // Truly empty folder
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center h-full py-16 px-4 text-center',
          className
        )}
      >
        <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-medium mb-2">No Reports Found</h3>
        <p className="text-sm text-muted-foreground max-w-[280px]">
          This folder doesn't contain any reports, or you may not have
          permission to view them.
        </p>
      </div>
    )
  }

  // Reports table with virtual scrolling
  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Search and toolbar */}
      <SearchHeader
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        totalCount={data?.data?.length || 0}
        filteredCount={processedReports.length}
        isFetching={isFetching}
        onRefresh={() => refetch()}
      />

      {/* Table header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30 text-xs font-medium text-muted-foreground">
        <button
          className="flex items-center gap-1.5 flex-1 min-w-0 hover:text-foreground transition-colors"
          onClick={() => handleSort('name')}
        >
          <FileText className="h-3.5 w-3.5 shrink-0" />
          <span>Name</span>
          <SortIndicator field="name" />
        </button>
        <button
          className="flex items-center gap-1.5 w-[120px] shrink-0 hover:text-foreground transition-colors"
          onClick={() => handleSort('modified_date')}
        >
          <Calendar className="h-3.5 w-3.5 shrink-0" />
          <span>Modified</span>
          <SortIndicator field="modified_date" />
        </button>
        <button
          className="flex items-center gap-1.5 w-[80px] shrink-0 hover:text-foreground transition-colors"
          onClick={() => handleSort('size_bytes')}
        >
          <HardDrive className="h-3.5 w-3.5 shrink-0" />
          <span>Size</span>
          <SortIndicator field="size_bytes" />
        </button>
      </div>

      {/* Virtual scrolling container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto"
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div
            style={{
              position: 'absolute',
              top: offsetY,
              left: 0,
              right: 0,
            }}
          >
            {visibleReports.map((report, index) => (
              <ReportRow
                key={report.id}
                report={report}
                isSelected={report.id === selectedReportId}
                onClick={() => handleReportClick(report)}
                onDoubleClick={() => handleReportDoubleClick(report)}
                index={startIndex + index}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Search header component
interface SearchHeaderProps {
  searchQuery: string
  setSearchQuery: (query: string) => void
  totalCount: number
  filteredCount: number
  isFetching: boolean
  onRefresh: () => void
}

function SearchHeader({
  searchQuery,
  setSearchQuery,
  totalCount,
  filteredCount,
  isFetching,
  onRefresh,
}: SearchHeaderProps) {
  return (
    <div className="flex items-center gap-3 p-4 border-b">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search reports..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 h-9"
        />
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground shrink-0">
        <span>
          {filteredCount === totalCount
            ? `${totalCount} reports`
            : `${filteredCount} of ${totalCount}`}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onRefresh}
          disabled={isFetching}
        >
          <RefreshCw
            className={cn('h-4 w-4', isFetching && 'animate-spin')}
          />
        </Button>
      </div>
    </div>
  )
}

// Individual report row component
interface ReportRowProps {
  report: ReportItem
  isSelected: boolean
  onClick: () => void
  onDoubleClick?: () => void
  index: number
}

function ReportRow({ report, isSelected, onClick, onDoubleClick, index }: ReportRowProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 cursor-pointer transition-colors',
        'hover:bg-muted/50',
        isSelected && 'bg-primary/10 hover:bg-primary/15',
        index % 2 === 0 ? 'bg-background' : 'bg-muted/20'
      )}
      style={{ height: ROW_HEIGHT }}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
    >
      {/* Name and description */}
      <div className="flex-1 min-w-0 py-2">
        <div className="flex items-center gap-2">
          <FileText
            className={cn(
              'h-4 w-4 shrink-0',
              isSelected ? 'text-primary' : 'text-muted-foreground'
            )}
          />
          <span
            className={cn(
              'font-medium truncate',
              isSelected && 'text-primary'
            )}
          >
            {report.name}
          </span>
        </div>
        {report.description && (
          <p className="text-xs text-muted-foreground truncate mt-0.5 ml-6">
            {report.description}
          </p>
        )}
      </div>

      {/* Modified date */}
      <div className="w-[120px] shrink-0 text-sm text-muted-foreground">
        {formatDate(report.modified_date)}
      </div>

      {/* Size */}
      <div className="w-[80px] shrink-0 text-sm text-muted-foreground text-right">
        {formatFileSize(report.size_bytes)}
      </div>
    </div>
  )
}
