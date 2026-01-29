/**
 * Sidebar Component - Collapsible left panel for SSRS folder navigation
 */

import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  FolderTree as FolderTreeIcon,
  Wifi,
  WifiOff,
  Settings,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useUIStore } from '@/store/uiStore'
import { useHealthStore } from '@/store/healthStore'
import { cn } from '@/lib/utils'
import { FolderTree } from '@/components/ssrs/FolderTree'
import { useSSRSFolders, isSSRSNotConfigured } from '@/hooks/useSSRSFolders'

interface SidebarProps {
  className?: string
  onFolderSelect?: (path: string) => void
}

export function Sidebar({ className, onFolderSelect }: SidebarProps) {
  const navigate = useNavigate()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { services } = useHealthStore()

  // Check SSRS connection status from health store
  const ssrsHealth = services.find((s) => s.service === 'ssrs')
  const isSSRSConnected = ssrsHealth?.status === 'connected'
  const isSSRSConfigured = ssrsHealth?.status !== 'not_configured'

  // Also check via folder query for real-time status
  const { error: foldersError } = useSSRSFolders('/', isSSRSConfigured)
  const ssrsNotConfigured = isSSRSNotConfigured(foldersError)

  const handleFolderSelect = useCallback(
    (path: string) => {
      onFolderSelect?.(path)
    },
    [onFolderSelect]
  )

  const handleGoToSettings = () => {
    navigate('/settings?tab=ssrs')
  }

  // Determine what to show in the sidebar
  const showFolderTree = isSSRSConfigured && !ssrsNotConfigured
  const showNotConfigured = !isSSRSConfigured || ssrsNotConfigured

  return (
    <aside
      className={cn(
        'relative flex flex-col border-r border-border bg-card transition-all duration-200 ease-in-out',
        sidebarCollapsed ? 'w-[60px]' : 'w-[280px]',
        className
      )}
    >
      {/* Collapse toggle button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute -right-3 top-4 z-10 h-6 w-6 rounded-full border border-border bg-background shadow-sm"
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronLeft className="h-4 w-4" />
        )}
      </Button>

      {/* Sidebar content */}
      <div className="flex flex-1 flex-col overflow-hidden p-4">
        {/* Section header */}
        <div className="flex items-center gap-2 mb-4">
          <FolderTreeIcon className="h-5 w-5 shrink-0 text-muted-foreground" />
          {!sidebarCollapsed && <span className="font-medium">SSRS Browser</span>}
        </div>

        <Separator className="mb-4" />

        {/* Folder tree or placeholder */}
        <div className="flex-1 overflow-auto">
          {sidebarCollapsed ? (
            <div className="flex flex-col items-center gap-4 py-4">
              <div className="h-4 w-4 rounded bg-muted" />
              <div className="h-4 w-4 rounded bg-muted" />
              <div className="h-4 w-4 rounded bg-muted" />
            </div>
          ) : showNotConfigured ? (
            <div className="flex flex-col items-center justify-center py-8 px-2 text-center">
              <WifiOff className="h-8 w-8 text-muted-foreground mb-3" />
              <p className="text-sm font-medium mb-1">SSRS Not Configured</p>
              <p className="text-xs text-muted-foreground mb-4">
                Configure your SSRS connection in Settings to browse reports.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGoToSettings}
                className="gap-2"
              >
                <Settings className="h-4 w-4" />
                Go to Settings
              </Button>
            </div>
          ) : showFolderTree ? (
            <FolderTree onFolderSelect={handleFolderSelect} />
          ) : null}
        </div>

        <Separator className="my-4" />

        {/* Connection status */}
        <div className="flex items-center gap-2">
          {isSSRSConnected ? (
            <>
              <Wifi className="h-4 w-4 shrink-0 text-green-500" />
              {!sidebarCollapsed && (
                <span className="text-xs text-green-600">Connected</span>
              )}
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 shrink-0 text-muted-foreground" />
              {!sidebarCollapsed && (
                <span className="text-xs text-muted-foreground">Not connected</span>
              )}
            </>
          )}
        </div>
      </div>
    </aside>
  )
}
