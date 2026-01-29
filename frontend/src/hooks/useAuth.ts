/**
 * useAuth Hook - Provides authentication functionality with navigation
 */

import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

interface LoginCredentials {
  username: string
  password: string
  domain: string
}

export function useAuth() {
  const navigate = useNavigate()
  const {
    token,
    user,
    isAuthenticated,
    isLoading,
    error,
    login: storeLogin,
    logout: storeLogout,
    clearError,
  } = useAuthStore()

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      await storeLogin(credentials)
      navigate('/')
    },
    [storeLogin, navigate]
  )

  const logout = useCallback(() => {
    storeLogout()
    navigate('/login')
  }, [storeLogout, navigate])

  return {
    token,
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    clearError,
  }
}
