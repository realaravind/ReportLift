/**
 * Snowflake Settings Tab - Configuration for Snowflake data warehouse connection
 */

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Snowflake,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Database as DatabaseIcon,
  Server,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
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
import { SnowflakeOAuthButton } from '@/components/auth/SnowflakeOAuthButton'
import {
  useSnowflakeSettings,
  useUpdateSnowflakeSettings,
  useClearSnowflakeCredentials,
  useTestSnowflakeConnection,
  SnowflakeTestResult,
} from '@/hooks/useSnowflakeSettings'

// Zod validation schema
const snowflakeConfigSchema = z
  .object({
    account_identifier: z
      .string()
      .min(1, 'Account identifier is required')
      .regex(/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/, 'Invalid account identifier format'),
    warehouse: z.string().min(1, 'Warehouse is required'),
    database: z.string().min(1, 'Database is required'),
    schema_name: z.string().min(1, 'Schema is required'),
    auth_method: z.enum(['oauth', 'basic']),
    username: z.string().optional(),
    password: z.string().optional(),
  })
  .refine(
    (data) => {
      // Username is required when auth_method is basic
      if (data.auth_method === 'basic' && !data.username) {
        return false
      }
      return true
    },
    {
      message: 'Username is required for basic authentication',
      path: ['username'],
    }
  )

type SnowflakeConfigFormData = z.infer<typeof snowflakeConfigSchema>

