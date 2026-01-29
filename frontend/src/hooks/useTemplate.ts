/**
 * React Query hooks for branding template management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export interface ThemeMetadata {
  name: string | null
  dataColors: string[] | null
  background: string | null
  foreground: string | null
}

export interface TemplateResponse {
  id: number
  name: string
  file_size: number
  file_size_mb: number
  uploaded_at: string
  uploaded_by: string | null
  is_active: boolean
  theme_metadata: ThemeMetadata | null
}

export interface TemplateStatusResponse {
  data: TemplateResponse | null
  is_configured: boolean
  message: string | null
}

export interface TemplateUploadResponse {
  data: TemplateResponse
  message: string
  replaced_existing: boolean
}

export interface TemplateDeleteResponse {
  id: number
  deleted: boolean
  message: string
}

const TEMPLATE_KEY = ['templates', 'current']

/**
 * Hook to fetch current template status
 */
export function useTemplateStatus() {
  return useQuery<TemplateStatusResponse>({
    queryKey: TEMPLATE_KEY,
    queryFn: async () => {
      const response = await api.get<TemplateStatusResponse>('/api/v1/templates/current')
      return response.data
    },
  })
}

/**
 * Hook to upload a new template
 */
export function useUploadTemplate() {
  const queryClient = useQueryClient()

  return useMutation<TemplateUploadResponse, Error, { file: File; replaceExisting?: boolean }>({
    mutationFn: async ({ file, replaceExisting = true }) => {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post<TemplateUploadResponse>(
        `/api/v1/templates?replace_existing=${replaceExisting}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      return response.data
    },
    onSuccess: (data) => {
      // Update the cache with the new template
      queryClient.setQueryData<TemplateStatusResponse>(TEMPLATE_KEY, {
        data: data.data,
        is_configured: true,
        message: null,
      })
    },
  })
}

/**
 * Hook to delete a template
 */
export function useDeleteTemplate() {
  const queryClient = useQueryClient()

  return useMutation<TemplateDeleteResponse, Error, number>({
    mutationFn: async (templateId: number) => {
      const response = await api.delete<TemplateDeleteResponse>(`/api/v1/templates/${templateId}`)
      return response.data
    },
    onSuccess: () => {
      // Update the cache to reflect no template
      queryClient.setQueryData<TemplateStatusResponse>(TEMPLATE_KEY, {
        data: null,
        is_configured: false,
        message: 'No branding template configured',
      })
    },
  })
}

/**
 * Hook to download a template
 */
export function useDownloadTemplate() {
  return useMutation<void, Error, { templateId: number; filename: string }>({
    mutationFn: async ({ templateId, filename }) => {
      const response = await api.get(`/api/v1/templates/${templateId}/download`, {
        responseType: 'blob',
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    },
  })
}

/**
 * Validation helpers
 */
export const TEMPLATE_MAX_SIZE_MB = 50
export const TEMPLATE_MAX_SIZE_BYTES = TEMPLATE_MAX_SIZE_MB * 1024 * 1024

export function validateTemplateFile(file: File): { valid: boolean; error?: string } {
  // Check extension
  if (!file.name.toLowerCase().endsWith('.pbit')) {
    return { valid: false, error: 'Only .pbit files are accepted' }
  }

  // Check size
  if (file.size > TEMPLATE_MAX_SIZE_BYTES) {
    return { valid: false, error: `File size exceeds ${TEMPLATE_MAX_SIZE_MB}MB limit` }
  }

  if (file.size === 0) {
    return { valid: false, error: 'File is empty' }
  }

  return { valid: true }
}
