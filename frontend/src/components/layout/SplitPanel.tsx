/**
 * SplitPanel Component - Main layout wrapper with responsive behavior
 */

import { useEffect, useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { MainContent } from './MainContent'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useUIStore } from '@/store/uiStore'

interface SplitPanelProps {
  children?: React.ReactNode
  onFolderSelect?: (path: string) => void
}

export function SplitPanel({ children, onFolderSelect }: SplitPanelProps) {
  const { mobileDrawerOpen, setMobileDrawerOpen } = useUIStore()
  const [isMobile, setIsMobile] = useState(false)

  // Handle responsive behavior
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024)
    }

    // Check on mount
    checkMobile()

    // Add resize listener
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Close mobile drawer on navigation
  useEffect(() => {
    if (!isMobile && mobileDrawerOpen) {
      setMobileDrawerOpen(false)
    }
  }, [isMobile, mobileDrawerOpen, setMobileDrawerOpen])

  return (
    <div className="flex min-h-screen flex-col">
      {/* Fixed header */}
      <Header />

      {/* Main content area below header */}
      <div className="flex flex-1 pt-16">
        {/* Desktop sidebar - hidden on mobile */}
        {!isMobile && <Sidebar onFolderSelect={onFolderSelect} />}

        {/* Mobile drawer - Sheet component */}
        {isMobile && (
          <Sheet open={mobileDrawerOpen} onOpenChange={setMobileDrawerOpen}>
            <SheetContent side="left" className="w-[280px] p-0">
              <SheetHeader className="p-4 border-b">
                <SheetTitle>Navigation</SheetTitle>
              </SheetHeader>
              <Sidebar className="border-r-0 w-full" onFolderSelect={onFolderSelect} />
            </SheetContent>
          </Sheet>
        )}

        {/* Main content area */}
        <MainContent>{children}</MainContent>
      </div>
    </div>
  )
}
