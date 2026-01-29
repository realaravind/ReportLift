/**
 * OAuth Error Page
 *
 * Displays OAuth error messages when authentication fails.
 * This page is shown when the IdP redirects back with an error.
 */

import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function OAuthError() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const errorCode = searchParams.get('code') || 'UNKNOWN_ERROR'
  const errorMessage =
    searchParams.get('message') || 'An unknown error occurred during authentication.'

  // Map error codes to user-friendly titles
  const getErrorTitle = (code: string): string => {
    const titles: Record<string, string> = {
      OAUTH_NOT_CONFIGURED: 'OAuth Not Configured',
      OAUTH_INVALID_STATE: 'Session Expired',
      OAUTH_TOKEN_EXCHANGE_FAILED: 'Authentication Failed',
      OAUTH_REFRESH_FAILED: 'Token Refresh Failed',
      OAUTH_ACCESS_DENIED: 'Access Denied',
      OAUTH_INVALID_REQUEST: 'Invalid Request',
    }
    return titles[code] || 'Authentication Error'
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
            <svg
              className="h-8 w-8 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h1 className="mt-4 text-2xl font-bold text-foreground">
            {getErrorTitle(errorCode)}
          </h1>
        </div>

        <Alert variant="destructive">
          <AlertTitle>Error Details</AlertTitle>
          <AlertDescription className="mt-2">
            <p>{errorMessage}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Error Code: {errorCode}
            </p>
          </AlertDescription>
        </Alert>

        <div className="flex flex-col gap-2">
          <Button onClick={() => navigate(-1)} variant="default">
            Go Back
          </Button>
          <Button onClick={() => navigate('/')} variant="outline">
            Return to Home
          </Button>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          If this problem persists, please contact your administrator.
        </p>
      </div>
    </div>
  )
}

export default OAuthError
