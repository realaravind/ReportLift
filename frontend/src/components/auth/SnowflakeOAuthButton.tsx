/**
 * Snowflake OAuth Button Component
 *
 * A button that initiates Snowflake OAuth authentication via popup.
 * Displays connection status and handles authentication flow.
 */

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSnowflakeOAuth } from '@/hooks/useSnowflakeOAuth'
import { cn } from '@/lib/utils'

export interface SnowflakeOAuthButtonProps {
  /** Custom class name */
  className?: string
  /** Whether to check status on mount */
  checkStatusOnMount?: boolean
  /** Callback when authentication succeeds */
  onSuccess?: () => void
  /** Callback when authentication fails */
  onError?: (error: string) => void
  /** Button variant */
  variant?: 'default' | 'outline' | 'secondary' | 'ghost'
  /** Button size */
  size?: 'default' | 'sm' | 'lg'
  /** Custom label for connect button */
  connectLabel?: string
  /** Custom label for disconnect button */
  disconnectLabel?: string
  /** Show status badge */
  showStatus?: boolean
  /** Compact mode (icon only when connected) */
  compact?: boolean
}

export function SnowflakeOAuthButton({
  className,
  checkStatusOnMount = true,
  onSuccess,
  onError,
  variant = 'default',
  size = 'default',
  connectLabel = 'Connect to Snowflake',
  disconnectLabel = 'Disconnect',
  showStatus = true,
  compact = false,
}: SnowflakeOAuthButtonProps) {
  const {
    status,
    isLoading,
    isAuthenticating,
    error,
    initiateAuth,
    checkStatus,
    revokeTokens,
    clearError,
  } = useSnowflakeOAuth({
    checkStatusOnMount,
    onSuccess,
    onError,
  })

  // Handle connect button click
  const handleConnect = async () => {
    await initiateAuth(window.location.pathname)
  }

  // Handle disconnect button click
  const handleDisconnect = async () => {
    try {
      await revokeTokens()
    } catch {
      // Error is already set in the hook
    }
  }

  // Check status when component gains focus (user returns from popup)
  useEffect(() => {
    const handleFocus = () => {
      if (!isAuthenticating) {
        checkStatus().catch(() => {
          // Ignore errors on focus refresh
        })
      }
    }

    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [isAuthenticating, checkStatus])

  // Not configured state
  if (status && !status.configured) {
    return (
      <div className={cn('space-y-2', className)}>
        <Button variant="outline" size={size} disabled>
          <SnowflakeIcon className="mr-2 h-4 w-4" />
          Snowflake Not Configured
        </Button>
        {showStatus && (
          <p className="text-xs text-muted-foreground">
            OAuth not configured. Contact your administrator.
          </p>
        )}
      </div>
    )
  }

  // Connected state
  if (status?.authenticated) {
    const expiresAt = status.expires_at ? new Date(status.expires_at) : null
    const expiresLabel = expiresAt
      ? `Expires ${expiresAt.toLocaleTimeString()}`
      : ''

    if (compact) {
      return (
        <div className={cn('flex items-center gap-2', className)}>
          <div className="flex items-center gap-1">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span className="text-xs text-muted-foreground">Connected</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDisconnect}
            disabled={isLoading}
          >
            {disconnectLabel}
          </Button>
        </div>
      )
    }

    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center gap-2">
          <Button
            variant={variant}
            size={size}
            onClick={handleDisconnect}
            disabled={isLoading}
          >
            <SnowflakeIcon className="mr-2 h-4 w-4" />
            {isLoading ? 'Disconnecting...' : disconnectLabel}
          </Button>
          {showStatus && (
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm text-green-600">Connected</span>
            </div>
          )}
        </div>
        {showStatus && expiresLabel && (
          <p className="text-xs text-muted-foreground">{expiresLabel}</p>
        )}
      </div>
    )
  }

  // Disconnected state
  return (
    <div className={cn('space-y-2', className)}>
      {error && (
        <Alert variant="destructive" className="mb-2">
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={clearError}
              className="text-destructive-foreground hover:opacity-70"
            >
              &times;
            </button>
          </AlertDescription>
        </Alert>
      )}
      <div className="flex items-center gap-2">
        <Button
          variant={variant}
          size={size}
          onClick={handleConnect}
          disabled={isLoading || isAuthenticating}
          className={className}
        >
          <SnowflakeIcon className="mr-2 h-4 w-4" />
          {isAuthenticating
            ? 'Authenticating...'
            : isLoading
              ? 'Loading...'
              : connectLabel}
        </Button>
        {showStatus && !isAuthenticating && (
          <div className="flex items-center gap-1">
            <div className="h-2 w-2 rounded-full bg-gray-400" />
            <span className="text-sm text-muted-foreground">Not connected</span>
          </div>
        )}
      </div>
    </div>
  )
}

// Snowflake Icon Component
function SnowflakeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="2" x2="12" y2="22" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
      <line x1="19.07" y1="4.93" x2="4.93" y2="19.07" />
      <circle cx="12" cy="12" r="3" />
      <line x1="12" y1="6" x2="12" y2="9" />
      <line x1="12" y1="15" x2="12" y2="18" />
      <line x1="7.76" y1="7.76" x2="9.88" y2="9.88" />
      <line x1="14.12" y1="14.12" x2="16.24" y2="16.24" />
      <line x1="16.24" y1="7.76" x2="14.12" y2="9.88" />
      <line x1="9.88" y1="14.12" x2="7.76" y2="16.24" />
    </svg>
  )
}

export default SnowflakeOAuthButton
