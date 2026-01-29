/**
 * UnsavedChangesDialog - Confirmation dialog for unsaved changes
 *
 * Used with useUnsavedChanges hook to prompt user before discarding changes.
 */

import { useEffect } from 'react'
import type { Blocker } from 'react-router-dom'
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

export interface UnsavedChangesDialogProps {
  /** React Router blocker from useUnsavedChanges hook */
  blocker: Blocker
  /** Custom title */
  title?: string
  /** Custom description */
  description?: string
  /** Label for confirm button */
  confirmLabel?: string
  /** Label for cancel button */
  cancelLabel?: string
}

export function UnsavedChangesDialog({
  blocker,
  title = 'Unsaved Changes',
  description = 'You have unsaved changes. Are you sure you want to leave? Your changes will be lost.',
  confirmLabel = 'Leave Page',
  cancelLabel = 'Stay',
}: UnsavedChangesDialogProps) {
  const isBlocked = blocker.state === 'blocked'

  // Handle escape key to cancel
  useEffect(() => {
    if (!isBlocked) return

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        blocker.reset?.()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isBlocked, blocker])

  return (
    <AlertDialog open={isBlocked}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => blocker.reset?.()}>
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={() => blocker.proceed?.()}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export default UnsavedChangesDialog
