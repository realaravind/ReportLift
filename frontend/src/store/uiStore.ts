/**
 * UI State Store - Manages sidebar collapse state and other UI preferences
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Report type for selected report
export interface SelectedReport {
  id: string
  name: string
  path: string
  description: string | null
  modified_date: string | null
  size_bytes: number
  created_by: string | null
}

interface UIState {
  // Sidebar state
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void

  // Mobile drawer state
  mobileDrawerOpen: boolean
  setMobileDrawerOpen: (open: boolean) => void
  toggleMobileDrawer: () => void

  // Selected folder path
  selectedFolderPath: string | null
  setSelectedFolderPath: (path: string | null) => void

  // Selected report
  selectedReport: SelectedReport | null
  setSelectedReport: (report: SelectedReport | null) => void
  clearSelection: () => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar state - persisted to localStorage
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Mobile drawer state - not persisted
      mobileDrawerOpen: false,
      setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
      toggleMobileDrawer: () =>
        set((state) => ({ mobileDrawerOpen: !state.mobileDrawerOpen })),

      // Selected folder path - not persisted
      selectedFolderPath: null,
      setSelectedFolderPath: (path) =>
        set({ selectedFolderPath: path, selectedReport: null }),

      // Selected report - not persisted
      selectedReport: null,
      setSelectedReport: (report) => set({ selectedReport: report }),
      clearSelection: () => set({ selectedReport: null }),
    }),
    {
      name: 'reportlift-ui-storage',
      partialize: (state) => ({ sidebarCollapsed: state.sidebarCollapsed }),
    }
  )
)

// Convenience hooks
export const useSelectedReport = () => useUIStore((state) => state.selectedReport)
export const useSelectedFolderPath = () => useUIStore((state) => state.selectedFolderPath)
