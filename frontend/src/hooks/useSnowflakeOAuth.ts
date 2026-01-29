/**
 * Custom hook for Snowflake OAuth authentication
 *
 * Handles the OAuth popup flow, status checking, and token management
 * for Snowflake SSO authentication.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

export interface OAuthStatus {
  authenticated: boolean
  service: string
  expires_at: string | null
  configured: boolean
}

export interface OAuthAuthorizeResponse {
  auth_url: string
  state: string
}

export interface UseSnowflakeOAuthOptions {
  /** Whether to check status on mount */
  checkStatusOnMount?: boolean
  /** Callback when authentication succeeds */
  onSuccess?: () => void
  /** Callback when authentication fails */
  onError?: (error: string) => void
}

export interface UseSnowflakeOAuthReturn {
  /** Current OAuth status */
  status: OAuthStatus | null
  /** Whether status is loading */
  isLoading: boolean
  /** Whether OAuth is in progress */
  isAuthenticating: boolean
  /** Error message if any */
  error: string | null
  /** Initiate OAuth flow in popup */
  initiateAuth: (redirectAfter?: string) => Promise<void>
  /** Check current OAuth status */
  checkStatus: () => Promise<OAuthStatus>
  /** Revoke current OAuth tokens */
  revokeTokens: () => Promise<void>
  /** Refresh OAuth tokens */
  refreshTokens: () => Promise<void>
  /** Clear error state */
  clearError: () => void
}

const POPUP_WIDTH = 600
const POPUP_HEIGHT = 700
const POPUP_CHECK_INTERVAL = 500 // ms

export function useSnowflakeOAuth(
  options: UseSnowflakeOAuthOptions = {}
): UseSnowflakeOAuthReturn {
  const { checkStatusOnMount = false, onSuccess, onError } = options

  const [status, setStatus] = useState<OAuthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const popupRef = useRef<Window | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Check OAuth status
  const checkStatus = useCallback(async (): Promise<OAuthStatus> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.get<OAuthStatus>('/api/v1/auth/snowflake/status')
      setStatus(response.data)
      return response.data
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to check OAuth status'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Clean up popup and polling
  const cleanupPopup = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    if (popupRef.current && !popupRef.current.closed) {
      popupRef.current.close()
    }
    popupRef.current = null
    setIsAuthenticating(false)
  }, [])

  // Handle popup completion
  const handlePopupComplete = useCallback(
    async (success: boolean, errorCode?: string, errorMessage?: string) => {
      cleanupPopup()

      if (success) {
        // Refresh status after successful auth
        try {
          await checkStatus()
          onSuccess?.()
        } catch {
          // Status check failed, but auth may have succeeded
          onSuccess?.()
        }
      } else {
        const message = errorMessage || errorCode || 'OAuth authentication failed'
        setError(message)
        onError?.(message)
      }
    },
    [cleanupPopup, checkStatus, onSuccess, onError]
  )

  // Listen for messages from popup
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin (should match our app's origin)
      if (event.origin !== window.location.origin) {
        return
      }

      const data = event.data
      if (data?.type === 'oauth-callback') {
        handlePopupComplete(data.success, data.errorCode, data.errorMessage)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [handlePopupComplete])

  // Initiate OAuth flow
  const initiateAuth = useCallback(
    async (redirectAfter: string = '/'): Promise<void> => {
      setError(null)
      setIsAuthenticating(true)

      try {
        // Get authorization URL from backend
        const response = await api.get<OAuthAuthorizeResponse>(
          '/api/v1/auth/snowflake/authorize',
          {
            params: { redirect_after: redirectAfter },
          }
        )

        // Calculate popup position (center of screen)
        const left = window.screenX + (window.outerWidth - POPUP_WIDTH) / 2
        const top = window.screenY + (window.outerHeight - POPUP_HEIGHT) / 2

        // Open popup
        popupRef.current = window.open(
          response.data.auth_url,
          'snowflake-oauth',
          `width=${POPUP_WIDTH},height=${POPUP_HEIGHT},left=${left},top=${top},` +
            'menubar=no,toolbar=no,location=yes,status=yes,scrollbars=yes'
        )

        if (!popupRef.current) {
          throw new Error(
            'Failed to open OAuth popup. Please allow popups for this site.'
          )
        }

        // Poll for popup closure (fallback if message listener fails)
        pollIntervalRef.current = setInterval(() => {
          if (popupRef.current?.closed) {
            // Popup was closed, check if it was successful
            // by checking the current URL for OAuth callback params
            cleanupPopup()
            // Refresh status to see if auth succeeded
            checkStatus().catch(() => {
              // If status check fails, that's okay
            })
          }
        }, POPUP_CHECK_INTERVAL)
      } catch (err: unknown) {
        setIsAuthenticating(false)
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to initiate OAuth flow'

        // Check for specific error codes
        const axiosError = err as { response?: { data?: { code?: string; message?: string } } }
        if (axiosError?.response?.data?.code === 'OAUTH_NOT_CONFIGURED') {
          setError('Snowflake OAuth is not configured. Please contact your administrator.')
        } else {
          setError(errorMessage)
        }
        onError?.(errorMessage)
      }
    },
    [cleanupPopup, checkStatus, onError]
  )

  // Revoke tokens
  const revokeTokens = useCallback(async (): Promise<void> => {
    setIsLoading(true)
    setError(null)

    try {
      await api.post('/api/v1/auth/snowflake/revoke')
      setStatus((prev) =>
        prev ? { ...prev, authenticated: false, expires_at: null } : null
      )
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to revoke OAuth tokens'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Refresh tokens
  const refreshTokens = useCallback(async (): Promise<void> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.post<OAuthStatus>('/api/v1/auth/snowflake/refresh')
      setStatus(response.data)
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to refresh OAuth tokens'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Clear error
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // Check status on mount if requested
  useEffect(() => {
    if (checkStatusOnMount) {
      checkStatus().catch(() => {
        // Ignore errors on initial status check
      })
    }
  }, [checkStatusOnMount, checkStatus])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupPopup()
    }
  }, [cleanupPopup])

  return {
    status,
    isLoading,
    isAuthenticating,
    error,
    initiateAuth,
    checkStatus,
    revokeTokens,
    refreshTokens,
    clearError,
  }
}
