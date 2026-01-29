/**
 * Ollama Settings Tab - Configuration for Ollama AI service connection
 */

import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Bot, Info } from 'lucide-react'
import { toast } from 'sonner'
import { SettingsCard } from './SettingsCard'
import { SaveButton } from './SaveButton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  useOllamaSettings,
  useUpdateOllamaSettings,
  MODEL_SUGGESTIONS,
} from '@/hooks/useOllamaSettings'

// Zod validation schema
const ollamaConfigSchema = z.object({
  host_url: z
    .string()
    .min(1, 'Host URL is required')
    .regex(/^https?:\/\/[^\s/$.?#].[^\s]*$/i, 'Invalid URL format. Must start with http:// or https://'),
  model_name: z.string().min(1, 'Model name is required'),
  enabled: z.boolean(),
  timeout_seconds: z
    .number()
    .min(1, 'Timeout must be at least 1 second')
    .max(300, 'Timeout cannot exceed 300 seconds'),
})

type OllamaConfigFormData = z.infer<typeof ollamaConfigSchema>

export function OllamaSettings() {
  const { data: settings, isLoading, error } = useOllamaSettings()
  const updateMutation = useUpdateOllamaSettings()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    control,
    formState: { errors, isDirty },
  } = useForm<OllamaConfigFormData>({
    resolver: zodResolver(ollamaConfigSchema),
    defaultValues: {
      host_url: 'http://localhost:11434',
      model_name: 'codellama:13b',
      enabled: false,
      timeout_seconds: 60,
    },
  })

  // Update form when settings are loaded
  useEffect(() => {
    if (settings) {
      reset({
        host_url: settings.host_url || 'http://localhost:11434',
        model_name: settings.model_name || 'codellama:13b',
        enabled: settings.enabled || false,
        timeout_seconds: settings.timeout_seconds || 60,
      })
    }
  }, [settings, reset])

  const onSubmit = async (data: OllamaConfigFormData) => {
    try {
      await updateMutation.mutateAsync({
        host_url: data.host_url,
        model_name: data.model_name,
        enabled: data.enabled,
        timeout_seconds: data.timeout_seconds,
      })

      toast.success('Ollama configuration saved')
    } catch (err) {
      toast.error('Failed to save configuration', {
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
      })
    }
  }

  const watchEnabled = watch('enabled')
  const watchHostUrl = watch('host_url')
  const watchModelName = watch('model_name')

  const isFormValid = watchHostUrl && watchModelName && !errors.host_url && !errors.model_name

  if (isLoading) {
    return (
      <SettingsCard
        title="Ollama AI Service"
        description="Configure the connection to your local Ollama instance for AI-assisted conversions."
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
        title="Ollama AI Service"
        description="Configure the connection to your local Ollama instance for AI-assisted conversions."
      >
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Bot className="h-12 w-12 text-destructive mb-4" />
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
        title="Ollama AI Service"
        description="Configure the connection to your local Ollama instance for AI-assisted conversions."
        actions={
          <SaveButton
            type="submit"
            isSaving={updateMutation.isPending}
            disabled={!isFormValid || !isDirty}
          />
        }
      >
        <div className="space-y-6">
          {/* AI Features Toggle */}
          <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
            <div className="space-y-0.5">
              <Label htmlFor="enabled" className="text-base font-medium">
                Enable AI Features
              </Label>
              <p className="text-sm text-muted-foreground">
                {watchEnabled
                  ? 'AI-assisted stored procedure conversion is enabled'
                  : 'When disabled, the system uses rule-based conversion only'}
              </p>
            </div>
            <Controller
              name="enabled"
              control={control}
              render={({ field }) => (
                <Switch
                  id="enabled"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          {/* Info Banner when disabled */}
          {!watchEnabled && (
            <div className="flex items-start gap-3 p-3 rounded-md border border-blue-200 bg-blue-50">
              <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
              <p className="text-sm text-blue-700">
                AI features are disabled. The system will use rule-based conversion for stored
                procedures. Enable AI features for more intelligent analysis and suggestions.
              </p>
            </div>
          )}

          {/* Host URL */}
          <div className="space-y-2">
            <Label htmlFor="host_url">
              Host URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="host_url"
              placeholder="http://localhost:11434"
              disabled={!watchEnabled}
              {...register('host_url')}
              aria-invalid={!!errors.host_url}
              className={!watchEnabled ? 'opacity-50' : ''}
            />
            {errors.host_url && (
              <p className="text-sm text-destructive">{errors.host_url.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              The URL of your Ollama instance (default: http://localhost:11434)
            </p>
          </div>

          {/* Model Name */}
          <div className="space-y-2">
            <Label htmlFor="model_name">
              Model <span className="text-destructive">*</span>
            </Label>
            <Select
              id="model_name"
              disabled={!watchEnabled}
              {...register('model_name')}
              className={!watchEnabled ? 'opacity-50' : ''}
            >
              {MODEL_SUGGESTIONS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                  {model.recommended ? ' (Recommended)' : ''}
                </option>
              ))}
            </Select>
            {errors.model_name && (
              <p className="text-sm text-destructive">{errors.model_name.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              {MODEL_SUGGESTIONS.find((m) => m.value === watchModelName)?.description ||
                'Select a model for AI-assisted conversion'}
            </p>
          </div>

          {/* Custom Model Input */}
          <div className="space-y-2">
            <Label htmlFor="custom_model">Or enter custom model name</Label>
            <Input
              id="custom_model"
              placeholder="e.g., deepseek-coder:6.7b"
              disabled={!watchEnabled}
              onChange={(e) => {
                if (e.target.value) {
                  reset({ ...watch(), model_name: e.target.value }, { keepDirty: true })
                }
              }}
              className={!watchEnabled ? 'opacity-50' : ''}
            />
            <p className="text-xs text-muted-foreground">
              Enter a custom model name if your model is not in the dropdown
            </p>
          </div>

          {/* Timeout */}
          <div className="space-y-2">
            <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
            <Input
              id="timeout_seconds"
              type="number"
              min={1}
              max={300}
              disabled={!watchEnabled}
              {...register('timeout_seconds', { valueAsNumber: true })}
              aria-invalid={!!errors.timeout_seconds}
              className={!watchEnabled ? 'opacity-50' : ''}
            />
            {errors.timeout_seconds && (
              <p className="text-sm text-destructive">{errors.timeout_seconds.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Maximum time to wait for AI responses (1-300 seconds)
            </p>
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

export default OllamaSettings
