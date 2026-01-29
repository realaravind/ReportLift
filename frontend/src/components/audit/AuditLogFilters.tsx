/**
 * Audit Log Filters Component
 * Provides filtering options for audit logs
 */

import { Search, X, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  EventType,
  AuditStatus,
  type AuditLogFilter,
  type DateRangePreset,
  getDateFromPreset,
  EVENT_TYPE_CONFIG,
} from '@/types/audit'

interface AuditLogFiltersProps {
  filters: AuditLogFilter
  onFilterChange: (filters: AuditLogFilter) => void
  isLoading?: boolean
  onRefresh?: () => void
}

export function AuditLogFilters({
  filters,
  onFilterChange,
  isLoading,
  onRefresh,
}: AuditLogFiltersProps) {
  const handleDatePresetChange = (preset: DateRangePreset) => {
    if (preset === 'custom') {
      return // Keep current dates for custom
    }
    onFilterChange({
      ...filters,
      dateFrom: getDateFromPreset(preset),
      dateTo: new Date().toISOString(),
    })
  }

  const handleEventTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '') {
      onFilterChange({ ...filters, eventTypes: undefined })
    } else {
      onFilterChange({ ...filters, eventTypes: [value as EventType] })
    }
  }

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    if (value === '') {
      onFilterChange({ ...filters, status: undefined })
    } else {
      onFilterChange({ ...filters, status: value as AuditStatus })
    }
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, searchText: e.target.value || undefined })
  }

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, username: e.target.value || undefined })
  }

  const clearFilters = () => {
    onFilterChange({
      dateFrom: getDateFromPreset('last24h'),
      dateTo: new Date().toISOString(),
    })
  }

  // Check if any filters are applied beyond the default
  const hasActiveFilters =
    filters.eventTypes?.length ||
    filters.status ||
    filters.searchText ||
    filters.username

  // Count active filter chips
  const activeFilterCount = [
    filters.eventTypes?.length ? 1 : 0,
    filters.status ? 1 : 0,
    filters.searchText ? 1 : 0,
    filters.username ? 1 : 0,
  ].reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-4 mb-6">
      {/* Filter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Date Range Preset */}
        <div className="space-y-1.5">
          <Label htmlFor="dateRange">Time Range</Label>
          <Select id="dateRange" onChange={(e) => handleDatePresetChange(e.target.value as DateRangePreset)}>
            <option value="last24h">Last 24 Hours</option>
            <option value="last7d">Last 7 Days</option>
            <option value="last30d">Last 30 Days</option>
          </Select>
        </div>

        {/* Event Type Filter */}
        <div className="space-y-1.5">
          <Label htmlFor="eventType">Event Type</Label>
          <Select
            id="eventType"
            value={filters.eventTypes?.[0] || ''}
            onChange={handleEventTypeChange}
          >
            <option value="">All Events</option>
            {Object.values(EventType).map((type) => (
              <option key={type} value={type}>
                {EVENT_TYPE_CONFIG[type]?.label || type}
              </option>
            ))}
          </Select>
        </div>

        {/* Status Filter */}
        <div className="space-y-1.5">
          <Label htmlFor="status">Status</Label>
          <Select
            id="status"
            value={filters.status || ''}
            onChange={handleStatusChange}
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILURE">Failure</option>
          </Select>
        </div>

        {/* Username Filter */}
        <div className="space-y-1.5">
          <Label htmlFor="username">User</Label>
          <Input
            id="username"
            placeholder="Filter by username..."
            value={filters.username || ''}
            onChange={handleUsernameChange}
          />
        </div>

        {/* Search Text */}
        <div className="space-y-1.5">
          <Label htmlFor="search">Search</Label>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              id="search"
              placeholder="Search actions..."
              className="pl-9"
              value={filters.searchText || ''}
              onChange={handleSearchChange}
            />
          </div>
        </div>
      </div>

      {/* Active Filters and Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Show active filter chips */}
          {filters.eventTypes?.map((type) => (
            <Badge key={type} variant="secondary" className="gap-1">
              {EVENT_TYPE_CONFIG[type]?.label || type}
              <button
                onClick={() => onFilterChange({ ...filters, eventTypes: undefined })}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {filters.status && (
            <Badge variant="secondary" className="gap-1">
              Status: {filters.status}
              <button
                onClick={() => onFilterChange({ ...filters, status: undefined })}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}
          {filters.username && (
            <Badge variant="secondary" className="gap-1">
              User: {filters.username}
              <button
                onClick={() => onFilterChange({ ...filters, username: undefined })}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}
          {filters.searchText && (
            <Badge variant="secondary" className="gap-1">
              Search: "{filters.searchText}"
              <button
                onClick={() => onFilterChange({ ...filters, searchText: undefined })}
                className="ml-1 hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}

          {/* Clear all filters button */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-7">
              Clear All ({activeFilterCount})
            </Button>
          )}
        </div>

        {/* Refresh button */}
        {onRefresh && (
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
      </div>
    </div>
  )
}
