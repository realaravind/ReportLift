/**
 * Auth State Store - Manages authentication state and user session
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '@/lib/api'

interface UserInfo {
  identity: string
  username: string
  domain: string
}

interface LoginCredentials {
  username: string
  password: string
  domain: string
}

interface AuthState {
  // Auth state
  token: string | null
  user: UserInfo | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  clearError: () => void
  setToken: (token: string, user: UserInfo) => void
}

interface LoginResponse {
  data: {
    access_token: string
    token_type: string
    expires_in: number
    user: UserInfo
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Login action
      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null })

        try {
          const response = await api.post<LoginResponse>('/api/v1/auth/login', credentials)
          const { access_token, user } = response.data.data

          set({
            token: access_token,
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: { message?: string } } } }
          const message =
            error.response?.data?.detail?.message || 'Login failed. Please try again.'

          set({
            token: null,
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: message,
          })

          throw new Error(message)
        }
      },

      // Logout action
      logout: () => {
        const { token } = get()

        // Call logout endpoint if we have a token (fire and forget)
        if (token) {
          api.post('/api/v1/auth/logout').catch(() => {
            // Ignore errors - we're logging out anyway
          })
        }

        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        })
      },

      // Clear error
      clearError: () => set({ error: null }),

      // Set token directly (for restoring session)
      setToken: (token: string, user: UserInfo) => {
        set({
          token,
          user,
          isAuthenticated: true,
          error: null,
        })
      },
    }),
    {
      name: 'reportlift-auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
