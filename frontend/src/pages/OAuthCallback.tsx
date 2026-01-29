/**
 * OAuth Callback Page
 *
 * This page handles the OAuth callback redirect from the IdP.
 * It parses the URL parameters and communicates the result back
 * to the parent window (opener) if in a popup.
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

export function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    // Parse URL parameters
    const oauth = searchParams.get('oauth')
    const service = searchParams.get('service')
    const errorCode = searchParams.get('code')
    const errorMessage = searchParams.get('message')

    // Determine success or error
    const isSuccess = oauth === 'success'
    const isError = errorCode || errorMessage

    if (isSuccess) {
      setStatus('success')
      setMessage(`Successfully connected to ${service || 'Snowflake'}`)

      // Notify parent window if in popup
      if (window.opener) {
        window.opener.postMessage(
          {
            type: 'oauth-callback',
            success: true,
            service: service || 'snowflake',
          },
          window.location.origin
        )

        // Close popup after brief delay
        setTimeout(() => {
          window.close()
        }, 1500)
      }
    } else if (isError) {
      setStatus('error')
      setMessage(errorMessage || `Authentication failed: ${errorCode}`)

      // Notify parent window if in popup
      if (window.opener) {
        window.opener.postMessage(
          {
            type: 'oauth-callback',
            success: false,
            errorCode,
            errorMessage,
          },
          window.location.origin
        )

        // Close popup after brief delay
        setTimeout(() => {
          window.close()
        }, 3000)
      }
    } else {
      // Unknown state - might be a direct navigation
      setStatus('error')
      setMessage('Invalid OAuth callback. Please try authenticating again.')
    }
  }, [searchParams])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm">
        {status === 'loading' && (
          <div className="flex flex-col items-center gap-4">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">Processing...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="flex flex-col items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <svg
                className="h-6 w-6 text-green-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div className="text-center">
              <h2 className="text-lg font-semibold text-foreground">
                Authentication Successful
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">{message}</p>
            </div>
            <p className="text-xs text-muted-foreground">
              This window will close automatically...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <svg
                className="h-6 w-6 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <div className="text-center">
              <h2 className="text-lg font-semibold text-foreground">
                Authentication Failed
              </h2>
              <p className="mt-1 text-sm text-destructive">{message}</p>
            </div>
            {window.opener && (
              <p className="text-xs text-muted-foreground">
                This window will close automatically...
              </p>
            )}
            {!window.opener && (
              <button
                onClick={() => (window.location.href = '/')}
                className="mt-2 text-sm text-primary hover:underline"
              >
                Return to application
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default OAuthCallback
