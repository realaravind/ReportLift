/**
 * React Query hooks for TODO operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { api } from '@/lib/api'
import type {
  TodoItem,
  TodoListResponse,
  EmptyTodoListResponse,
  TodoListSummary,
} from '@/types/analysis'

// Query keys
export const TODO_QUERY_KEY = ['todos']

interface ErrorDetail {
  code: string
  message: string
}

/**
 * Get TODO items for an analysis
 */
export function useTodosForAnalysis(
  analysisId: number | null,
  includeResolved = true,
  enabled = true
) {
  return useQuery<
    TodoListResponse | EmptyTodoListResponse,
    AxiosError<{ detail: ErrorDetail }>
  >({
    queryKey: [...TODO_QUERY_KEY, 'analysis', analysisId, { includeResolved }],
    queryFn: async () => {
      const response = await api.get<TodoListResponse | EmptyTodoListResponse>(
        `/api/todos/analysis/${analysisId}`,
        {
          params: { include_resolved: includeResolved },
        }
      )
      return response.data
    },
    enabled: enabled && !!analysisId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Get TODO summary for an analysis
 */
export function useTodoSummary(analysisId: number | null, enabled = true) {
  return useQuery<TodoListSummary, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...TODO_QUERY_KEY, 'analysis', analysisId, 'summary'],
    queryFn: async () => {
      const response = await api.get<TodoListSummary>(
        `/api/todos/analysis/${analysisId}/summary`
      )
      return response.data
    },
    enabled: enabled && !!analysisId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Get a single TODO item
 */
export function useTodoItem(todoId: number | null, enabled = true) {
  return useQuery<TodoItem, AxiosError<{ detail: ErrorDetail }>>({
    queryKey: [...TODO_QUERY_KEY, todoId],
    queryFn: async () => {
      const response = await api.get<TodoItem>(`/api/todos/${todoId}`)
      return response.data
    },
    enabled: enabled && !!todoId,
    staleTime: 5 * 60 * 1000,
  })
}

interface UpdateTodoVariables {
  todoId: number
  isResolved: boolean
}

/**
 * Mutation hook for updating TODO items
 */
export function useUpdateTodo() {
  const queryClient = useQueryClient()

  return useMutation<TodoItem, AxiosError<{ detail: ErrorDetail }>, UpdateTodoVariables>({
    mutationFn: async ({ todoId, isResolved }) => {
      const response = await api.patch<TodoItem>(`/api/todos/${todoId}`, {
        is_resolved: isResolved,
      })
      return response.data
    },
    onSuccess: () => {
      // Refetch to ensure cache is in sync
      queryClient.invalidateQueries({ queryKey: TODO_QUERY_KEY })
      // Also invalidate analysis queries since todo counts affect display
      queryClient.invalidateQueries({ queryKey: ['analysis'] })
    },
  })
}

/**
 * Quick resolve TODO mutation
 */
export function useResolveTodo() {
  const queryClient = useQueryClient()

  return useMutation<TodoItem, AxiosError<{ detail: ErrorDetail }>, number>({
    mutationFn: async (todoId) => {
      const response = await api.post<TodoItem>(`/api/todos/${todoId}/resolve`)
      return response.data
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TODO_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ['analysis'] })
    },
  })
}

/**
 * Quick unresolve TODO mutation
 */
export function useUnresolveTodo() {
  const queryClient = useQueryClient()

  return useMutation<TodoItem, AxiosError<{ detail: ErrorDetail }>, number>({
    mutationFn: async (todoId) => {
      const response = await api.post<TodoItem>(`/api/todos/${todoId}/unresolve`)
      return response.data
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: TODO_QUERY_KEY })
      queryClient.invalidateQueries({ queryKey: ['analysis'] })
    },
  })
}

/**
 * Helper function to check if todos response has items
 */
export function hasTodos(
  response: TodoListResponse | EmptyTodoListResponse | undefined
): response is TodoListResponse {
  return !!response && 'items' in response && Array.isArray(response.items) && response.items.length > 0
}

/**
 * Get unresolved count from todos response
 */
export function getUnresolvedCount(
  response: TodoListResponse | EmptyTodoListResponse | undefined
): number {
  if (!response) return 0
  return response.summary?.unresolved_count ?? 0
}
