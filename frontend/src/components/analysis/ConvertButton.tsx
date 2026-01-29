/**
 * Convert button component for analysis display
 */

import { useNavigate } from 'react-router-dom'
import { CheckCircle, AlertTriangle, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ConversionStatus } from '@/types/analysis'

interface ConvertButtonProps {
  status: ConversionStatus | null
  reportPath: string
  todoCount: number
  disabled?: boolean
}

export function ConvertButton({
  status,
  reportPath,
  todoCount,
  disabled = false,
}: ConvertButtonProps) {
  const navigate = useNavigate()

  const handleConvert = () => {
    // Navigate to conversion page with the report path
    navigate('/convert', { state: { reportPath } })
  }

  // Green status - ready to convert
  if (status === 'green') {
    return (
      <Button
        onClick={handleConvert}
        disabled={disabled}
        className="bg-green-600 hover:bg-green-700 text-white"
      >
        <CheckCircle className="mr-2 h-4 w-4" />
        Convert Report
      </Button>
    )
  }

  // Yellow or Red status - convert with warning
  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        onClick={handleConvert}
        disabled={disabled}
        variant="outline"
        className="border-yellow-500 text-yellow-700 hover:bg-yellow-50"
      >
        <AlertTriangle className="mr-2 h-4 w-4" />
        Convert Report
      </Button>
      {todoCount > 0 && (
        <span className="text-xs text-muted-foreground">
          Review {todoCount} TODO item{todoCount > 1 ? 's' : ''} before converting
        </span>
      )}
    </div>
  )
}

/**
 * Re-analyze button component
 */
interface ReAnalyzeButtonProps {
  onReanalyze: () => void
  isLoading?: boolean
  disabled?: boolean
}

export function ReAnalyzeButton({
  onReanalyze,
  isLoading = false,
  disabled = false,
}: ReAnalyzeButtonProps) {
  return (
    <Button
      onClick={onReanalyze}
      disabled={disabled || isLoading}
      variant="outline"
    >
      <Play className="mr-2 h-4 w-4" />
      {isLoading ? 'Analyzing...' : 'Re-Analyze'}
    </Button>
  )
}