export function SnowflakeSettings() {
  const { data: settings, isLoading, error } = useSnowflakeSettings()
  const updateMutation = useUpdateSnowflakeSettings()
  const clearCredentialsMutation = useClearSnowflakeCredentials()
  const testConnectionMutation = useTestSnowflakeConnection()
  const [lastTestResult, setLastTestResult] = useState<SnowflakeTestResult | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<SnowflakeConfigFormData>({
    resolver: zodResolver(snowflakeConfigSchema),
    defaultValues: {
      account_identifier: '',
      warehouse: '',
      database: '',
      schema_name: '',
      auth_method: 'oauth',
      username: '',
      password: '',
    },
  })

  // Update form when settings are loaded
  useEffect(() => {
    if (settings) {
      reset({
        account_identifier: settings.account_identifier || '',
        warehouse: settings.warehouse || '',
        database: settings.database || '',
        schema_name: settings.schema_name || '',
        auth_method: (settings.auth_method as 'oauth' | 'basic') || 'oauth',
        username: settings.username || '',
        password: '',
      })
    }
  }, [settings, reset])

  const onSubmit = async (data: SnowflakeConfigFormData) => {
    try {
      await updateMutation.mutateAsync({
        account_identifier: data.account_identifier,
        warehouse: data.warehouse,
        database: data.database,
        schema_name: data.schema_name,
        auth_method: data.auth_method,
        username: data.auth_method === 'basic' ? data.username : undefined,
        password: data.auth_method === 'basic' && data.password ? data.password : undefined,
      })

      // Clear the password field after save
      reset({
        ...data,
        password: '',
      })

      // Clear previous test result since settings changed
      setLastTestResult(null)
      toast.success('Snowflake configuration saved')
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
      return result.success
    } catch (err) {
      // Handle API error
      const errorMessage = err instanceof Error ? err.message : 'Connection test failed'
      setLastTestResult({
        success: false,
        message: errorMessage,
        details: {
          account: null,
          warehouse: null,
          database: null,
          schema: null,
          role: null,
          user: null,
          response_time_ms: 0,
          error_code: 'API_ERROR',
          snowflake_error_code: null,
        },
        suggestions: ['Check that Snowflake is properly configured', 'Try saving your configuration first'],
        requires_reauth: false,
        tested_at: new Date().toISOString(),
      })
      return false
    }
  }

  const watchAuthMethod = watch('auth_method')
  const watchAccountId = watch('account_identifier')
  const watchWarehouse = watch('warehouse')
  const watchDatabase = watch('database')
  const watchSchema = watch('schema_name')
  const watchUsername = watch('username')

  const isFormValid =
    watchAccountId &&
    watchWarehouse &&
    watchDatabase &&
    watchSchema &&
    !errors.account_identifier &&
    !errors.warehouse &&
    !errors.database &&
    !errors.schema_name &&
    (watchAuthMethod === 'oauth' || (watchAuthMethod === 'basic' && watchUsername))

  const isConfigured = Boolean(settings?.account_identifier)
  const canTest = isConfigured && !isDirty

  if (isLoading) {
    return (
      <div className="space-y-4">
        <SettingsCard
          title="Snowflake SSO"
          description="Connect to Snowflake using corporate single sign-on (OAuth)."
        >
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        </SettingsCard>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <SettingsCard
          title="Snowflake Connection"
          description="Configure the connection to your Snowflake data warehouse."
        >
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Snowflake className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to Load Settings</h3>
            <p className="text-sm text-muted-foreground">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
          </div>
        </SettingsCard>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* OAuth Connection - Only show when OAuth is configured and auth_method is oauth */}
      {settings?.has_oauth_config && watchAuthMethod === 'oauth' && (
        <SettingsCard
          title="Snowflake SSO"
          description="Connect to Snowflake using corporate single sign-on (OAuth)."
        >
          <div className="py-4">
            <SnowflakeOAuthButton
              checkStatusOnMount
              variant="default"
              connectLabel="Connect with SSO"
              disconnectLabel="Disconnect"
            />
            {settings.oauth_status === 'authorized' && (
              <p className="text-xs text-muted-foreground mt-2">
                Your Snowflake session is active. Connection details below will use this authentication.
              </p>
            )}
          </div>
        </SettingsCard>
      )}

      {/* Connection Details Form */}
      <form onSubmit={handleSubmit(onSubmit)}>
        <SettingsCard
          title="Connection Details"
          description="Configure Snowflake account settings and defaults."
          actions={
            <>
              <div className="relative group">
                <TestConnectionButton onTest={handleTestConnection} disabled={!canTest} />
                {!canTest && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover border rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    {!isConfigured ? 'Configure Snowflake settings first' : 'Save changes before testing'}
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
            {lastTestResult && <SnowflakeConnectionTestResult result={lastTestResult} />}

            {/* Account Identifier */}
            <div className="space-y-2">
              <Label htmlFor="account_identifier">
                Account Identifier <span className="text-destructive">*</span>
              </Label>
              <Input
                id="account_identifier"
                placeholder="orgname-account_name"
                {...register('account_identifier')}
                aria-invalid={!!errors.account_identifier}
              />
              {errors.account_identifier && (
                <p className="text-sm text-destructive">{errors.account_identifier.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Your Snowflake account identifier (e.g., orgname-account_name or account.region)
              </p>
            </div>

            {/* Warehouse */}
            <div className="space-y-2">
              <Label htmlFor="warehouse">
                Warehouse <span className="text-destructive">*</span>
              </Label>
              <Input
                id="warehouse"
                placeholder="COMPUTE_WH"
                {...register('warehouse')}
                aria-invalid={!!errors.warehouse}
              />
              {errors.warehouse && (
                <p className="text-sm text-destructive">{errors.warehouse.message}</p>
              )}
              <p className="text-xs text-muted-foreground">Default warehouse for query execution</p>
            </div>

            {/* Database */}
            <div className="space-y-2">
              <Label htmlFor="database">
                Database <span className="text-destructive">*</span>
              </Label>
              <Input
                id="database"
                placeholder="MY_DATABASE"
                {...register('database')}
                aria-invalid={!!errors.database}
              />
              {errors.database && (
                <p className="text-sm text-destructive">{errors.database.message}</p>
              )}
              <p className="text-xs text-muted-foreground">Default database for queries</p>
            </div>

            {/* Schema */}
            <div className="space-y-2">
              <Label htmlFor="schema_name">
                Schema <span className="text-destructive">*</span>
              </Label>
              <Input
                id="schema_name"
                placeholder="PUBLIC"
                {...register('schema_name')}
                aria-invalid={!!errors.schema_name}
              />
              {errors.schema_name && (
                <p className="text-sm text-destructive">{errors.schema_name.message}</p>
              )}
              <p className="text-xs text-muted-foreground">Default schema for queries</p>
            </div>

            {/* Authentication Method */}
            <div className="border-t pt-6">
              <h4 className="text-sm font-medium mb-4">Authentication</h4>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="auth_method">Authentication Method</Label>
                  <Select id="auth_method" {...register('auth_method')}>
                    {settings?.has_oauth_config && <option value="oauth">OAuth (SSO)</option>}
                    <option value="basic">Basic (Username/Password)</option>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {watchAuthMethod === 'oauth'
                      ? 'Uses corporate SSO via OAuth. Click "Connect with SSO" above to authenticate.'
                      : 'Uses username and password for authentication.'}
                  </p>
                </div>

                {/* Basic Auth Fields */}
                {watchAuthMethod === 'basic' && (
                  <>
                    {/* Security Warning */}
                    <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                      <p className="text-sm text-amber-800">
                        <strong>Security Notice:</strong> OAuth/SSO is recommended for better security.
                        Username/password credentials will be encrypted before storage.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="username">
                        Username <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="username"
                        placeholder="snowflake_user"
                        {...register('username')}
                        aria-invalid={!!errors.username}
                      />
                      {errors.username && (
                        <p className="text-sm text-destructive">{errors.username.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="password">Password</Label>
                      <MaskedInput
                        id="password"
                        placeholder={settings?.has_password ? undefined : 'Enter password'}
                        hasExistingValue={settings?.has_password || false}
                        {...register('password')}
                      />
                      {settings?.has_password && (
                        <p className="text-xs text-muted-foreground">
                          A password is already configured. Enter a new value to change it.
                        </p>
                      )}
                    </div>

                    {/* Clear Credentials Button */}
                    {settings?.has_password && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Clear Password
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Clear Snowflake Password?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to clear the stored Snowflake password? This action
                              cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={handleClearCredentials}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Clear Password
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                  </>
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
    </div>
  )
}

/**
 * Snowflake Connection Test Result Component
 */
function SnowflakeConnectionTestResult({ result }: { result: SnowflakeTestResult }) {
  const isSuccess = result.success
  const requiresReauth = result.requires_reauth

  // Determine variant and icon
  let variant: 'default' | 'destructive' = isSuccess ? 'default' : 'destructive'
  if (requiresReauth) {
    variant = 'default' // Use default for orange/warning state
  }

  return (
    <Alert variant={variant} className={requiresReauth ? 'border-amber-500 bg-amber-50' : undefined}>
      <div className="flex items-start gap-3">
        {isSuccess ? (
          <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
        ) : requiresReauth ? (
          <RefreshCw className="h-5 w-5 text-amber-500 mt-0.5" />
        ) : (
          <XCircle className="h-5 w-5 mt-0.5" />
        )}
        <div className="flex-1">
          <AlertTitle className="mb-1">
            {isSuccess ? 'Connection Successful' : requiresReauth ? 'Re-authorization Required' : 'Connection Failed'}
          </AlertTitle>
          <AlertDescription>
            <p className="mb-2">{result.message}</p>

            {/* Success details */}
            {isSuccess && result.details && (
              <div className="mt-3 space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {result.details.user && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <User className="h-3 w-3" />
                      <span>User: {result.details.user}</span>
                    </div>
                  )}
                  {result.details.role && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Server className="h-3 w-3" />
                      <span>Role: {result.details.role}</span>
                    </div>
                  )}
                  {result.details.warehouse && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Snowflake className="h-3 w-3" />
                      <span>Warehouse: {result.details.warehouse}</span>
                    </div>
                  )}
                  {result.details.database && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <DatabaseIcon className="h-3 w-3" />
                      <span>Database: {result.details.database}</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  <span>{result.details.response_time_ms}ms</span>
                </div>
              </div>
            )}

            {/* Re-auth prompt */}
            {requiresReauth && (
              <div className="mt-3">
                <p className="text-xs text-amber-700 mb-2">
                  Your OAuth session has expired or is not authorized. Please click "Connect with SSO" above
                  to re-authorize your connection.
                </p>
              </div>
            )}

            {/* Failure suggestions */}
            {!isSuccess && !requiresReauth && result.suggestions && result.suggestions.length > 0 && (
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

export default SnowflakeSettings
