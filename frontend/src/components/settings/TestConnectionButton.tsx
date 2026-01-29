/**
 * TestConnectionButton - Button for testing service connections
 *
 * Provides visual feedback during connection testing with loading state.
 */

import { useState } from 'react'
import { CheckCircle, XCircle, Loader2, Plug } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

export interface TestConnectionButtonProps {
  /** Function to perform the connection test */
  onTest: () => Promise<boolean>
  /** Button disabled state */
  disabled?: boolean
  /** Custom label */
  label?: string
  /** Custom class name */
  className?: string
}

export function TestConnectionButton({
  onTest,
  disabled = false,
  label = 'Test Connection',
  className,
}: TestConnectionButtonProps) {
  const [isTesting, setIsTesting] = useState(false)
  const [lastResult, setLastResult] = useState<'success' | 'error' | null>(null)

  const handleTest = async () => {
    setIsTesting(true)
    setLastResult(null)

    try {
      const success = await onTest()
      setLastResult(success ? 'success' : 'error')

      if (success) {
        toast.success('Connection successful', {
          description: 'The service is reachable and responding.',
        })
      } else {
        toast.error('Connection failed', {
          description: 'Unable to connect to the service. Please check your settings.',
        })
      }
    } catch (error) {
      setLastResult('error')
      toast.error('Connection test failed', {
        description: error instanceof Error ? error.message : 'An unexpected error occurred.',
      })
    } finally {
      setIsTesting(false)
    }
  }

  const getIcon = () => {
    if (isTesting) {
      return <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    }
    if (lastResult === 'success') {
      return <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
    }
    if (lastResult === 'error') {
      return <XCircle className="mr-2 h-4 w-4 text-red-500" />
    }
    return <Plug className="mr-2 h-4 w-4" />
  }

  return (
    <Button
      variant="outline"
      onClick={handleTest}
      disabled={disabled || isTesting}
      className={className}
    >
      {getIcon()}
      {isTesting ? 'Testing...' : label}
    </Button>
  )
}

export default TestConnectionButton
