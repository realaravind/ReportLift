/**
 * Live Mode Toggle Component
 * Toggles automatic polling of audit logs
 */

import { Radio } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface LiveModeToggleProps {
  enabled: boolean
  onToggle: (enabled: boolean) => void
}

export function LiveModeToggle({ enabled, onToggle }: LiveModeToggleProps) {
  return (
    <Button
      variant={enabled ? 'default' : 'outline'}
      size="sm"
      onClick={() => onToggle(!enabled)}
      className="gap-2"
    >
      <Radio className={`h-4 w-4 ${enabled ? 'animate-pulse text-red-500' : ''}`} />
      {enabled ? 'Live' : 'Live Mode'}
    </Button>
  )
}
