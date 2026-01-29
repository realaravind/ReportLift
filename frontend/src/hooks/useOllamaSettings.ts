/**
 * React Query hooks for Ollama settings management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface OllamaSettings {
  host_url: string
  model_name: string
  enabled: boolean
  timeout_seconds: number
  updated_at: string | null
}

export interface OllamaSettingsUpdateRequest {
  host_url: string
  model_name: string
  enabled: boolean
  timeout_seconds: number
}

const OLLAMA_SETTINGS_KEY = ['settings', 'ollama']

/**
 * Hook to fetch Ollama settings
 */
export function useOllamaSettings() {
  return useQuery<OllamaSettings>({
    queryKey: OLLAMA_SETTINGS_KEY,
    queryFn: async () => {
      const response = await api.get<OllamaSettings>('/api/v1/settings/ollama')
      return response.data
    },
  })
}

/**
 * Hook to update Ollama settings
 */
export function useUpdateOllamaSettings() {
  const queryClient = useQueryClient()

  return useMutation<OllamaSettings, Error, OllamaSettingsUpdateRequest>({
    mutationFn: async (data: OllamaSettingsUpdateRequest) => {
      const response = await api.put<OllamaSettings>('/api/v1/settings/ollama', data)
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new settings
      queryClient.setQueryData(OLLAMA_SETTINGS_KEY, data)
    },
  })
}

/**
 * Suggested models for the dropdown
 */
export const MODEL_SUGGESTIONS = [
  {
    value: 'codellama:13b',
    label: 'CodeLlama 13B',
    recommended: true,
    description: 'Best for code analysis and generation',
  },
  {
    value: 'codellama:7b',
    label: 'CodeLlama 7B',
    recommended: false,
    description: 'Faster, good for simpler tasks',
  },
  {
    value: 'llama2:13b',
    label: 'Llama 2 13B',
    recommended: false,
    description: 'General purpose, good reasoning',
  },
  {
    value: 'mistral:7b',
    label: 'Mistral 7B',
    recommended: false,
    description: 'Fast and efficient',
  },
]
