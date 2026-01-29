/**
 * CancelConversionDialog - Confirmation dialog for cancelling an in-progress conversion
 */

import { XCircle } from 'lucide-react'
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

interface CancelConversionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  currentStep: string | null
  progress: number
}

export function CancelConversionDialog({
  open,
  onOpenChange,
  onConfirm,
  currentStep,
  progress,
}: CancelConversionDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-destructive" />
            Cancel Conversion?
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3">
              <p>
                Are you sure you want to cancel the conversion? This action cannot be undone.
              </p>
              {currentStep && (
                <div className="bg-muted p-3 rounded text-sm">
                  <p className="font-medium">Current progress:</p>
                  <p className="text-muted-foreground">{currentStep}</p>
                  <p className="text-muted-foreground">{progress}% complete</p>
                </div>
              )}
              <p className="text-sm">
                Any partially generated files will be discarded.
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Continue Converting</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            Cancel Conversion
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
