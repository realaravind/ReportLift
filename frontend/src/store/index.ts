/**
 * Zustand store for client-side state management
 */

import { create } from 'zustand'

interface AppState {
  // Application state
  isInitialized: boolean
  setInitialized: (value: boolean) => void

  // User state (will be expanded with authentication)
  user: null | { id: string; name: string; email: string }
  setUser: (user: AppState['user']) => void
  clearUser: () => void

  // UI state
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Application state
  isInitialized: false,
  setInitialized: (value) => set({ isInitialized: value }),

  // User state
  user: null,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),

  // UI state
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
