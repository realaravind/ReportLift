/**
 * SnowflakeWarningDialog - Warns user when Snowflake is not configured
 */

import { AlertTriangle, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
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
import { Button } from '@/components/ui/button'

interface SnowflakeWarningDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onProceed: () => void
  placeholderSchema: string
}

export function SnowflakeWarningDialog({
  open,
  onOpenChange,
  onProceed,
  placeholderSchema,
}: SnowflakeWarningDialogProps) {
  const navigate = useNavigate()

  const handleConfigureSnowflake = () => {
    onOpenChange(false)
    navigate('/settings')
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Snowflake Not Configured
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-3">
              <p>
                Snowflake connection is not configured. The conversion will still proceed, but:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>
                  SQL scripts will use <code className="bg-muted px-1 py-0.5 rounded">{placeholderSchema}</code> as the schema name
                </li>
                <li>You&apos;ll need to update schema references before running the scripts</li>
                <li>Stored procedure validation against Snowflake will be skipped</li>
              </ul>
              <p className="text-sm font-medium">
                Configure Snowflake in Settings for optimal conversion results.
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="sm:space-x-2">
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button variant="outline" onClick={handleConfigureSnowflake}>
            <Settings className="mr-2 h-4 w-4" />
            Configure Snowflake
          </Button>
          <AlertDialogAction onClick={onProceed}>
            Proceed Anyway
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
