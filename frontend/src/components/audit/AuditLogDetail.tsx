/**
 * Audit Log Detail Component
 * Displays expanded details for a single audit log entry
 */

import { Globe, Monitor, Clock, User, FileText, Tag } from 'lucide-react'
import type { AuditLog } from '@/types/audit'
import { formatTimestampFull } from '@/types/audit'

interface AuditLogDetailProps {
  log: AuditLog
}

export function AuditLogDetail({ log }: AuditLogDetailProps) {
  return (
    <div className="p-4 space-y-4">
      {/* Metadata Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Full Timestamp */}
        <div className="flex items-start gap-2">
          <Clock className="h-4 w-4 mt-0.5 text-muted-foreground" />
          <div>
            <div className="text-xs font-medium text-muted-foreground">Timestamp</div>
            <div className="text-sm">{formatTimestampFull(log.timestamp)}</div>
          </div>
        </div>

        {/* User Info */}
        <div className="flex items-start gap-2">
          <User className="h-4 w-4 mt-0.5 text-muted-foreground" />
          <div>
            <div className="text-xs font-medium text-muted-foreground">User</div>
            <div className="text-sm">
              {log.username || 'System'}
              {log.user_id && (
                <span className="text-xs text-muted-foreground ml-1">
                  (ID: {log.user_id})
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Resource Info */}
        {(log.resource_type || log.resource_id) && (
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 mt-0.5 text-muted-foreground" />
            <div>
              <div className="text-xs font-medium text-muted-foreground">Resource</div>
              <div className="text-sm">
                {log.resource_type && (
                  <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                    {log.resource_type}
                  </span>
                )}
                {log.resource_id && (
                  <span className="ml-2 text-muted-foreground">{log.resource_id}</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Event ID */}
        <div className="flex items-start gap-2">
          <Tag className="h-4 w-4 mt-0.5 text-muted-foreground" />
          <div>
            <div className="text-xs font-medium text-muted-foreground">Event ID</div>
            <div className="text-sm font-mono text-xs">{log.id}</div>
          </div>
        </div>
      </div>

      {/* Client Info Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* IP Address */}
        {log.ip_address && (
          <div className="flex items-start gap-2">
            <Globe className="h-4 w-4 mt-0.5 text-muted-foreground" />
            <div>
              <div className="text-xs font-medium text-muted-foreground">IP Address</div>
              <div className="text-sm font-mono">{log.ip_address}</div>
            </div>
          </div>
        )}

        {/* User Agent */}
        {log.user_agent && (
          <div className="flex items-start gap-2">
            <Monitor className="h-4 w-4 mt-0.5 text-muted-foreground" />
            <div>
              <div className="text-xs font-medium text-muted-foreground">User Agent</div>
              <div className="text-sm text-muted-foreground truncate max-w-md" title={log.user_agent}>
                {log.user_agent}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action */}
      <div>
        <div className="text-xs font-medium text-muted-foreground mb-1">Action</div>
        <div className="text-sm">{log.action}</div>
      </div>

      {/* Details JSON */}
      {log.details && Object.keys(log.details).length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-2">Details</div>
          <pre className="bg-muted p-3 rounded-md text-xs font-mono overflow-x-auto max-h-64">
            {JSON.stringify(log.details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
