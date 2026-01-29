/**
 * SaveButton - Button for saving settings with status feedback
 *
 * Provides visual feedback during save operation and optional warning for untested connections.
 */

import { useState } from 'react'
import { Save, Loader2, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

export interface SaveButtonProps {
  /** Function to perform the save operation (optional if type="submit") */
  onSave?: () => Promise<void>
  /** Whether the form has unsaved changes */
  hasChanges?: boolean
  /** Whether the connection has been tested */
  hasBeenTested?: boolean
  /** Button disabled state */
  disabled?: boolean
  /** Custom label */
  label?: string
  /** Custom class name */
  className?: string
  /** Button type (for form submission) */
  type?: 'button' | 'submit'
  /** Whether save is currently in progress (for external control) */
  isSaving?: boolean
}

export function SaveButton({
  onSave,
  hasChanges = false,
  hasBeenTested = false,
  disabled = false,
  label = 'Save',
  className,
  type = 'button',
  isSaving: externalIsSaving,
}: SaveButtonProps) {
  const [internalIsSaving, setInternalIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Use external saving state if provided, otherwise use internal
  const isSaving = externalIsSaving !== undefined ? externalIsSaving : internalIsSaving

  // When type="button" with onSave, also check hasChanges for disabled state
  const shouldDisable = disabled || isSaving || (type === 'button' && onSave && !hasChanges)

  const handleSave = async () => {
    // If type="submit", the form will handle submission
    if (type === 'submit' || !onSave) {
      return
    }

    setInternalIsSaving(true)
    setSaveSuccess(false)

    try {
      await onSave()
      setSaveSuccess(true)

      if (!hasBeenTested) {
        toast.warning('Configuration saved', {
          description: 'Test connection recommended to verify settings.',
        })
      } else {
        toast.success('Configuration saved', {
          description: 'Your settings have been saved successfully.',
        })
      }

      // Reset success indicator after a delay
      setTimeout(() => {
        setSaveSuccess(false)
      }, 2000)
    } catch (error) {
      toast.error('Save failed', {
        description: error instanceof Error ? error.message : 'Failed to save settings.',
      })
    } finally {
      setInternalIsSaving(false)
    }
  }

  const getIcon = () => {
    if (isSaving) {
      return <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    }
    if (saveSuccess) {
      return <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
    }
    return <Save className="mr-2 h-4 w-4" />
  }

  return (
    <Button
      type={type}
      onClick={type === 'button' ? handleSave : undefined}
      disabled={shouldDisable}
      className={className}
    >
      {getIcon()}
      {isSaving ? 'Saving...' : saveSuccess ? 'Saved!' : label}
    </Button>
  )
}

export default SaveButton
