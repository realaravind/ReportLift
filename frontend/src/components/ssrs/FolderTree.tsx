/**
 * FolderTree Component - Recursive tree view for SSRS folder navigation
 */

import { useState, useCallback } from 'react'
import { ChevronRight, ChevronDown, Folder, FolderOpen, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSSRSFolders, FolderItem, getSSRSFoldersError } from '@/hooks/useSSRSFolders'
import { Button } from '@/components/ui/button'

interface FolderNodeProps {
  folder: FolderItem
  level: number
  selectedPath: string | null
  onSelect: (path: string) => void
  expandedPaths: Set<string>
  onToggleExpand: (path: string) => void
}

function FolderNode({
  folder,
  level,
  selectedPath,
  onSelect,
  expandedPaths,
  onToggleExpand,
}: FolderNodeProps) {
  const isExpanded = expandedPaths.has(folder.path)
  const isSelected = selectedPath === folder.path
  const hasChildren = folder.has_children

  // Fetch children only when expanded
  const { data, isLoading, error, refetch } = useSSRSFolders(
    folder.path,
    isExpanded && hasChildren
  )

  const handleClick = () => {
    onSelect(folder.path)
    if (hasChildren) {
      onToggleExpand(folder.path)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleClick()
    }
  }

  return (
    <div>
      <div
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelected}
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={cn(
          'flex items-center gap-1 px-2 py-1.5 cursor-pointer rounded-md transition-colors',
          'hover:bg-accent hover:text-accent-foreground',
          'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
          isSelected && 'bg-primary/10 text-primary font-medium'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {/* Expand/Collapse icon or spacer */}
        {hasChildren ? (
          <span className="shrink-0 w-4 h-4 flex items-center justify-center">
            {isLoading ? (
              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
            ) : isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </span>
        ) : (
          <span className="w-4" />
        )}

        {/* Folder icon */}
        {isExpanded && hasChildren ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-amber-500" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-amber-500" />
        )}

        {/* Folder name */}
        <span className="truncate text-sm">{folder.name}</span>
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div role="group">
          {error ? (
            <div
              className="flex items-center gap-2 px-2 py-2 text-sm text-destructive"
              style={{ paddingLeft: `${(level + 1) * 16 + 8}px` }}
            >
              <AlertCircle className="h-4 w-4" />
              <span>{getSSRSFoldersError(error)?.message || 'Failed to load'}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2"
                onClick={(e) => {
                  e.stopPropagation()
                  refetch()
                }}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            </div>
          ) : data?.data.length === 0 && !isLoading ? (
            <div
              className="px-2 py-1 text-sm text-muted-foreground italic"
              style={{ paddingLeft: `${(level + 1) * 16 + 8}px` }}
            >
              No subfolders
            </div>
          ) : (
            data?.data.map((childFolder) => (
              <FolderNode
                key={childFolder.path}
                folder={childFolder}
                level={level + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
                expandedPaths={expandedPaths}
                onToggleExpand={onToggleExpand}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}

interface FolderTreeProps {
  onFolderSelect?: (path: string) => void
  className?: string
}

export function FolderTree({ onFolderSelect, className }: FolderTreeProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())

  // Fetch root folders
  const { data, isLoading, error, refetch } = useSSRSFolders('/')

  const handleSelect = useCallback(
    (path: string) => {
      setSelectedPath(path)
      onFolderSelect?.(path)
    },
    [onFolderSelect]
  )

  const handleToggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">Loading folders...</p>
      </div>
    )
  }

  // Error state
  if (error) {
    const errorDetail = getSSRSFoldersError(error)
    return (
      <div className={cn('flex flex-col items-center justify-center py-8 px-4', className)}>
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-destructive mb-1">Unable to load folders</p>
        <p className="text-xs text-muted-foreground text-center mb-3">
          {errorDetail?.message}
        </p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  // Empty state
  if (!data?.data.length) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-8 px-4', className)}>
        <Folder className="h-8 w-8 text-muted-foreground mb-3" />
        <p className="text-sm text-muted-foreground text-center">
          No folders found in the Report Server
        </p>
      </div>
    )
  }

  return (
    <div role="tree" aria-label="SSRS Folder Structure" className={cn('', className)}>
      {data.data.map((folder) => (
        <FolderNode
          key={folder.path}
          folder={folder}
          level={0}
          selectedPath={selectedPath}
          onSelect={handleSelect}
          expandedPaths={expandedPaths}
          onToggleExpand={handleToggleExpand}
        />
      ))}
    </div>
  )
}

export default FolderTree
