/**
 * useUnsavedChanges - Hook for tracking unsaved form changes
 *
 * Provides:
 * - Dirty state tracking
 * - Browser beforeunload warning
 * - React Router navigation blocking
 */

import { useState, useCallback, useEffect } from 'react'
import { useBlocker } from 'react-router-dom'

export interface UseUnsavedChangesOptions {
  /** Initial values to compare against */
  initialValues?: Record<string, unknown>
  /** Whether to enable browser beforeunload warning */
  enableBeforeUnload?: boolean
  /** Whether to enable React Router blocking */
  enableRouterBlocking?: boolean
  /** Custom message for the warning dialog */
  message?: string
}

export interface UseUnsavedChangesReturn {
  /** Whether there are unsaved changes */
  isDirty: boolean
  /** Set dirty state */
  setIsDirty: (dirty: boolean) => void
  /** Mark form as clean (after save) */
  markClean: () => void
  /** Mark form as dirty */
  markDirty: () => void
  /** Check if values have changed from initial */
  hasChanges: (currentValues: Record<string, unknown>) => boolean
  /** Navigation blocker state (for React Router) */
  blocker: ReturnType<typeof useBlocker>
}

export function useUnsavedChanges(
  options: UseUnsavedChangesOptions = {}
): UseUnsavedChangesReturn {
  const {
    initialValues,
    enableBeforeUnload = true,
    enableRouterBlocking = true,
    message = 'You have unsaved changes. Are you sure you want to leave?',
  } = options

  const [isDirty, setIsDirty] = useState(false)

  // Browser beforeunload handler
  useEffect(() => {
    if (!enableBeforeUnload || !isDirty) {
      return
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      // Modern browsers ignore custom message, but we need to set returnValue
      event.returnValue = message
      return message
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty, enableBeforeUnload, message])

  // React Router navigation blocker
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      enableRouterBlocking &&
      isDirty &&
      currentLocation.pathname !== nextLocation.pathname
  )

  // Mark form as clean
  const markClean = useCallback(() => {
    setIsDirty(false)
  }, [])

  // Mark form as dirty
  const markDirty = useCallback(() => {
    setIsDirty(true)
  }, [])

  // Check if values have changed from initial
  const hasChanges = useCallback(
    (currentValues: Record<string, unknown>): boolean => {
      if (!initialValues) {
        return false
      }

      const keys = new Set([
        ...Object.keys(initialValues),
        ...Object.keys(currentValues),
      ])

      for (const key of keys) {
        if (JSON.stringify(initialValues[key]) !== JSON.stringify(currentValues[key])) {
          return true
        }
      }

      return false
    },
    [initialValues]
  )

  return {
    isDirty,
    setIsDirty,
    markClean,
    markDirty,
    hasChanges,
    blocker,
  }
}

export default useUnsavedChanges
