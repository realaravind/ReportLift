/**
 * TypeScript interfaces for audit log types
 */

// Event types for audit logs
export enum EventType {
  LOGIN = 'LOGIN',
  LOGOUT = 'LOGOUT',
  ANALYSIS = 'ANALYSIS',
  CONVERSION = 'CONVERSION',
  CONFIG_CHANGE = 'CONFIG_CHANGE',
}

// Audit status
export enum AuditStatus {
  SUCCESS = 'SUCCESS',
  FAILURE = 'FAILURE',
}

// Event type display configuration
export interface EventTypeConfig {
  label: string
  color: string
  variant: 'default' | 'secondary' | 'outline' | 'destructive'
}

export const EVENT_TYPE_CONFIG: Record<EventType, EventTypeConfig> = {
  [EventType.LOGIN]: { label: 'Login', color: 'blue', variant: 'default' },
  [EventType.LOGOUT]: { label: 'Logout', color: 'gray', variant: 'secondary' },
  [EventType.ANALYSIS]: { label: 'Analysis', color: 'purple', variant: 'outline' },
  [EventType.CONVERSION]: { label: 'Conversion', color: 'green', variant: 'default' },
  [EventType.CONFIG_CHANGE]: { label: 'Config Change', color: 'orange', variant: 'secondary' },
}

// Single audit log entry
export interface AuditLog {
  id: string
  timestamp: string
  event_type: EventType
  user_id: string | null
  username: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  status: AuditStatus
}

// Filter options for audit logs
export interface AuditLogFilter {
  dateFrom?: string
  dateTo?: string
  eventTypes?: EventType[]
  userId?: string
  username?: string
  status?: AuditStatus
  searchText?: string
}

// Pagination options
export interface AuditLogPagination {
  page: number
  pageSize: number
}

// API response for audit logs list
export interface AuditLogListResponse {
  data: {
    logs: AuditLog[]
    total: number
    page: number
    page_size: number
  }
  meta: {
    timestamp: string
  }
}

// API response for distinct users
export interface AuditLogUser {
  user_id: string
  username: string
}

export interface AuditLogUsersResponse {
  data: {
    users: AuditLogUser[]
  }
}

// Date range preset options
export type DateRangePreset = 'last24h' | 'last7d' | 'last30d' | 'custom'

// Format timestamp for table display
export function formatTimestamp(isoString: string): string {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'medium',
    hour12: true,
  }).format(new Date(isoString))
}

// Format timestamp for detail view (full precision)
export function formatTimestampFull(isoString: string): string {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'full',
    timeStyle: 'long',
  }).format(new Date(isoString))
}

// Get default date from (last 24 hours)
export function getDefaultDateFrom(): string {
  const date = new Date()
  date.setHours(date.getHours() - 24)
  return date.toISOString()
}

// Get date from preset
export function getDateFromPreset(preset: DateRangePreset): string {
  const date = new Date()
  switch (preset) {
    case 'last24h':
      date.setHours(date.getHours() - 24)
      break
    case 'last7d':
      date.setDate(date.getDate() - 7)
      break
    case 'last30d':
      date.setDate(date.getDate() - 30)
      break
    default:
      date.setHours(date.getHours() - 24)
  }
  return date.toISOString()
}
