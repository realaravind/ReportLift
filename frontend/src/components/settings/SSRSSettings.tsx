/**
 * SSRS Settings Tab - Configuration for SQL Server Reporting Services connection
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Database, Trash2, CheckCircle, XCircle, Clock, Server, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { SettingsCard } from './SettingsCard'
import { TestConnectionButton } from './TestConnectionButton'
import { SaveButton } from './SaveButton'
import { MaskedInput } from './MaskedInput'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  useSSRSSettings,
  useUpdateSSRSSettings,
  useClearSSRSCredentials,
  useTestSSRSConnection,
  SSRSTestResult,
} from '@/hooks/useSSRSSettings'

// Zod validation schema
const ssrsConfigSchema = z.object({
  report_server_url: z
    .string()
    .min(1, 'Report Server URL is required')
    .url('Invalid Report Server URL format')
    .refine(
      (url) => url.startsWith('http://') || url.startsWith('https://'),
      'URL must start with http:// or https://'
    ),
  auth_method: z.enum(['windows_integrated']),
  service_account_username: z.string().optional(),
  service_account_password: z.string().optional(),
})

type SSRSConfigFormData = z.infer<typeof ssrsConfigSchema>

export function SSRSSettings() {
  const { data: settings, isLoading, error } = useSSRSSettings()
  const updateMutation = useUpdateSSRSSettings()
  const clearCredentialsMutation = useClearSSRSCredentials()
  const testConnectionMutation = useTestSSRSConnection()
  const [connectionTested, setConnectionTested] = useState(false)
  const [lastTestResult, setLastTestResult] = useState<SSRSTestResult | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<SSRSConfigFormData>({
    resolver: zodResolver(ssrsConfigSchema),
    defaultValues: {
      report_server_url: '',
      auth_method: 'windows_integrated',
      service_account_username: '',
      service_account_password: '',
    },
  })

  // Update form when settings are loaded
  useEffect(() => {
    if (settings) {
      reset({
        report_server_url: settings.report_server_url || '',
        auth_method: settings.auth_method as 'windows_integrated' || 'windows_integrated',
        service_account_username: settings.service_account_username || '',
        service_account_password: '',
      })
    }
  }, [settings, reset])

  const onSubmit = async (data: SSRSConfigFormData) => {
    try {
      await updateMutation.mutateAsync({
        report_server_url: data.report_server_url,
        auth_method: data.auth_method,
        service_account_username: data.service_account_username || undefined,
        service_account_password: data.service_account_password || undefined,
      })

      // Clear the password field after save
      reset({
        ...data,
        service_account_password: '',
      })

      if (!connectionTested) {
        toast.warning('Configuration saved', {
          description: 'Test connection recommended before using.',
        })
      } else {
        toast.success('SSRS configuration saved')
      }
      setConnectionTested(false)
      // Clear previous test result since settings changed
      setLastTestResult(null)
    } catch (err) {
      toast.error('Failed to save configuration', {
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
      })
    }
  }

  const handleClearCredentials = async () => {
    try {
      await clearCredentialsMutation.mutateAsync()
      toast.success('Credentials cleared')
    } catch (err) {
      toast.error('Failed to clear credentials', {
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
      })
    }
  }

  const handleTestConnection = async (): Promise<boolean> => {
    try {
      const result = await testConnectionMutation.mutateAsync()
      setLastTestResult(result)
      setConnectionTested(result.success)
      return result.success
    } catch (err) {
      // Handle API error (e.g., SSRS not configured)
      const errorMessage = err instanceof Error ? err.message : 'Connection test failed'
      setLastTestResult({
        success: false,
        message: errorMessage,
        details: {
          server_version: null,
          response_time_ms: 0,
          root_folder_accessible: false,
          error_code: 'API_ERROR',
        },
        suggestions: ['Check that SSRS is properly configured', 'Try saving your configuration first'],
        tested_at: new Date().toISOString(),
      })
      return false
    }
  }

  const watchUrl = watch('report_server_url')
  const isConfigured = Boolean(settings?.report_server_url)
  const isFormValid = watchUrl && !errors.report_server_url
  const canTest = isConfigured && !isDirty

  if (isLoading) {
    return (
      <SettingsCard
        title="SSRS Connection"
        description="Configure the connection to your SQL Server Reporting Services instance."
      >
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      </SettingsCard>
    )
  }

  if (error) {
    return (
      <SettingsCard
        title="SSRS Connection"
        description="Configure the connection to your SQL Server Reporting Services instance."
      >
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Database className="h-12 w-12 text-destructive mb-4" />
          <h3 className="text-lg font-medium mb-2">Failed to Load Settings</h3>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : 'An unexpected error occurred.'}
          </p>
        </div>
      </SettingsCard>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <SettingsCard
        title="SSRS Connection"
        description="Configure the connection to your SQL Server Reporting Services instance."
        actions={
          <>
            <div className="relative group">
              <TestConnectionButton
                onTest={handleTestConnection}
                disabled={!canTest}
              />
              {!canTest && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  {!isConfigured ? 'Configure SSRS settings first' : 'Save changes before testing'}
                </div>
              )}
            </div>
            <SaveButton
              type="submit"
              isSaving={updateMutation.isPending}
              disabled={!isFormValid || !isDirty}
            />
          </>
        }
      >
        <div className="space-y-6">
          {/* Connection Test Result */}
          {lastTestResult && (
            <ConnectionTestResult result={lastTestResult} />
          )}

          {/* Report Server URL */}
          <div className="space-y-2">
            <Label htmlFor="report_server_url">
              Report Server URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="report_server_url"
              placeholder="https://reportserver.company.com/ReportServer"
              {...register('report_server_url')}
              aria-invalid={!!errors.report_server_url}
            />
            {errors.report_server_url && (
              <p className="text-sm text-destructive">{errors.report_server_url.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              The full URL to your SSRS Report Server instance
            </p>
          </div>

          {/* Authentication Method */}
          <div className="space-y-2">
            <Label htmlFor="auth_method">Authentication Method</Label>
            <Select
              id="auth_method"
              {...register('auth_method')}
              disabled
            >
              <option value="windows_integrated">Windows Integrated</option>
            </Select>
            <p className="text-xs text-muted-foreground">
              Currently only Windows Integrated authentication is supported
            </p>
          </div>

          {/* Service Account Section */}
          <div className="border-t pt-6">
            <h4 className="text-sm font-medium mb-4">Service Account (Optional)</h4>
            <p className="text-xs text-muted-foreground mb-4">
              Provide service account credentials for scheduled operations. Leave blank to use the current user's credentials.
            </p>

            <div className="space-y-4">
              {/* Service Account Username */}
              <div className="space-y-2">
                <Label htmlFor="service_account_username">Username</Label>
                <Input
                  id="service_account_username"
                  placeholder="DOMAIN\username"
                  {...register('service_account_username')}
                />
              </div>

              {/* Service Account Password */}
              <div className="space-y-2">
                <Label htmlFor="service_account_password">Password</Label>
                <MaskedInput
                  id="service_account_password"
                  placeholder={settings?.has_credentials ? undefined : "Enter password"}
                  hasExistingValue={settings?.has_credentials || false}
                  {...register('service_account_password')}
                />
                {settings?.has_credentials && (
                  <p className="text-xs text-muted-foreground">
                    A password is already configured. Enter a new value to change it.
                  </p>
                )}
              </div>

              {/* Clear Credentials Button */}
              {settings?.has_credentials && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Clear Credentials
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Clear SSRS Credentials?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Are you sure you want to clear the stored SSRS service account credentials?
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleClearCredentials}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Clear Credentials
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </div>
          </div>

          {/* Last Updated */}
          {settings?.updated_at && (
            <div className="border-t pt-4">
              <p className="text-xs text-muted-foreground">
                Last updated: {new Date(settings.updated_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>
      </SettingsCard>
    </form>
  )
}

/**
 * Connection Test Result Component
 */
function ConnectionTestResult({ result }: { result: SSRSTestResult }) {
  const isSuccess = result.success

  return (
    <Alert variant={isSuccess ? 'default' : 'destructive'}>
      <div className="flex items-start gap-3">
        {isSuccess ? (
          <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
        ) : (
          <XCircle className="h-5 w-5 mt-0.5" />
        )}
        <div className="flex-1">
          <AlertTitle className="mb-1">
            {isSuccess ? 'Connection Successful' : 'Connection Failed'}
          </AlertTitle>
          <AlertDescription>
            <p className="mb-2">{result.message}</p>

            {/* Success details */}
            {isSuccess && (
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                {result.details.server_version && (
                  <span className="flex items-center gap-1">
                    <Server className="h-3 w-3" />
                    {result.details.server_version}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {result.details.response_time_ms}ms
                </span>
              </div>
            )}

            {/* Failure suggestions */}
            {!isSuccess && result.suggestions && result.suggestions.length > 0 && (
              <div className="mt-3 space-y-1">
                <p className="text-xs font-medium flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Suggestions:
                </p>
                <ul className="text-xs list-disc list-inside space-y-0.5 text-muted-foreground">
                  {result.suggestions.map((suggestion, index) => (
                    <li key={index}>{suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Test timestamp */}
            <p className="text-xs text-muted-foreground mt-2">
              Tested: {new Date(result.tested_at).toLocaleString()}
            </p>
          </AlertDescription>
        </div>
      </div>
    </Alert>
  )
}

export default SSRSSettings
